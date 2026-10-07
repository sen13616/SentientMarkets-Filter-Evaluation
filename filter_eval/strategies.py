"""Base strategies (INSTRUCTIONS.md section 7). Unfitted, conventional parameters.

Each strategy returns the unfiltered trade list. A trade is decided on session
index `t` using closes through `t` only, enters at the open of `t + 1`, and exits
at the open of `exit` (the session after the holding period ends). An `exit`
beyond the last window session means the trade is marked and closed at the last
close. Decisions are taken on sessions d0 .. we-1 (an entry needs a session
t + 1 inside the window).

Columns: tk (ticker index), t (decision), entry, exit, dir (+1/-1), w (absolute
capital weight at entry), group (leg/cohort id for within-leg redistribution).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .market import Market

TRADE_COLS = ["tk", "t", "entry", "exit", "dir", "w", "group"]


def _frame(rows) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=TRADE_COLS)
    for c in ["tk", "t", "entry", "exit", "dir"]:
        df[c] = df[c].astype(np.int64)
    df["w"] = df["w"].astype(float)
    df["group"] = df["group"].astype(str)
    return df.sort_values(["t", "tk", "dir"]).reset_index(drop=True)


def lookback_return(close: np.ndarray, t: int, k: int) -> np.ndarray:
    if t - k < 0:
        return np.full(close.shape[1], np.nan)
    return close[t] / close[t - k] - 1.0


def quintiles(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Indices of the bottom and top quintiles among finite values (q = floor(n/5) names each)."""
    ok = np.flatnonzero(np.isfinite(values))
    q = len(ok) // 5
    if q == 0:
        return np.array([], int), np.array([], int)
    order = ok[np.argsort(values[ok], kind="mergesort")]
    return order[:q], order[-q:]


def csm(m: Market, lookback: int = 20, hold: int = 5, every: int = 5) -> pd.DataFrame:
    """Every fifth session: long top / short bottom quintile by 20-session return, half capital per leg."""
    rows = []
    for t in range(m.d0, m.we, every):
        bot, top = quintiles(lookback_return(m.close, t, lookback))
        for leg, names, d in (("L", top, 1), ("S", bot, -1)):
            for i in names:
                rows.append((i, t, t + 1, t + 1 + hold, d, 0.5 / len(names), f"{t}{leg}"))
    return _frame(rows)


def str_(m: Market, lookback: int = 5, hold: int = 5) -> pd.DataFrame:
    """Every session: long bottom quintile by 5-session return; five cohorts of 1/5 capital."""
    rows = []
    for t in range(m.d0, m.we):
        bot, _ = quintiles(lookback_return(m.close, t, lookback))
        for i in bot:
            rows.append((i, t, t + 1, t + 1 + hold, 1, (1.0 / hold) / len(bot), f"{t}"))
    return _frame(rows)


def tsmom(m: Market, lookback: int = 60) -> pd.DataFrame:
    """Per name, long while the 60-session return is positive; entry is a flat-to-long transition."""
    rows = []
    w = 1.0 / m.n
    for i in range(m.n):
        open_t = None
        for t in range(m.d0, m.we + 1):
            r = m.close[t, i] / m.close[t - lookback, i] - 1.0 if t >= lookback else np.nan
            long_ = bool(np.isfinite(r) and r > 0)
            if open_t is None and long_ and t < m.we:
                open_t = t
            elif open_t is not None and not long_:
                rows.append((i, open_t, open_t + 1, t + 1, 1, w, f"{i}"))
                open_t = None
        if open_t is not None:
            rows.append((i, open_t, open_t + 1, m.we + 1, 1, w, f"{i}"))
    return _frame(rows)


def brk(m: Market, lookback: int = 252, hold: int = 20) -> pd.DataFrame:
    """Per name, enter on a close above the prior 252 closes; hold 20 sessions; no signals while held."""
    rows = []
    w = 1.0 / m.n
    for i in range(m.n):
        c = m.close[:, i]
        free_from = m.d0  # first decision session on which the name is flat
        for t in range(m.d0, m.we):
            if t < free_from or t < lookback:
                continue
            past = c[t - lookback:t]
            if np.isfinite(c[t]) and np.all(np.isfinite(past)) and c[t] > past.max():
                rows.append((i, t, t + 1, t + 1 + hold, 1, w, f"{i}"))
                free_from = t + 1 + hold  # flat again from the exit open
    return _frame(rows)


def wilder_rsi(close: np.ndarray, period: int = 14) -> np.ndarray:
    """Wilder RSI per column; NaN until `period` changes are available."""
    out = np.full(close.shape, np.nan)
    for i in range(close.shape[1]):
        c = close[:, i]
        ok = np.flatnonzero(np.isfinite(c))
        if len(ok) <= period:
            continue
        s = ok[0]
        d = np.diff(c[s:])
        g, l = np.clip(d, 0, None), np.clip(-d, 0, None)
        ag, al = g[:period].mean(), l[:period].mean()
        def rsi(ag, al):
            return 100.0 if al == 0 else 100.0 - 100.0 / (1.0 + ag / al)
        out[s + period, i] = rsi(ag, al)
        for k in range(period, len(d)):
            if not np.isfinite(d[k]):
                break
            ag = (ag * (period - 1) + g[k]) / period
            al = (al * (period - 1) + l[k]) / period
            out[s + k + 1, i] = rsi(ag, al)
    return out


def rsi_mr(m: Market, period: int = 14, lower: float = 30, upper: float = 50, max_hold: int = 20) -> pd.DataFrame:
    """Per name, enter when RSI(14) crosses below 30; exit when it crosses above 50 or after 20 sessions."""
    rsi = wilder_rsi(m.close, period)
    rows = []
    w = 1.0 / m.n
    for i in range(m.n):
        r = rsi[:, i]
        free_from = m.d0
        for t in range(m.d0, m.we):
            if t < free_from or not (np.isfinite(r[t - 1]) and np.isfinite(r[t])):
                continue
            if r[t - 1] >= lower > r[t]:
                e = t + 1
                x = e + max_hold
                for u in range(e, min(e + max_hold - 1, m.we) + 1):
                    if np.isfinite(r[u - 1]) and np.isfinite(r[u]) and r[u - 1] <= upper < r[u]:
                        x = u + 1
                        break
                rows.append((i, t, e, x, 1, w, f"{i}"))
                free_from = x
    return _frame(rows)


STRATEGIES = {"CSM": csm, "STR": str_, "TSMOM": tsmom, "BRK": brk, "RSI-MR": rsi_mr}
