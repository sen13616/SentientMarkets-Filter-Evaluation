"""Score states, before/after readings and noise units (BRIEF.md section 4).

- Daily state of session d: the last tick stamped on UTC day d before 21:45 UTC
  (the first experiment's rule); NaN if there is none.
- Before: the last tick stamped strictly before an instant, on any day.
- Noise unit: per stock and index, the sample standard deviation (ddof 1) of
  state(d+1) - state(d-1) over the stock's noise sessions d.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd

from .config import INDICES
from .events import Calendar, cutoff_utc


@dataclass
class TickBook:
    """Per-ticker tick arrays: `ts` (int64 ns UTC, sorted) and `vals` (n_ticks x n_indices)."""
    ts: dict[str, np.ndarray]
    vals: dict[str, np.ndarray]
    indices: tuple[str, ...] = INDICES

    @classmethod
    def from_frame(cls, ticks: pd.DataFrame, indices: tuple[str, ...] = INDICES) -> "TickBook":
        ts, vals = {}, {}
        for t, g in ticks.sort_values("ts").groupby("ticker", sort=False):
            s = g["ts"].dt.tz_convert("UTC") if g["ts"].dt.tz is not None else g["ts"].dt.tz_localize("UTC")
            ts[t] = s.dt.as_unit("ns").astype("int64").to_numpy()      # ns, whatever the stored unit
            vals[t] = g[list(indices)].to_numpy(dtype=float)
        return cls(ts=ts, vals=vals, indices=indices)

    def last_before(self, ticker: str, instant: pd.Timestamp) -> tuple[np.ndarray, pd.Timestamp | None]:
        """Index values of the last tick stamped strictly before `instant`."""
        nan = np.full(len(self.indices), np.nan)
        if ticker not in self.ts or pd.isna(instant):
            return nan, None
        k = np.searchsorted(self.ts[ticker], pd.Timestamp(instant).value, side="left") - 1
        if k < 0:
            return nan, None
        return self.vals[ticker][k], pd.Timestamp(self.ts[ticker][k], tz="UTC")

    def state(self, ticker: str, d: date) -> np.ndarray:
        """Daily state: last tick on UTC day d stamped before 21:45 UTC."""
        v, ts = self.last_before(ticker, cutoff_utc(d))
        if ts is None or ts.date() != d:
            return np.full(len(self.indices), np.nan)
        return v


def state_cube(book: TickBook, tickers: list[str], sessions: list[date]) -> np.ndarray:
    """Array (n_indices, n_tickers, n_sessions) of daily states."""
    out = np.full((len(book.indices), len(tickers), len(sessions)), np.nan)
    for i, t in enumerate(tickers):
        for j, d in enumerate(sessions):
            out[:, i, j] = book.state(t, d)
    return out


def two_session_changes(cube: np.ndarray) -> np.ndarray:
    """chg[..., j] = state(j+1) - state(j-1); NaN at the edges."""
    out = np.full_like(cube, np.nan)
    out[..., 1:-1] = cube[..., 2:] - cube[..., :-2]
    return out


def noise_sessions(tickers: list[str], sessions: list[date], period: tuple[date, date],
                   ev_sessions: dict[str, set], cal: Calendar, exclusion: int) -> np.ndarray:
    """Boolean (n_tickers, n_sessions): d in the event period, with d-1 and d+1 in the
    session list, and no candidate event R within `exclusion` sessions of d."""
    lo, hi = period
    mask = np.zeros((len(tickers), len(sessions)), dtype=bool)
    for j, d in enumerate(sessions):
        if not (lo <= d <= hi) or j == 0 or j == len(sessions) - 1:
            continue
        for i, t in enumerate(tickers):
            evs = ev_sessions.get(t, set())
            near = any(cal.shift(d, k) in evs for k in range(-exclusion, exclusion + 1))
            mask[i, j] = not near
    return mask


def noise_units(chg: np.ndarray, mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Per (index, ticker): SD (ddof 1) of the changes on noise sessions, and the number
    of defined changes it uses. SD is NaN with fewer than 2 changes."""
    n_ix, n_t, _ = chg.shape
    sd = np.full((n_ix, n_t), np.nan)
    cnt = np.zeros((n_ix, n_t), dtype=int)
    for a in range(n_ix):
        for i in range(n_t):
            x = chg[a, i, mask[i]]
            x = x[~np.isnan(x)]
            cnt[a, i] = len(x)
            if len(x) >= 2:
                sd[a, i] = np.std(x, ddof=1)
    return sd, cnt
