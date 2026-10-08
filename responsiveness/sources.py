"""Event sources from yfinance (BRIEF.md section 3).

For each ticker, three tables are fetched: earnings dates (with EPS estimate,
reported EPS and surprise), analyst rating actions, and insider transactions.
Every table is filtered through the data lock in memory before anything is
written: rows stamped after 22 June 2026 are dropped and only their count is
recorded. The written tables are a local cache under SM_DATA_DIR and are never
committed (they are third-party downloads).
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import pandas as pd

from .config import EVENT_RAW
from .data import assert_locked, lock_filter_events

SOURCES = ("earnings", "ratings", "insider")
MANIFEST = EVENT_RAW / "manifest.json"
EARNINGS_LIMIT = 12          # 12 most recent and upcoming rows; reaches back well before May 2026


def yf_symbol(ticker: str) -> str:
    return ticker.replace(".", "-")


def normalise_earnings(df: pd.DataFrame | None) -> pd.DataFrame:
    cols = ["release_et", "eps_estimate", "eps_reported", "surprise_pct"]
    if df is None or not len(df):
        return pd.DataFrame(columns=cols)
    out = pd.DataFrame({
        "release_et": pd.DatetimeIndex(df.index).tz_convert("America/New_York"),
        "eps_estimate": pd.to_numeric(df.get("EPS Estimate"), errors="coerce").to_numpy(),
        "eps_reported": pd.to_numeric(df.get("Reported EPS"), errors="coerce").to_numpy(),
        "surprise_pct": pd.to_numeric(df.get("Surprise(%)"), errors="coerce").to_numpy(),
    })
    return out[cols]


def normalise_ratings(df: pd.DataFrame | None) -> pd.DataFrame:
    cols = ["grade_ts", "firm", "action", "to_grade", "from_grade"]
    if df is None or not len(df):
        return pd.DataFrame(columns=cols)
    d = df.reset_index()
    return pd.DataFrame({
        "grade_ts": pd.to_datetime(d["GradeDate"]),
        "firm": d.get("Firm"), "action": d.get("Action"),
        "to_grade": d.get("ToGrade"), "from_grade": d.get("FromGrade"),
    })[cols]


def normalise_insider(df: pd.DataFrame | None) -> pd.DataFrame:
    cols = ["start_date", "text", "shares", "value", "position", "ownership"]
    if df is None or not len(df):
        return pd.DataFrame(columns=cols)
    return pd.DataFrame({
        "start_date": pd.to_datetime(df["Start Date"]),
        "text": df.get("Text").fillna("").astype(str),
        "shares": pd.to_numeric(df.get("Shares"), errors="coerce"),
        "value": pd.to_numeric(df.get("Value"), errors="coerce"),
        "position": df.get("Position"), "ownership": df.get("Ownership"),
    })[cols]


TIME_COL = {"earnings": "release_et", "ratings": "grade_ts", "insider": "start_date"}


def fetch_ticker(ticker: str) -> dict[str, pd.DataFrame]:
    import yfinance as yf
    t = yf.Ticker(yf_symbol(ticker))
    return {"earnings": normalise_earnings(t.get_earnings_dates(limit=EARNINGS_LIMIT)),
            "ratings": normalise_ratings(t.upgrades_downgrades),
            "insider": normalise_insider(t.insider_transactions)}


def _write(df: pd.DataFrame, path: Path, col: str) -> None:
    assert_locked(df, col, f"event table {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".parquet.tmp")
    df.to_parquet(tmp, index=False)
    os.replace(tmp, path)


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {"tickers": {}}


def fetch_all(tickers: list[str], fetch: Callable[[str], dict] = fetch_ticker, raw_dir: Path = EVENT_RAW,
              pause_s: float = 0.4, retries: int = 3, log: Callable[[str], None] = print) -> dict:
    """Fetch every ticker's three tables, lock-filter in memory, cache. Resumable."""
    manifest_path = raw_dir / "manifest.json"
    m = json.loads(manifest_path.read_text()) if manifest_path.exists() else {"tickers": {}}
    import yfinance as yf
    m["source"] = f"yfinance {yf.__version__}"
    todo = [t for t in tickers if m["tickers"].get(t, {}).get("status") != "ok"]
    log(f"fetch: {len(tickers)} tickers, {len(tickers) - len(todo)} cached, {len(todo)} to fetch")
    for i, t in enumerate(todo, 1):
        entry: dict = {}
        for attempt in range(retries):
            try:
                tables = fetch(t)
                entry = {"status": "ok"}
                for src, df in tables.items():
                    col = TIME_COL[src]
                    kept, dropped = lock_filter_events(df, col)
                    _write(kept, raw_dir / src / f"{t}.parquet", col)
                    entry[src] = {"rows_returned": int(len(df)), "rows_kept": int(len(kept)),
                                  "rows_dropped_after_lock": dropped,
                                  "earliest": str(kept[col].min()) if len(kept) else None}
                break
            except Exception as e:  # network or parse failure: retry, then record
                entry = {"status": "failed", "error": f"{type(e).__name__}: {str(e)[:200]}"}
                time.sleep(2 * (attempt + 1))
        entry["fetched_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        m["tickers"][t] = entry
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(m, indent=1, sort_keys=True))
        if entry["status"] != "ok":
            log(f"  FAILED {t}: {entry['error']}")
        if i % 25 == 0 or i == len(todo):
            log(f"  {i}/{len(todo)}")
        time.sleep(pause_s)
    return m


def load_source(src: str, tickers: list[str], raw_dir: Path = EVENT_RAW) -> pd.DataFrame:
    """Concatenate one cached source across tickers; lock-asserted."""
    frames = []
    for t in tickers:
        p = raw_dir / src / f"{t}.parquet"
        if p.exists():
            d = pd.read_parquet(p)
            if len(d):
                frames.append(d.assign(ticker=t))
    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["ticker", TIME_COL[src]])
    return assert_locked(df, TIME_COL[src], f"{src} events")
