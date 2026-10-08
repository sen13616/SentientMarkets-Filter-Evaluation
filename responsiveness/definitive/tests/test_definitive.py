"""Synthetic-data tests for the definitive run's Phase 0 (definitive/BRIEF.md section 6). No real data."""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from responsiveness.definitive import data as ddata
from responsiveness.definitive.integrity import flag_sessions, max_gap, window_flagged
from responsiveness.definitive.lock import LockViolation, assert_allowed, assert_date_allowed, drop_outside
from responsiveness.definitive.regression import date_bootstrap_bc, fit
from responsiveness.definitive.synthetic import one_test


# --------------------------------------------------------------------------- extended lock

@pytest.mark.parametrize("stamp,ok", [
    ("2026-06-22 23:59:59", True), ("2026-06-23 00:00:00", False), ("2026-08-15 12:00", False),
    ("2026-10-01 23:59:59", False), ("2026-10-02 00:00:00", True), ("2026-11-23 23:59:59", True),
    ("2026-11-24 00:00:00", False), ("2027-01-05 10:00", False), ("2026-05-01 10:00", True)])
def test_lock_by_timestamp(stamp, ok):
    df = pd.DataFrame({"ts": pd.to_datetime([stamp], utc=True)})
    if ok:
        assert_allowed(df, "ts")
    else:
        with pytest.raises(LockViolation):
            assert_allowed(df, "ts")


def test_lock_by_date_and_drop_outside():
    df = pd.DataFrame({"date": [date(2026, 6, 22), date(2026, 6, 23), date(2026, 9, 30), date(2026, 10, 2),
                                date(2026, 11, 23), date(2026, 11, 24)]})
    kept, dropped = drop_outside(df, "date")
    assert list(kept["date"]) == [date(2026, 6, 22), date(2026, 10, 2), date(2026, 11, 23)] and dropped == 3
    assert_date_allowed(date(2026, 10, 2))
    for d in (date(2026, 10, 1), date(2026, 11, 24)):
        with pytest.raises(LockViolation):
            assert_date_allowed(d)


def test_writer_drops_and_loaders_refuse(tmp_path):
    ts = pd.to_datetime(["2026-09-30 21:30", "2026-10-02 21:30", "2026-11-23 21:30", "2026-11-24 21:30"], utc=True)
    ticks = pd.DataFrame({"ticker": "X", "ts": ts, "score": 50.0, "market": 50.0, "narrative": 50.0,
                          "influencer": 50.0, "macro": 50.0})
    assert ddata.write_frame(ticks, tmp_path / "ticks" / "X.parquet", "ts") == 2
    assert len(ddata.load_ticks(["X"], tick_dir=tmp_path / "ticks")) == 2
    ticks.to_parquet(tmp_path / "ticks" / "X.parquet")           # bypass the writer
    with pytest.raises(LockViolation):
        ddata.load_ticks(["X"], tick_dir=tmp_path / "ticks")
    # Price bars (P1): the reserved period is allowed for prices, after 23 November is not.
    bars = pd.DataFrame({"ticker": "X", "date": [date(2025, 1, 2), date(2026, 9, 1), date(2026, 11, 23),
                                                 date(2026, 11, 24)], "close": 1.0})
    assert ddata.write_frame(bars, tmp_path / "daily.parquet", "date", kind="prices") == 1
    assert len(ddata.load_prices(tmp_path / "daily.parquet")) == 3
    bars.to_parquet(tmp_path / "daily.parquet")
    with pytest.raises(LockViolation):
        ddata.load_prices(tmp_path / "daily.parquet")
    # ...but sentiment from the reserved period is still refused, even through the price writer's path.
    with pytest.raises(LockViolation):
        assert_allowed(pd.DataFrame({"d": [date(2026, 9, 1)]}), "d")


# --------------------------------------------------------------------------- integrity rule

def _day_ticks(d: str, tickers, gap: tuple[str, str] | None = None, no_narr: int = 0):
    """15-minute ticks 13:30-21:45 UTC for each ticker; optional gap; `no_narr` tickers lack
    narrative at the 21:30 tick."""
    stamps = pd.date_range(f"{d} 13:30", f"{d} 21:30", freq="15min", tz="UTC")
    if gap:
        stamps = stamps[(stamps <= pd.Timestamp(f"{d} {gap[0]}", tz="UTC")) |
                        (stamps >= pd.Timestamp(f"{d} {gap[1]}", tz="UTC"))]   # no ticks strictly inside
    rows = []
    for k, t in enumerate(tickers):
        for s in stamps:
            narr = np.nan if (k < no_narr and s.time() == pd.Timestamp("21:30").time()) else 50.0
            rows.append({"ticker": t, "ts": s, "narrative": narr})
    return pd.DataFrame(rows)


TICKERS = [f"T{i}" for i in range(10)]


def test_integrity_flags_planted_gap():
    d1, d2 = date(2026, 10, 6), date(2026, 10, 7)
    ticks = pd.concat([_day_ticks("2026-10-06", TICKERS, gap=("15:00", "17:15")),     # 2h15 without ticks
                       _day_ticks("2026-10-07", TICKERS, gap=("15:00", "17:00"))])    # exactly 2h: not flagged
    f = flag_sessions(ticks, TICKERS, [d1, d2]).set_index("session")
    assert f.loc[d1, "gap"] and f.loc[d1, "flagged"]
    assert not f.loc[d2, "gap"] and not f.loc[d2, "flagged"]
    assert f.loc[d2, "max_gap_hours"] == pytest.approx(2.0)


def test_integrity_counts_open_and_close_as_gap_ends():
    stamps = pd.to_datetime(["2026-10-06 16:00", "2026-10-06 17:00"], utc=True).as_unit("ns").astype("int64")
    g = max_gap(np.asarray(stamps), pd.Timestamp("2026-10-06 13:30", tz="UTC"),
                pd.Timestamp("2026-10-06 20:00", tz="UTC"))
    assert g == pd.Timedelta(hours=3)                             # 17:00 to the close


def test_integrity_flags_missing_narrative_share():
    d1, d2 = date(2026, 10, 6), date(2026, 10, 7)
    ticks = pd.concat([_day_ticks("2026-10-06", TICKERS, no_narr=3),       # 30% missing: flagged
                       _day_ticks("2026-10-07", TICKERS, no_narr=2)])      # 20%: not more than 20%
    f = flag_sessions(ticks, TICKERS, [d1, d2]).set_index("session")
    assert f.loc[d1, "narrative"] and not f.loc[d2, "narrative"]


def test_integrity_status_outage_and_event_windows():
    sess = [date(2026, 10, d) for d in (5, 6, 7, 8, 9)]
    ticks = pd.concat([_day_ticks(str(d), TICKERS) for d in sess])
    f = flag_sessions(ticks, TICKERS, sess, status_outages={date(2026, 10, 7)})
    assert list(f["flagged"]) == [False, False, True, False, False]
    assert list(window_flagged(f, sess)) == [False, True, True, True, False]


# --------------------------------------------------------------------------- Test B regression

def test_fit_recovers_coefficients():
    rng = np.random.default_rng(0)
    d, r = rng.choice([-1.0, 1.0], 200), rng.normal(0, 0.02, 200)
    a, b, c = fit(1.5 + 2.0 * d + 80 * r, d, r)
    assert (a, b, c) == pytest.approx((1.5, 2.0, 80.0))
    assert np.isnan(fit(np.ones(5), np.ones(5), np.arange(5.0))[1])       # d constant: b undefined


def _rates(n, controls="linear", **kw):
    rng = np.random.default_rng(42)
    return np.array([one_test(rng, K=99, controls=controls, **kw)[1] for _ in range(n)])


def test_no_effect_gives_roughly_uniform_p_values():
    p = _rates(150, design="independent")
    assert stats.kstest(p, "uniform").pvalue > 0.01 and (p < 0.05).mean() <= 0.08


def test_planted_effect_beyond_price_is_detected():
    assert (_rates(40, design="mixed", echo="linear", delta=1.5) < 0.05).mean() >= 0.9


def test_linear_price_echo_is_not_detected():
    """The brief's check: delta proportional to r, nothing from d."""
    for dsg in ("independent", "mixed"):
        assert (_rates(150, design=dsg, echo="linear") < 0.05).mean() <= 0.10


@pytest.mark.xfail(strict=True, reason="Test B as first specified (linear control, E1-E3 pooled; now a secondary "
                                       "cell) is fooled by a price echo that is not linear: see "
                                       "results/test_b_synthetic.md and DECISIONS.md P2")
def test_specified_test_b_not_fooled_by_saturating_echo():
    assert (_rates(100, design="mixed", echo="saturating") < 0.05).mean() <= 0.10


@pytest.mark.parametrize("echo", ["none", "linear", "saturating", "step"])
def test_primary_e3_flexible_not_fooled_by_any_echo(echo):
    """Primary Test B (DECISIONS.md P2): E3-like events only, flexible price controls."""
    assert (_rates(100, controls="flexible", design="rating_like", n_indep=3, echo=echo) < 0.05).mean() <= 0.10


def test_primary_e3_flexible_not_fooled_by_all_three_echoes_at_once():
    """Researcher's added check: a score echoing price in all three forms (linear + saturating
    + step) gives about 5% false positives under the primary Test B."""
    p = _rates(300, controls="flexible", design="rating_like", n_indep=3, echo="all three")
    assert 0.02 <= (p < 0.05).mean() <= 0.08      # calibration at 1,000 reps: results/test_b_calibration.md


def test_spline_knots_are_frozen_symmetric_and_ordered():
    from responsiveness.definitive.config import SPLINE_KNOTS
    k = np.array(SPLINE_KNOTS)
    assert len(k) == 6 and np.all(np.diff(k) > 0) and np.allclose(k, -k[::-1])
    assert np.allclose(k[3:], (0.0091, 0.0289, 0.0737))


def test_primary_e3_flexible_detects_planted_effect():
    assert (_rates(40, controls="flexible", design="rating_like", n_indep=3, echo="saturating", delta=1.0)
            < 0.05).mean() >= 0.9


def test_date_bootstrap_interval_covers_true_b():
    rng = np.random.default_rng(3)
    n = 240
    d, r, dates = rng.choice([-1.0, 1.0], n), rng.normal(0, 0.02, n), rng.integers(0, 30, n)
    y = 2.0 * d + 50 * r + rng.normal(0, 3, n)
    ci = date_bootstrap_bc(y, d, r, dates, 2000, rng)
    assert ci["b"][0] < 2.0 < ci["b"][1] and ci["draws"].shape == (2000, 3)


def test_empty_spline_term_drops_out_of_the_fit():
    """D11: with no return beyond the outer knots, the flexible fit equals the fit without those terms."""
    from responsiveness.definitive.config import SPLINE_KNOTS
    from responsiveness.definitive.regression import design
    rng = np.random.default_rng(9)
    d, r = rng.choice([-1.0, 1.0], 150), rng.uniform(-0.05, 0.05, 150)     # nothing beyond +-0.0737
    y = 1.0 * d + 30 * r + 3 * np.sign(r) + rng.normal(0, 1, 150)
    b_full = fit(y, d, r, "flexible")[1]
    X = design(d, r, "flexible")
    keep = [j for j in range(X.shape[1]) if np.any(X[:, j] != 0)]
    assert len(keep) == X.shape[1] - 1 and SPLINE_KNOTS[-1] > 0.05
    b_ref = np.linalg.lstsq(X[:, keep], y, rcond=None)[0][1]
    assert b_full == pytest.approx(b_ref)
