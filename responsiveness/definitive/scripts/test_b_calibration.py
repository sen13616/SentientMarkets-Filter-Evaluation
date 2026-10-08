"""Phase 0: false-positive rate of the primary Test B on synthetic data, at 1,000 replications.

    python -m responsiveness.definitive.scripts.test_b_calibration

The primary Test B (E3-like events, flexible price controls with the frozen knots) under no
planted effect, with no price echo and with all three echoes at once (linear + saturating +
step). 1,000 replications of 199 relabellings each, seed 99. Writes
results/test_b_calibration.md.
"""

from __future__ import annotations

import numpy as np
from scipy import stats

from responsiveness.definitive.config import RESULTS
from responsiveness.definitive.synthetic import one_test

REPS, K, SEED = 1000, 199, 99


def main() -> None:
    L = ["# Primary Test B: false-positive rate on synthetic data (Phase 0)", "",
         f"E3-like events (drawn toward bigger moves; about 70% agree with the move's sign), flexible price "
         f"controls with the frozen knots, no planted effect. {REPS:,} replications of {K} relabellings each, "
         f"seed {SEED}. A test that is exactly calibrated rejects 5% of the time at the 0.05 level.", "",
         "| price echo | share p < 0.05 (SE) | share p < 0.10 | median p | KS vs uniform, p |",
         "|---|---|---|---|---|"]
    for echo in ("none", "all three"):
        rng = np.random.default_rng(SEED)
        p = np.array([one_test(rng, K=K, controls="flexible", design="rating_like", n_indep=3, echo=echo)[1]
                      for _ in range(REPS)])
        r = (p < 0.05).mean()
        L.append(f"| {echo} | {r:.3f} ({np.sqrt(r * (1 - r) / REPS):.3f}) | {(p < 0.10).mean():.3f} | "
                 f"{np.median(p):.3f} | {stats.kstest(p, 'uniform').pvalue:.3f} |")
    L += ["", "The rate is the same with and without the echo: the price controls absorb the echo. Both sit "
          "slightly above 5%. In this design ratings land on bigger moves and often agree with the move's "
          "sign, so the real estimate of b varies a little more than the relabelled null allows for "
          "(DECISIONS.md D13).", ""]
    (RESULTS / "test_b_calibration.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
