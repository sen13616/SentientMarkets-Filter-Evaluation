"""Daily price bars from yfinance (INSTRUCTIONS.md section 4; D12).

Split- and dividend-adjusted open, high, low and close (auto_adjust=True), from
1 January 2025 to 22 June 2026. Bars dated after the window are dropped before
writing, and the loader refuses any that appear.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from .config import DATA, PRICE_START, WINDOW_END
from .holdout import assert_locked, drop_after_lock
from .ingest import frame_hash

PRICE_FILE = DATA / "prices" / "daily.parquet"
PRICE_MANIFEST = DATA / "prices" / "manifest.json"


def yf_symbol(ticker: str) -> str:
    return ticker.replace(".", "-")


def download(tickers: list[str], chunk: int = 50) -> pd.DataFrame:
    import yfinance as yf

    frames = []
    sym = {yf_symbol(t): t for t in tickers}
    syms = list(sym)
    for i in range(0, len(syms), chunk):
        part = syms[i:i + chunk]
        raw = yf.download(part, start=str(PRICE_START), end=str(WINDOW_END + timedelta(days=1)),
                          auto_adjust=True, actions=False, group_by="ticker", progress=False,
                          threads=False)
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
            d["ticker"] = sym[s]
            d["date"] = pd.to_datetime(d.index).date
            frames.append(d.reset_index(drop=True))
    cols = ["ticker", "date", "open", "high", "low", "close", "volume"]
    if not frames:
        return pd.DataFrame(columns=cols)
    return pd.concat(frames, ignore_index=True)[cols]


def save(df: pd.DataFrame, requested: list[str], path: Path = PRICE_FILE,
         manifest: Path = PRICE_MANIFEST) -> dict:
    kept, dropped = drop_after_lock(df, "date")
    assert_locked(kept, "date", "prices")
    kept = kept.sort_values(["ticker", "date"]).reset_index(drop=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".parquet.tmp")
    kept.to_parquet(tmp, index=False)
    os.replace(tmp, path)
    got = set(kept["ticker"])
    import yfinance as yf
    m = {
        "download_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": f"yfinance {yf.__version__}, auto_adjust=True",
        "start": str(PRICE_START), "end": str(WINDOW_END),
        "tickers_requested": len(requested), "tickers_returned": len(got),
        "no_data": sorted(set(requested) - got),
        "rows": int(len(kept)), "rows_dropped_after_lock": dropped,
        "content_sha256": frame_hash(kept, ["ticker", "date"]),
    }
    manifest.write_text(json.dumps(m, indent=1))
    return m


def load(path: Path = PRICE_FILE) -> pd.DataFrame:
    df = pd.read_parquet(path)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return assert_locked(df, "date", "prices")
