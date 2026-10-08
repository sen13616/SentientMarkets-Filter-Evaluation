"""Extended data lock for the definitive run (definitive/BRIEF.md ground rule 2).

Sentiment and events (kind="data"): allowed on or before 2026-06-22 (the pilot's data) and from
2026-10-02 to 2026-11-23 inclusive (UTC); refused from 23 June to 1 October 2026 (reserved for a
later experiment) and after 23 November 2026.

Daily price bars (kind="prices"; DECISIONS.md P1): allowed on or before 2026-11-23, including
the reserved period, because the ATR(14) and typical-move lookbacks need them. The reservation
protects sentiment and filter outcomes, not public prices.

Writers filter with `drop_outside`; loaders check with `assert_allowed`. There is no switch to
turn either off.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from .config import ALLOWED, PRICE_ALLOWED_END

RANGES = {"data": ALLOWED, "prices": ((None, PRICE_ALLOWED_END),)}


class LockViolation(RuntimeError):
    """Raised when data dated in the reserved period or after 23 November 2026 reaches the harness."""


def _as_utc(values) -> pd.Series:
    s = pd.Series(values)
    if pd.api.types.is_datetime64_any_dtype(s):
        s = pd.to_datetime(s)
        return s.dt.tz_localize("UTC") if s.dt.tz is None else s.dt.tz_convert("UTC")
    return pd.to_datetime(s).dt.tz_localize("UTC")     # plain dates: read as that UTC day (00:00)


def allowed_mask(values, kind: str = "data") -> pd.Series:
    u = _as_utc(values)
    ok = pd.Series(False, index=u.index)
    for lo, hi in RANGES[kind]:
        ok |= (u >= lo if lo is not None else True) & (u <= hi)
    return ok & u.notna()


def drop_outside(df: pd.DataFrame, col: str, kind: str = "data") -> tuple[pd.DataFrame, int]:
    """Rows inside the allowed ranges, and the count dropped (only the count is kept)."""
    if not len(df):
        return df.copy(), 0
    d = df.reset_index(drop=True)
    keep = allowed_mask(d[col], kind).to_numpy()
    return d.loc[keep].copy(), int((~keep).sum())


def assert_allowed(df: pd.DataFrame, col: str, what: str = "data", kind: str = "data") -> pd.DataFrame:
    if len(df):
        bad = ~allowed_mask(df[col].reset_index(drop=True), kind)
        if bad.any():
            where = "after 23 November 2026" if kind == "prices" else \
                "in the reserved period (23 June to 1 October 2026) or after 23 November 2026"
            raise LockViolation(f"{what}: {int(bad.sum())} row(s) dated {where}")
    return df


def assert_date_allowed(d: date, what: str = "date", kind: str = "data") -> None:
    if not bool(allowed_mask(pd.Series([pd.Timestamp(d)]), kind).iloc[0]):
        raise LockViolation(f"{what} {d} is outside the allowed ranges")
