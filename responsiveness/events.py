"""Event list construction (BRIEF.md section 4; DECISIONS.md).

Each candidate event gets a reaction session R, a direction (+1 up, -1 down, 0
none) and a measurement window running from its "before" instant to the daily
state of R+1. Candidates then pass through, in order:

1. direction: candidates with direction 0 are dropped (counted);
2. same-type overlap: within a stock and type, events are taken in time order
   and one whose window overlaps an already-kept event of that type is dropped;
   a kept event whose window holds a same-type event of the opposite direction
   is dropped as conflicting (DECISIONS.md R4);
3. cross-type overlap: an event whose window overlaps a kept event of a
   higher-ranked type (E1 > E2 > E3 > E4) on the same stock is dropped;
4. event period: only events with R in [12 May, 18 June 2026] are kept.

Every candidate, kept or not, is retained with a `status` so drops and overlaps
can be counted. The full candidate list (before any drop, and with both possible
reaction sessions for an earnings release with no time) is what "any event"
means for noise sessions and unexplained moves.
"""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from datetime import date, datetime, time, timezone

import numpy as np
import pandas as pd

from .config import E2_ATR_MULT, EVENT_END, EVENT_START, EVENT_TYPES, STATE_CUTOFF
from .data import session_close_utc
from .market import Prices

RANK = {t: i for i, t in enumerate(EVENT_TYPES)}


class Calendar:
    """Session arithmetic on a fixed, lock-bounded session list."""

    def __init__(self, sessions: list[date]):
        self.sessions = list(sessions)
        self.pos = {d: i for i, d in enumerate(self.sessions)}

    def first_on_or_after(self, d: date) -> date | None:
        i = bisect_left(self.sessions, d)
        return self.sessions[i] if i < len(self.sessions) else None

    def first_after(self, d: date) -> date | None:
        i = bisect_right(self.sessions, d)
        return self.sessions[i] if i < len(self.sessions) else None

    def shift(self, d: date, k: int) -> date | None:
        i = self.pos[d] + k
        return self.sessions[i] if 0 <= i < len(self.sessions) else None


def cutoff_utc(d: date) -> pd.Timestamp:
    """21:45 UTC on session d: the instant a daily state is read."""
    return pd.Timestamp(datetime.combine(d, STATE_CUTOFF, tzinfo=timezone.utc))


# --------------------------------------------------------------------------- E1

def earnings_time_known(release_et: pd.Timestamp) -> bool:
    """Whether a release carries a time of day. See DECISIONS.md R1 for how an
    unknown time is encoded by the source."""
    return not (release_et.hour == 0 and release_et.minute == 0)


def earnings_reaction_session(release_et: pd.Timestamp, cal: Calendar) -> date | None:
    """Same session if released before that session's close, otherwise the next session."""
    d = release_et.date()
    if d in cal.pos and release_et.tz_convert("UTC") < session_close_utc(d):
        return d
    return cal.first_after(d)


def build_e1(earn: pd.DataFrame, prices: Prices, cal: Calendar) -> pd.DataFrame:
    rows = []
    for r in earn.itertuples(index=False):
        rel = pd.Timestamp(r.release_et)
        known = earnings_time_known(rel)
        base = {"ticker": r.ticker, "type": "E1", "event_time": rel.tz_convert("UTC"),
                "surprise_pct": r.surprise_pct, "time_known": known}
        if known:
            R = earnings_reaction_session(rel, cal)
            rows.append({**base, "R": R, "R_alt": None})
        else:
            # Unknown time: either the release date's session or the next one.
            d = rel.date()
            R0 = d if d in cal.pos else cal.first_after(d)
            rows.append({**base, "R": R0, "R_alt": cal.first_after(R0) if R0 else None})
    df = pd.DataFrame(rows)
    if not len(df):
        return df
    df = df[df["R"].notna()].copy()
    adj = [prices.adj.at[R, t] if (R in prices.adj.index and t in prices.adj.columns) else np.nan
           for t, R in zip(df["ticker"], df["R"])]
    df["adj_ret"] = adj
    df["direction"] = np.sign(df["adj_ret"]).fillna(0).astype(int)
    df["surprise_sign"] = np.sign(df["surprise_pct"]).fillna(0).astype(int)
    return df


# --------------------------------------------------------------------------- E2

def build_e2(prices: Prices, cal: Calendar, start: date, end: date) -> pd.DataFrame:
    """Sessions where |close(R) - close(R-1)| > 3 x ATR(14) through R-1. The 'not an
    E1 reaction session' rule is applied later, together with the overlap rules."""
    rows = []
    for R in cal.sessions:
        if R < start or R > end:
            continue
        prev = cal.shift(R, -1)
        if prev is None:
            continue
        move = prices.close.loc[R] - prices.close.loc[prev]
        atr = prices.atr.loc[prev]
        hit = (move.abs() > E2_ATR_MULT * atr) & atr.notna() & move.notna()
        for t in hit[hit].index:
            rows.append({"ticker": t, "type": "E2", "R": R, "R_alt": None, "event_time": pd.NaT,
                         "move": float(move[t]), "atr_prev": float(atr[t]),
                         "direction": int(np.sign(move[t]))})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- E3

def build_e3(ratings: pd.DataFrame, cal: Calendar) -> pd.DataFrame:
    r = ratings[ratings["action"].isin(["up", "down"])].copy()
    if not len(r):
        return pd.DataFrame()
    r["R"] = [cal.first_on_or_after(pd.Timestamp(ts).date()) for ts in r["grade_ts"]]
    r["direction"] = np.where(r["action"] == "up", 1, -1)
    return pd.DataFrame({"ticker": r["ticker"], "type": "E3", "R": r["R"], "R_alt": None,
                         "event_time": pd.NaT, "direction": r["direction"], "firm": r["firm"]})


# --------------------------------------------------------------------------- E4

def insider_kind(text: str) -> str:
    """'purchase', 'sale' or 'other', from the leading words of the source's Text field."""
    s = (text or "").strip().lower()
    if s.startswith("purchase"):
        return "purchase"
    if s.startswith("sale"):
        return "sale"
    return "other"


def build_e4(insider: pd.DataFrame, cal: Calendar) -> pd.DataFrame:
    if not len(insider):
        return pd.DataFrame()
    k = insider["text"].map(insider_kind)
    i = insider[k != "other"].copy()
    i["kind"] = k[k != "other"]
    i["R"] = [cal.first_on_or_after(pd.Timestamp(ts).date()) for ts in i["start_date"]]
    return pd.DataFrame({"ticker": i["ticker"], "type": "E4", "R": i["R"], "R_alt": None,
                         "event_time": pd.NaT, "direction": np.where(i["kind"] == "purchase", 1, -1),
                         "kind": i["kind"]})


# --------------------------------------------------------------------------- windows and overlaps

def add_windows(ev: pd.DataFrame, cal: Calendar) -> pd.DataFrame:
    """before = min(event time, 21:45 UTC on R-1); after = 21:45 UTC on R+1."""
    ev = ev.copy()
    bef, aft = [], []
    for R, et in zip(ev["R"], ev["event_time"]):
        p, n = cal.shift(R, -1), cal.shift(R, 1)
        b = cutoff_utc(p) if p else pd.NaT
        if p and pd.notna(et):
            b = min(b, pd.Timestamp(et))
        bef.append(b)
        aft.append(cutoff_utc(n) if n else pd.NaT)
    ev["before_ts"] = pd.to_datetime(pd.Series(bef, index=ev.index), utc=True)
    ev["after_ts"] = pd.to_datetime(pd.Series(aft, index=ev.index), utc=True)
    ev["R_minus_1"] = [cal.shift(R, -1) for R in ev["R"]]
    ev["R_plus_1"] = [cal.shift(R, 1) for R in ev["R"]]
    return ev


def _overlaps(a_b, a_a, b_b, b_a) -> bool:
    return (a_b < b_a) and (b_b < a_a)


def resolve(cands: pd.DataFrame, start: date = EVENT_START, end: date = EVENT_END) -> pd.DataFrame:
    """Apply the drop and overlap rules; returns every candidate with a `status`:
    kept | no_time | no_direction | no_window | same_type_overlap | same_type_conflict |
    overlap_<higher type> | outside_period. `overlaps_dropped` on a kept event lists the
    lower-ranked events it displaced."""
    ev = cands.copy()
    ev["status"] = "pending"
    ev.loc[(ev["type"] == "E1") & ~ev.get("time_known", pd.Series(True, index=ev.index)).fillna(True)
           .astype(bool), "status"] = "no_time"
    ev.loc[(ev["status"] == "pending") & (ev["before_ts"].isna() | ev["after_ts"].isna()), "status"] = "no_window"
    ev.loc[(ev["status"] == "pending") & (ev["direction"] == 0), "status"] = "no_direction"
    ev["overlaps_dropped"] = ""

    # Same-type overlap, greedy in time order, with a conflict check.
    for (tk, ty), g in ev[ev["status"] == "pending"].groupby(["ticker", "type"]):
        g = g.sort_values(["before_ts", "after_ts"])
        kept: list = []
        for idx, row in g.iterrows():
            if any(_overlaps(row.before_ts, row.after_ts, ev.at[k, "before_ts"], ev.at[k, "after_ts"])
                   for k in kept):
                ev.at[idx, "status"] = "same_type_overlap"
            else:
                kept.append(idx)
        for k in kept:
            opp = g[(g["direction"] == -ev.at[k, "direction"])]
            if any(_overlaps(ev.at[k, "before_ts"], ev.at[k, "after_ts"], o.before_ts, o.after_ts)
                   for o in opp.itertuples()):
                ev.at[k, "status"] = "same_type_conflict"
            else:
                ev.at[k, "status"] = "type_kept"

    # E2 sessions that are E1 reaction sessions are not E2 events (definition, not overlap).
    is_e1 = (ev["type"] == "E1") & (ev["status"] != "no_time")
    e1R = set(zip(ev.loc[is_e1, "ticker"], ev.loc[is_e1, "R"]))
    m = (ev["type"] == "E2") & (ev["status"] == "type_kept") & \
        pd.Series([(t, R) in e1R for t, R in zip(ev["ticker"], ev["R"])], index=ev.index)
    ev.loc[m, "status"] = "e1_reaction_session"

    # Cross-type overlap: higher rank wins.
    for tk, g in ev[ev["status"] == "type_kept"].groupby("ticker"):
        g = g.assign(rank=g["type"].map(RANK)).sort_values(["rank", "before_ts"])
        kept: list = []
        for idx, row in g.iterrows():
            hit = [k for k in kept if _overlaps(row.before_ts, row.after_ts,
                                                ev.at[k, "before_ts"], ev.at[k, "after_ts"])]
            if hit:
                ev.at[idx, "status"] = f"overlap_{ev.at[hit[0], 'type']}"
                for k in hit:
                    ev.at[k, "overlaps_dropped"] = (ev.at[k, "overlaps_dropped"] + f"{row.type};").lstrip(";")
            else:
                kept.append(idx)
                ev.at[idx, "status"] = "kept"

    in_period = pd.Series([start <= R <= end if R is not None else False for R in ev["R"]], index=ev.index)
    ev.loc[(ev["status"] == "kept") & ~in_period, "status"] = "outside_period"
    ev["in_period"] = in_period
    return ev


def event_sessions(cands: pd.DataFrame) -> dict[str, set]:
    """Per ticker, every session that is (or may be) a reaction session of any candidate."""
    out: dict[str, set] = {}
    for t, R, Ra in zip(cands["ticker"], cands["R"], cands["R_alt"]):
        s = out.setdefault(t, set())
        if R is not None and not pd.isna(R):
            s.add(R)
        if Ra is not None and not pd.isna(Ra):
            s.add(Ra)
    return out


def build_candidates(earn: pd.DataFrame, ratings: pd.DataFrame, insider: pd.DataFrame,
                     prices: Prices, cal: Calendar, start: date, end: date) -> pd.DataFrame:
    """All candidates with R in [start, end] (wider than the event period, so that
    overlaps across its edges are seen)."""
    parts = [build_e1(earn, prices, cal), build_e2(prices, cal, start, end),
             build_e3(ratings, cal), build_e4(insider, cal)]
    ev = pd.concat([p for p in parts if len(p)], ignore_index=True)
    ev = ev[ev["R"].notna()]
    ev = ev[[(start <= R <= end) for R in ev["R"]]].reset_index(drop=True)
    ev["event_time"] = pd.to_datetime(ev["event_time"], utc=True)
    ev["time_known"] = ev["time_known"].astype("boolean").fillna(True).astype(bool)
    return add_windows(ev, cal)
