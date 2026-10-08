"""Phase 0: noise units and a power estimate from non-event sessions only.

    SM_DATA_DIR=/path/to/data python -m responsiveness.scripts.power

Uses only two-session score changes on each stock's noise sessions (sessions in
the event period more than two sessions from any candidate event). No change
around any event is read. Writes results/power.md.

Method (DECISIONS.md P1-P3):
- Placebo base rate p0: share of noise-session changes larger than one noise unit.
- Response: the relabelling null is simulated by drawing, for each stock, as many
  noise sessions as it has kept events (without replacement; with replacement if it
  has fewer noise sessions than events), 1,000 times. A result is significant when
  the observed rate is above the null's 95th percentile (p = (1 + #null >= obs) /
  1001 < 0.05). The detectable response rate is the smallest rate r with
  P(Binomial(N, r) / N > that percentile) >= 0.80, treating events as independent.
- Direction: for M moves, the smallest true accuracy with 80% power for a two-sided
  exact binomial test at 0.05, and for the primary rule (accuracy >= 60% and the
  95% interval above 50%, with the exact Clopper-Pearson interval standing in for
  the bootstrap). M is shown at N x p0 (no response beyond the base rate) and at N
  x the detectable response rate.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from responsiveness import ledger, pipeline
from responsiveness.config import (ALPHA, CONTAMINATED, EVENT_TYPES, INDICES, MOVE_UNITS, N_PERM,
                                   POWER_TARGET, PRIMARY_INDEX, PRIMARY_MIN_ACCURACY, RESULTS, SEED)

GROUPS = {"E1": ["E1"], "E2": ["E2"], "E1+E2": ["E1", "E2"], "E3": ["E3"], "E4": ["E4"]}
GRID = np.round(np.arange(0.0, 1.0001, 0.005), 3)


def null_crit(z_by_stock: dict[int, np.ndarray], n_by_stock: dict[int, int], rng) -> tuple[float, float]:
    """95th-percentile response rate under the simulated relabelling null, and its mean."""
    N = sum(n_by_stock.values())
    sims = np.empty(N_PERM)
    for b in range(N_PERM):
        hits = 0
        for i, n in n_by_stock.items():
            z = z_by_stock[i]
            pick = rng.choice(len(z), size=n, replace=n > len(z))
            hits += int((np.abs(z[pick]) > MOVE_UNITS).sum())
        sims[b] = hits / N
    k = int(np.ceil((1 - ALPHA) * (N_PERM + 1))) - 1      # obs must exceed this order statistic
    return float(np.sort(sims)[min(k, N_PERM - 1)]), float(sims.mean())


def mde_rate(N: int, crit: float) -> float:
    for r in GRID:
        if stats.binom.sf(np.floor(crit * N + 1e-12), N, r) >= POWER_TARGET:
            return float(r)
    return float("nan")


def mde_accuracy_binom(M: int) -> float:
    if M < 1:
        return float("nan")
    x = np.arange(M + 1)
    rej = np.array([stats.binomtest(int(k), M, 0.5).pvalue < ALPHA for k in x])
    for a in GRID[GRID >= 0.5]:
        if stats.binom.pmf(x, M, a)[rej & (x / M > 0.5)].sum() >= POWER_TARGET:
            return float(a)
    return float("nan")


def mde_accuracy_primary(M: int) -> float:
    if M < 1:
        return float("nan")
    x = np.arange(M + 1)
    lo = np.array([stats.binomtest(int(k), M, 0.5).proportion_ci(0.95, method="exact").low for k in x])
    ok = (x / M >= PRIMARY_MIN_ACCURACY) & (lo > 0.5)
    for a in GRID[GRID >= 0.5]:
        if stats.binom.pmf(x, M, a)[ok].sum() >= POWER_TARGET:
            return float(a)
    return float("nan")


def fmt(x, pct=True):
    return "n/a" if x is None or (isinstance(x, float) and np.isnan(x)) else (f"{x:.1%}" if pct else f"{x}")


def main() -> None:
    inp = pipeline.load_inputs()
    st = pipeline.load_states(inp)
    kept = inp.cands[inp.cands["status"] == "kept"]
    tix = {t: i for i, t in enumerate(inp.tickers)}
    rng = np.random.default_rng(SEED)

    n_noise = st.noise_mask.sum(axis=1)
    L = ["# Noise units and power estimate (Phase 0)", "",
         "Built from two-session score changes on noise sessions only (sessions in the event period more "
         "than two sessions from any candidate event of the stock). No score change around any event was "
         "read. Method: see the docstring of `responsiveness/scripts/power.py` and DECISIONS.md.", "",
         f"Data hash `{inp.data_hash}`; seed {SEED}; {N_PERM} null draws.", "",
         "## Noise sessions per stock", "",
         f"Event-period sessions with a defined two-session change: up to 27 per stock. Noise sessions per "
         f"stock: min {n_noise.min()}, 10th pct {int(np.percentile(n_noise, 10))}, median "
         f"{int(np.median(n_noise))}, 90th pct {int(np.percentile(n_noise, 90))}, max {n_noise.max()}.", "",
         pd.Series(n_noise).value_counts().sort_index().rename("stocks").rename_axis("noise sessions")
         .to_frame().T.to_markdown(), ""]

    # Noise units per index.
    rows = []
    for a, ix in enumerate(INDICES):
        sd, n = st.sd[a], st.sd_n[a]
        good = ~np.isnan(sd) & (sd > 0)
        rows.append({"index": ix + (" (contaminated)" if ix in CONTAMINATED else ""),
                     "stocks with a noise unit": int(good.sum()),
                     "SD = 0": int((sd == 0).sum()), "fewer than 2 changes": int(np.isnan(sd).sum()),
                     "median changes used": int(np.median(n)),
                     "median noise unit (pts)": round(float(np.nanmedian(np.where(good, sd, np.nan))), 2),
                     "IQR noise unit (pts)": f"{np.nanpercentile(np.where(good, sd, np.nan), 25):.2f}-"
                                             f"{np.nanpercentile(np.where(good, sd, np.nan), 75):.2f}"})
    L += ["## Noise units by index", "", pd.DataFrame(rows).to_markdown(index=False), "",
          "A stock with no noise unit for an index (SD 0 or fewer than 2 changes) cannot have moves measured "
          "on that index; its events drop out of that index's cells.", ""]

    # Power.
    prow, head = [], {}
    for a, ix in enumerate(INDICES):
        sd = st.sd[a]
        z_by = {}
        for i in range(len(inp.tickers)):
            if np.isnan(sd[i]) or sd[i] <= 0:
                continue
            z = st.chg[a, i, st.noise_mask[i]] / sd[i]
            z = z[~np.isnan(z)]
            if len(z):
                z_by[i] = z
        allz = np.concatenate(list(z_by.values())) if z_by else np.array([])
        p0 = float((np.abs(allz) > MOVE_UNITS).mean()) if len(allz) else float("nan")
        for g, types in GROUPS.items():
            ev = kept[kept["type"].isin(types)]
            n_by = ev.groupby("ticker").size()
            n_by = {tix[t]: int(n) for t, n in n_by.items() if tix[t] in z_by}
            N = sum(n_by.values())
            if N == 0:
                continue
            crit, mean = null_crit(z_by, n_by, rng)
            r = mde_rate(N, crit)
            M0, M1 = int(round(N * p0)), (int(round(N * r)) if not np.isnan(r) else 0)
            prow.append({"index": ix + (" (contaminated)" if ix in CONTAMINATED else ""), "events": g, "N": N,
                         "placebo rate p0": fmt(p0), "null 95th pct": fmt(crit),
                         "detectable response rate": fmt(r),
                         "moves at p0": M0, "detectable accuracy (binomial) at p0": fmt(mde_accuracy_binom(M0)),
                         "detectable accuracy (primary rule) at p0": fmt(mde_accuracy_primary(M0)),
                         "moves at detectable rate": M1,
                         "detectable accuracy (binomial)": fmt(mde_accuracy_binom(M1)),
                         "detectable accuracy (primary rule)": fmt(mde_accuracy_primary(M1))})
            if ix == PRIMARY_INDEX and g == "E1+E2":
                head = {"N": N, "p0": round(p0, 4), "crit": round(crit, 4), "mde_rate": r}
    p = pd.DataFrame(prow)
    prim = p[(p["index"] == PRIMARY_INDEX) & (p["events"] == "E1+E2")]
    L += ["## Primary cell: score_exo, E1 and E2 pooled", "", prim.set_index("events").T.to_markdown(), "",
          "## All cells: detectable response rate", "",
          p[["index", "events", "N", "placebo rate p0", "null 95th pct", "detectable response rate"]]
          .to_markdown(index=False), "",
          "## All cells: detectable direction accuracy", "",
          "At 80% power. 'Primary rule' means accuracy >= 60% with the 95% interval wholly above 50%.", "",
          p[["index", "events", "moves at p0", "detectable accuracy (binomial) at p0",
             "detectable accuracy (primary rule) at p0", "moves at detectable rate",
             "detectable accuracy (binomial)", "detectable accuracy (primary rule)"]].to_markdown(index=False), "",
          "## Caveats", "",
          "- Events are treated as independent. Events cluster in time (e.g. common news days), so the "
          "bootstrap over event dates in Phase 2 will give wider intervals than the exact binomial interval "
          "used here; the detectable accuracies are optimistic.",
          "- The null here is drawn from noise sessions only. Which sessions the Phase 2 relabelling draws "
          "from is fixed in Phase 1 (DECISIONS.md); if it includes sessions near events, its null rate will "
          "differ from p0.",
          "- The unexplained-move rate (the primary rule's third condition) is not estimated here: its "
          "denominator includes changes around events.", ""]
    (RESULTS / "power.md").write_text("\n".join(L) + "\n")
    p.to_csv(RESULTS / "power.csv", index=False)
    row = ledger.append("phase0_power", inp.data_hash, SEED, head)
    print("\n".join(L))
    print("ledger:", row["code_commit"], row["headline"])


if __name__ == "__main__":
    main()
