"""Aligned price matrices on the NYSE session grid."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import exchange_calendars as xc
import numpy as np
import pandas as pd

from .config import FIRST_DECISION, PRICE_START, WINDOW_END, WINDOW_START
from .holdout import assert_date_locked, assert_locked


@dataclass
class Market:
    """Open and close matrices (sessions x tickers) plus the window positions.

    `ws` and `we` are the indices of the first and last window sessions; `d0` is
    the first decision session. Rows after `we` never exist (holdout lock).
    """
    sessions: list[date]
    tickers: list[str]
    open: np.ndarray
    close: np.ndarray
    ws: int
    we: int
    d0: int

    @property
    def n(self) -> int:
        return len(self.tickers)

    def idx(self, d: date) -> int:
        return self.sessions.index(d)


def nyse_sessions(start: date = PRICE_START, end: date = WINDOW_END) -> list[date]:
    assert_date_locked(end, "session range end")
    cal = xc.get_calendar("XNYS")
    return [s.date() for s in cal.sessions_in_range(pd.Timestamp(start), pd.Timestamp(end))]


def build_market(prices: pd.DataFrame, tickers: list[str], sessions: list[date] | None = None,
                 window_start: date = WINDOW_START, first_decision: date = FIRST_DECISION) -> Market:
    assert_locked(prices, "date", "prices")
    sessions = sessions or nyse_sessions()
    assert_date_locked(sessions[-1], "last session")
    p = prices[prices["ticker"].isin(tickers)]
    def mat(col):
        m = p.pivot(index="date", columns="ticker", values=col)
        return m.reindex(index=sessions, columns=tickers).to_numpy(dtype=float)
    return Market(sessions=list(sessions), tickers=list(tickers), open=mat("open"), close=mat("close"),
                  ws=sessions.index(window_start), we=len(sessions) - 1,
                  d0=sessions.index(first_decision))
