"""Writers and loaders for the definitive run, behind the extended lock (lock.py).

Sentiment ticks, prices and event tables for the definitive run live under
`$SM_DATA_DIR/definitive/` and are never committed. Every writer drops rows outside the
allowed ranges in memory before writing; every loader refuses any such row. Price bars use
the price lock (lock.py; DECISIONS.md P1).
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

from responsiveness.data import add_score_exo

from .config import PRICE_FILE, TICK_DIR
from .lock import assert_allowed, drop_outside


def write_frame(df: pd.DataFrame, path: Path, col: str, kind: str = "data") -> int:
    """Lock-filter `df` on `col` (kind "data" or "prices"), write the rest atomically, and
    return the number dropped."""
    kept, dropped = drop_outside(df, col, kind)
    assert_allowed(kept, col, str(path), kind)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    kept.to_parquet(tmp, index=False)
    os.replace(tmp, path)
    return dropped


def load_ticks(tickers: list[str] | None = None, tick_dir: Path = TICK_DIR) -> pd.DataFrame:
    if not tick_dir.exists():
        raise FileNotFoundError(f"definitive tick cache not found at {tick_dir}")
    files = sorted(tick_dir.glob("*.parquet"))
    if tickers is not None:
        files = [f for f in files if f.stem in set(tickers)]
    df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    assert_allowed(df, "ts", "definitive sentiment ticks")
    df = df[["ticker", "ts", "score", "market", "narrative", "influencer", "macro"]].copy()
    df["score"] = df["score"].astype("float64")
    return add_score_exo(df).sort_values(["ticker", "ts"]).reset_index(drop=True)


def load_prices(path: Path = PRICE_FILE) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"definitive price cache not found at {path}")
    df = pd.read_parquet(path)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return assert_allowed(df, "date", "definitive prices", kind="prices")
