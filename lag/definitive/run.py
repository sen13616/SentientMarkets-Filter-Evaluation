"""Phase 4: the definitive run, once, on or after 24 November 2026 and after Experiment 5A's
definitive results are committed (the lock's gate). Measures everything in lag/definitive/config.py
and writes lag/definitive/results/; RESULTS.md is rendered separately.

    python -m lag.definitive.run
"""

from __future__ import annotations

from lag.definitive.config import EXTENDED_HOURS_CURVE, RESULTS, RUN
from lag.lock import LockViolation, gate_open
from lag.scripts.run_measures import main


def run() -> None:
    if not gate_open():
        raise LockViolation("the definitive run is gated until 5A's definitive results are committed, on or after "
                            "24 November 2026 (lag/lock.py gate_open)")
    main(RUN, out_dir=RESULTS, ext_hours=EXTENDED_HOURS_CURVE)


if __name__ == "__main__":
    run()
