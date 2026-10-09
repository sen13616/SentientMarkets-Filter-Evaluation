"""The three-range data lock (BRIEF.md section 3).

Three ranges, by UTC instant, inclusive:

| range                              | prices | sentiment and events |
|------------------------------------|--------|----------------------|
| up to 22 June 2026                 | yes    | yes                  |
| 23 June to 1 October 2026          | never  | never                |
| 2 October to 23 November 2026      | yes    | only once the gate is open |
| after 23 November 2026             | never  | never                |

The gate protects Experiment 5A: sentiment and events from October and November may be read only
after 5A's definitive results (`responsiveness/definitive/RESULTS.md`) are committed, on or after
24 November 2026. `gate_open()` checks both; the loaders call it, and the tests pass the flag
explicitly so that they never depend on the repository's state.

Writers filter with `drop_outside` before anything is written; loaders check with
`assert_allowed`. There is no switch to turn either off.
"""

from __future__ import annotations

import subprocess
from datetime import date, datetime, timezone

import pandas as pd

from .config import (DEFINITIVE_END, DEFINITIVE_START, GATE_DATE, GATE_FILE, PILOT_END, RESERVED_END,
                     RESERVED_START, ROOT)

KINDS = ("prices", "sentiment", "events")


class LockViolation(RuntimeError):
    """Raised when data from a forbidden range, or from a gated range before the gate opens, reaches the code."""


def as_utc(values) -> pd.Series:
    """Timestamps as UTC. Naive stamps are read as UTC; plain dates as 00:00 UTC on that day."""
    s = pd.Series(values)
    if not pd.api.types.is_datetime64_any_dtype(s):
        s = pd.to_datetime(s)           # plain dates, strings or Timestamp objects
    return s.dt.tz_localize("UTC") if s.dt.tz is None else s.dt.tz_convert("UTC")


def gate_open(today: date | None = None, root=ROOT) -> bool:
    """True once 5A's definitive results are committed and the date is 24 November 2026 or later."""
    today = today or datetime.now(timezone.utc).date()
    if today < GATE_DATE:
        return False
    try:
        r = subprocess.run(["git", "ls-files", "--error-unmatch", GATE_FILE], cwd=root,
                           capture_output=True, text=True)
    except FileNotFoundError:
        return False
    return r.returncode == 0 and (root / GATE_FILE).exists()


def allowed_mask(values, kind: str, definitive_open: bool) -> pd.Series:
    if kind not in KINDS:
        raise ValueError(f"unknown data kind {kind!r}; expected one of {KINDS}")
    u = as_utc(values)
    ok = u.le(PILOT_END)
    in_def = u.ge(DEFINITIVE_START) & u.le(DEFINITIVE_END)
    if kind == "prices" or definitive_open:
        ok = ok | in_def
    return ok & u.notna()


def describe_violation(values, kind: str, definitive_open: bool) -> str:
    u = as_utc(values)
    bad = ~allowed_mask(u, kind, definitive_open)
    parts = []
    reserved = int((bad & u.ge(RESERVED_START) & u.le(RESERVED_END)).sum())
    late = int((bad & u.gt(DEFINITIVE_END)).sum())
    gated = int((bad & u.ge(DEFINITIVE_START) & u.le(DEFINITIVE_END)).sum())
    if reserved:
        parts.append(f"{reserved} in the reserved period (23 June to 1 October 2026)")
    if gated:
        parts.append(f"{gated} from 2 October to 23 November 2026 before the gate is open ({kind})")
    if late:
        parts.append(f"{late} after 23 November 2026")
    other = int(bad.sum()) - reserved - gated - late
    if other:
        parts.append(f"{other} with no usable timestamp")
    return "; ".join(parts)


def drop_outside(df: pd.DataFrame, col: str, kind: str,
                 definitive_open: bool | None = None) -> tuple[pd.DataFrame, int]:
    """Rows inside the allowed ranges, and the count dropped. Only the count is kept."""
    if definitive_open is None:
        definitive_open = gate_open()
    if not len(df):
        return df.copy(), 0
    d = df.reset_index(drop=True)
    keep = allowed_mask(d[col], kind, definitive_open).to_numpy()
    return d.loc[keep].copy(), int((~keep).sum())


def assert_allowed(df: pd.DataFrame, col: str, what: str, kind: str,
                   definitive_open: bool | None = None) -> pd.DataFrame:
    if definitive_open is None:
        definitive_open = gate_open()
    if len(df):
        vals = df[col].reset_index(drop=True)
        if (~allowed_mask(vals, kind, definitive_open)).any():
            raise LockViolation(f"{what}: {describe_violation(vals, kind, definitive_open)}")
    return df


def assert_instant_allowed(instant, what: str, kind: str, definitive_open: bool | None = None) -> None:
    if definitive_open is None:
        definitive_open = gate_open()
    if not bool(allowed_mask(pd.Series([pd.Timestamp(instant)]), kind, definitive_open).iloc[0]):
        raise LockViolation(f"{what} {instant} is outside the allowed ranges for {kind}")
