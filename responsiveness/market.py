"""Price-derived quantities on the NYSE session grid: returns, market adjustment, ATR."""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd

from .config import ATR_N


@dataclass
class Prices:
    """Session x ticker matrices. `ret` is close-to-close; `adj` is ret minus the
    equal-weighted universe return that session; `atr` is Wilder ATR(14) through
    that session (inclusive)."""
    sessions: list[date]
    tickers: list[str]
    close: pd.DataFrame
    ret: pd.DataFrame
    adj: pd.DataFrame
    atr: pd.DataFrame

    def pos(self, d: date) -> int:
        return self.sessions.index(d)


def wilder_atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, n: int = ATR_N) -> np.ndarray:
    """Wilder ATR for one series. TR uses the previous close; the first value is the
    simple mean of the first n true ranges; NaN until then. Missing bars carry ATR forward."""
    T = len(close)
    prev = np.r_[np.nan, close[:-1]]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)      # all-NaN columns on missing bars
        tr = np.nanmax(np.vstack([high - low, np.abs(high - prev), np.abs(low - prev)]), axis=0)
    tr[np.isnan(high) | np.isnan(low) | np.isnan(close)] = np.nan
    tr[0] = np.nan if np.isnan(high[0]) else high[0] - low[0]
    out = np.full(T, np.nan)
    valid = np.flatnonzero(~np.isnan(tr))
    if len(valid) < n:
        return out
    seed_end = valid[n - 1]
    a = np.nanmean(tr[valid[:n]])
    out[seed_end] = a
    for t in range(seed_end + 1, T):
        if not np.isnan(tr[t]):
            a = (a * (n - 1) + tr[t]) / n
        out[t] = a
    return out


def build_prices(bars: pd.DataFrame, tickers: list[str], sessions: list[date]) -> Prices:
    b = bars[bars["ticker"].isin(tickers)]

    def mat(col):
        return b.pivot(index="date", columns="ticker", values=col).reindex(index=sessions, columns=tickers)

    close, high, low = mat("close"), mat("high"), mat("low")
    ret = close / close.shift(1) - 1.0
    ew = ret.mean(axis=1, skipna=True)
    adj = ret.sub(ew, axis=0)
    atr = pd.DataFrame({t: wilder_atr(high[t].to_numpy(float), low[t].to_numpy(float), close[t].to_numpy(float))
                        for t in tickers}, index=sessions)
    return Prices(sessions=list(sessions), tickers=list(tickers), close=close, ret=ret, adj=adj, atr=atr)
