"""Timed events for Experiment 5B (BRIEF.md section 3; DECISIONS.md L1 to L5 and L14).

Two event types, each with a time zero t0 fixed to within an hour:

- L-E1, an earnings release with a time of day. t0 is the release time. The direction is the sign
  of the stock's market-adjusted return from the last close at or before the release to the first
  close after it (the reaction session R, as in Experiment 5A).
- L-E2, a large move within the day: the first regular-session bar of a stock whose standardised
  market-adjusted move (the move over the stock's normal move for that time of day, z) exceeds the
  rarity threshold of L14: the |z| exceeded by 0.2% of in-session bars, pooled over the universe
  and the period. The original rule, |z| > 3, is kept as a secondary sensitivity cell. t0 is the
  start of that bar; the direction is the sign of the bar's market-adjusted move. A session that
  is (or may be) an earnings reaction session for the stock is excluded.

The bar move is the return from the bar's open to its close, so an overnight gap, whose time
cannot be fixed, never creates an event (L1). The market return is the equal-weighted universe
return for the same bar. The normal move for a time of day is 1.4826 times the median absolute
market-adjusted return of the stock's bars at that time of day over the period's sessions that are
not earnings reaction sessions for the stock, given at least MIN_NORMAL_OBS such bars (L3).

Clustering: at most one event per stock in any 48-hour window; earnings win over large moves,
then the earlier event (greedy in that order). Every candidate is kept with a `status`, so every
drop can be counted.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import pandas as pd

from responsiveness.events import Calendar, earnings_reaction_session, earnings_time_known
from responsiveness.market import Prices

from .config import CLUSTER_WINDOW, E2_RARITY_SHARE, EVENT_TYPES, MIN_NORMAL_OBS, NY, POST_WINDOW, ROBUST_SD_FACTOR
from .data import session_bounds

RANK = {t: i for i, t in enumerate(EVENT_TYPES)}
EVENT_COLS = ["ticker", "type", "t0", "direction", "session", "in_session", "status"]


# --------------------------------------------------------------------------- bar panel

@dataclass
class BarPanel:
    """Regular-session bars as (bar start x ticker) matrices, in time order.

    `ret` is the within-bar move (close / open - 1); `mkt` its equal-weighted universe mean per
    bar; `adj` = ret - mkt. `cc` is the close-to-close return from the previous stored bar of the
    same stock (across the overnight gap too), and `cc_adj` its market-adjusted version; these
    serve the price curve, not the event definition."""
    ts: pd.DatetimeIndex
    session: np.ndarray
    tod: np.ndarray
    tickers: list[str]
    open: pd.DataFrame
    close: pd.DataFrame
    ret: pd.DataFrame
    mkt: pd.Series
    adj: pd.DataFrame
    cc: pd.DataFrame
    cc_adj: pd.DataFrame


LOO_MIN_OTHERS = 10   # extended-hours bars: market return needs at least this many other tickers (L18)


def build_panel(bars: pd.DataFrame, tickers: list[str], sessions: list[date], regular_only: bool = True) -> BarPanel:
    """Regular-session bars by default (the event definition and the pilot's price curve): the
    market return is the equal-weighted mean over the universe. With `regular_only=False`, pre- and
    post-market bars are included in time order (L18: the extended-hours price curve of the
    definitive run); few tickers trade in an extended bar, so there the market return is the
    leave-one-out equal-weighted mean over the other tickers that have the bar, and zero (the bar
    is used unadjusted) when fewer than LOO_MIN_OTHERS others have it."""
    b = bars[bars["ticker"].isin(tickers) & bars["session"].isin(sessions)]
    if regular_only and "regular" in b.columns:
        b = b[b["regular"].astype(bool)]
    if b.duplicated(["ticker", "ts"]).any():
        raise ValueError("duplicate (ticker, ts) bars")
    op = b.pivot(index="ts", columns="ticker", values="open").reindex(columns=tickers).sort_index()
    cl = b.pivot(index="ts", columns="ticker", values="close").reindex(columns=tickers).sort_index()
    ts = pd.DatetimeIndex(op.index)
    ts = (ts.tz_localize("UTC") if ts.tz is None else ts.tz_convert("UTC")).as_unit("ns")
    op.index = cl.index = ts
    sess = b.drop_duplicates("ts").set_index("ts")["session"].reindex(ts).to_numpy()
    tod = ts.tz_convert(NY).strftime("%H:%M").to_numpy()
    ret = cl / op - 1.0
    cc = cl / cl.shift(1) - 1.0
    if regular_only:
        mkt = ret.mean(axis=1, skipna=True)
        adj = ret.sub(mkt, axis=0)
        cc_adj = cc.sub(cc.mean(axis=1, skipna=True), axis=0)
    else:
        def loo(x: pd.DataFrame) -> pd.DataFrame:
            n_other = x.notna().sum(axis=1).to_numpy()[:, None] - x.notna().astype(int)
            with np.errstate(invalid="ignore", divide="ignore"):
                other_mean = (x.sum(axis=1, skipna=True).to_numpy()[:, None] - x.fillna(0.0)) / n_other
            return x - other_mean.where(n_other >= LOO_MIN_OTHERS, 0.0)
        adj = loo(ret)
        cc_adj = loo(cc)
        mkt = (ret - adj).mean(axis=1, skipna=True)
    return BarPanel(ts=ts, session=sess, tod=tod, tickers=list(tickers), open=op, close=cl, ret=ret,
                    mkt=mkt, adj=adj, cc=cc, cc_adj=cc_adj)


# --------------------------------------------------------------------------- earnings

def earnings_sessions(earn: pd.DataFrame, cal: Calendar) -> dict[str, set[date]]:
    """Per ticker, every session that is or may be an earnings reaction session: the reaction
    session of every release with a time, and both candidate sessions of a release without one."""
    out: dict[str, set[date]] = {}
    for r in earn.itertuples(index=False):
        rel = pd.Timestamp(r.release_et)
        s = out.setdefault(r.ticker, set())
        if earnings_time_known(rel):
            R = earnings_reaction_session(rel, cal)
            if R:
                s.add(R)
        else:
            d = rel.date()
            R0 = d if d in cal.pos else cal.first_after(d)
            if R0:
                s.add(R0)
                R1 = cal.first_after(R0)
                if R1:
                    s.add(R1)
    return out


def in_session_flag(t0: pd.Timestamp, cal: Calendar) -> tuple[bool, date | None]:
    """Whether t0 falls inside a regular session, and that session (the New York date) if so.
    Outside a session the returned date is the New York calendar day of t0."""
    d = t0.tz_convert(NY).date()
    if d in cal.pos:
        o, c = session_bounds(d)
        if o <= t0 < c:
            return True, d
    return False, d


def build_le1(earn: pd.DataFrame, prices: Prices, cal: Calendar,
              window: tuple[pd.Timestamp, pd.Timestamp] | None = None) -> pd.DataFrame:
    """Every earnings row as an L-E1 candidate with a status: pending | no_time | no_reaction_session |
    no_direction | outside_price_history (release outside `window`, the span of the bar period widened
    by the clustering window, so that releases just before the period still cluster)."""
    rows = []
    for r in earn.itertuples(index=False):
        rel = pd.Timestamp(r.release_et)
        t0 = rel.tz_convert("UTC")
        known = earnings_time_known(rel)
        row = {"ticker": r.ticker, "type": "L-E1", "t0": t0, "release_et": rel, "time_known": known,
               "R": None, "adj_ret": np.nan, "direction": 0, "status": "pending"}
        if window is not None and not (window[0] <= t0 <= window[1]):
            row["status"] = "outside_price_history"
        elif not known:
            row["status"] = "no_time"
        else:
            R = earnings_reaction_session(rel, cal)
            row["R"] = R
            if R is None or R not in prices.adj.index or r.ticker not in prices.adj.columns:
                row["status"] = "no_reaction_session"
            else:
                a = prices.adj.at[R, r.ticker]
                row["adj_ret"] = a
                row["direction"] = int(np.sign(a)) if pd.notna(a) else 0
                if row["direction"] == 0:
                    row["status"] = "no_direction"
        rows.append(row)
    df = pd.DataFrame(rows)
    if not len(df):
        return df
    df["t0"] = pd.to_datetime(df["t0"], utc=True)
    flags = [in_session_flag(t, cal) for t in df["t0"]]
    df["in_session"] = [f[0] for f in flags]
    df["session"] = [f[1] for f in flags]
    return df


# --------------------------------------------------------------------------- large bar moves

def normal_move(panel: BarPanel, excluded: dict[str, set[date]], min_obs: int = MIN_NORMAL_OBS) -> pd.DataFrame:
    """Robust SD of the market-adjusted bar move per (time of day x ticker), over bars whose session
    is not excluded for that ticker; NaN with fewer than `min_obs` bars."""
    out = {}
    tods = sorted(set(panel.tod))
    for t in panel.tickers:
        a = panel.adj[t].to_numpy(float)
        ex = excluded.get(t, set())
        ok = ~np.isnan(a) & np.array([s not in ex for s in panel.session])
        col = {}
        for tod in tods:
            m = ok & (panel.tod == tod)
            n = int(m.sum())
            col[tod] = ROBUST_SD_FACTOR * float(np.median(np.abs(a[m]))) if n >= min_obs else np.nan
        out[t] = col
    return pd.DataFrame(out).reindex(index=tods, columns=panel.tickers)


def z_scores(panel: BarPanel, normal: pd.DataFrame) -> pd.DataFrame:
    """Each bar's market-adjusted move divided by the stock's normal move at that time of day."""
    thr = pd.DataFrame({t: normal[t].reindex(panel.tod).to_numpy() for t in panel.tickers}, index=panel.ts)
    with np.errstate(invalid="ignore", divide="ignore"):
        return panel.adj / thr


def rarity_threshold(z: pd.DataFrame, share: float = E2_RARITY_SHARE) -> float:
    """The |z| exceeded by `share` of the bars that have a z, pooled over every stock and bar (L14)."""
    a = np.abs(z.to_numpy(float))
    a = a[np.isfinite(a)]
    return float(np.quantile(a, 1.0 - share))


def build_le2(panel: BarPanel, normal: pd.DataFrame, excluded: dict[str, set[date]], cal: Calendar,
              threshold: float) -> pd.DataFrame:
    """L-E2 candidates: the first bar per (ticker, session) with |z| > `threshold`, where z is the
    market-adjusted move over the stock's normal move at that time of day. A session excluded for the
    ticker (earnings reaction) is marked, not kept. Also returns, in `attrs`, the number of bars that
    passed the threshold and the number with no normal move."""
    thr = pd.DataFrame({t: normal[t].reindex(panel.tod).to_numpy() for t in panel.tickers}, index=panel.ts)
    adj = panel.adj
    with np.errstate(invalid="ignore"):
        hit = (adj.abs() > threshold * thr) & thr.notna() & adj.notna()
    no_normal = int((thr.isna() & adj.notna()).sum().sum())
    rows = []
    for t in panel.tickers:
        h = hit[t].to_numpy()
        if not h.any():
            continue
        seen: set[date] = set()
        for i in np.flatnonzero(h):
            s = panel.session[i]
            if s in seen:
                continue
            seen.add(s)
            a = float(adj.iat[i, panel.tickers.index(t)])
            rows.append({"ticker": t, "type": "L-E2", "t0": panel.ts[i], "session": s, "tod": panel.tod[i],
                         "bar_move": float(panel.ret[t].iat[i]), "adj_move": a, "normal": float(thr[t].iat[i]),
                         "z": a / float(thr[t].iat[i]), "direction": int(np.sign(a)),
                         "status": "earnings_session" if s in excluded.get(t, set()) else "pending"})
    df = pd.DataFrame(rows)
    df.attrs = {"bars_over_threshold": int(hit.to_numpy().sum()), "bars_without_normal_move": no_normal,
                "bars_tested": int((thr.notna() & adj.notna()).to_numpy().sum())}
    if len(df):
        df["t0"] = pd.to_datetime(df["t0"], utc=True)
        df["in_session"] = True
    return df


# --------------------------------------------------------------------------- clustering and period

def cluster(cands: pd.DataFrame, window: pd.Timedelta = CLUSTER_WINDOW) -> pd.DataFrame:
    """Among pending candidates, keep at most one per stock in any `window`: earnings first, then the
    earlier t0. A dropped candidate's status names the type of the event that displaced it."""
    ev = cands.copy()
    ev["displaced_by"] = ""
    pend = ev["status"] == "pending"
    ev.loc[pend, "status"] = "clustered"          # provisional
    for t, g in ev[pend].groupby("ticker"):
        g = g.assign(rank=g["type"].map(RANK)).sort_values(["rank", "t0"])
        kept: list[tuple[int, pd.Timestamp, str]] = []
        for idx, row in g.iterrows():
            hit = [k for k in kept if abs(row.t0 - k[1]) < window]
            if hit:
                ev.at[idx, "status"] = f"cluster_dropped_for_{hit[0][2]}"
                ev.at[idx, "displaced_by"] = str(hit[0][0])
            else:
                kept.append((idx, row.t0, row.type))
                ev.at[idx, "status"] = "kept"
    return ev


def apply_period(ev: pd.DataFrame, event_start: date, last_tick: pd.Timestamp,
                 post: pd.Timedelta = POST_WINDOW) -> pd.DataFrame:
    """Kept events must have t0 on or after `event_start` (New York date) and t0 + 48 h at or before
    the last tick; others become `outside_period`."""
    ev = ev.copy()
    if not len(ev):
        return ev
    d0 = ev["t0"].dt.tz_convert(NY).dt.date
    inside = (d0 >= event_start) & (ev["t0"] + post <= last_tick)
    ev.loc[(ev["status"] == "kept") & ~inside, "status"] = "outside_period"
    ev["in_period"] = inside
    return ev


def week_label(t0: pd.Timestamp) -> date:
    d = t0.tz_convert(NY).date()
    return d - timedelta(days=d.weekday())


def build_events(earn: pd.DataFrame, prices: Prices, panel: BarPanel, cal: Calendar, event_start: date,
                 last_tick: pd.Timestamp, z_threshold: float) -> tuple[pd.DataFrame, dict]:
    """All candidates of both types with a status, and the counts behind results/event_counts.md.
    `z_threshold` is the L-E2 threshold in units of the normal move: the rarity value of L14 for the
    primary definition, 3.0 for the sensitivity cell."""
    excluded = earnings_sessions(earn, cal)
    window = (panel.ts.min() - CLUSTER_WINDOW, last_tick)
    e1 = build_le1(earn, prices, cal, window)
    normal = normal_move(panel, excluded)
    e2 = build_le2(panel, normal, excluded, cal, z_threshold)
    parts = [p for p in (e1, e2) if len(p)]
    ev = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=EVENT_COLS)
    ev["t0"] = pd.to_datetime(ev["t0"], utc=True)
    ev = cluster(ev)
    ev = apply_period(ev, event_start, last_tick)
    ev["week"] = [week_label(t) for t in ev["t0"]]
    counts = {"e2_attrs": dict(e2.attrs), "normal_move_cells": int(normal.notna().sum().sum()),
              "normal_move_cells_missing": int(normal.isna().sum().sum()),
              "tickers_with_earnings_sessions": len(excluded)}
    return ev.sort_values(["ticker", "t0"]).reset_index(drop=True), counts
