"""Live-data integrity rule (definitive/BRIEF.md section 3; DECISIONS.md D2-D4).

A session is flagged if any of these holds:
- gap: within the session's trading hours (NYSE open to close, in UTC), the union of
  all universe tick stamps, with the open and the close added as end points, has a gap
  longer than 2 hours;
- narrative: more than 20% of the universe has no 21:30-slot tick with a narrative
  value (the tick stamped in [21:30, 21:45) UTC, or if there is none, in [21:45, 22:00));
- status: the session is in the set of sessions an outage report covers (DECISIONS.md D4).

An event is excluded if any session from R-1 to R+1 is flagged; a noise, placebo or
relabelled session d is excluded on the same rule applied to d-1, d and d+1.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from responsiveness.data import calendar

from .config import INTEGRITY_MAX_GAP, INTEGRITY_NARRATIVE_MISSING, SLOT_2130, SLOT_2130_LATE_END, STATE_CUTOFF


def session_hours_utc(d: date) -> tuple[pd.Timestamp, pd.Timestamp]:
    cal = calendar()
    return (cal.session_open(pd.Timestamp(d)).tz_convert("UTC"),
            cal.session_close(pd.Timestamp(d)).tz_convert("UTC"))


def max_gap(stamps: np.ndarray, start: pd.Timestamp, end: pd.Timestamp) -> pd.Timedelta:
    """Longest interval in [start, end] containing no stamp (stamps are ns ints, UTC)."""
    s = stamps[(stamps >= start.value) & (stamps <= end.value)]
    pts = np.concatenate([[start.value], np.sort(s), [end.value]])
    return pd.Timedelta(int(np.diff(pts).max()), unit="ns")


def narrative_missing_share(ticks: pd.DataFrame, tickers: list[str], d: date) -> float:
    """Share of `tickers` without a narrative value at the 21:30 tick of session d."""
    day = ticks[ticks["ts"].dt.date == d]
    tod = day["ts"].dt.time
    slot = day[(tod >= SLOT_2130) & (tod < STATE_CUTOFF)]
    late = day[(tod >= STATE_CUTOFF) & (tod < SLOT_2130_LATE_END)]
    first = slot.sort_values("ts").groupby("ticker").head(1).set_index("ticker")["narrative"]
    first_late = late.sort_values("ts").groupby("ticker").head(1).set_index("ticker")["narrative"]
    val = first.reindex(tickers).combine_first(first_late.reindex(tickers))
    return float(val.isna().mean())


def flag_sessions(ticks: pd.DataFrame, tickers: list[str], sessions: list[date],
                  status_outages: set[date] | None = None) -> pd.DataFrame:
    """One row per session with each criterion, its measurement and `flagged`."""
    t = ticks[ticks["ticker"].isin(tickers)]
    stamps = t["ts"].dt.tz_convert("UTC").dt.as_unit("ns").astype("int64").to_numpy()
    rows = []
    for d in sessions:
        o, c = session_hours_utc(d)
        g = max_gap(stamps, o, c)
        nm = narrative_missing_share(t, tickers, d)
        st = d in (status_outages or set())
        rows.append({"session": d, "max_gap_hours": round(g / pd.Timedelta(hours=1), 3),
                     "gap": g > INTEGRITY_MAX_GAP, "narrative_missing_share": round(nm, 4),
                     "narrative": nm > INTEGRITY_NARRATIVE_MISSING, "status": st})
    df = pd.DataFrame(rows)
    df["flagged"] = df["gap"] | df["narrative"] | df["status"]
    return df


def window_flagged(flags: pd.DataFrame, sessions: list[date]) -> np.ndarray:
    """Boolean per session d: any of d-1, d, d+1 is flagged (ends count only their neighbours)."""
    f = flags.set_index("session")["flagged"].reindex(sessions).fillna(False).to_numpy(dtype=bool)
    out = f.copy()
    out[1:] |= f[:-1]
    out[:-1] |= f[1:]
    return out


