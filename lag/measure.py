"""Measurement (BRIEF.md section 4; DECISIONS.md L6, L7, L11, L12).

Everything works on plain arrays so that the synthetic tests exercise exactly the code the real
run uses.

- Readings. S(t) is the index value at the last tick stamped at or before t. The before reading
  S(t0⁻) is the last tick strictly before t0, and must be at most MAX_BEFORE_AGE old (L6).
- Grid. Offsets every GRID_STEP from -PRE_WINDOW to +POST_WINDOW around t0 (L12). The change at
  offset h is Δ(h) = S(t0 + h) - S(t0⁻); signed by the event direction, m(h) = d·Δ(h).
- Response curve. R(h) = mean m(h) / mean m(48 h) (a ratio of averages). T½ and T₉₀ are the first
  offsets at which R reaches 0.5 and 0.9, interpolated linearly between grid points, NaN if not
  reached within 48 h.
- Price curve. rₑ(h) is the cumulative market-adjusted close-to-close return over the bars whose
  end falls in (t0, t0 + h]; flat between sessions (L7). Rₚ(h) = mean d·rₑ(h) / mean d·rₑ(48 h).
- Alignment. Over hourly session bars, the pooled correlation between the within-hour
  market-adjusted return and the index change over the hour shifted by k trading hours (L11), with
  both demeaned within stock. Cell sums per (k, stock, session) make a session-date bootstrap cheap.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd

from responsiveness.measure import TickBook

from .config import (ALIGN_K, FULL_LEVEL, GRID_STEP, HALF_LEVEL, INDICES, MAIN_HORIZONS_MIN, MAX_BEFORE_AGE,
                     POST_WINDOW, PRE_WINDOW)

NS_PER_H = 3_600_000_000_000


def grid_offsets_ns() -> np.ndarray:
    """Grid offsets in ns: -6 h to +48 h every 5 minutes (last point exactly +48 h)."""
    step = int(GRID_STEP.value)
    return np.arange(-int(PRE_WINDOW.value), int(POST_WINDOW.value) + step, step, dtype=np.int64)


OFFSETS_NS = grid_offsets_ns()
OFFSETS_H = OFFSETS_NS / NS_PER_H
MAIN_IDX = np.array([int(np.argmin(np.abs(OFFSETS_NS - m * 60_000_000_000))) for m in MAIN_HORIZONS_MIN])
M_IDX = int(np.argmin(np.abs(OFFSETS_NS - int(POST_WINDOW.value))))      # the 48 h point
ZERO_IDX = int(np.argmin(np.abs(OFFSETS_NS)))


def to_ns(ts) -> int:
    return int(pd.Timestamp(ts).value)


# --------------------------------------------------------------------------- readings

class Ticks:
    """Index values per ticker on a sorted int64-ns time axis (wraps 5A's TickBook)."""

    def __init__(self, book: TickBook):
        self.book = book
        self.indices = book.indices

    @classmethod
    def from_frame(cls, ticks: pd.DataFrame, indices: tuple[str, ...] = INDICES) -> "Ticks":
        return cls(TickBook.from_frame(ticks, indices=indices))

    def has(self, ticker: str) -> bool:
        return ticker in self.book.ts

    def at_or_before(self, ticker: str, instants_ns: np.ndarray) -> np.ndarray:
        """S(t) for each instant: values of the last tick stamped at or before t; NaN rows before the first tick."""
        n_i = len(self.indices)
        out = np.full((len(instants_ns), n_i), np.nan)
        if ticker not in self.book.ts:
            return out
        ts, vals = self.book.ts[ticker], self.book.vals[ticker]
        k = np.searchsorted(ts, instants_ns, side="right") - 1
        ok = k >= 0
        out[ok] = vals[k[ok]]
        return out

    def before(self, ticker: str, instant_ns: int) -> tuple[np.ndarray, int | None]:
        """The last tick strictly before the instant: (values, its stamp in ns) or (NaN, None)."""
        n_i = len(self.indices)
        if ticker not in self.book.ts:
            return np.full(n_i, np.nan), None
        ts, vals = self.book.ts[ticker], self.book.vals[ticker]
        k = int(np.searchsorted(ts, instant_ns, side="left")) - 1
        if k < 0:
            return np.full(n_i, np.nan), None
        return vals[k].copy(), int(ts[k])

    def span(self, ticker: str) -> tuple[int, int] | None:
        if ticker not in self.book.ts or not len(self.book.ts[ticker]):
            return None
        return int(self.book.ts[ticker][0]), int(self.book.ts[ticker][-1])


def event_curves(ticks: Ticks, tickers: np.ndarray, t0_ns: np.ndarray,
                 max_age_ns: int = int(MAX_BEFORE_AGE.value)) -> dict:
    """Unsigned curves for a list of (ticker, t0). Returns `curves` (E x G x I) = S(t0 + h) - S(t0⁻),
    `before` (E x I), `before_age_s` (E; NaN when there is no before reading) and `valid` (E; the
    before reading exists and is at most `max_age_ns` old). Invalid events have NaN curves."""
    E, G, I = len(t0_ns), len(OFFSETS_NS), len(ticks.indices)
    curves = np.full((E, G, I), np.nan)
    before = np.full((E, I), np.nan)
    age = np.full(E, np.nan)
    for e in range(E):
        b, bts = ticks.before(tickers[e], int(t0_ns[e]))
        if bts is None:
            continue
        age[e] = (int(t0_ns[e]) - bts) / 1e9
        if int(t0_ns[e]) - bts > max_age_ns:
            continue
        before[e] = b
        curves[e] = ticks.at_or_before(tickers[e], int(t0_ns[e]) + OFFSETS_NS) - b[None, :]
    valid = ~np.isnan(age) & (age * 1e9 <= max_age_ns)
    return {"curves": curves, "before": before, "before_age_s": age, "valid": valid}


def sign_curves(curves: np.ndarray, direction: np.ndarray) -> np.ndarray:
    """m = d · Δ, broadcasting the direction over grid and indices."""
    d = np.asarray(direction, float)
    return curves * d.reshape((-1,) + (1,) * (curves.ndim - 1))


# --------------------------------------------------------------------------- response curve and timings

def weighted_mean(x: np.ndarray, w: np.ndarray | None = None) -> np.ndarray:
    """Mean over the first axis ignoring NaN, with optional non-negative weights per row."""
    if w is None:
        w = np.ones(x.shape[0])
    w = np.asarray(w, float)
    ok = ~np.isnan(x)
    num = np.tensordot(w, np.where(ok, x, 0.0), axes=(0, 0))
    den = np.tensordot(w, ok.astype(float), axes=(0, 0))
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(den > 0, num / den, np.nan)


def response_curve(m: np.ndarray, w: np.ndarray | None = None) -> dict:
    """From signed curves m (E x G x I): mean_m (G x I), M (I; the mean at 48 h) and R = mean_m / M."""
    mean_m = weighted_mean(m, w)
    M = mean_m[M_IDX]
    with np.errstate(invalid="ignore", divide="ignore"):
        R = mean_m / M[None, :]
    return {"mean_m": mean_m, "M": M, "R": R}


def crossing_index(R: np.ndarray, level: float, zero_idx: int = ZERO_IDX) -> int | None:
    """Index of the first grid point at or after t0 where R >= level; None if never."""
    r = np.asarray(R, float)
    post = np.arange(zero_idx, len(r))
    hit = post[np.flatnonzero(r[post] >= level)]
    return int(hit[0]) if len(hit) else None


def crossing_time(R: np.ndarray, level: float, offsets_h: np.ndarray = OFFSETS_H, zero_idx: int = ZERO_IDX) -> float:
    """First offset h >= 0 at which R reaches `level`, linearly interpolated between grid points;
    NaN if not reached within the grid. R is one index's curve on the grid."""
    r = np.asarray(R, float)
    i = crossing_index(r, level, zero_idx)
    if i is None:
        return np.nan
    if i == zero_idx or np.isnan(r[i - 1]):
        return float(max(offsets_h[i], 0.0))
    r0, r1 = r[i - 1], r[i]
    h0, h1 = offsets_h[i - 1], offsets_h[i]
    frac = (level - r0) / (r1 - r0) if r1 != r0 else 1.0
    return float(max(h0 + frac * (h1 - h0), 0.0))


def timings(R: np.ndarray, M: np.ndarray) -> dict:
    """T½ and T₉₀ per index (columns of R), NaN where M <= 0 (no eventual move to time) or not
    reached; and `idx_half`, the grid index at which R first reaches 0.5 (-1 if never or no move)."""
    I = R.shape[1]
    t_half, t_full = np.full(I, np.nan), np.full(I, np.nan)
    idx_half = np.full(I, -1, dtype=int)
    for i in range(I):
        if not np.isfinite(M[i]) or M[i] <= 0:
            continue
        t_half[i] = crossing_time(R[:, i], HALF_LEVEL)
        t_full[i] = crossing_time(R[:, i], FULL_LEVEL)
        j = crossing_index(R[:, i], HALF_LEVEL)
        idx_half[i] = -1 if j is None else j
    return {"t_half": t_half, "t_full": t_full, "idx_half": idx_half}


def price_at_half(Rp: np.ndarray, idx_half: int) -> float:
    """Rₚ(T½) read at the first grid point where the score has reached half (L16); if the score
    never gets there within 48 h, the price share at 48 h, which is 1 by construction."""
    if not np.isfinite(Rp).any():
        return np.nan
    return float(Rp[idx_half]) if idx_half >= 0 else float(Rp[M_IDX])


def value_at(curve: np.ndarray, h: float, offsets_h: np.ndarray = OFFSETS_H) -> float:
    """Linear interpolation of a grid curve at offset h (hours); NaN if h is NaN."""
    if not np.isfinite(h):
        return np.nan
    return float(np.interp(h, offsets_h, curve))


# --------------------------------------------------------------------------- price curve

@dataclass
class PriceSeries:
    """Per ticker: bar end stamps (ns, sorted) and the cumulative market-adjusted close-to-close
    return at each bar end (NaN bars contribute 0 and are counted in `n_missing`)."""
    end_ns: dict[str, np.ndarray]
    cum: dict[str, np.ndarray]
    n_missing: dict[str, int]

    @classmethod
    def from_panel(cls, panel, bar_minutes: int) -> "PriceSeries":
        end = (panel.ts + pd.Timedelta(minutes=bar_minutes)).asi8
        ends, cums, miss = {}, {}, {}
        for t in panel.tickers:
            a = panel.cc_adj[t].to_numpy(float)
            miss[t] = int(np.isnan(a).sum())
            ends[t] = end
            cums[t] = np.cumsum(np.nan_to_num(a))
        return cls(end_ns=ends, cum=cums, n_missing=miss)

    def cumulative(self, ticker: str, t0_ns: int, instants_ns: np.ndarray) -> np.ndarray:
        """Cumulative market-adjusted return over bars whose end lies in (t0, t] for each t."""
        if ticker not in self.end_ns:
            return np.full(len(instants_ns), np.nan)
        end, cum = self.end_ns[ticker], self.cum[ticker]
        ref = np.searchsorted(end, t0_ns, side="right")             # bars with end <= t0
        idx = np.searchsorted(end, instants_ns, side="right")       # bars with end <= t
        base = cum[ref - 1] if ref > 0 else 0.0
        out = np.where(idx > 0, cum[np.maximum(idx - 1, 0)], 0.0) - base
        return out


def price_curves(prices: PriceSeries, tickers: np.ndarray, t0_ns: np.ndarray) -> np.ndarray:
    """rₑ(h) for every event on the grid (E x G)."""
    out = np.full((len(t0_ns), len(OFFSETS_NS)), np.nan)
    for e in range(len(t0_ns)):
        out[e] = prices.cumulative(tickers[e], int(t0_ns[e]), int(t0_ns[e]) + OFFSETS_NS)
    return out


def price_response(rp_signed: np.ndarray, w: np.ndarray | None = None) -> dict:
    """Rₚ(h) = mean d·rₑ(h) / mean d·rₑ(48 h) from signed price curves (E x G)."""
    mean_r = weighted_mean(rp_signed, w)
    Mp = mean_r[M_IDX]
    with np.errstate(invalid="ignore", divide="ignore"):
        Rp = mean_r / Mp
    return {"mean_r": mean_r, "Mp": float(Mp), "Rp": Rp}


# --------------------------------------------------------------------------- alignment

@dataclass
class HourlyBars:
    """Per ticker, in time order across sessions: start and end stamps (ns), the within-hour
    market-adjusted return, and the session index of each bar."""
    tickers: list[str]
    sessions: list[date]
    start_ns: dict[str, np.ndarray]
    end_ns: dict[str, np.ndarray]
    adj: dict[str, np.ndarray]
    session_idx: dict[str, np.ndarray]


def hourly_bars(bars: pd.DataFrame, tickers: list[str], sessions: list[date], bar_minutes: int) -> HourlyBars:
    """Hourly session bars from a bar store. Hourly stores are used as they are; 15-minute bars are
    aggregated into the hours starting at the session open (open of the first bar, close of the
    last). The market return is the equal-weighted mean across tickers of the hourly return."""
    b = bars[bars["ticker"].isin(tickers) & bars["session"].isin(sessions)].copy()
    if bar_minutes == 60:
        b["hour_start"] = b["ts"]
    else:
        # hours start at the session open: floor each bar to the hour boundary counted from 09:30 New York.
        ny = b["ts"].dt.tz_convert("America/New_York")
        minutes = (ny - ny.dt.normalize()).dt.total_seconds() / 60 - 570          # minutes since 09:30
        b["hour_start"] = b["ts"] - pd.to_timedelta((minutes % 60).round().astype(int), unit="min")
    g = b.sort_values("ts").groupby(["ticker", "hour_start"])
    h = g.agg(open=("open", "first"), close=("close", "last"), session=("session", "first"),
              n=("ts", "size"), last_ts=("ts", "last")).reset_index()
    h["end"] = h["last_ts"] + pd.Timedelta(minutes=bar_minutes)
    h["ret"] = h["close"] / h["open"] - 1.0
    mkt = h.groupby("hour_start")["ret"].mean()
    h["adj"] = h["ret"] - h["hour_start"].map(mkt)
    pos = {d: i for i, d in enumerate(sessions)}
    start, end, adj, sidx = {}, {}, {}, {}
    for t, gt in h.groupby("ticker"):
        gt = gt.sort_values("hour_start")
        start[t] = gt["hour_start"].to_numpy("datetime64[ns]").astype(np.int64)
        end[t] = gt["end"].to_numpy("datetime64[ns]").astype(np.int64)
        adj[t] = gt["adj"].to_numpy(float)
        sidx[t] = np.array([pos[s] for s in gt["session"]], dtype=int)
    return HourlyBars(tickers=[t for t in tickers if t in start], sessions=list(sessions), start_ns=start,
                      end_ns=end, adj=adj, session_idx=sidx)


def alignment_cells(ticks: Ticks, hb: HourlyBars, index_pos: int, ks: tuple[int, ...] = ALIGN_K) -> dict:
    """Sums per (k, stock, session) of n, x, y, xx, yy, xy, where x is the hourly market-adjusted return
    and y the index change over the hour shifted by k bars along the stock's bar sequence
    (positive k: the index change k hours after the price return)."""
    K, I, S = len(ks), len(hb.tickers), len(hb.sessions)
    sums = {name: np.zeros((K, I, S)) for name in ("n", "x", "y", "xx", "yy", "xy")}
    for i, t in enumerate(hb.tickers):
        x_all = hb.adj[t]
        s_start = ticks.at_or_before(t, hb.start_ns[t])[:, index_pos]
        s_end = ticks.at_or_before(t, hb.end_ns[t])[:, index_pos]
        y_all = s_end - s_start
        sess = hb.session_idx[t]
        J = len(x_all)
        for kk, k in enumerate(ks):
            if k >= 0:
                x, y, s = x_all[:J - k], y_all[k:], sess[:J - k]
            else:
                x, y, s = x_all[-k:], y_all[:J + k], sess[-k:]
            ok = np.isfinite(x) & np.isfinite(y)
            x, y, s = x[ok], y[ok], s[ok]
            for name, v in (("n", np.ones_like(x)), ("x", x), ("y", y), ("xx", x * x), ("yy", y * y), ("xy", x * y)):
                sums[name][kk, i] += np.bincount(s, weights=v, minlength=S)
    return {"ks": np.array(ks), "sums": sums, "tickers": hb.tickers, "sessions": hb.sessions}


def alignment_corr(cells: dict, session_w: np.ndarray | None = None) -> np.ndarray:
    """Pooled correlation per k, with x and y demeaned within stock; `session_w` (B x S) gives a
    bootstrap over sessions and returns (B x K); None returns (K,)."""
    s = cells["sums"]
    K, I, S = s["n"].shape
    W = np.ones((1, S)) if session_w is None else np.asarray(session_w, float)
    agg = {name: np.einsum("bs,kis->bki", W, s[name]) for name in s}       # B x K x I
    with np.errstate(invalid="ignore", divide="ignore"):
        n = agg["n"]
        xbar, ybar = agg["x"] / n, agg["y"] / n
        sxy = agg["xy"] - n * xbar * ybar
        sxx = agg["xx"] - n * xbar * xbar
        syy = agg["yy"] - n * ybar * ybar
        ok = n > 1
        num = np.where(ok, sxy, 0.0).sum(axis=2)
        den = np.sqrt(np.where(ok, sxx, 0.0).sum(axis=2) * np.where(ok, syy, 0.0).sum(axis=2))
        corr = num / den
    return corr[0] if session_w is None else corr


def best_k(corr: np.ndarray, ks: np.ndarray) -> int | float:
    """The k with the largest correlation (NaN if every correlation is NaN)."""
    c = np.asarray(corr, float)
    if not np.isfinite(c).any():
        return np.nan
    return int(ks[int(np.nanargmax(c))])
