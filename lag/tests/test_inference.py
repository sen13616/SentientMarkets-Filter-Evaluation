"""Phase 1 synthetic tests of the inference: Holm, non-event sessions, placebo instants, the relabelling null."""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from lag import inference as inf
from lag import measure as ms
from lag import synthetic as syn
from lag.config import INDICES

H = 3_600_000_000_000


def test_holm():
    p = np.array([0.01, 0.04, 0.03, np.nan, 0.5])
    adj = inf.holm(p)
    assert np.isnan(adj[3])
    assert adj[0] == pytest.approx(0.04) and adj[2] == pytest.approx(0.09) and adj[1] == pytest.approx(0.09)
    assert adj[4] == pytest.approx(0.5)


def test_non_event_sessions_radius():
    sess = syn.sessions(10)
    out = inf.non_event_sessions({"A": {sess[4]}, "B": set(), "C": {date(2026, 5, 16)}}, sess, radius=2)
    assert out["A"] == sess[:2] + sess[7:]
    assert out["B"] == sess
    # a Saturday candidate blocks two sessions on each side
    sat_before = [s for s in sess if s < date(2026, 5, 16)][-2:]
    sat_after = [s for s in sess if s > date(2026, 5, 16)][:2]
    assert all(s not in out["C"] for s in sat_before + sat_after) and len(out["C"]) == 6


def test_same_time_on_keeps_new_york_time_of_day():
    t0 = pd.Timestamp("2026-05-20 11:30", tz="America/New_York")
    inst = inf.same_time_on(t0, [date(2026, 6, 1), date(2026, 11, 5)])     # across the DST change in November
    got = pd.to_datetime(inst, utc=True).tz_convert("America/New_York").strftime("%H:%M").tolist()
    assert got == ["11:30", "11:30"]


def test_pools_respect_the_tick_span():
    sess = syn.sessions(12)
    stamps = syn.tick_times(sess, days_before=0, days_after=0)
    stamps = stamps[stamps >= syn.bar_start(sess[0], "09:30").value]        # ticks start at the first open
    ticks = ms.Ticks.from_frame(syn.ticks_frame({"A": np.full(len(stamps), 50.0)}, stamps))
    ev = syn.events_frame([("A", syn.bar_start(sess[6], "11:30"), 1, "L-E2")])
    pools = inf.pools(ticks, ev, {"A": sess})
    days = pd.to_datetime(pools[0], utc=True).tz_convert("America/New_York").date
    # the first session has no 6 hours of ticks before 11:30; the last ones cannot fit 48 hours after
    assert sess[0] not in days and sess[-1] not in days and sess[6] in days and sess[1] in days


def synthetic_world(rng, n_events=8, n_sessions=28, planted=0.0):
    """`n_events` stocks with one event each (as most real stocks have), on a random session, with
    independent random-walk-plus-noise ticks; each stock keeps about 23 non-event sessions."""
    sess = syn.sessions(n_sessions)
    stamps = syn.tick_times(sess)
    values, rows = {}, []
    for j in range(n_events):
        t = f"S{j:02d}"
        v = 50.0 + np.cumsum(rng.normal(0, 0.3, len(stamps))) + rng.normal(0, 1.0, len(stamps))
        t0 = syn.bar_start(sess[int(rng.integers(3, n_sessions - 4))], "11:30")
        d = int(rng.choice([-1, 1]))
        rows.append((t, t0, d, "L-E2"))
        if planted:
            v = v + d * syn.step(stamps, t0.value, H, planted)
        values[t] = v
    ticks = ms.Ticks.from_frame(syn.ticks_frame(values, stamps))
    ev = syn.events_frame(rows)
    cand = {r.ticker: {pd.Timestamp(r.t0).tz_convert("America/New_York").date()} for r in ev.itertuples()}
    pools = inf.pools(ticks, ev, inf.non_event_sessions(cand, sess))
    t0_ns = ev["t0"].to_numpy("datetime64[ns]").astype(np.int64)
    cur = ms.event_curves(ticks, ev["ticker"].to_numpy(), t0_ns)
    m = ms.sign_curves(cur["curves"], ev["direction"].to_numpy())
    return ticks, ev, pools, m[:, ms.MAIN_IDX, :]


def test_relabelling_p_values_uniform_without_response():
    rng = np.random.default_rng(7)
    ps = []
    for _ in range(150):
        ticks, ev, pools, obs = synthetic_world(rng)
        res = inf.relabel_test(ticks, ev, pools, obs, k_perm=199, rng=rng)
        ps.append(res["p_M"][0])
    ps = np.array(ps)
    assert 0.01 <= np.mean(ps < 0.05) <= 0.11, np.mean(ps < 0.05)
    assert 0.38 <= np.mean(ps < 0.5) <= 0.62, np.mean(ps < 0.5)
    assert stats.kstest(ps, "uniform").pvalue > 0.01


def test_relabelling_detects_a_planted_response():
    rng = np.random.default_rng(8)
    ticks, ev, pools, obs = synthetic_world(rng, planted=12.0)
    res = inf.relabel_test(ticks, ev, pools, obs, k_perm=199, rng=rng)
    assert res["p_M"][0] == pytest.approx(1 / 200)
    assert res["p_h_holm"][2:, 0].max() < 0.05 and res["p_h"][0, 0] > 0.05       # response from 1 h, none at 15 min
    assert inf.first_response(res["p_h_holm"], (15, 30, 60, 120, 240, 480, 1440, 2880))[0] == 60


def test_placebo_curves_are_flat_without_response():
    rng = np.random.default_rng(9)
    ticks, ev, pools, obs = synthetic_world(rng, planted=12.0)
    pc = inf.placebo_curves(ticks, ev, pools, n_placebo=5, rng=rng)
    assert pc["n"] == 8 * 5 and abs(pc["mean_m"][ms.M_IDX, 0]) < 3.0


def test_date_bootstrap_caps_unreached_timings():
    rng = np.random.default_rng(10)
    G, I = len(ms.OFFSETS_H), len(INDICES)
    m = np.zeros((6, G, I))
    m[:, ms.ZERO_IDX + 12:, :] = 1.0                 # step after 1 hour for every event
    rp = np.zeros((6, G))
    rp[:, ms.ZERO_IDX + 12:] = 0.02
    bt = inf.date_bootstrap(m, rp, np.array([date(2026, 5, d) for d in (12, 13, 14, 15, 18, 19)]), n_boot=50, rng=rng)
    assert np.all(np.abs(bt["t_half"] - (ms.OFFSETS_H[ms.ZERO_IDX + 11] + 0.5 * 5 / 60)) < 1e-9)
    assert np.allclose(bt["rp_half"], 1.0)
    m2 = np.zeros((6, G, I))
    m2[:, ms.M_IDX, :] = 1.0                          # only the 48-hour point moves: T½ is "over 48 h" -> cap
    bt2 = inf.date_bootstrap(m2, rp, np.array([date(2026, 5, d) for d in (12, 13, 14, 15, 18, 19)]), n_boot=20, rng=rng)
    assert np.all(bt2["t_half"] >= 47.9)
