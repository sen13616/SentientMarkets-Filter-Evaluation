"""Sentiment history pull (Phase 1).

For each candidate ticker, fetch raw history reaching back to 24 April 2026,
drop every row stamped after the lock cutoff in memory, and write the remaining
ticks (all of them, not just the selected daily tick; D1) to one parquet file
per ticker. The manifest records, per ticker, the fetch status and row counts;
for discarded rows it records the count and nothing else.

The pull is resumable: tickers already marked ok with a file on disk are
skipped. A ticker that fails after the client's retries is logged, the pull
carries on, failures are retried in a second pass, and any that still fail are
listed in the manifest and the return value.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable

import pandas as pd

from .api import FetchError
from .config import DATA, WINDOW_START
from .holdout import assert_locked, drop_after_lock

TICK_DIR = DATA / "sentiment" / "ticks"
MANIFEST = DATA / "sentiment" / "manifest.json"

TICK_COLUMNS = ["ticker", "ts", "score", "score_raw", "score_exo_served", "label", "confidence",
                "market", "narrative", "influencer", "macro", "missing_layers"]


def days_needed(today: date | None = None) -> int:
    today = today or datetime.now(timezone.utc).date()
    return (today - WINDOW_START).days + 1


def parse_history(ticker: str, body: dict) -> pd.DataFrame:
    """Flatten a history response into one row per tick."""
    rows = body.get("history") or []
    out = []
    for r in rows:
        sub = r.get("sub_indices") or {}
        out.append({
            "ticker": ticker,
            "ts": r["timestamp"],
            "score": r.get("score"),
            "score_raw": r.get("score_raw"),
            "score_exo_served": r.get("score_exo"),
            "label": r.get("label"),
            "confidence": r.get("confidence"),
            "market": sub.get("market"),
            "narrative": sub.get("narrative"),
            "influencer": sub.get("influencer"),
            "macro": sub.get("macro"),
            "missing_layers": "|".join(sorted(r.get("missing_layers") or [])),
        })
    df = pd.DataFrame(out, columns=TICK_COLUMNS)
    df["ts"] = pd.to_datetime(df["ts"], utc=True, format="ISO8601")
    for c in ["score", "score_raw", "confidence"]:
        df[c] = pd.to_numeric(df[c]).astype("Int64")
    for c in ["score_exo_served", "market", "narrative", "influencer", "macro"]:
        df[c] = pd.to_numeric(df[c]).astype("float64")
    return df.sort_values("ts").reset_index(drop=True)


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def _write_ticks(df: pd.DataFrame, path: Path) -> None:
    assert_locked(df, "ts", f"ticks for {path.stem}")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".parquet.tmp")
    df.to_parquet(tmp, index=False)
    os.replace(tmp, path)


def load_manifest(path: Path = MANIFEST) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return {"tickers": {}}


def save_manifest(m: dict, path: Path = MANIFEST) -> None:
    _atomic_write_bytes(path, json.dumps(m, indent=1, sort_keys=True).encode())


def pull(tickers: list[str], client, tick_dir: Path = TICK_DIR, manifest_path: Path = MANIFEST,
         days: int | None = None, log: Callable[[str], None] = print) -> dict:
    """Pull every ticker; returns the manifest. Safe to re-run (resumes)."""
    days = days or days_needed()
    m = load_manifest(manifest_path)
    m.setdefault("tickers", {})
    m["days_param"] = days
    m["lock_cutoff"] = "2026-06-22T23:59:59.999999Z"

    def done(t: str) -> bool:
        e = m["tickers"].get(t)
        return bool(e and e.get("status") == "ok" and (tick_dir / f"{t}.parquet").exists())

    def fetch_one(t: str) -> bool:
        try:
            body, nbytes, secs = client.get_json(f"/v1/sentiment/{t}/history",
                                                 params={"days": days, "interval": "raw"})
            df = parse_history(t, body)
            kept, discarded = drop_after_lock(df, "ts")
            _write_ticks(kept, tick_dir / f"{t}.parquet")
            m["tickers"][t] = {
                "status": "ok", "rows_window": int(len(kept)), "rows_discarded": discarded,
                "first_ts": kept["ts"].min().isoformat() if len(kept) else None,
                "last_ts": kept["ts"].max().isoformat() if len(kept) else None,
                "bytes": nbytes, "seconds": round(secs, 2),
                "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
            ok = True
        except (FetchError, KeyError, ValueError) as e:
            m["tickers"][t] = {"status": "failed", "error": str(e)[:300],
                               "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
            log(f"  FAILED {t}: {str(e)[:120]}")
            ok = False
        save_manifest(m, manifest_path)
        return ok

    todo = [t for t in tickers if not done(t)]
    log(f"pull: {len(tickers)} tickers, {len(tickers) - len(todo)} already done, {len(todo)} to fetch, days={days}")
    failed = []
    for i, t in enumerate(todo, 1):
        if not fetch_one(t):
            failed.append(t)
        if i % 25 == 0 or i == len(todo):
            log(f"  {i}/{len(todo)} fetched, {len(failed)} failed so far")
    if failed:
        log(f"retrying {len(failed)} failed ticker(s)")
        failed = [t for t in failed if not fetch_one(t)]
    m["still_failed"] = failed
    m["completed_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    save_manifest(m, manifest_path)
    if failed:
        log(f"STILL FAILED after retry: {failed}")
    return m


def load_ticks(tickers: list[str] | None = None, tick_dir: Path = TICK_DIR) -> pd.DataFrame:
    """Load stored ticks; raises HoldoutViolation if anything post-window is present."""
    files = sorted(tick_dir.glob("*.parquet"))
    if tickers is not None:
        want = set(tickers)
        files = [f for f in files if f.stem in want]
    df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True) if files else \
        pd.DataFrame(columns=TICK_COLUMNS)
    return assert_locked(df, "ts", "sentiment ticks")


def frame_hash(df: pd.DataFrame, sort_by: list[str]) -> str:
    """Content hash of a frame, independent of row order and file encoding."""
    canon = df.sort_values(sort_by).reset_index(drop=True)
    return hashlib.sha256(canon.to_csv(index=False, float_format="%.10g").encode()).hexdigest()
