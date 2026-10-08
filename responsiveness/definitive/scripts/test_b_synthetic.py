"""Phase 0: how Test B behaves on synthetic data (no real data).

    python -m responsiveness.definitive.scripts.test_b_synthetic

Writes results/test_b_synthetic.md: the share of replications with p < 0.05, for Test B as first
specified (linear price control) and as amended (flexible price controls; DECISIONS.md P2), across
event designs, price echoes and planted effects. See responsiveness/definitive/synthetic.py.
"""

from __future__ import annotations

import numpy as np

from responsiveness.definitive.config import RESULTS
from responsiveness.definitive.synthetic import ECHOES, one_test

DESIGNS = {
    "independent": ("directions unrelated to price (random sessions)", {}),
    "rating_like": ("like E3: drawn toward bigger moves, about 70% agree with the move's sign", {"n_indep": 3}),
    "mixed": ("E1/E2-like (direction = sign of the move) plus independent, as in the pooled E1-E3 cell", {}),
    "price_labelled": ("like E1/E2 only: direction = sign of the move", {"n_indep": 0}),
}
REPS, K = 200, 199


def main() -> None:
    L = ["# Test B on synthetic data (Phase 0)", "",
         f"Each cell: share of {REPS} replications with p < 0.05 ({K} relabellings each). 60 stocks, 35 sessions. "
         "Scores are noise (SD 3 points) plus a price echo at every session, plus a planted effect of "
         "`delta` points in the event's direction at event sessions. Echoes: none; linear (100 x r: a 6% move "
         "gives 6 points); saturating (6 x tanh(r / 0.02)); step (4 x sign(r)); all three (their sum). Under delta = 0 a valid test "
         "rejects about 5% of the time; above 5% means it can be fooled.", ""]
    for controls, title in (("linear", "Test B as first specified (now a secondary cell when pooled over E1-E3): price control c x r"),
                            ("flexible", "Test B as amended (primary on E3): price controls r, sign(r) and a linear spline in r with the frozen knots")):
        L += [f"## {title}", "",
              "| events | echo | delta = 0 | delta = 1 point | delta = 2 points |", "|---|---|---|---|---|"]
        for dsg, (label, kw) in DESIGNS.items():
            for echo in ECHOES:
                cells = []
                for delta in (0.0, 1.0, 2.0):
                    rng = np.random.default_rng(2026)
                    p = np.array([one_test(rng, K=K, controls=controls, design=dsg, echo=echo, delta=delta, **kw)[1]
                                  for _ in range(REPS)])
                    cells.append("not estimable" if np.isnan(p).all() else f"{np.mean(p[~np.isnan(p)] < 0.05):.3f}")
                L.append(f"| {dsg}: {label} | {echo} | " + " | ".join(cells) + " |")
        L.append("")
    (RESULTS / "test_b_synthetic.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
