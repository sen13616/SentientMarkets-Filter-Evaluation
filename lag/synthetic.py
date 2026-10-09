"""Synthetic ticks, bars and events for the Phase 1 tests. No real data is read here.

The tick schedule copies the system's: a tick every 15 minutes inside the NYSE session and every
30 minutes outside it. Sessions are real NYSE sessions (the calendar is public), values are made up.
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

from .config import INDICES, NY
from .data import calendar, session_bounds

NS_MIN = 60_000_000_000


def sessions(n: int = 28, start: date = date(2026, 5, 12)) -> list[date]:
    """The first `n` NYSE sessions on or after `start`."""
    cal = calendar()
    s = cal.sessions_in_range(pd.Timestamp(start), pd.Timestamp(start) + pd.Timedelta(days=3 * n))
    return [d.date() for d in s[:n]]


def tick_times(sess: list[date], days_before: int = 1, days_after: int = 3) -> np.ndarray:
    """Tick stamps (int64 ns UTC): every 15 minutes inside sessions, every 30 minutes otherwise,
    from `days_before` days before the first session to `days_after` days after the last."""
    start = pd.Timestamp(sess[0], tz="UTC") - pd.Timedelta(days=days_before)
    end = pd.Timestamp(sess[-1], tz="UTC") + pd.Timedelta(days=days_after + 1)
    half = pd.date_range(start, end, freq="30min")
    bounds = [session_bounds(d) for d in sess]
    quarter = []
    for o, c in bounds:
        quarter.append(pd.date_range(o, c, freq="15min", inclusive="left"))
    stamps = half.union(pd.DatetimeIndex(np.concatenate([q.asi8 for q in quarter])).tz_localize("UTC"))
    return np.sort(stamps.asi8.astype(np.int64))


def in_session_mask(stamps_ns: np.ndarray, sess: list[date]) -> np.ndarray:
    b = np.array([[o.value, c.value] for o, c in (session_bounds(d) for d in sess)])
    i = np.searchsorted(b[:, 0], stamps_ns, side="right") - 1
    ok = i >= 0
    out = np.zeros(len(stamps_ns), dtype=bool)
    out[ok] = stamps_ns[ok] < b[i[ok], 1]
    return out


def step(stamps_ns: np.ndarray, t0_ns: int, delay_ns: int, size: float) -> np.ndarray:
    """A step of `size` at t0 + delay (0 before, size at and after)."""
    return np.where(stamps_ns >= t0_ns + delay_ns, size, 0.0)


def ema(stamps_ns: np.ndarray, raw: np.ndarray, half_life_h: float) -> np.ndarray:
    """Variable-step exponential smoother: alpha = 1 - 0.5 ** (dt / half-life), as the system's."""
    out = np.empty_like(raw, dtype=float)
    out[0] = raw[0]
    hl = half_life_h * 3_600e9
    for k in range(1, len(raw)):
        dt = stamps_ns[k] - stamps_ns[k - 1]
        a = 1.0 - 0.5 ** (dt / hl)
        out[k] = out[k - 1] + a * (raw[k] - out[k - 1])
    return out


def ticks_frame(values: dict[str, np.ndarray], stamps_ns: np.ndarray, indices: tuple[str, ...] = INDICES) -> pd.DataFrame:
    """Build a tick frame from per-ticker arrays (one series copied into every index)."""
    frames = []
    ts = pd.to_datetime(stamps_ns, utc=True)
    for t, v in values.items():
        d = {"ticker": t, "ts": ts}
        for i in indices:
            d[i] = np.asarray(v, float)
        frames.append(pd.DataFrame(d))
    return pd.concat(frames, ignore_index=True)


def quiet_bars(tickers: list[str], sess: list[date], rng: np.random.Generator, bar_minutes: int = 60,
               scale: float = 0.002, start_price: float = 100.0) -> pd.DataFrame:
    """Regular-session bars with small bounded within-bar moves and no gaps."""
    rows = []
    for t in tickers:
        px = start_price
        for d in sess:
            o, c = session_bounds(d)
            opens = pd.date_range(o, c, freq=f"{bar_minutes}min", inclusive="left")
            for ts in opens:
                r = rng.uniform(-scale, scale)
                rows.append({"ticker": t, "ts": ts, "session": d, "open": px, "high": px * (1 + abs(r)),
                             "low": px * (1 - abs(r)), "close": px * (1 + r), "volume": 1000})
                px = px * (1 + r)
    df = pd.DataFrame(rows)
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    return df


def plant_bar_move(bars: pd.DataFrame, ticker: str, ts, move: float) -> pd.DataFrame:
    """Multiply the close of one bar, and every later price of the stock, by (1 + move): a permanent step."""
    b = bars.copy()
    ts = pd.Timestamp(ts).tz_convert("UTC")
    at = (b["ticker"] == ticker) & (b["ts"] == ts)
    later = (b["ticker"] == ticker) & (b["ts"] > ts)
    b.loc[at, "close"] *= 1 + move
    b.loc[at, "high"] = b.loc[at, ["high", "close"]].max(axis=1)
    b.loc[at, "low"] = b.loc[at, ["low", "close"]].min(axis=1)
    b.loc[later, ["open", "high", "low", "close"]] *= 1 + move
    return b


def events_frame(rows: list[tuple]) -> pd.DataFrame:
    """rows of (ticker, t0, direction, type)."""
    df = pd.DataFrame(rows, columns=["ticker", "t0", "direction", "type"])
    df["t0"] = pd.to_datetime(df["t0"], utc=True)
    df["status"] = "kept"
    df["in_session"] = True
    return df


def bar_start(d: date, hhmm: str) -> pd.Timestamp:
    return pd.Timestamp(f"{d} {hhmm}", tz=NY).tz_convert("UTC")
