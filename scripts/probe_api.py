"""Phase 0 API contract probe.

Prints schema summaries and statistics to stdout. Writes nothing to disk: the
probe is the only permitted contact with post-22-June data, and nothing from it
may be stored except the hand-written API_FINDINGS.md.

The API key is read from .env (SENTIENT_API_KEY) and never printed.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

BASE = "https://sentimentapi-p.up.railway.app"
TICKERS = ["AAPL", "JPM", "XOM"]
# Seed-universe names that stopped trading before the window ended; used only
# to see how history behaves for a delisted ticker.
DELISTED_CANDIDATES = ["HES", "PXD", "ANSS"]
MIN_INTERVAL_S = 2.5  # <= 24 requests/minute, under the 30/min ceiling
MAX_RETRIES = 5

_last_request = 0.0


def get(path: str, params: dict | None = None, auth: bool = True):
    """One throttled GET with backoff on 429/5xx. Returns (response, seconds)."""
    global _last_request
    headers = {}
    if auth:
        key = os.environ.get("SENTIENT_API_KEY")
        if not key:
            raise RuntimeError("SENTIENT_API_KEY not set in .env")
        headers["Authorization"] = f"Bearer {key}"
    for attempt in range(MAX_RETRIES):
        wait = MIN_INTERVAL_S - (time.monotonic() - _last_request)
        if wait > 0:
            time.sleep(wait)
        t0 = time.monotonic()
        r = requests.get(BASE + path, params=params, headers=headers, timeout=120)
        _last_request = time.monotonic()
        elapsed = _last_request - t0
        if r.status_code == 429 or r.status_code >= 500:
            retry_after = r.headers.get("Retry-After")
            backoff = float(retry_after) if retry_after else 2 ** (attempt + 2)
            print(f"  [{r.status_code}] backing off {backoff:.0f}s", file=sys.stderr)
            time.sleep(backoff)
            continue
        return r, elapsed
    return r, elapsed


def schema(obj, depth: int = 0, max_depth: int = 6):
    """Recursive type summary: dict -> {key: type}, list -> [type of items]."""
    if depth > max_depth:
        return "..."
    if isinstance(obj, dict):
        return {k: schema(v, depth + 1) for k, v in obj.items()}
    if isinstance(obj, list):
        if not obj:
            return "list[empty]"
        # Merge the key sets of dict items so optional fields show up.
        if all(isinstance(x, dict) for x in obj):
            merged: dict = {}
            for x in obj:
                for k, v in x.items():
                    t = schema(v, depth + 2)
                    if k not in merged:
                        merged[k] = t
                    elif merged[k] == "null" and t != "null":
                        merged[k] = f"{t} | null"
                    elif t == "null" and "null" not in str(merged[k]):
                        merged[k] = f"{merged[k]} | null"
            return [merged]
        return [schema(obj[0], depth + 1)]
    if obj is None:
        return "null"
    return type(obj).__name__


def truncate(obj, n_list: int = 2):
    """Shorten lists in an example payload so it can be shown."""
    if isinstance(obj, dict):
        return {k: truncate(v, n_list) for k, v in obj.items()}
    if isinstance(obj, list):
        out = [truncate(x, n_list) for x in obj[:n_list]]
        if len(obj) > n_list:
            out.append(f"... ({len(obj) - n_list} more)")
        return out
    return obj


def show(label: str, r: requests.Response, elapsed: float, example: bool = True,
         with_schema: bool = True):
    print(f"\n=== {label} ===")
    print(f"status={r.status_code} bytes={len(r.content)} seconds={elapsed:.2f} "
          f"content-type={r.headers.get('content-type')}")
    interesting = {k: v for k, v in r.headers.items()
                   if k.lower().startswith(("x-ratelimit", "ratelimit", "retry", "x-cache", "cache"))}
    if interesting:
        print("headers:", interesting)
    try:
        body = r.json()
    except ValueError:
        print("non-JSON body:", r.text[:300])
        return None
    if with_schema:
        print("schema:", json.dumps(schema(body), indent=1))
    if example:
        print("example:", json.dumps(truncate(body), indent=1, default=str)[:4000])
    return body


def find_rows(body):
    """Locate the list of history rows in a history response."""
    if isinstance(body, list):
        return body
    if isinstance(body, dict):
        for k in ("history", "data", "rows", "items", "points", "results"):
            if isinstance(body.get(k), list):
                return body[k]
        for v in body.values():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                return v
    return []


def ts_of(row: dict):
    for k in ("timestamp", "ts", "time", "scored_at", "computed_at", "date", "created_at"):
        if k in row and row[k]:
            try:
                return datetime.fromisoformat(str(row[k]).replace("Z", "+00:00"))
            except ValueError:
                pass
    return None


def history_stats(rows: list[dict]):
    if not rows:
        print("  no rows")
        return
    stamps = [t for t in (ts_of(r) for r in rows) if t]
    print(f"  rows={len(rows)}")
    if stamps:
        print(f"  first={min(stamps).isoformat()} last={max(stamps).isoformat()}")
        gaps = sorted((b - a).total_seconds() / 60 for a, b in zip(sorted(stamps), sorted(stamps)[1:]))
        if gaps:
            print(f"  tick gap minutes: min={gaps[0]:.1f} median={gaps[len(gaps)//2]:.1f} max={gaps[-1]:.1f}")
    # Which numeric fields are integer-valued throughout?
    for k in rows[0]:
        vals = [r.get(k) for r in rows if isinstance(r.get(k), (int, float)) and not isinstance(r.get(k), bool)]
        if vals:
            all_int = all(float(v).is_integer() for v in vals)
            print(f"  {k}: n={len(vals)} min={min(vals)} max={max(vals)} all_integer_valued={all_int}")
    for k in rows[0]:
        vals = [r.get(k) for r in rows]
        if all(isinstance(v, (str, bool)) or v is None for v in vals):
            distinct = sorted({json.dumps(v) for v in vals})
            if len(distinct) <= 12:
                print(f"  {k}: distinct={distinct}")


def exo_check(rows: list[dict]):
    """Compare served score_exo with the reconstruction from sub-indices."""
    w = {"narrative": 0.30, "influencer": 0.25, "macro": 0.10}

    def sub(row, name):
        for container in (row, row.get("sub_indices") or {}, row.get("layers") or {},
                          row.get("subindices") or {}, row.get("components") or {}):
            if isinstance(container, dict):
                for k in (name, f"{name}_score", f"{name}_index", f"score_{name}"):
                    v = container.get(k)
                    if isinstance(v, dict):
                        v = v.get("score") or v.get("value")
                    if isinstance(v, (int, float)):
                        return float(v)
        return None

    diffs = []
    for r in rows:
        served = r.get("score_exo")
        if not isinstance(served, (int, float)):
            continue
        present = {k: sub(r, k) for k in w}
        present = {k: v for k, v in present.items() if v is not None}
        if not present:
            continue
        tot = sum(w[k] for k in present)
        recon = sum(w[k] * v for k, v in present.items()) / tot
        diffs.append(abs(recon - served))
    if diffs:
        diffs.sort()
        print(f"  score_exo reconstruction |diff|: n={len(diffs)} "
              f"median={diffs[len(diffs)//2]:.4f} p95={diffs[int(0.95*(len(diffs)-1))]:.4f} max={diffs[-1]:.4f}")
    else:
        print("  score_exo reconstruction: not possible from these rows (field or sub-indices absent)")


def main():
    load_dotenv()
    have_key = bool(os.environ.get("SENTIENT_API_KEY"))
    print(f"probe run at {datetime.now(timezone.utc).isoformat()} key_present={have_key}")

    r, s = get("/health", auth=False)
    show("GET /health (no auth)", r, s)
    r, s = get("/openapi.json", auth=False)
    spec = show("GET /openapi.json (no auth)", r, s, example=False, with_schema=False)
    if isinstance(spec, dict) and "paths" in spec:
        for p, ops in spec["paths"].items():
            for method, op in ops.items():
                params = [f"{x.get('name')}({x.get('in')})" for x in op.get("parameters", [])]
                print(f"  {method.upper()} {p} params={params}")

    if not have_key:
        print("\nNo key: stopping before authenticated endpoints.")
        return

    r, s = get("/v1/tickers")
    tickers = show("GET /v1/tickers", r, s)
    tick_rows = find_rows(tickers) if tickers is not None else []
    if tick_rows:
        print(f"  ticker entries={len(tick_rows)}")
        for k in tick_rows[0]:
            vals = [t.get(k) for t in tick_rows]
            distinct = {json.dumps(v) for v in vals}
            if len(distinct) <= 12:
                print(f"  {k}: distinct={sorted(distinct)}")
            else:
                print(f"  {k}: {len(distinct)} distinct values, nulls={sum(v is None for v in vals)}")

    for t in TICKERS:
        r, s = get(f"/v1/sentiment/{t}", params={"detail": "full"})
        show(f"GET /v1/sentiment/{t}?detail=full", r, s, example=(t == TICKERS[0]))

    for t in TICKERS:
        r, s = get(f"/v1/sentiment/{t}/history", params={"days": 2, "interval": "raw"})
        body = show(f"GET /v1/sentiment/{t}/history?days=2&interval=raw", r, s, example=(t == TICKERS[0]))
        rows = find_rows(body) if body is not None else []
        history_stats(rows)
        exo_check(rows)

    r, s = get(f"/v1/sentiment/{TICKERS[0]}/history", params={"days": 2, "interval": "daily"})
    body = show(f"GET /v1/sentiment/{TICKERS[0]}/history?days=2&interval=daily", r, s)
    history_stats(find_rows(body) if body is not None else [])

    for t in DELISTED_CANDIDATES:
        r, s = get(f"/v1/sentiment/{t}")
        show(f"GET /v1/sentiment/{t} (delisted candidate)", r, s)
        r, s = get(f"/v1/sentiment/{t}/history", params={"days": 2, "interval": "raw"})
        body = show(f"GET /v1/sentiment/{t}/history?days=2&interval=raw (delisted candidate)", r, s)
        history_stats(find_rows(body) if body is not None else [])

    # Reach-back check for the Phase 0 stop condition: can raw history reach
    # 24 April 2026? One ticker only; only summary statistics are kept.
    days_needed = (datetime.now(timezone.utc).date() - datetime(2026, 4, 24).date()).days + 1
    r, s = get(f"/v1/sentiment/{TICKERS[0]}/history", params={"days": days_needed, "interval": "raw"})
    print(f"\n=== reach-back: {TICKERS[0]} raw days={days_needed} ===")
    print(f"status={r.status_code} bytes={len(r.content)} seconds={s:.2f}")
    try:
        rows = find_rows(r.json())
    except ValueError:
        rows = []
        print("non-JSON body:", r.text[:300])
    history_stats(rows)
    stamps = [t for t in (ts_of(x) for x in rows) if t]
    in_window = [t for t in stamps if datetime(2026, 4, 24, tzinfo=timezone.utc) <= t
                 < datetime(2026, 6, 23, tzinfo=timezone.utc)]
    print(f"  rows in research window (24 Apr - 22 Jun): {len(in_window)}")
    if in_window:
        print(f"  research-window first={min(in_window).isoformat()} last={max(in_window).isoformat()}")
    del rows, stamps, in_window


if __name__ == "__main__":
    main()
