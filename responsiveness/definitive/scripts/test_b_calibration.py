"""Phase 0: calibration of the two Test B versions on synthetic data, and the pre-registered
choice between them (DECISIONS.md D14).

    python -m responsiveness.definitive.scripts.test_b_calibration

Both versions use E3-like events and the flexible price controls with the frozen knots:
- relabelling: random-session relabelling within stock (P2);
- Freedman-Lane: permutation of the price-only model's residuals (D14).

Each scenario has 1,000 replications; each test uses K = 1,000 permutations. Writes
results/test_b_calibration.md and results/test_b_calibration.csv.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from responsiveness.definitive.config import RESULTS
from responsiveness.definitive.synthetic import SCORE_NOISE, one_test

REPS, K = 1000, 1000
SEEDS = {"relabel": 101, "freedman_lane": 202}
SCENARIOS = [  # (label, kwargs, kind)
    ("no effect, no echo", {}, "false positive"),
    ("no effect, linear echo", {"echo": "linear"}, "false positive"),
    ("no effect, saturating echo", {"echo": "saturating"}, "false positive"),
    ("no effect, step echo", {"echo": "step"}, "false positive"),
    (f"no effect, date-wide shock (SD {SCORE_NOISE:g} points, common to every event on a date)",
     {"date_shock": SCORE_NOISE}, "false positive"),
    ("planted effect of 1 point, no echo", {"delta": 1.0}, "power"),
]
FP_LO, FP_HI, POWER_MIN = 0.036, 0.064, 0.90


def main() -> None:
    rows = []
    for method, seed in SEEDS.items():
        rng = np.random.default_rng(seed)
        for label, kw, kind in SCENARIOS:
            p = np.array([one_test(rng, K=K, controls="flexible", method=method, design="rating_like", n_indep=3,
                                   **kw)[1] for _ in range(REPS)])
            r = float((p < 0.05).mean())
            rows.append({"method": method, "scenario": label, "kind": kind, "reject_rate": r,
                         "se": float(np.sqrt(r * (1 - r) / REPS)), "n_nan": int(np.isnan(p).sum())})
    df = pd.DataFrame(rows)
    df.to_csv(RESULTS / "test_b_calibration.csv", index=False)

    fl = df[df["method"] == "freedman_lane"]
    fp = fl[fl["kind"] == "false positive"]
    power = float(fl[fl["kind"] == "power"]["reject_rate"].iloc[0])
    fp_ok = bool(((fp["reject_rate"] >= FP_LO) & (fp["reject_rate"] <= FP_HI)).all())
    pw_ok = power >= POWER_MIN
    chosen = "Freedman-Lane" if (fp_ok and pw_ok) else "relabelling (with D13)"

    tab = df.pivot(index="scenario", columns="method", values="reject_rate").reindex([s[0] for s in SCENARIOS])
    se = df.pivot(index="scenario", columns="method", values="se").reindex(tab.index)
    L = ["# Test B calibration on synthetic data (Phase 0; DECISIONS.md D14)", "",
         f"E3-like events (drawn toward bigger moves; about 70% agree with the move's sign), flexible price "
         f"controls with the frozen knots. {REPS:,} replications per scenario; each test uses K = {K:,} "
         f"permutations. Seeds: relabelling {SEEDS['relabel']}, Freedman-Lane {SEEDS['freedman_lane']}. Each "
         "cell is the share of replications with p < 0.05 (standard error in brackets).", "",
         "| scenario | relabelling (P2) | Freedman-Lane (D14) |", "|---|---|---|"]
    for s in tab.index:
        L.append(f"| {s} | {tab.loc[s, 'relabel']:.3f} ({se.loc[s, 'relabel']:.3f}) | "
                 f"{tab.loc[s, 'freedman_lane']:.3f} ({se.loc[s, 'freedman_lane']:.3f}) |")
    L += ["", "## Pre-registered selection rule (DECISIONS.md D14)", "",
          f"Freedman-Lane becomes the primary Test B if its false-positive rate is between {FP_LO:.1%} and "
          f"{FP_HI:.1%} in every no-effect scenario and its power at 1 point is at least {POWER_MIN:.0%}.", "",
          f"- False-positive rates within {FP_LO:.1%} to {FP_HI:.1%} in every no-effect scenario: "
          f"**{'yes' if fp_ok else 'no'}** (range {fp['reject_rate'].min():.1%} to {fp['reject_rate'].max():.1%}).",
          f"- Power at 1 point at least {POWER_MIN:.0%}: **{'yes' if pw_ok else 'no'}** ({power:.1%}).",
          f"- **Primary Test B: {chosen}.** The other version is reported as secondary.", ""]
    (RESULTS / "test_b_calibration.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
