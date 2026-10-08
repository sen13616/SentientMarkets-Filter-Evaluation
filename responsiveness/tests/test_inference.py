"""Synthetic-data tests for measurement and inference (BRIEF.md Phase 1). No real data is read.

The synthetic world: each stock's score is a random walk observed once per session.
A date-only change at session j is state(j+1) - state(j-1). Events are sessions drawn
at random; a planted response adds k noise units to the stock's score from session j
on, in (or against) the event's direction.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from responsiveness import data, events
from responsiveness.inference import (Cell, bh_adjust, binom_p, date_bootstrap, placebo, primary_verdict,
                                      relabel_tests, scorecard, unexplained)
from responsiveness.measure import TickBook, event_readings, noise_units

N_STOCKS, N_SESS, EV_PER_STOCK = 40, 30, 2


def world(rng, plant: float = 0.0, sign: int = 1):
    """States (stock x session), events, D and the cell. `plant` is the response size in
    noise units (0 = none); `sign` -1 plants it against the event's direction."""
    steps = rng.normal(0, 1, (N_STOCKS, N_SESS))
    ev_sess = np.array([rng.choice(np.arange(1, N_SESS - 1), EV_PER_STOCK, replace=False)
                        for _ in range(N_STOCKS)])
    ev_dir = rng.choice([-1, 1], size=ev_sess.shape)
    sigma = np.full(N_STOCKS, np.sqrt(2.0))            # SD of a two-step change of a unit random walk
    for i in range(N_STOCKS):
        for j, d in zip(ev_sess[i], ev_dir[i]):
            steps[i, j] += sign * d * plant * sigma[i]   # the score jumps at the event session
    states = np.cumsum(steps, axis=1)
    D = np.full_like(states, np.nan)
    D[:, 1:-1] = states[:, 2:] - states[:, :-2]
    stock = np.repeat(np.arange(N_STOCKS), EV_PER_STOCK)
    sess = ev_sess.ravel()
    cell = Cell(stock, sess, ev_dir.ravel(), D[stock, sess], sigma[stock])
    eligible = ~np.isnan(D)
    return cell, D, eligible, sigma


# --------------------------------------------------------------------------- null check

def test_null_p_values_are_roughly_uniform():
    rng = np.random.default_rng(1)
    pr, ps = [], []
    for _ in range(300):
        cell, D, elig, sigma = world(rng)
        r = relabel_tests(cell, D, elig, sigma, n_perm=199, rng=rng)
        pr.append(r["p_response"])
        ps.append(r["p_signed"])
    pr, ps = np.array(pr), np.array(ps)
    # Signed move: a continuous statistic, so p is close to uniform.
    assert stats.kstest(ps, "uniform").pvalue > 0.01
    # Both tests are valid (false-positive rate at most alpha, within simulation error) and not
    # degenerate. The response rate is discrete (steps of 1/N) and ties count as ">= observed",
    # so test 1 is slightly conservative rather than exactly uniform.
    for p in (pr, ps):
        for alpha in (0.05, 0.10):
            assert (p < alpha).mean() <= alpha + 0.03
        assert (p < 0.05).mean() >= 0.01
        assert 0.4 <= np.median(p) <= 0.6


def test_null_direction_p_values_roughly_uniform():
    rng = np.random.default_rng(2)
    ps = []
    for _ in range(300):
        cell, *_ = world(rng)
        s = scorecard(cell)
        ps.append(binom_p(s["right"], s["moves"]))
    ps = np.array(ps)
    assert (ps < 0.05).mean() <= 0.10            # exact test: conservative under the null


# --------------------------------------------------------------------------- planted responses

def test_planted_response_detected_in_right_direction():
    rng = np.random.default_rng(3)
    cell, D, elig, sigma = world(rng, plant=2.0, sign=1)
    s = scorecard(cell)
    r = relabel_tests(cell, D, elig, sigma, n_perm=999, rng=rng)
    assert s["response_rate"] > 0.6 and s["direction_accuracy"] > 0.9 and s["avg_signed_move"] > 2.0
    assert r["p_response"] < 0.01 and r["p_signed"] < 0.01
    assert binom_p(s["right"], s["moves"]) < 0.01
    ci = date_bootstrap(cell, cell.session, 2000, rng)
    assert ci["direction_accuracy"][0] > 0.5 and ci["avg_signed_move"][0] > 0


def test_planted_wrong_way_response():
    rng = np.random.default_rng(4)
    cell, D, elig, sigma = world(rng, plant=2.0, sign=-1)
    s = scorecard(cell)
    r = relabel_tests(cell, D, elig, sigma, n_perm=999, rng=rng)
    assert r["p_response"] < 0.01                         # the score moves...
    assert s["direction_accuracy"] < 0.1 and s["wrong_way_rate"] > 0.5
    assert s["avg_signed_move"] < -2.0 and r["p_signed"] > 0.95   # ...the wrong way
    assert primary_verdict(r["p_response"], r["p_signed"], 0.0)["pass"] is False


def test_scorecard_rates_add_up():
    cell = Cell([0, 0, 0, 0], [1, 2, 3, 4], [1, 1, -1, -1], [3.0, -3.0, 0.5, -3.0], [1, 1, 1, 1])
    s = scorecard(cell)
    assert (s["moves"], s["right"], s["wrong"]) == (3, 2, 1)
    assert s["response_rate"] == 0.75 and s["direction_accuracy"] == pytest.approx(2 / 3)
    assert s["wrong_way_rate"] + (s["response_rate"] - s["wrong_way_rate"]) + s["miss_rate"] == pytest.approx(1)
    assert s["avg_signed_move"] == pytest.approx((3 - 3 - 0.5 + 3) / 4)


def test_zero_change_is_never_a_move():
    s = scorecard(Cell([0], [1], [1], [0.0], [0.0]))
    assert s["moves"] == 0


# --------------------------------------------------------------------------- measurement on ticks

def _ticks(rows):
    df = pd.DataFrame(rows, columns=["ts", "score"])
    df["ts"] = pd.to_datetime(df["ts"], utc=True, format="ISO8601").dt.as_unit("us")
    df["ticker"] = "X"
    df["score_exo"] = df["score"]
    return TickBook.from_frame(df, indices=("score", "score_exo"))


CAL = events.Calendar(data.sessions(date(2026, 5, 1), date(2026, 6, 22)))


def _event(rows):
    ev = pd.DataFrame(rows)
    ev["R_alt"] = None
    ev["time_known"] = True
    ev["event_time"] = pd.to_datetime(ev["event_time"], utc=True)
    return events.add_windows(ev, CAL)


def test_after_close_release_before_and_after_readings():
    # Release Wed 3 June 16:00 ET (20:00 UTC) -> R = Thu 4 June; after = state of Fri 5 June.
    book = _ticks([("2026-06-03 19:45", 50.0),       # last tick before the release: the before reading
                   ("2026-06-03 20:15", 60.0),       # after the release but before 21:45: excluded
                   ("2026-06-03 21:30", 61.0),
                   ("2026-06-05 21:30", 70.0),       # state of R+1
                   ("2026-06-05 21:45", 99.0)])      # stamped at the cutoff: excluded
    rel = pd.Timestamp("2026-06-03 16:00", tz="America/New_York")
    R = events.earnings_reaction_session(rel, CAL)
    ev = _event([{"ticker": "X", "type": "E1", "R": R, "direction": 1, "event_time": rel.tz_convert("UTC")}])
    bef, aft = event_readings(book, ev)
    assert R == date(2026, 6, 4)
    assert bef[0, 0] == 50.0 and aft[0, 0] == 70.0


def test_date_only_event_uses_2145_cutoff_on_r_minus_1():
    book = _ticks([("2026-06-03 21:44:59", 40.0), ("2026-06-03 21:45:00", 45.0), ("2026-06-05 21:44", 55.0)])
    ev = _event([{"ticker": "X", "type": "E3", "R": date(2026, 6, 4), "direction": 1, "event_time": pd.NaT}])
    bef, aft = event_readings(book, ev)
    assert bef[0, 0] == 40.0 and aft[0, 0] == 55.0


def test_before_reading_may_not_predate_model_change():
    # R = 13 May: R-1 = 12 May. With no tick on 12 May, the last tick (11 May) is refused.
    book = _ticks([("2026-05-11 21:30", 40.0), ("2026-05-14 21:30", 55.0)])
    ev = _event([{"ticker": "X", "type": "E3", "R": date(2026, 5, 13), "direction": 1, "event_time": pd.NaT}])
    bef, aft = event_readings(book, ev)
    assert np.isnan(bef[0]).all() and aft[0, 0] == 55.0


def test_noise_unit_requires_ten_changes():
    rng = np.random.default_rng(5)
    chg = rng.normal(0, 1, (1, 2, 30))
    mask = np.zeros((2, 30), dtype=bool)
    mask[0, :10] = True
    mask[1, :9] = True
    sd, n = noise_units(chg, mask)
    assert not np.isnan(sd[0, 0]) and np.isnan(sd[0, 1]) and list(n[0]) == [10, 9]


# --------------------------------------------------------------------------- other pieces

def test_placebo_draws_only_from_pool_and_at_most_20():
    rng = np.random.default_rng(6)
    D = rng.normal(0, 1, (2, 40))
    pool = np.zeros((2, 40), dtype=bool)
    pool[0, 5:35] = True
    pool[1, :8] = True
    cell = Cell([0, 1], [3, 3], [1, -1], [0.0, 0.0], [1.0, 1.0])
    out = placebo(cell, D, pool, np.array([1.0, 1.0]), 20, rng)
    picks = out["picks"]
    assert sum(1 for s, _ in picks if s == 0) == 20 and sum(1 for s, _ in picks if s == 1) == 8
    assert all(pool[s, j] for s, j in picks)


def test_unexplained_counts():
    chg = np.array([[5.0, 5.0, 5.0, 0.0], [5.0, 0.0, 0.0, 0.0]])
    sigma = np.array([1.0, 1.0])
    period = np.array([True, True, True, False])
    ev = np.array([[True, False, False, False], [False] * 4])
    pr = np.array([[True, True, False, False], [False] * 4])
    u = unexplained(chg, sigma, period, ev, pr, 2.0)
    assert (u["large"], u["unexplained"], u["both"], u["price_only"], u["event_only"]) == (4, 2, 1, 1, 0)
    assert u["rate"] == 0.5


def test_bh_adjust_matches_reference():
    p = np.array([0.01, 0.04, 0.03, 0.005, np.nan])
    assert np.allclose(bh_adjust(p)[:4], [0.02, 0.04, 0.04, 0.02]) and np.isnan(bh_adjust(p)[4])


def test_primary_verdict_needs_all_three():
    assert primary_verdict(0.01, 0.01, 0.4)["pass"] is True
    assert primary_verdict(0.01, 0.01, 0.5)["pass"] is False
    assert primary_verdict(0.06, 0.01, 0.1)["pass"] is False


def test_build_cell_measures_and_counts_exclusions():
    from responsiveness.cells import build_cell
    sessions = [date(2026, 6, d) for d in (1, 2, 3, 4, 5)]
    ev = pd.DataFrame({"ticker": ["A", "A", "B", "C"], "R": [sessions[1], sessions[3], sessions[2], sessions[2]],
                       "direction": [1, -1, 1, 1], "k": [0, 1, 2, 3]})
    bef = np.array([[10.0], [20.0], [np.nan], [5.0]])
    aft = np.array([[13.0], [15.0], [9.0], [6.0]])
    sd = np.array([[2.0, 2.0, np.nan]])                       # C has no noise unit
    m = build_cell(ev, bef, aft, 0, sd, ["A", "B", "C"], sessions)
    assert m.excluded == {"no noise unit": 1, "no before reading": 1, "no after reading": 0}
    assert list(m.cell.change) == [3.0, -5.0] and list(m.cell.session) == [1, 3]
    s = scorecard(m.cell)
    assert (s["moves"], s["right"], s["avg_signed_move"]) == (2, 2, 4.0)
