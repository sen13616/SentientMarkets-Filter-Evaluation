"""Pre-pilot check: the relabelling test's p-values under no response, over many synthetic worlds.

Main check: the scenario of lag/tests/test_inference.py (8 stocks, one event each at 11:30 New York
on a random session, random-walk-plus-white-noise ticks, K = 199), same seed scheme, N worlds.
Diagnostics with the same seed: white noise only; random walk only; and the main scenario with the
placebo pool restricted to sessions on the event's weekday. Writes results/null_check.md.

    python -m lag.scripts.null_check [N]
"""

from __future__ import annotations

import json
import sys
import time

import numpy as np
import pandas as pd
from scipy import stats

from lag import inference as inf
from lag import measure as ms
from lag import synthetic as syn
from lag.config import B_BOOT, NY, RESULTS

H = 3_600_000_000_000
M_COL = int(np.flatnonzero(ms.MAIN_IDX == ms.M_IDX)[0])
BAND = (0.036, 0.064)


def spans_weekend(weekday: int) -> bool:
    """Whether a 48-hour window starting on this weekday (0 = Monday) crosses a weekend."""
    return weekday >= 3


def world(rng, n_events=8, n_sessions=28, walk=0.3, white=1.0, match_weekday=False, radius=2, match_class=False,
          seed_offset=0):
    """One synthetic world: `n_events` stocks with one event each. `radius` is the non-event
    radius in sessions; `match_class` keeps only pool sessions whose 48-hour window has the same
    weekend-crossing class as the event's; `match_weekday` keeps only the event's weekday."""
    sess = syn.sessions(n_sessions)
    stamps = syn.tick_times(sess)
    values, rows = {}, []
    for j in range(n_events):
        t = f"S{j:02d}"
        v = 50.0 + (np.cumsum(rng.normal(0, walk, len(stamps))) if walk else 0.0) + \
            (rng.normal(0, white, len(stamps)) if white else 0.0)
        t0 = syn.bar_start(sess[int(rng.integers(3, n_sessions - 4))], "11:30")
        rows.append((t, t0, int(rng.choice([-1, 1])), "L-E2"))
        values[t] = v
    ticks = ms.Ticks.from_frame(syn.ticks_frame(values, stamps))
    ev = syn.events_frame(rows)
    cand = {r.ticker: {pd.Timestamp(r.t0).tz_convert(NY).date()} for r in ev.itertuples()}
    pools = inf.pools(ticks, ev, inf.non_event_sessions(cand, sess, radius=radius))
    if match_weekday or match_class:
        new = []
        for e, r in enumerate(ev.itertuples()):
            wd = pd.Timestamp(r.t0).tz_convert(NY).weekday()
            days = np.asarray(pd.to_datetime(pools[e], utc=True).tz_convert(NY).weekday)
            keep = (days == wd) if match_weekday else (np.array([spans_weekend(d) for d in days]) == spans_weekend(wd))
            new.append(pools[e][keep])
        pools = new
    t0_ns = ev["t0"].to_numpy("datetime64[ns]").astype(np.int64)
    cur = ms.event_curves(ticks, ev["ticker"].to_numpy(), t0_ns)
    m = ms.sign_curves(cur["curves"], ev["direction"].to_numpy())
    return ticks, ev, pools, m[:, ms.MAIN_IDX, :]


def run(n_worlds: int, k_perm: int, n_boot: int = B_BOOT, **kw) -> dict:
    """Per world: the relabelling p for M and the date-bootstrap interval for M; the combined gate
    (L17) is p < 0.05 and the interval wholly above zero."""
    rng = np.random.default_rng(7)
    rng_boot = np.random.default_rng([7, 17])
    t = time.time()
    ps, lo = [], []
    for _ in range(n_worlds):
        ticks, ev, pools, obs = world(rng, **kw)
        ps.append(inf.relabel_test(ticks, ev, pools, obs, k_perm=k_perm, rng=rng)["p_M"][0])
        m48 = obs[:, M_COL, :1]                                             # E x 1, the 48-hour column
        dates = ev["t0"].dt.tz_convert(NY).dt.date.to_numpy()
        lo.append(inf.ci(inf.m_bootstrap(m48, dates, n_boot, rng_boot)[:, 0])[0])
    ps, lo = np.array(ps), np.array(lo)
    both = inf.gate(ps, lo)
    return {"n": n_worlds, "k": k_perm, "share05": float(np.mean(ps < 0.05)), "share10": float(np.mean(ps < 0.10)),
            "share50": float(np.mean(ps < 0.5)), "ks": float(stats.kstest(ps, "uniform").pvalue),
            "ci_above_zero": float(np.mean(lo > 0)), "combined": float(np.mean(both)),
            "se": float(np.sqrt(0.05 * 0.95 / n_worlds)), "seconds": round(time.time() - t)}


def main(n_worlds: int = 1000) -> None:
    variants = [
        ("main: random walk + white noise, pool on any non-event session", dict()),
        ("white noise only", dict(walk=0.0)),
        ("random walk only", dict(white=0.0)),
        ("random walk + white noise, pool restricted to the event's weekday", dict(match_weekday=True)),
    ]
    results = [(name, run(n_worlds, 199, **kw)) for name, kw in variants]
    main_r = results[0][1]
    lines = ["# Null check of the relabelling test and of the combined gate (before the pilot)", "",
             f"{n_worlds} synthetic worlds per variant with no planted response: 8 stocks with one event each at "
             "11:30 New York on a random session, K = 199 relabellings, seed 7 (the scenario of lag/tests/test_inference.py). "
             "The agreed band for the share of p-values below 0.05 is 3.6% to 6.4%. The combined gate (DECISIONS.md L17) "
             f"requires the relabelling p below 0.05 and the date-bootstrap 95% interval for M (B = {B_BOOT}) wholly above zero.", "",
             "| variant | relabelling: share p < 0.05 | share < 0.10 | share < 0.50 | KS p (uniform) | in band | "
             "bootstrap: share with interval above 0 | combined gate: false-positive rate | seconds |",
             "|---|---|---|---|---|---|---|---|---|"]
    for name, r in results:
        lines.append(f"| {name} | {r['share05']:.3f} | {r['share10']:.3f} | {r['share50']:.3f} | {r['ks']:.3f} | "
                     f"{'yes' if BAND[0] <= r['share05'] <= BAND[1] else 'NO'} | {r['ci_above_zero']:.3f} | "
                     f"**{r['combined']:.3f}** | {r['seconds']} |")
    lines += ["", f"Binomial standard error of a share near 0.05 with {n_worlds} worlds: {main_r['se']:.3f}.", "",
              f"**Headline (main scenario): relabelling alone {main_r['share05']:.1%} false positives; combined gate "
              f"{main_r['combined']:.1%}.** These two rates are quoted in RESULTS.md next to every gate decision.", ""]
    (RESULTS / "null_check.json").write_text(json.dumps(
        {"n_worlds": n_worlds, "k_perm": 199, "b_boot": B_BOOT, "relabel_rate": main_r["share05"],
         "combined_rate": main_r["combined"], "variants": {name: r for name, r in results}}, indent=1))
    lines += [
              "Reading: the share is about two standard errors above 5% in the main scenario and within the band "
              "for white noise alone and for a random walk alone, so the excess appears only when the two are "
              "combined; its cause is not pinned down here. Restricting the pool to the event's weekday shrinks each "
              "pool to about four sessions and makes the null coarser, not better. The synthetic worlds are a stand-in: "
              "how the real ticks move over 48 hours is not known before the run.", ""]
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "null_check.md").write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 1000)
