"""Intraday price bars from yfinance: download, lock-filter in memory, merge into a local store, report coverage.

Two stores, both under `$SM_DATA_DIR/lag/` and never committed (they are third-party downloads):

- `bars_1h.parquet`: hourly bars, 12 May to 22 June 2026, for the pilot;
- `bars_15m.parquet`: 15-minute bars, 2 October to 23 November 2026, for the definitive run.
  yfinance serves 15-minute bars for about 60 days only, so this store is filled by repeated runs
  of `python -m lag.scripts.collect_15m` while the period is live.

Rows are keyed by (ticker, bar start). Bars are regular-session only (no pre- or post-market),
split- and dividend-adjusted (yfinance `auto_adjust=True`), stamped by their start in UTC with the
session date in New York time. A re-download never changes a bar already in the store: the first
value seen is kept, and the number of overlapping bars whose values differ is recorded in the
manifest (L4), so the store and its hash only grow.
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from .config import BAR_MINUTES, NY
from .lock import assert_allowed, drop_outside

COLS = ["ticker", "ts", "session", "open", "high", "low", "close", "volume", "regular"]
PRICE_COLS = ["open", "high", "low", "close"]


def yf_symbol(ticker: str) -> str:
    return ticker.replace(".", "-")


def regular_mask(ts: pd.Series, sessions: list[date]) -> np.ndarray:
    """True where a bar starts inside a regular NYSE session [open, close)."""
    from .data import session_bounds
    if not len(ts):
        return np.zeros(0, dtype=bool)
    b = np.array([[o.value, c.value] for o, c in (session_bounds(d) for d in sessions)])
    t = pd.to_datetime(ts, utc=True).to_numpy("datetime64[ns]").astype(np.int64)
    i = np.searchsorted(b[:, 0], t, side="right") - 1
    ok = i >= 0
    out = np.zeros(len(t), dtype=bool)
    out[ok] = t[ok] < b[i[ok], 1]
    return out


def download(tickers: list[str], interval: str, start: date, end: date, chunk: int = 50,
             prepost: bool = False, log=print) -> pd.DataFrame:
    """Bars for [start, end) at `interval` ("1h" or "15m"); regular-session bars only, or with
    pre- and post-market bars too when `prepost` is set (L18). Every bar carries `regular`, True
    when it starts inside a NYSE session. Returns the frame in memory only; nothing is written here."""
    import yfinance as yf

    from .data import calendar

    frames = []
    sym = {yf_symbol(t): t for t in tickers}
    syms = list(sym)
    for i in range(0, len(syms), chunk):
        part = syms[i:i + chunk]
        raw = yf.download(part, interval=interval, start=str(start), end=str(end), auto_adjust=True,
                          prepost=prepost, actions=False, group_by="ticker", progress=False, threads=False)
        for s in part:
            if isinstance(raw.columns, pd.MultiIndex):
                if s not in raw.columns.get_level_values(0):
                    continue
                d = raw[s]
            else:
                d = raw
            d = d.dropna(how="all")
            if d.empty:
                continue
            d = d.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]].copy()
            idx = pd.DatetimeIndex(d.index)
            idx = idx.tz_localize(NY) if idx.tz is None else idx.tz_convert(NY)
            d["ticker"] = sym[s]
            d["session"] = idx.date
            d["ts"] = idx.tz_convert("UTC")
            frames.append(d.reset_index(drop=True))
        log(f"  downloaded {min(i + chunk, len(syms))}/{len(syms)} tickers")
    if not frames:
        return pd.DataFrame(columns=COLS)
    out = pd.concat(frames, ignore_index=True)
    out["ts"] = pd.to_datetime(out["ts"], utc=True)
    sess = [d.date() for d in calendar().sessions_in_range(pd.Timestamp(start) - pd.Timedelta(days=1),
                                                            pd.Timestamp(end) + pd.Timedelta(days=1))]
    out["regular"] = regular_mask(out["ts"], sess)
    if not prepost:
        out = out[out["regular"]]
    return out[COLS].sort_values(["ticker", "ts"]).reset_index(drop=True)


def load_store(path: Path) -> pd.DataFrame:
    """The store; a store written before L18 has no `regular` column and held regular bars only."""
    if not path.exists():
        return pd.DataFrame(columns=COLS)
    df = pd.read_parquet(path)
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    df["session"] = pd.to_datetime(df["session"]).dt.date
    if "regular" not in df.columns:
        df["regular"] = True
    df["regular"] = df["regular"].astype(bool)
    return assert_allowed(df[COLS], "ts", f"bar store {path.name}", "prices")


def merge_store(new: pd.DataFrame, path: Path) -> dict:
    """Lock-filter `new`, add bars whose (ticker, ts) is not yet stored, write atomically, and
    return counts: rows dropped by the lock, added, already present, and present with different values."""
    kept, dropped = drop_outside(new, "ts", "prices")
    assert_allowed(kept, "ts", "new bars", "prices")
    if "regular" not in kept.columns:
        kept = kept.assign(regular=True)
    old = load_store(path)
    key = ["ticker", "ts"]
    if len(old):
        m = kept.merge(old[key + PRICE_COLS], on=key, how="left", suffixes=("", "_old"), indicator=True)
        present = m["_merge"] == "both"
        differ = present & (np.abs(m[PRICE_COLS].to_numpy(float) - m[[c + "_old" for c in PRICE_COLS]]
                                   .to_numpy(float)) > 1e-6).any(axis=1)
        add = kept.loc[~present.to_numpy()]
        n_present, n_differ = int(present.sum()), int(differ.sum())
    else:
        add, n_present, n_differ = kept, 0, 0
    merged = (pd.concat([old, add], ignore_index=True) if len(old) else add.copy())[COLS].drop_duplicates(key)
    merged = merged.sort_values(key).reset_index(drop=True)
    assert_allowed(merged, "ts", f"bar store {path.name}", "prices")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".parquet.tmp")
    merged.to_parquet(tmp, index=False)
    os.replace(tmp, path)
    return {"rows_dropped_by_lock": dropped, "rows_added": int(len(add)), "rows_already_present": n_present,
            "rows_present_with_different_values": n_differ, "rows_in_store": int(len(merged))}


def store_hash(path: Path) -> str:
    import hashlib
    df = load_store(path)
    canon = df.sort_values(["ticker", "ts"]).reset_index(drop=True)
    return hashlib.sha256(canon.to_csv(index=False, float_format="%.6f").encode()).hexdigest()[:12]


def expected_bars(sessions: list[date], bar: str) -> dict[date, int]:
    """Bars per session from the NYSE open and close (7 hourly bars, 26 fifteen-minute bars on a full day)."""
    from .data import session_bounds
    mins = BAR_MINUTES[bar]
    return {d: int(np.ceil((session_bounds(d)[1] - session_bounds(d)[0]) / pd.Timedelta(minutes=mins)))
            for d in sessions}


def coverage(bars: pd.DataFrame, sessions: list[date], bar: str, universe: list[str],
             through: date | None = None) -> dict:
    """Coverage of the store against the sessions already closed (`through`: the last session to
    count; by default every session whose close is before now). Returns per-ticker and per-session
    tables and a summary."""
    from .data import session_bounds
    if through is None:
        now = pd.Timestamp.now(tz="UTC")
        done = [d for d in sessions if session_bounds(d)[1] <= now]
        through = done[-1] if done else sessions[0] - timedelta(days=1)
    else:
        done = [d for d in sessions if d <= through]
    exp = expected_bars(done, bar)
    reg = bars["regular"].astype(bool) if "regular" in bars.columns else pd.Series(True, index=bars.index)
    in_scope = bars["session"].isin(done) & bars["ticker"].isin(universe)
    n_extended = int((in_scope & ~reg).sum())
    bars = bars[in_scope & reg]
    cnt = bars.groupby(["ticker", "session"]).size()
    grid = cnt.unstack("session").reindex(index=universe, columns=done).fillna(0).astype(int)
    exp_row = pd.Series(exp)
    missing = (exp_row - grid).clip(lower=0)
    per_ticker = pd.DataFrame({
        "sessions_with_bars": (grid > 0).sum(axis=1),
        "sessions_complete": (missing == 0).sum(axis=1),
        "bars": grid.sum(axis=1),
        "bars_expected": int(exp_row.sum()),
        "bars_missing": missing.sum(axis=1),
    })
    per_session = pd.DataFrame({
        "bars_expected_per_ticker": exp_row,
        "tickers_with_bars": (grid > 0).sum(axis=0),
        "tickers_complete": (missing == 0).sum(axis=0),
        "bars_missing": missing.sum(axis=0),
    })
    gaps = missing.stack()
    gaps = gaps[gaps > 0].rename("bars_missing").reset_index()
    return {"through": through, "sessions_done": len(done), "sessions_total": len(sessions),
            "tickers": len(universe), "tickers_complete": int((per_ticker["bars_missing"] == 0).sum()),
            "bars": int(grid.to_numpy().sum()), "bars_expected": int(exp_row.sum() * len(universe)),
            "bars_extended": n_extended,
            "per_ticker": per_ticker, "per_session": per_session, "gaps": gaps}


def coverage_markdown(cov: dict, title: str, store_name: str, manifest: dict | None = None) -> str:
    pt, ps, gaps = cov["per_ticker"], cov["per_session"], cov["gaps"]
    lines = [f"# {title}", "",
             f"Store: `$SM_DATA_DIR/lag/{store_name}` (local, not committed). "
             f"Coverage is measured against NYSE sessions up to {cov['through']} "
             f"({cov['sessions_done']} of the period's {cov['sessions_total']} sessions so far).", ""]
    if manifest:
        lines += [f"Last collection: {manifest.get('last_run_utc')} (yfinance {manifest.get('yfinance')}); "
                  f"{manifest.get('runs', 0)} run(s) so far; last run added {manifest.get('last_rows_added')} bars, "
                  f"found {manifest.get('last_rows_already_present')} already stored, "
                  f"{manifest.get('last_rows_present_with_different_values')} of those with different values "
                  f"(the stored values are kept).", ""]
    lines += ["| | value |", "|---|---|",
              f"| tickers | {cov['tickers']} |",
              f"| tickers with every expected bar | {cov['tickers_complete']} |",
              f"| bars stored (universe, sessions done) | {cov['bars']:,} |",
              f"| bars expected | {cov['bars_expected']:,} |",
              f"| bars missing | {cov['bars_expected'] - cov['bars']:,} |",
              f"| extended-hours bars stored (pre- and post-market, L18; not counted above) | {cov.get('bars_extended', 0):,} |", ""]
    lines += ["## By session", "", "| session | bars per ticker expected | tickers with bars | tickers complete | bars missing |",
              "|---|---|---|---|---|"]
    for d, r in ps.iterrows():
        lines.append(f"| {d} | {r.bars_expected_per_ticker} | {r.tickers_with_bars} | {r.tickers_complete} | {r.bars_missing} |")
    inc = pt[pt["bars_missing"] > 0].sort_values("bars_missing", ascending=False)
    lines += ["", "## Tickers with missing bars", ""]
    if len(inc):
        lines += ["| ticker | sessions with bars | sessions complete | bars | bars missing |", "|---|---|---|---|---|"]
        for t, r in inc.iterrows():
            lines.append(f"| {t} | {r.sessions_with_bars} | {r.sessions_complete} | {r.bars} | {r.bars_missing} |")
    else:
        lines.append("None.")
    lines += ["", f"Gaps (ticker-sessions with fewer bars than expected): {len(gaps)}.", ""]
    return "\n".join(lines)


def write_manifest(path: Path, stats: dict, extra: dict | None = None) -> dict:
    import yfinance as yf
    m = json.loads(path.read_text()) if path.exists() else {"runs": 0}
    m["runs"] = m.get("runs", 0) + 1
    m["last_run_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    m["yfinance"] = yf.__version__
    for k, v in stats.items():
        m["last_" + k] = v
    m.setdefault("history", []).append({"run_utc": m["last_run_utc"], **stats, **(extra or {})})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(m, indent=1, sort_keys=True, default=str))
    return m


def collection_window(period_start: date, period_end: date, today: date | None = None,
                      keep_days: int = 58) -> tuple[date, date]:
    """[start, end) to request from yfinance: the period, cut to what yfinance still serves."""
    today = today or datetime.now(timezone.utc).date()
    start = max(period_start, today - timedelta(days=keep_days))
    end = min(period_end + timedelta(days=1), today + timedelta(days=1))
    return start, end
