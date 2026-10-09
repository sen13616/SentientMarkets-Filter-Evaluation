"""The three-range data lock (BRIEF.md section 3), on synthetic stamps only."""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from lag import lock
from lag.config import GATE_DATE

PILOT = pd.Timestamp("2026-06-22 23:59:59", tz="UTC")
RESERVED = [pd.Timestamp("2026-06-23 00:00:00", tz="UTC"), pd.Timestamp("2026-08-15 12:00", tz="UTC"),
            pd.Timestamp("2026-10-01 23:59:59", tz="UTC")]
DEFINITIVE = [pd.Timestamp("2026-10-02 00:00:00", tz="UTC"), pd.Timestamp("2026-11-05 15:00", tz="UTC"),
              pd.Timestamp("2026-11-23 23:59:59", tz="UTC")]
LATE = [pd.Timestamp("2026-11-24 00:00:00", tz="UTC"), pd.Timestamp("2027-01-01", tz="UTC")]


def frame(stamps):
    return pd.DataFrame({"ts": pd.to_datetime(stamps, utc=True), "x": range(len(stamps))})


@pytest.mark.parametrize("kind", lock.KINDS)
@pytest.mark.parametrize("gate", [False, True])
def test_pilot_range_always_allowed(kind, gate):
    df = frame([pd.Timestamp("2026-04-24", tz="UTC"), pd.Timestamp("2026-05-12 13:30", tz="UTC"), PILOT])
    assert lock.allowed_mask(df["ts"], kind, gate).all()
    lock.assert_allowed(df, "ts", "t", kind, definitive_open=gate)


@pytest.mark.parametrize("kind", lock.KINDS)
@pytest.mark.parametrize("gate", [False, True])
def test_reserved_range_never_allowed(kind, gate):
    df = frame(RESERVED)
    assert not lock.allowed_mask(df["ts"], kind, gate).any()
    with pytest.raises(lock.LockViolation, match="reserved"):
        lock.assert_allowed(df, "ts", "t", kind, definitive_open=gate)
    kept, dropped = lock.drop_outside(df, "ts", kind, definitive_open=gate)
    assert len(kept) == 0 and dropped == 3


@pytest.mark.parametrize("kind", lock.KINDS)
@pytest.mark.parametrize("gate", [False, True])
def test_after_period_never_allowed(kind, gate):
    df = frame(LATE)
    assert not lock.allowed_mask(df["ts"], kind, gate).any()
    with pytest.raises(lock.LockViolation, match="after 23 November"):
        lock.assert_allowed(df, "ts", "t", kind, definitive_open=gate)


@pytest.mark.parametrize("gate", [False, True])
def test_definitive_prices_allowed_whatever_the_gate(gate):
    df = frame(DEFINITIVE)
    assert lock.allowed_mask(df["ts"], "prices", gate).all()
    lock.assert_allowed(df, "ts", "t", "prices", definitive_open=gate)


@pytest.mark.parametrize("kind", ["sentiment", "events"])
def test_definitive_sentiment_and_events_gated(kind):
    df = frame(DEFINITIVE)
    assert not lock.allowed_mask(df["ts"], kind, False).any()
    with pytest.raises(lock.LockViolation, match="before the gate"):
        lock.assert_allowed(df, "ts", "t", kind, definitive_open=False)
    kept, dropped = lock.drop_outside(df, "ts", kind, definitive_open=False)
    assert len(kept) == 0 and dropped == 3
    assert lock.allowed_mask(df["ts"], kind, True).all()
    lock.assert_allowed(df, "ts", "t", kind, definitive_open=True)


def test_mixed_frame_is_filtered_in_memory_and_counted():
    stamps = [pd.Timestamp("2026-05-20", tz="UTC"), *RESERVED, *DEFINITIVE, *LATE]
    df = frame(stamps)
    kept, dropped = lock.drop_outside(df, "ts", "prices", definitive_open=False)
    assert len(kept) == 4 and dropped == 5
    kept, dropped = lock.drop_outside(df, "ts", "sentiment", definitive_open=False)
    assert len(kept) == 1 and dropped == 8
    msg = lock.describe_violation(df["ts"], "sentiment", False)
    assert "3 in the reserved period" in msg and "3 from 2 October" in msg and "2 after 23 November" in msg


def test_plain_dates_and_naive_stamps_read_as_utc():
    df = pd.DataFrame({"d": [date(2026, 6, 22), date(2026, 6, 23), date(2026, 10, 2), date(2026, 11, 23), date(2026, 11, 24)]})
    m = lock.allowed_mask(df["d"], "prices", False).tolist()
    assert m == [True, False, True, True, False]
    naive = pd.DataFrame({"ts": pd.to_datetime(["2026-06-22 23:59:59", "2026-06-23 00:00:00"])})
    assert lock.allowed_mask(naive["ts"], "sentiment", True).tolist() == [True, False]


def test_instant_check():
    lock.assert_instant_allowed(pd.Timestamp("2026-05-12", tz="UTC"), "d", "sentiment", definitive_open=False)
    lock.assert_instant_allowed(pd.Timestamp("2026-10-02", tz="UTC"), "d", "prices", definitive_open=False)
    with pytest.raises(lock.LockViolation):
        lock.assert_instant_allowed(pd.Timestamp("2026-10-02", tz="UTC"), "d", "sentiment", definitive_open=False)
    with pytest.raises(lock.LockViolation):
        lock.assert_instant_allowed(pd.Timestamp("2026-07-01", tz="UTC"), "d", "prices", definitive_open=True)


def test_gate_closed_before_24_november(tmp_path):
    # Whatever the repository holds, the gate stays closed before the date.
    assert lock.gate_open(today=date(2026, 11, 23)) is False
    # On or after the date, it opens only when the results file is committed in the repository.
    assert lock.gate_open(today=GATE_DATE, root=tmp_path) is False


def test_unknown_kind_rejected():
    with pytest.raises(ValueError):
        lock.allowed_mask(pd.Series([PILOT]), "sentiments", True)
