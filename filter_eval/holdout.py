"""Holdout lock (ground rule 1).

Every writer filters through `drop_after_lock` and every loader asserts through
`assert_locked`. There is deliberately no flag to disable either.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from .config import LOCK_CUTOFF, WINDOW_END


class HoldoutViolation(RuntimeError):
    """Raised when data dated after the research window reaches the harness."""


def _as_utc(values) -> pd.Series:
    s = pd.Series(values)
    if pd.api.types.is_datetime64_any_dtype(s):
        s = pd.to_datetime(s)
        return s.dt.tz_localize("UTC") if s.dt.tz is None else s.dt.tz_convert("UTC")
    # Plain dates (price sessions): compare as end-of-day.
    return pd.to_datetime(s).dt.tz_localize("UTC")


def drop_after_lock(df: pd.DataFrame, col: str) -> tuple[pd.DataFrame, int]:
    """Return rows stamped at or before the lock cutoff, and the count dropped."""
    keep = _as_utc(df[col]).le(LOCK_CUTOFF).to_numpy()
    return df.loc[keep].copy(), int((~keep).sum())


def assert_locked(df: pd.DataFrame, col: str, what: str = "data") -> pd.DataFrame:
    """Raise HoldoutViolation if any row is stamped after the lock cutoff."""
    if len(df) and _as_utc(df[col]).gt(LOCK_CUTOFF).any():
        n = int(_as_utc(df[col]).gt(LOCK_CUTOFF).sum())
        raise HoldoutViolation(f"{what}: {n} row(s) dated after {WINDOW_END}")
    return df


def assert_date_locked(d: date, what: str = "date") -> None:
    if d > WINDOW_END:
        raise HoldoutViolation(f"{what} {d} is after {WINDOW_END}")
