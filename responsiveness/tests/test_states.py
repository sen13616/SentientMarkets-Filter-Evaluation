"""Synthetic-data tests: daily states and before readings around the 21:45 UTC cutoff."""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from responsiveness.measure import TickBook

IX = ("score", "score_exo")


def book(stamps, values, unit="us"):
    ts = pd.to_datetime(stamps, utc=True, format="ISO8601").as_unit(unit)
    df = pd.DataFrame({"ticker": "X", "ts": ts, "score": values, "score_exo": values})
    return TickBook.from_frame(df, indices=IX)


def test_state_is_last_tick_before_2145_on_the_day():
    b = book(["2026-06-03 21:30:05", "2026-06-03 21:44:59.999", "2026-06-03 21:45:00",
              "2026-06-04 13:00"], [10.0, 20.0, 30.0, 40.0])
    assert b.state("X", date(2026, 6, 3))[0] == 20.0          # 21:45:00 itself is excluded


def test_state_needs_a_tick_on_that_day():
    b = book(["2026-06-02 21:30"], [10.0])
    assert np.isnan(b.state("X", date(2026, 6, 3))).all()


def test_before_reading_any_day_and_strictly_before():
    b = book(["2026-06-02 21:30", "2026-06-03 19:59:59", "2026-06-03 20:00:00"], [1.0, 2.0, 3.0])
    v, ts = b.last_before("X", pd.Timestamp("2026-06-03 20:00", tz="UTC"))   # after-close release
    assert v[0] == 2.0 and ts == pd.Timestamp("2026-06-03 19:59:59", tz="UTC")
    v, _ = b.last_before("X", pd.Timestamp("2026-06-03 08:00", tz="UTC"))
    assert v[0] == 1.0                                         # previous day's tick


def test_tick_unit_does_not_matter():
    for unit in ("s", "ms", "us", "ns"):
        b = book(["2026-06-03 21:30"], [5.0], unit=unit)
        assert b.state("X", date(2026, 6, 3))[0] == 5.0
