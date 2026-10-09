"""Phase 1 synthetic tests of the measurement: readings, planted steps, smoothing, alignment, price copy."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from lag import events as ev_mod
from lag import measure as ms
from lag import pipeline as pl
from lag import synthetic as syn
from lag.config import INDICES

H = 3_600_000_000_000
MIN = 60_000_000_000


# --------------------------------------------------------------------------- readings around t0

def test_tick_exactly_at_t0_is_not_a_before_reading():
    t0 = pd.Timestamp("2026-05-20 15:30", tz="UTC").value
    stamps = np.array([t0 - 15 * MIN, t0, t0 + 15 * MIN], dtype=np.int64)
    ticks = ms.Ticks.from_frame(syn.ticks_frame({"AAA": np.array([10.0, 20.0, 30.0])}, stamps))
    before, bts = ticks.before("AAA", t0)
    assert before[0] == 10.0 and bts == t0 - 15 * MIN
    s = ticks.at_or_before("AAA", np.array([t0 - 1, t0, t0 + 14 * MIN, t0 + 15 * MIN]))[:, 0]
    assert s.tolist() == [10.0, 20.0, 20.0, 30.0]
    cur = ms.event_curves(ticks, np.array(["AAA"]), np.array([t0]))
    assert cur["valid"][0] and cur["before"][0, 0] == 10.0
    assert cur["curves"][0, ms.ZERO_IDX, 0] == 10.0           # S(t0) - S(t0⁻) = 20 - 10
    assert cur["curves"][0, ms.ZERO_IDX - 1, 0] == 0.0        # 5 minutes before t0: still the before tick


def test_stale_before_reading_is_rejected():
    t0 = pd.Timestamp("2026-05-20 15:30", tz="UTC").value
    stamps = np.array([t0 - 3 * H, t0 + 15 * MIN], dtype=np.int64)
    ticks = ms.Ticks.from_frame(syn.ticks_frame({"AAA": np.array([10.0, 30.0])}, stamps))
    cur = ms.event_curves(ticks, np.array(["AAA"]), np.array([t0]))
    assert not cur["valid"][0] and np.isnan(cur["curves"][0]).all() and cur["before_age_s"][0] == 3 * 3600


def test_crossing_time_interpolates_and_caps():
    R = np.zeros(len(ms.OFFSETS_H))
    R[ms.ZERO_IDX + 24:] = 1.0                                 # step 2 h after t0 (24 x 5 min)
    assert ms.crossing_time(R, 0.5) == pytest.approx(ms.OFFSETS_H[ms.ZERO_IDX + 23] + 0.5 * 5 / 60)
    R2 = np.linspace(-0.2, 0.4, len(ms.OFFSETS_H))             # never reaches 0.5
    assert np.isnan(ms.crossing_time(R2, 0.5))
    assert ms.crossing_time(np.ones(len(ms.OFFSETS_H)), 0.5) == 0.0


# --------------------------------------------------------------------------- planted steps through the full path

def world(n_tickers=6, n_sessions=28, seed=0):
    rng = np.random.default_rng(seed)
    sess = syn.sessions(n_sessions)
    tickers = [f"S{i:02d}" for i in range(n_tickers)]
    stamps = syn.tick_times(sess)
    bars = syn.quiet_bars(tickers, sess, rng)
    return rng, sess, tickers, stamps, bars


def run_cell(ticks_df, events, bars, tickers, sess, seed=1, k_perm=100, n_boot=100):
    panel = ev_mod.build_panel(bars, tickers, sess)
    cand = {r.ticker: {pd.Timestamp(r.t0).tz_convert("America/New_York").date()} for r in events.itertuples()}
    prep = pl.prepare(ticks_df, events, panel, 60, cand, sess)
    return prep, pl.measure_cell(prep, np.ones(len(events), bool), seed, k_perm=k_perm, n_boot=n_boot, n_placebo=5)


@pytest.mark.parametrize("delay_h,hhmm,tol_h", [(2.0, "11:30", 0.25), (0.0, "11:30", 0.25), (5.0, "16:00", 0.5)])
def test_planted_step_recovered_within_one_tick(delay_h, hhmm, tol_h):
    """A step of +10 in every index at t0 + delay: T½ and T₉₀ land within one tick of the delay
    (15 minutes in session, 30 outside)."""
    rng, sess, tickers, stamps, bars = world()
    values, rows = {}, []
    for i, t in enumerate(tickers):
        t0 = syn.bar_start(sess[5 + 3 * i], hhmm)
        values[t] = 50.0 + rng.normal(0, 0.01, len(stamps)) + syn.step(stamps, t0.value, int(delay_h * H), 10.0)
        rows.append((t, t0, 1, "L-E1"))
    prep, res = run_cell(syn.ticks_frame(values, stamps), syn.events_frame(rows), bars, tickers, sess)
    assert res["n"] == len(tickers)
    for i in range(len(INDICES)):
        assert res["M"][i] == pytest.approx(10.0, abs=0.1)
        assert abs(res["t_half"][i] - delay_h) <= tol_h, res["t_half"]
        assert abs(res["t_full"][i] - delay_h) <= tol_h, res["t_full"]
    assert (res["p_M"] <= 0.02).all()                            # 6 events, step of 10 against 0.01 noise


def test_smoothed_step_gives_half_life_timing():
    """A raw step at t0 through a 2-hour exponential smoother: T½ about 2 h, T₉₀ about 6.6 h."""
    rng, sess, tickers, stamps, bars = world()
    values, rows = {}, []
    for i, t in enumerate(tickers):
        t0 = syn.bar_start(sess[5 + 3 * i], "10:30")
        raw = 50.0 + syn.step(stamps, t0.value, 0, 10.0)
        values[t] = syn.ema(stamps, raw, 2.0) + rng.normal(0, 0.01, len(stamps))
        rows.append((t, t0, 1, "L-E2"))
    prep, res = run_cell(syn.ticks_frame(values, stamps), syn.events_frame(rows), bars, tickers, sess)
    # The smoother applies a tick's weight at the tick itself, so the discrete response runs one
    # tick (15 min) ahead of the continuous 1 - 0.5^(t / 2 h): T½ about 1.75 to 2 h, T₉₀ about 6.4 to 6.64 h.
    for i in range(len(INDICES)):
        assert abs(res["t_half"][i] - 2.0) <= 0.3, res["t_half"]
        assert abs(res["t_full"][i] - 6.64) <= 0.5, res["t_full"]


def test_direction_sign_flips_the_curve():
    rng, sess, tickers, stamps, bars = world()
    values, rows = {}, []
    for i, t in enumerate(tickers):
        t0 = syn.bar_start(sess[5 + 3 * i], "11:30")
        values[t] = 50.0 - syn.step(stamps, t0.value, H, 8.0)                       # falls by 8 one hour later
        rows.append((t, t0, -1, "L-E2"))                                            # a downward event
    prep, res = run_cell(syn.ticks_frame(values, stamps), syn.events_frame(rows), bars, tickers, sess)
    assert res["M"][0] == pytest.approx(8.0) and abs(res["t_half"][0] - 1.0) <= 0.25


# --------------------------------------------------------------------------- alignment

def ticks_from_hourly(hb: ms.HourlyBars, shift: int, scale: float = 1000.0, noise: np.ndarray | None = None):
    """An index whose change over each session hour equals the market-adjusted return `shift` hours
    earlier (positive shift: the score lags price). Values are set at bar ends and held between."""
    values, stamps = {}, {}
    for t in hb.tickers:
        x = np.nan_to_num(hb.adj[t])
        y = np.zeros_like(x)
        if shift >= 0:
            y[shift:] = x[:len(x) - shift] if shift else x
        else:
            y[:len(x) + shift] = x[-shift:]
        if noise is not None:
            y = noise
        s = 50.0 + scale * np.cumsum(y)
        stamps[t] = np.r_[hb.start_ns[t][0] - H, hb.end_ns[t]]
        values[t] = np.r_[50.0, s]
    frames = [syn.ticks_frame({t: values[t]}, stamps[t]) for t in hb.tickers]
    return pd.concat(frames, ignore_index=True)


@pytest.mark.parametrize("shift", [3, 0, -2])
def test_alignment_recovers_planted_offset(shift):
    rng, sess, tickers, stamps, bars = world(n_tickers=8)
    hb = ms.hourly_bars(bars, tickers, sess, 60)
    ticks = ms.Ticks.from_frame(ticks_from_hourly(hb, shift))
    res = pl.alignment(ticks, hb, "score", n_boot=50, seed=3)
    assert res["best_k"] == shift and res["best_corr"] > 0.95
    assert res["ci_k"] == (shift, shift)


def test_alignment_finds_none_without_a_relation():
    rng, sess, tickers, stamps, bars = world(n_tickers=8)
    hb = ms.hourly_bars(bars, tickers, sess, 60)
    frames = []
    for t in hb.tickers:
        noise = rng.normal(0, 0.002, len(hb.adj[t]))
        frames.append(ticks_from_hourly(ms.HourlyBars(tickers=[t], sessions=hb.sessions, start_ns={t: hb.start_ns[t]},
                                                      end_ns={t: hb.end_ns[t]}, adj={t: hb.adj[t]},
                                                      session_idx={t: hb.session_idx[t]}), 0, noise=noise))
    ticks = ms.Ticks.from_frame(pd.concat(frames, ignore_index=True))
    res = pl.alignment(ticks, hb, "score", n_boot=50, seed=4)
    assert abs(res["best_corr"]) < 0.08                       # 8 x 28 x 7 = 1,568 pairs: noise level about 0.025
    lo, hi = res["ci_k"]
    assert hi - lo >= 6                                        # the bootstrap cannot settle on one k


def test_hourly_aggregation_of_15_minute_bars_matches_hourly_bars():
    rng, sess, tickers, _, _ = world(n_tickers=3, n_sessions=4)
    b15 = syn.quiet_bars(tickers, sess, rng, bar_minutes=15)
    hb = ms.hourly_bars(b15, tickers, sess, 15)
    for t in tickers:
        assert len(hb.start_ns[t]) == 7 * len(sess)
        starts = pd.to_datetime(hb.start_ns[t], utc=True).tz_convert("America/New_York").strftime("%H:%M")
        assert sorted(set(starts)) == ["09:30", "10:30", "11:30", "12:30", "13:30", "14:30", "15:30"]
    # the hour's return is the compounded 15-minute return, market-adjusted by the mean across tickers
    g = b15[(b15["ticker"] == tickers[0]) & (b15["session"] == sess[0])].sort_values("ts").iloc[:4]
    expected = g["close"].iloc[-1] / g["open"].iloc[0] - 1
    rets = []
    for t in tickers:
        gt = b15[(b15["ticker"] == t) & (b15["session"] == sess[0])].sort_values("ts").iloc[:4]
        rets.append(gt["close"].iloc[-1] / gt["open"].iloc[0] - 1)
    assert hb.adj[tickers[0]][0] == pytest.approx(expected - np.mean(rets), abs=1e-12)


# --------------------------------------------------------------------------- an index that copies price

def test_price_copy_is_aligned_at_zero_and_price_is_done_at_t_half():
    """Every event is a one-bar price step; the index copies price at bar ends. Then the index is
    aligned at k = 0, T½ is one bar, and Rₚ(T½) is about 1: the price move is complete when the
    score is half done."""
    rng, sess, tickers, stamps, bars = world(n_tickers=12)
    rows = []
    for i, t in enumerate(tickers):
        t0 = syn.bar_start(sess[4 + 2 * (i % 10)], ["10:30", "12:30"][i % 2])
        bars = syn.plant_bar_move(bars, t, t0, 0.04)
        rows.append((t, t0, 1, "L-E2"))
    hb = ms.hourly_bars(bars, tickers, sess, 60)
    ticks_df = ticks_from_hourly(hb, 0)
    events = syn.events_frame(rows)
    prep, res = run_cell(ticks_df, events, bars, tickers, sess, k_perm=50, n_boot=100)
    i = 0
    assert res["M"][i] > 0 and 0.9 <= res["t_half"][i] <= 1.1, res["t_half"]
    assert res["rp_half"][i] == pytest.approx(1.0, abs=0.1), res["rp_half"]
    assert res["ci_rp_half"][i][0] > 0.9
    al = pl.alignment(prep.ticks, hb, "score", n_boot=50, seed=5)
    assert al["best_k"] == 0 and al["best_corr"] > 0.99


def test_price_series_handles_microsecond_bar_stamps():
    """A bar store read from parquet carries microsecond stamps; the price curve must still move."""
    rng, sess, tickers, stamps, bars = world(n_tickers=3, n_sessions=6)
    t0 = syn.bar_start(sess[2], "10:30")
    bars = syn.plant_bar_move(bars, tickers[0], t0, 0.05)
    bars["ts"] = bars["ts"].dt.as_unit("us")
    panel = ev_mod.build_panel(bars, tickers, sess)
    ps = ms.PriceSeries.from_panel(panel, 60)
    rp = ms.price_curves(ps, np.array([tickers[0]]), np.array([t0.value]))[0]
    assert rp[ms.ZERO_IDX] == 0.0 and rp[ms.M_IDX] > 0.03 and np.isfinite(rp).all()
