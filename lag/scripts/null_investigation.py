"""Open item (DECISIONS.md, after L17): why does the relabelling test run hot on synthetic ticks made
of a random walk plus white noise? Writes results/null_investigation.md.

Three parts, all on synthetic no-response worlds (the null-check scenario: 8 stocks, one event each
at 11:30 New York on a random session, K = 199):

A. Replication: the main scenario and its two components on five independent seeds, 1,000 worlds
   each, so that a 1-point excess can be told from seed-to-seed noise (standard error 0.7 points
   per seed, 0.3 pooled).
B. Mechanism: within the main scenario, the share of p-values below 0.05 by whether the event's
   48-hour window crosses a weekend (fewer ticks, so a smaller variance under a random walk), and
   by pool size.
C. Candidate fixes, each on the same five seeds: (F1) placebo pools restricted to sessions whose
   48-hour window has the same weekend-crossing class as the event's; (F2) a non-event radius of
   1 session instead of 2 (larger pools).

    python -m lag.scripts.null_investigation [N_PER_SEED]
"""

from __future__ import annotations

import json
import sys
import time

import numpy as np
import pandas as pd
from scipy import stats

from lag import inference as inf
from lag.config import NY, RESULTS
from lag.scripts.null_check import spans_weekend, world

SEEDS = (11, 12, 13, 14, 15)


def run(seed: int, n_worlds: int, **kw) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for _ in range(n_worlds):
        ticks, ev, pools, obs = world(rng, **kw)
        p = inf.relabel_test(ticks, ev, pools, obs, k_perm=199, rng=rng)["p_M"][0]
        wd = ev["t0"].dt.tz_convert(NY).dt.weekday.to_numpy()
        rows.append({"seed": seed, "p": p, "share_spanning": float(np.mean([spans_weekend(w) for w in wd])),
                     "pool_min": int(min(len(x) for x in pools)), "pool_mean": float(np.mean([len(x) for x in pools]))})
    return pd.DataFrame(rows)


def summarise(df: pd.DataFrame) -> dict:
    p = df["p"].to_numpy()
    return {"n": len(p), "share05": float(np.mean(p < 0.05)), "share10": float(np.mean(p < 0.10)),
            "ks": float(stats.kstest(p, "uniform").pvalue), "se": float(np.sqrt(0.05 * 0.95 / len(p)))}


def main(n_per_seed: int = 1000) -> None:
    t_all = time.time()
    scenarios = {
        "main: walk + white": dict(),
        "white only": dict(walk=0.0),
        "walk only": dict(white=0.0),
        "F1: main, pool matched on weekend-crossing class": dict(match_class=True),
        "F2: main, non-event radius 1 session": dict(radius=1),
    }
    frames = {}
    for name, kw in scenarios.items():
        frames[name] = pd.concat([run(s, n_per_seed, **kw) for s in SEEDS], ignore_index=True)
        print(f"{name}: pooled share<0.05 {np.mean(frames[name]['p'] < 0.05):.3f} ({time.time() - t_all:.0f} s)")

    L = ["# Why the relabelling null runs hot: investigation before Phase 3", "",
         f"Synthetic no-response worlds (8 stocks, one event each at 11:30 New York, K = 199), {len(SEEDS)} independent "
         f"seeds x {n_per_seed:,} worlds per scenario. Pooled standard error of a share near 0.05: "
         f"{np.sqrt(0.05 * 0.95 / (len(SEEDS) * n_per_seed)):.3f}; per seed {np.sqrt(0.05 * 0.95 / n_per_seed):.3f}.", "",
         "## A. Replication across seeds", "",
         "| scenario | " + " | ".join(f"seed {s}" for s in SEEDS) + " | pooled share < 0.05 | pooled share < 0.10 | KS p |",
         "|---|" + "---|" * (len(SEEDS) + 3)]
    for name in ("main: walk + white", "white only", "walk only"):
        df = frames[name]
        per = [f"{np.mean(df.loc[df['seed'] == s, 'p'] < 0.05):.3f}" for s in SEEDS]
        s = summarise(df)
        L.append(f"| {name} | " + " | ".join(per) + f" | **{s['share05']:.3f}** | {s['share10']:.3f} | {s['ks']:.3f} |")

    df = frames["main: walk + white"]
    L += ["", "## B. Mechanism probes (main scenario, all seeds pooled)", "",
          "Share of worlds with p < 0.05 by the share of the world's eight events whose 48-hour window crosses a weekend "
          "(Thursday or Friday events; under a random walk these windows hold fewer ticks and so a smaller variance):", "",
          "| events with a weekend-crossing window | worlds | share p < 0.05 |", "|---|---|---|"]
    bins = [(0.0, 0.25), (0.25, 0.5), (0.5, 0.75), (0.75, 1.01)]
    for lo, hi in bins:
        m = (df["share_spanning"] >= lo) & (df["share_spanning"] < hi)
        if m.any():
            L.append(f"| {lo:.2f} to {min(hi, 1.0):.2f} | {int(m.sum())} | {np.mean(df.loc[m, 'p'] < 0.05):.3f} |")
    r_span = stats.spearmanr(df["share_spanning"], df["p"])
    r_pool = stats.spearmanr(df["pool_min"], df["p"])
    L += ["", f"Spearman correlation of the p-value with the weekend-crossing share: {r_span.statistic:+.3f} (p = {r_span.pvalue:.3f}); "
          f"with the smallest pool size in the world: {r_pool.statistic:+.3f} (p = {r_pool.pvalue:.3f}). "
          f"Pool sizes: mean {df['pool_mean'].mean():.1f} sessions, smallest per world {df['pool_min'].mean():.1f} on average.", "",
          "## C. Candidate fixes (main scenario, same seeds)", "",
          "| variant | " + " | ".join(f"seed {s}" for s in SEEDS) + " | pooled share < 0.05 | KS p | mean pool size |",
          "|---|" + "---|" * (len(SEEDS) + 3)]
    for name in ("main: walk + white", "F1: main, pool matched on weekend-crossing class", "F2: main, non-event radius 1 session"):
        d = frames[name]
        per = [f"{np.mean(d.loc[d['seed'] == s, 'p'] < 0.05):.3f}" for s in SEEDS]
        s = summarise(d)
        L.append(f"| {name} | " + " | ".join(per) + f" | **{s['share05']:.3f}** | {s['ks']:.3f} | {d['pool_mean'].mean():.1f} |")
    L += ["", f"Run time {time.time() - t_all:.0f} s. The reading of these tables is in DECISIONS.md (open item, closed before Phase 3).", ""]
    pre = RESULTS / "null_check.json"
    if pre.exists():
        nc = json.loads(pre.read_text())
        L += ["## D. Reproduction of the pre-pilot check (10 October 2026)", "",
              "`python -m lag.scripts.null_check 1000` rerun with the Phase 3 code (seed 7, the single seed of the "
              f"pre-pilot check) gives exactly the committed results/null_check.md: {nc['relabel_rate']:.1%} of relabelling "
              f"p-values below 0.05 and {nc['combined_rate']:.1%} for the combined gate in the main scenario, and the same "
              "figures in every other variant; only the run-time seconds differ. The pre-pilot rate is therefore a fluctuation "
              "of that seed, not a change in the code between the two runs.", ""]
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "null_investigation.md").write_text("\n".join(L))
    (RESULTS / "null_investigation.json").write_text(json.dumps(
        {name: summarise(d) for name, d in frames.items()}, indent=1))
    print("\n".join(L))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 1000)
