"""Daily sentiment state panel (INSTRUCTIONS.md sections 4 and 5; D3, D5, D6).

For each ticker and NYSE session t in the window, the state is the last tick
stamped on UTC day t before 21:45:00 UTC. Ticks on non-session days (weekends,
25 May, 19 June) are never selected.
"""

from __future__ import annotations

from datetime import date

import exchange_calendars as xc
import numpy as np
import pandas as pd

from .config import (DIVERGENCE_HIGH, EXO_LAYERS, LATE_SLOT_END, LAYER_WEIGHTS, SLOT_2130,
                     STATE_CUTOFF, WINDOW_END, WINDOW_START)
from .holdout import assert_date_locked, assert_locked

LAYERS = list(LAYER_WEIGHTS)


def window_sessions(start: date = WINDOW_START, end: date = WINDOW_END) -> list[date]:
    assert_date_locked(end, "session range end")
    cal = xc.get_calendar("XNYS")
    return [s.date() for s in cal.sessions_in_range(pd.Timestamp(start), pd.Timestamp(end))]


def reconstruct_exo(df: pd.DataFrame) -> pd.Series:
    """score_exo: narrative/influencer/macro weighted 0.30/0.25/0.10, renormalised over present layers."""
    w = np.array([LAYER_WEIGHTS[k] for k in EXO_LAYERS])
    vals = df[list(EXO_LAYERS)].to_numpy(dtype=float)
    present = ~np.isnan(vals)
    wsum = (present * w).sum(axis=1)
    num = np.nansum(vals * w, axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        out = np.where(wsum > 0, num / wsum, np.nan)
    return pd.Series(out, index=df.index)


def divergence_spread(df: pd.DataFrame) -> pd.Series:
    """Max minus min over the present sub-indices (all four); NaN if none present."""
    sub = df[LAYERS]
    return sub.max(axis=1, skipna=True) - sub.min(axis=1, skipna=True)


def round_half_up(x: pd.Series) -> pd.Series:
    return np.floor(x.astype(float) + 0.5)


def label_band(x: pd.Series) -> pd.Series:
    """Label band of the integer-rounded index (section 5)."""
    r = round_half_up(x)
    bins = [-np.inf, 20, 40, 60, 80, np.inf]
    names = ["Strongly Bearish", "Bearish", "Neutral", "Bullish", "Strongly Bullish"]
    return pd.cut(r, bins=bins, labels=names, right=True)


def build_state_panel(ticks: pd.DataFrame, tickers: list[str], sessions: list[date]) -> pd.DataFrame:
    """One row per (ticker, session); state columns NaN where no qualifying tick exists."""
    assert_locked(ticks, "ts", "ticks")
    t = ticks[ticks["ticker"].isin(tickers)].copy()
    t["day"] = t["ts"].dt.date
    tod = t["ts"].dt.time
    t = t[t["day"].isin(set(sessions))]
    t["in_2130_slot"] = (tod >= SLOT_2130) & (tod < STATE_CUTOFF)
    t["late_2130"] = (tod >= STATE_CUTOFF) & (tod < LATE_SLOT_END)

    # Slot diagnostics per ticker-day, computed before the cutoff filter.
    diag = t.groupby(["ticker", "day"]).agg(has_2130=("in_2130_slot", "any"),
                                            has_late_2130=("late_2130", "any"))

    eligible = t[tod.loc[t.index] < STATE_CUTOFF]
    last = eligible.sort_values("ts").groupby(["ticker", "day"]).tail(1).set_index(["ticker", "day"])

    grid = pd.MultiIndex.from_product([sorted(tickers), sessions], names=["ticker", "day"])
    p = last.reindex(grid)
    p = p.join(diag.reindex(grid))
    p[["has_2130", "has_late_2130"]] = p[["has_2130", "has_late_2130"]].fillna(False).astype(bool)
    p = p.drop(columns=["in_2130_slot", "late_2130"]).reset_index()

    p["has_tick"] = p["ts"].notna()
    p["composite"] = p["score"].astype("float64")
    p["score_exo"] = reconstruct_exo(p)
    p["div_spread"] = divergence_spread(p)
    p["div_high"] = p["div_spread"] > DIVERGENCE_HIGH
    p["slot"] = p["ts"].dt.floor("15min").dt.strftime("%H:%M")
    slot_start = pd.to_datetime(p["day"].astype(str) + " 21:30:00", utc=True)
    p["lag_2130_s"] = np.where(p["slot"] == "21:30", (p["ts"] - slot_start).dt.total_seconds(), np.nan)
    # Why the state did not come from the 21:30 slot (only meaningful when it didn't).
    p["non2130_reason"] = np.select(
        [p["slot"] == "21:30", p["has_late_2130"], ~p["has_2130"]],
        ["", "21:30 tick stamped at or after 21:45", "no 21:30 tick"], default="other")
    # A state is valid for the primary index when a tick exists and score_exo is defined (D10).
    p["state_valid"] = p["has_tick"] & p["score_exo"].notna() & p["confidence"].notna()
    return p
