"""Phase 0: noise units and a power estimate from non-event sessions only.

    SM_DATA_DIR=/path/to/data python -m responsiveness.scripts.power

Uses only two-session score changes on each stock's noise sessions (event-period
sessions more than two sessions from any E1-E3 candidate; DECISIONS.md A3). No change
around any event is read. Writes results/power.md and power.csv.

Method (DECISIONS.md P1-P3, A6):
- Placebo base rate p0: share of noise-session changes larger than one noise unit.
- Null draws: for each stock, as many noise sessions as it has kept events in the
  cell (without replacement; with replacement if it has fewer), 1,000 times.
- Response: significant when the observed rate exceeds the null's 95th percentile
  (p = (1 + #null >= obs) / 1001 < 0.05). The detectable response rate is the
  smallest rate r with P(Binomial(N, r) / N > that percentile) >= 0.80, treating
  events as independent.
- Signed average move (the amended primary rule's second test): the null multiplies
  the drawn changes by the cell's directions, permuted. A planted response of
  delta noise units in each event's direction adds delta x (mean noise unit) to the
  signed mean, so the detectable delta is (null 95th pct - 20th pct of the
  unpermuted draws) / mean noise unit.
- Direction accuracy (reported, no longer a pass condition): smallest true accuracy
  with 80% power for a two-sided exact binomial test at 0.05, at M = N x p0 and
  M = N x the detectable response rate.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from responsiveness import ledger, pipeline
from responsiveness.config import (ALPHA, CONTAMINATED, GROUPS, INDICES, MIN_NOISE_CHANGES, MOVE_UNITS, N_PERM,
                                   POWER_TARGET, PRIMARY_GROUP, PRIMARY_INDEX, RESULTS, SEED)

GRID = np.round(np.arange(0.0, 1.0001, 0.005), 3)


def null_draws(chg_by: dict[int, np.ndarray], sd_by: dict[int, float], n_by: dict[int, int], dirs: np.ndarray,
               rng) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Per draw: response rate, signed mean with permuted directions, and signed mean with the
    cell's directions as they are (events ordered by stock, matching `dirs`)."""
    cols, sds = [], []
    for i, n in n_by.items():
        x = chg_by[i]
        pick = (np.argsort(rng.random((N_PERM, len(x))), axis=1)[:, :n] if n <= len(x)
                else rng.integers(0, len(x), size=(N_PERM, n)))
        cols.append(x[pick])
        sds.append(np.full((N_PERM, n), sd_by[i]))
    C, S = np.hstack(cols), np.hstack(sds)
    resp = (np.abs(C) > MOVE_UNITS * S).mean(axis=1)
    perm = rng.permuted(np.tile(dirs, (N_PERM, 1)), axis=1)
    return resp, (C * perm).mean(axis=1), (C * dirs[None, :]).mean(axis=1)


def crit_of(null: np.ndarray) -> float:
    k = int(np.ceil((1 - ALPHA) * (N_PERM + 1))) - 1      # observed must exceed this order statistic
    return float(np.sort(null)[min(k, N_PERM - 1)])


def mde_rate(N: int, crit: float) -> float:
    for r in GRID:
        if stats.binom.sf(np.floor(crit * N + 1e-12), N, r) >= POWER_TARGET:
            return float(r)
    return float("nan")


def mde_accuracy(M: int) -> float:
    if M < 1:
        return float("nan")
    x = np.arange(M + 1)
    rej = np.array([stats.binomtest(int(k), M, 0.5).pvalue < ALPHA for k in x])
    for a in GRID[GRID >= 0.5]:
        if stats.binom.pmf(x, M, a)[rej & (x / M > 0.5)].sum() >= POWER_TARGET:
            return float(a)
    return float("nan")


def pct(x):
    return "n/a" if x is None or np.isnan(x) else f"{x:.1%}"


def main() -> None:
    inp = pipeline.load_inputs()
    st = pipeline.load_states(inp, with_date_only=False)
    kept = inp.cands[inp.cands["status"] == "kept"]
    tix = {t: i for i, t in enumerate(inp.tickers)}
    rng = np.random.default_rng(SEED)

    n_noise = st.noise_mask.sum(axis=1)
    L = ["# Noise units and power estimate (Phase 0, amended rules)", "",
         "Built from two-session score changes on noise sessions only: event-period sessions (13 May to 18 "
         "June 2026) more than two sessions from any E1, E2 or E3 candidate of the stock (DECISIONS.md A1, A3). "
         "No score change around any event was read. Method: see the docstring of "
         "`responsiveness/scripts/power.py`.", "",
         f"Data hash `{inp.data_hash}`; seed {SEED}; {N_PERM} null draws.", "",
         "## Noise sessions per stock", "",
         f"Noise sessions per stock (out of up to 26): min {n_noise.min()}, 10th pct "
         f"{int(np.percentile(n_noise, 10))}, median {int(np.median(n_noise))}, 90th pct "
         f"{int(np.percentile(n_noise, 90))}, max {n_noise.max()}. Stocks with fewer than {MIN_NOISE_CHANGES}: "
         f"{int((n_noise < MIN_NOISE_CHANGES).sum())}.", "",
         pd.Series(n_noise).value_counts().sort_index().rename("stocks").rename_axis("noise sessions")
         .to_frame().T.to_markdown(), ""]

    rows = []
    for a, ix in enumerate(INDICES):
        sd, n = st.sd[a], st.sd_n[a]
        good = ~np.isnan(sd)
        rows.append({"index": ix + (" (contaminated)" if ix in CONTAMINATED else ""),
                     "stocks with a noise unit": int(good.sum()),
                     f"excluded: fewer than {MIN_NOISE_CHANGES} changes": int((n < MIN_NOISE_CHANGES).sum()),
                     "excluded: SD = 0": int(((n >= MIN_NOISE_CHANGES) & ~good).sum()),
                     "median changes used": int(np.median(n[good])),
                     "median noise unit (pts)": round(float(np.median(sd[good])), 2),
                     "IQR noise unit (pts)": f"{np.percentile(sd[good], 25):.2f}-{np.percentile(sd[good], 75):.2f}"})
    L += ["## Noise units by index", "", pd.DataFrame(rows).to_markdown(index=False), "",
          "A stock without a noise unit for an index contributes no events to that index's cells.", ""]

    prow, head = [], {}
    for a, ix in enumerate(INDICES):
        chg_by, sd_by = {}, {}
        for i in range(len(inp.tickers)):
            if np.isnan(st.sd[a, i]):
                continue
            x = st.chg[a, i, st.noise_mask[i]]
            x = x[~np.isnan(x)]
            if len(x):
                chg_by[i], sd_by[i] = x, float(st.sd[a, i])
        allz = np.concatenate([chg_by[i] / sd_by[i] for i in chg_by])
        p0 = float((np.abs(allz) > MOVE_UNITS).mean())
        for g, (types, dfilt) in GROUPS.items():
            ev = kept[kept["type"].isin(types)]
            if dfilt is not None:
                ev = ev[ev["direction"] == dfilt]
            ev = ev[[tix[t] in chg_by for t in ev["ticker"]]]
            ev = ev.assign(row=ev["ticker"].map(tix)).sort_values("row", kind="stable")
            N = len(ev)
            if N == 0:
                continue
            n_by = ev.groupby("row", sort=True).size().to_dict()
            dirs = ev["direction"].to_numpy(dtype=float)
            resp, signed_null, signed_alt = null_draws(chg_by, sd_by, n_by, dirs, rng)
            crit_r, crit_s = crit_of(resp), crit_of(signed_null)
            r = mde_rate(N, crit_r)
            mean_sd = float(np.mean([sd_by[i] for i in ev["row"]]))
            delta = (crit_s - np.quantile(signed_alt, 1 - POWER_TARGET)) / mean_sd
            M0, M1 = int(round(N * p0)), (int(round(N * r)) if not np.isnan(r) else 0)
            prow.append({"index": ix + (" (contaminated)" if ix in CONTAMINATED else ""), "events": g, "N": N,
                         "placebo rate p0": pct(p0), "response null 95th pct": pct(crit_r),
                         "detectable response rate": pct(r),
                         "detectable signed move (noise units)": round(delta, 2),
                         "detectable signed move (pts)": round(delta * mean_sd, 2),
                         "mean noise unit (pts)": round(mean_sd, 2),
                         "moves at p0": M0, "detectable accuracy at p0": pct(mde_accuracy(M0)),
                         "moves at detectable rate": M1, "detectable accuracy at that rate": pct(mde_accuracy(M1))})
            if ix == PRIMARY_INDEX and g == PRIMARY_GROUP:
                head = {"N": N, "p0": round(p0, 4), "crit_response": round(crit_r, 4), "mde_rate": r,
                        "mde_signed_units": round(delta, 3), "mde_signed_pts": round(delta * mean_sd, 2)}
    p = pd.DataFrame(prow)
    prim = p[(p["index"] == PRIMARY_INDEX) & (p["events"] == PRIMARY_GROUP)]
    L += [f"## Primary cell: {PRIMARY_INDEX}, {PRIMARY_GROUP} pooled (amended rule, DECISIONS.md A6)", "",
          "The cell passes if response p < 0.05, signed-average-move p < 0.05 and the unexplained-move rate "
          "is below 50%. The smallest effects detectable with 80% power at the 0.05 level:", "",
          prim.set_index("events").T.to_markdown(), "",
          "## All cells: response and signed move", "",
          p[["index", "events", "N", "placebo rate p0", "response null 95th pct", "detectable response rate",
             "detectable signed move (noise units)", "detectable signed move (pts)", "mean noise unit (pts)"]]
          .to_markdown(index=False), "",
          "## All cells: direction accuracy (reported only; not a pass condition)", "",
          p[["index", "events", "moves at p0", "detectable accuracy at p0", "moves at detectable rate",
             "detectable accuracy at that rate"]].to_markdown(index=False), "",
          "## Caveats", "",
          "- Events are treated as independent. Events cluster in time (common news days), so the real tests "
          "will be somewhat less powerful than shown.",
          "- The null here is drawn from noise sessions only. The Phase 2 relabelling draws from every "
          "eligible event-period session of the stock, including sessions near E4 and other events "
          "(DECISIONS.md M3), so its null rate can differ from p0.",
          "- The signed-move estimate assumes a response of the same size in noise units for every event; a "
          "response concentrated in a few events needs a larger average to be detected.",
          "- The unexplained-move rate (the third condition) is not estimated here: its denominator includes "
          "changes around events.", ""]
    (RESULTS / "power.md").write_text("\n".join(L) + "\n")
    p.to_csv(RESULTS / "power.csv", index=False)
    row = ledger.append("phase0_power", inp.data_hash, SEED, head, note="amended rules (DECISIONS.md A1-A6)")
    print("\n".join(L))
    print("ledger:", row["code_commit"], row["headline"])


if __name__ == "__main__":
    main()
