"""Loaders for the universe, sessions, sentiment ticks and prices, all behind the data lock.

The lock (BRIEF.md ground rule 2) is the first experiment's: nothing stamped after
2026-06-22 23:59:59.999999 UTC may be stored or analysed. Writers filter with
`drop_after_lock`; every loader asserts with `assert_locked` and raises
`HoldoutViolation` on any later row. Neither has a switch to turn it off.
"""

from __future__ import annotations

import hashlib
from datetime import date
from pathlib import Path

import exchange_calendars as xc
import numpy as np
import pandas as pd

from filter_eval import ingest, prices as fe_prices
from filter_eval.holdout import HoldoutViolation, assert_date_locked, assert_locked, drop_after_lock

from .config import DATA_END, EXO_WEIGHTS, PRICE_FILE, TICK_DIR, UNIVERSE_FILE

__all__ = ["HoldoutViolation", "assert_locked", "drop_after_lock", "assert_date_locked",
           "universe", "sessions", "load_ticks", "load_prices", "add_score_exo", "file_hash"]

_CAL = None


def calendar():
    global _CAL
    if _CAL is None:
        _CAL = xc.get_calendar("XNYS")
    return _CAL


def universe(path: Path = UNIVERSE_FILE) -> list[str]:
    """The first experiment's used universe (473 names)."""
    return sorted(pd.read_csv(path)["ticker"])


def sessions(start: date, end: date = DATA_END) -> list[date]:
    """NYSE sessions in [start, end]; `end` may not pass the lock."""
    assert_date_locked(end, "session range end")
    return [s.date() for s in calendar().sessions_in_range(pd.Timestamp(start), pd.Timestamp(end))]


def session_close_utc(d: date) -> pd.Timestamp:
    return calendar().session_close(pd.Timestamp(d)).tz_convert("UTC")


def add_score_exo(df: pd.DataFrame) -> pd.DataFrame:
    """Reconstruct score_exo per tick: narrative/influencer/macro at 0.30/0.25/0.10,
    renormalised over the channels present (NaN if none)."""
    cols = list(EXO_WEIGHTS)
    w = np.array([EXO_WEIGHTS[c] for c in cols])
    vals = df[cols].to_numpy(dtype=float)
    present = ~np.isnan(vals)
    wsum = (present * w).sum(axis=1)
    num = np.nansum(vals * w, axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        df = df.copy()
        df["score_exo"] = np.where(wsum > 0, num / wsum, np.nan)
    return df


def load_ticks(tickers: list[str] | None = None, tick_dir: Path = TICK_DIR) -> pd.DataFrame:
    """All stored ticks (ticker, ts, score, the four channels, score_exo); lock-asserted."""
    if not tick_dir.exists():
        raise FileNotFoundError(f"sentiment tick cache not found at {tick_dir}; set SM_DATA_DIR")
    df = ingest.load_ticks(tickers, tick_dir=tick_dir)
    assert_locked(df, "ts", "sentiment ticks")
    df = df[["ticker", "ts", "score", "market", "narrative", "influencer", "macro"]].copy()
    df["score"] = df["score"].astype("float64")
    return add_score_exo(df).sort_values(["ticker", "ts"]).reset_index(drop=True)


def load_prices(path: Path = PRICE_FILE) -> pd.DataFrame:
    """Daily adjusted bars (ticker, date, open, high, low, close, volume); lock-asserted."""
    if not path.exists():
        raise FileNotFoundError(f"price cache not found at {path}; set SM_DATA_DIR")
    df = fe_prices.load(path)
    return assert_locked(df, "date", "prices")


def lock_filter_events(df: pd.DataFrame, col: str) -> tuple[pd.DataFrame, int]:
    """Drop event rows stamped after the lock. Timezone-aware stamps are compared in UTC;
    naive stamps and plain dates are read as UTC (dates as that UTC day)."""
    if not len(df):
        return df.copy(), 0
    return drop_after_lock(df.reset_index(drop=True), col)


def file_hash(paths: list[Path]) -> str:
    h = hashlib.sha256()
    for p in sorted(paths):
        h.update(p.name.encode())
        h.update(p.read_bytes())
    return h.hexdigest()[:12]
