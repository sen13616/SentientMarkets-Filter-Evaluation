"""Phase 1: numbers behind the synthetic checks (no real data).

    python -m responsiveness.scripts.synthetic_summary

Uses the same synthetic world as responsiveness/tests/test_inference.py and writes
results/phase1_synthetic.md.
"""

from __future__ import annotations

import numpy as np
from scipy import stats

from responsiveness.config import RESULTS
from responsiveness.inference import binom_p, date_bootstrap, relabel_tests, scorecard
from responsiveness.tests.test_inference import EV_PER_STOCK, N_SESS, N_STOCKS, world


def main() -> None:
    rng = np.random.default_rng(1)
    pr, ps, pb = [], [], []
    for _ in range(500):
        cell, D, elig, sigma = world(rng)
        r = relabel_tests(cell, D, elig, sigma, n_perm=199, rng=rng)
        s = scorecard(cell)
        pr.append(r["p_response"]); ps.append(r["p_signed"]); pb.append(binom_p(s["right"], s["moves"]))
    L = ["# Phase 1 synthetic checks", "",
         f"Synthetic world: {N_STOCKS} stocks, {N_SESS} sessions, {EV_PER_STOCK} events per stock (N = "
         f"{N_STOCKS * EV_PER_STOCK}); scores are unit random walks; noise unit = sqrt(2).", "",
         "## Null: random event dates, 500 replications (199 relabellings each)", "",
         "| test | share p < 0.05 | share p < 0.10 | median p | KS vs uniform, p |", "|---|---|---|---|---|"]
    for name, p in (("response (test 1)", pr), ("signed move (test 3)", ps), ("direction, exact binomial", pb)):
        p = np.array(p, float)
        p = p[~np.isnan(p)]
        L.append(f"| {name} | {(p < 0.05).mean():.3f} | {(p < 0.10).mean():.3f} | {np.median(p):.3f} | "
                 f"{stats.kstest(p, 'uniform').pvalue:.3f} |")
    L += ["", "The exact binomial test is discrete and conservative, so it is not expected to be uniform.", "",
          "## Planted responses (999 relabellings, 2,000 bootstrap draws)", "",
          "| plant | response rate | direction accuracy (95% CI) | signed move | p response | p signed | "
          "p binomial |", "|---|---|---|---|---|---|---|"]
    for size in (0.5, 1.0, 2.0):
        for sign, label in ((1, "right way"), (-1, "wrong way")):
            rng = np.random.default_rng(3)
            cell, D, elig, sigma = world(rng, plant=size, sign=sign)
            s = scorecard(cell)
            r = relabel_tests(cell, D, elig, sigma, n_perm=999, rng=rng)
            ci = date_bootstrap(cell, cell.session, 2000, rng)["direction_accuracy"]
            L.append(f"| {size} noise units, {label} | {s['response_rate']:.2f} | {s['direction_accuracy']:.2f} "
                     f"({ci[0]:.2f}-{ci[1]:.2f}) | {s['avg_signed_move']:+.2f} | {r['p_response']:.3f} | "
                     f"{r['p_signed']:.3f} | {binom_p(s['right'], s['moves']):.3g} |")
    (RESULTS / "phase1_synthetic.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
