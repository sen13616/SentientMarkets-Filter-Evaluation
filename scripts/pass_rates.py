"""Render results/pass_rates.{csv,md} (counts only; no returns, no ledger rows: no cell is evaluated)."""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from filter_eval.config import RESULTS  # noqa: E402
from filter_eval.evaluate import ALL_STRATEGIES  # noqa: E402
from filter_eval.load import load_inputs  # noqa: E402
from filter_eval.passrates import pass_rates, render  # noqa: E402
from filter_eval.strategies import STRATEGIES  # noqa: E402

if __name__ == "__main__":
    m, states = load_inputs()
    rows = []
    for s in ALL_STRATEGIES:
        rows += pass_rates(s, STRATEGIES[s](m), states, m.d0)
    pr = pd.DataFrame(rows)
    pr.to_csv(RESULTS / "pass_rates.csv", index=False)
    (RESULTS / "pass_rates.md").write_text(render(pr, m.sessions[m.d0]) + "\n")
    print("wrote results/pass_rates.md")
