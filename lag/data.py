"""Loaders for both runs, all behind the three-range lock (lock.py).

Everything this experiment reads comes through here:

- sentiment ticks: the pilot's tick cache (built by the first experiment) or the definitive pull
  made by Experiment 5A's definitive Phase 1, the latter only once the gate is open;
- intraday bars: this experiment's own stores (bars.py), hourly for the pilot and 15-minute for
  the definitive run;
- daily bars and earnings tables: Experiment 5A's caches, for the L-E1 direction and reaction
  sessions;
- the universe and the NYSE calendar: Experiment 5A's.

Every loader asserts the lock for its kind of data. Rows from the reserved period that another
experiment is allowed to hold (5A's definitive daily bars reach back for its ATR lookback) are
dropped in memory before this experiment sees them.
"""

from __future__ import annotations

import hashlib
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from filter_eval import ingest
from responsiveness import data as r5a_data
from responsiveness import sources as r5a_sources
from responsiveness.definitive import data as r5a_def_data

from .config import (COMPOSITE_WEIGHTS, DEFINITIVE_DAILY, DEFINITIVE_EARNINGS_RAW, DEFINITIVE_TICK_DIR, INDICES,
                     NY, PILOT_DAILY, PILOT_EARNINGS_RAW, PILOT_TICK_DIR, PILOT_UNIVERSE_FILE, RUNS)
from .lock import LockViolation, assert_allowed, assert_instant_allowed, drop_outside, gate_open

TICK_COLUMNS = ["ticker", "ts", *INDICES]


def calendar():
    return r5a_data.calendar()


def sessions(run: str) -> list[date]:
    """NYSE sessions of the run's price period. Both ends must be allowed for prices."""
    start, end = RUNS[run]["sessions"]
    assert_instant_allowed(pd.Timestamp(start, tz="UTC"), "session range start", "prices")
    assert_instant_allowed(pd.Timestamp(end, tz="UTC"), "session range end", "prices")
    return [s.date() for s in calendar().sessions_in_range(pd.Timestamp(start), pd.Timestamp(end))]


def session_bounds(d: date) -> tuple[pd.Timestamp, pd.Timestamp]:
    """(open, close) of session d in UTC."""
    cal = calendar()
    return cal.session_open(pd.Timestamp(d)).tz_convert("UTC"), cal.session_close(pd.Timestamp(d)).tz_convert("UTC")


def universe(run: str) -> list[str]:
    """Pilot: 5A's 473 names. Definitive: 5A definitive's universe, which is the same list less any
    name without a daily bar on every period session; that subtraction is made in Phase 4 from 5A's
    definitive price cache, so until then this returns the 473."""
    return r5a_data.universe(PILOT_UNIVERSE_FILE)


def add_score_raw(df: pd.DataFrame) -> pd.DataFrame:
    """Use the served `score_raw` where present; otherwise rebuild the unsmoothed composite from the
    four channels at 0.35 / 0.30 / 0.25 / 0.10, renormalised over the channels present (L2)."""
    df = df.copy()
    cols = list(COMPOSITE_WEIGHTS)
    w = np.array([COMPOSITE_WEIGHTS[c] for c in cols])
    vals = df[cols].to_numpy(dtype=float)
    present = ~np.isnan(vals)
    wsum = (present * w).sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        rebuilt = np.where(wsum > 0, np.nansum(vals * w, axis=1) / wsum, np.nan)
    served = pd.to_numeric(df["score_raw"], errors="coerce").astype("float64").to_numpy() \
        if "score_raw" in df.columns else np.full(len(df), np.nan)
    df["score_raw_rebuilt"] = np.isnan(served)
    df["score_raw"] = np.where(np.isnan(served), rebuilt, served)
    return df


def _finish_ticks(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["score"] = pd.to_numeric(df["score"], errors="coerce").astype("float64")
    df = add_score_raw(df)
    df = r5a_data.add_score_exo(df)
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    return df[TICK_COLUMNS + ["score_raw_rebuilt"]].sort_values(["ticker", "ts"]).reset_index(drop=True)


def load_ticks(run: str, tickers: list[str] | None = None) -> pd.DataFrame:
    """Ticks (ticker, ts, and every index) for the run, lock-asserted as sentiment."""
    if run == "pilot":
        if not PILOT_TICK_DIR.exists():
            raise FileNotFoundError(f"pilot tick cache not found under {PILOT_TICK_DIR.parent}; set SM_DATA_DIR")
        df = ingest.load_ticks(tickers, tick_dir=PILOT_TICK_DIR)
    elif run == "definitive":
        if not gate_open():
            raise LockViolation("definitive sentiment is gated until 5A's definitive results are committed "
                                "(24 November 2026 or later)")
        if not DEFINITIVE_TICK_DIR.exists():
            raise FileNotFoundError(f"definitive tick cache not found under {DEFINITIVE_TICK_DIR.parent}")
        files = sorted(DEFINITIVE_TICK_DIR.glob("*.parquet"))
        if tickers is not None:
            files = [f for f in files if f.stem in set(tickers)]
        df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    else:
        raise ValueError(run)
    assert_allowed(df, "ts", f"{run} sentiment ticks", "sentiment")
    return _finish_ticks(df)


def load_bars(run: str) -> pd.DataFrame:
    """This experiment's intraday bar store for the run (bars.py), lock-asserted as prices."""
    path = RUNS[run]["bars_file"]
    if not path.exists():
        raise FileNotFoundError(f"bar store not found at {path}; run the collector first")
    df = pd.read_parquet(path)
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    df["session"] = pd.to_datetime(df["session"]).dt.date
    return assert_allowed(df, "ts", f"{run} intraday bars", "prices")


def load_daily(run: str) -> pd.DataFrame:
    """Daily bars (ticker, date, open, high, low, close, volume) from 5A's caches. The definitive
    cache holds reserved-period bars for 5A's lookbacks; they are dropped here before anything else."""
    if run == "pilot":
        df = r5a_data.load_prices(PILOT_DAILY)
    else:
        df = r5a_def_data.load_prices(DEFINITIVE_DAILY)
        df, _ = drop_outside(df, "date", "prices")
    return assert_allowed(df, "date", f"{run} daily bars", "prices")


def load_earnings(run: str, tickers: list[str]) -> pd.DataFrame:
    """Earnings releases (ticker, release_et, eps_estimate, eps_reported, surprise_pct) from 5A's
    lock-filtered yfinance tables. Definitive: only once the gate is open."""
    if run == "pilot":
        df = r5a_sources.load_source("earnings", tickers, raw_dir=PILOT_EARNINGS_RAW)
    else:
        if not gate_open():
            raise LockViolation("definitive event tables are gated until 5A's definitive results are committed")
        df = r5a_sources.load_source("earnings", tickers, raw_dir=DEFINITIVE_EARNINGS_RAW)
    df = df.copy()
    df["release_et"] = pd.to_datetime(df["release_et"]).dt.tz_convert(NY)
    return assert_allowed(df, "release_et", f"{run} earnings", "events")


def file_hash(paths: list[Path]) -> str:
    h = hashlib.sha256()
    for p in sorted(paths):
        h.update(p.name.encode())
        h.update(p.read_bytes())
    return h.hexdigest()[:12]
