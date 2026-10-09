"""Phase 1: the seven synthetic checks of BRIEF.md, with their numbers, in results/phase1_synthetic.md.

Reuses the scenarios of the test suite (lag/tests). No real data is read.

    python -m lag.scripts.synthetic_summary
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from lag import inference as inf
from lag import measure as ms
from lag import pipeline as pl
from lag import synthetic as syn
from lag.config import RESULTS
from lag.tests.test_inference import synthetic_world
from lag.tests.test_measure import run_cell, ticks_from_hourly, world

H = 3_600_000_000_000


def fmt(x, d=2):
    return "n/a" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x:.{d}f}"


def main() -> None:
    rows = []

    # 1. data lock: counted from the saved test output.
    saved = RESULTS / "phase1_tests.txt"
    n_lock = sum(1 for l in saved.read_text().splitlines() if "test_lock.py::" in l and "PASSED" in l) if saved.exists() else 0
    rows.append(("Data lock, all three ranges", f"lag/tests/test_lock.py: {n_lock} tests pass (pilot range, reserved range, "
                 "definitive range for prices and for gated sentiment/events, after 23 November, plain dates, gate)",
                 "pass" if n_lock > 0 else "not run"))

    # 2. reading selection
    t0 = pd.Timestamp("2026-05-20 15:30", tz="UTC").value
    MIN = 60_000_000_000
    ticks = ms.Ticks.from_frame(syn.ticks_frame({"A": np.array([10.0, 20.0, 30.0])},
                                                np.array([t0 - 15 * MIN, t0, t0 + 15 * MIN], dtype=np.int64)))
    b, _ = ticks.before("A", t0)
    s0 = ticks.at_or_before("A", np.array([t0]))[0, 0]
    rows.append(("Reading selection around t0", f"ticks of 10, 20, 30 at t0 - 15 min, t0, t0 + 15 min: before reading {b[0]:.0f}, "
                 f"S(t0) {s0:.0f}", "pass" if b[0] == 10 and s0 == 20 else "FAIL"))

    # 3. planted step at a known delay
    for delay_h, hhmm, tick_min in ((2.0, "11:30", 15), (5.0, "16:00", 30)):
        rng, sess, tickers, stamps, bars = world()
        values, ev_rows = {}, []
        for i, t in enumerate(tickers):
            t0 = syn.bar_start(sess[5 + 3 * i], hhmm)
            values[t] = 50.0 + rng.normal(0, 0.01, len(stamps)) + syn.step(stamps, t0.value, int(delay_h * H), 10.0)
            ev_rows.append((t, t0, 1, "L-E1"))
        _, res = run_cell(syn.ticks_frame(values, stamps), syn.events_frame(ev_rows), bars, tickers, sess)
        ok = abs(res["t_half"][0] - delay_h) <= tick_min / 60 and abs(res["t_full"][0] - delay_h) <= tick_min / 60
        rows.append((f"Planted step of +10 at t0 + {delay_h:g} h ({hhmm} New York, tick spacing {tick_min} min)",
                     f"M {fmt(res['M'][0])}, T½ {fmt(res['t_half'][0])} h, T₉₀ {fmt(res['t_full'][0])} h, p(M) {fmt(res['p_M'][0], 3)}",
                     "pass" if ok else "FAIL"))

    # 4. smoothed step
    rng, sess, tickers, stamps, bars = world()
    values, ev_rows = {}, []
    for i, t in enumerate(tickers):
        t0 = syn.bar_start(sess[5 + 3 * i], "10:30")
        values[t] = syn.ema(stamps, 50.0 + syn.step(stamps, t0.value, 0, 10.0), 2.0) + rng.normal(0, 0.01, len(stamps))
        ev_rows.append((t, t0, 1, "L-E2"))
    _, res = run_cell(syn.ticks_frame(values, stamps), syn.events_frame(ev_rows), bars, tickers, sess)
    rows.append(("Step at t0 through a 2-hour exponential smoother",
                 f"T½ {fmt(res['t_half'][0])} h (continuous smoother: 2.00 h; the tick-wise smoother runs one 15-minute tick ahead), "
                 f"T₉₀ {fmt(res['t_full'][0])} h (6.64 h)", "pass" if abs(res["t_half"][0] - 2) <= 0.3 else "FAIL"))

    # 5. alignment
    for shift in (3, 0):
        rng, sess, tickers, stamps, bars = world(n_tickers=8)
        hb = ms.hourly_bars(bars, tickers, sess, 60)
        al = pl.alignment(ms.Ticks.from_frame(ticks_from_hourly(hb, shift)), hb, "score", n_boot=200, seed=3)
        rows.append((f"Alignment, index change equal to the price return {shift} hours earlier",
                     f"best k {al['best_k']} (95% interval {al['ci_k'][0]:.0f} to {al['ci_k'][1]:.0f}), correlation {fmt(al['best_corr'])}",
                     "pass" if al["best_k"] == shift else "FAIL"))
    rng, sess, tickers, stamps, bars = world(n_tickers=8)
    hb = ms.hourly_bars(bars, tickers, sess, 60)
    frames = []
    for t in hb.tickers:
        one = ms.HourlyBars(tickers=[t], sessions=hb.sessions, start_ns={t: hb.start_ns[t]}, end_ns={t: hb.end_ns[t]},
                            adj={t: hb.adj[t]}, session_idx={t: hb.session_idx[t]})
        frames.append(ticks_from_hourly(one, 0, noise=rng.normal(0, 0.002, len(hb.adj[t]))))
    al = pl.alignment(ms.Ticks.from_frame(pd.concat(frames, ignore_index=True)), hb, "score", n_boot=200, seed=4)
    rows.append(("Alignment, index unrelated to price",
                 f"largest correlation {fmt(al['best_corr'], 3)} at k {al['best_k']}; 95% interval for k {al['ci_k'][0]:.0f} to "
                 f"{al['ci_k'][1]:.0f} (no settled alignment)", "pass" if abs(al["best_corr"]) < 0.08 else "FAIL"))

    # 6. uniform p-values
    rng = np.random.default_rng(7)
    ps = []
    for _ in range(150):
        ticks, ev, pools, obs = synthetic_world(rng)
        ps.append(inf.relabel_test(ticks, ev, pools, obs, k_perm=199, rng=rng)["p_M"][0])
    ps = np.array(ps)
    ks = stats.kstest(ps, "uniform").pvalue
    rows.append(("No planted response: p-values of M over 150 synthetic worlds (8 stocks, 1 event each, K = 199)",
                 f"share below 0.05: {np.mean(ps < 0.05):.3f}; below 0.5: {np.mean(ps < 0.5):.3f}; "
                 f"Kolmogorov-Smirnov p against uniform {ks:.2f}", "pass" if ks > 0.01 else "FAIL"))

    # 7. price copy
    rng, sess, tickers, stamps, bars = world(n_tickers=12)
    ev_rows = []
    for i, t in enumerate(tickers):
        t0 = syn.bar_start(sess[4 + 2 * (i % 10)], ["10:30", "12:30"][i % 2])
        bars = syn.plant_bar_move(bars, t, t0, 0.04)
        ev_rows.append((t, t0, 1, "L-E2"))
    hb = ms.hourly_bars(bars, tickers, sess, 60)
    prep, res = run_cell(ticks_from_hourly(hb, 0), syn.events_frame(ev_rows), bars, tickers, sess, k_perm=50, n_boot=200)
    al = pl.alignment(prep.ticks, hb, "score", n_boot=200, seed=5)
    rows.append(("Index that only copies price (one-bar price step at each event)",
                 f"best k {al['best_k']} (correlation {fmt(al['best_corr'])}); T½ {fmt(res['t_half'][0])} h; "
                 f"Rₚ(T½) {fmt(res['rp_half'][0])} (95% interval {fmt(res['ci_rp_half'][0][0])} to {fmt(res['ci_rp_half'][0][1])})",
                 "pass" if al["best_k"] == 0 and abs(res["rp_half"][0] - 1) < 0.1 else "FAIL"))

    lines = ["# Phase 1 synthetic checks", "",
             "The seven checks of BRIEF.md section 7, Phase 1, on synthetic data only (no real ticks or bars). "
             "The full test suite is in results/phase1_tests.txt.", "",
             "| check | result | |", "|---|---|---|"]
    lines += [f"| {a} | {b} | {c} |" for a, b, c in rows]
    lines += ["", "Resolution note: T½ and T₉₀ are interpolated between 5-minute grid points of a step function, so a "
              "step exactly on a tick is reported up to half a tick early; every timing is reported next to the tick spacing.", ""]
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "phase1_synthetic.md").write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
