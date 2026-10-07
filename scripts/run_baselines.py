"""Phase 3: unfiltered baselines on the research window, plus filter pass rates (counts only).

Writes results/cells/base_<strategy>.json, results/baselines.md, results/pass_rates.csv and
results/pass_rates.md, and appends one ledger row per baseline cell. No filtered strategy
is run: the pass rates count entries that would pass each filter and use no returns.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from filter_eval import ledger  # noqa: E402
from filter_eval.config import RESULTS  # noqa: E402
from filter_eval.evaluate import ALL_STRATEGIES, Cell, run_cell  # noqa: E402
from filter_eval.load import data_snapshot, load_inputs  # noqa: E402
from filter_eval.passrates import pass_rates, render  # noqa: E402
from filter_eval.strategies import STRATEGIES  # noqa: E402

CELLS = RESULTS / "cells"
SEED = 20261007


def fmt(x, nd=3):
    if isinstance(x, (int, np.integer)):
        return f"{x:,}"
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "n/a" if x is None or np.isnan(x) else ("inf" if x > 0 else "-inf")
    return f"{x:.{nd}f}"


def main(note: str = "Phase 3 baseline"):
    m, states = load_inputs()
    snap = data_snapshot()
    commit = ledger.code_commit()
    CELLS.mkdir(parents=True, exist_ok=True)
    print(f"used universe {m.n}, window sessions {m.we - m.ws + 1}, data {snap}, code {commit}")

    rows, pass_rows = [], []
    for s in ALL_STRATEGIES:
        trades = STRATEGIES[s](m)
        cell = Cell(f"base/{s}", s, "none")
        try:
            res = run_cell(cell, m, states, trades, seed=SEED)
            status = "ok"
        except Exception as e:  # ledger failures too (ground rule 4)
            ledger.append({"cell": cell.id, "config_hash": cell.config_hash(), "code_commit": commit,
                           "data_snapshot": snap, "seed": SEED, "status": "failed",
                           "note": f"{type(e).__name__}: {e}"[:200]})
            raise
        res.update({"data_snapshot": snap, "code_commit": commit,
                    "n_decision_days": int(trades["t"].nunique())})
        (CELLS / f"base_{s}.json").write_text(json.dumps(res, indent=1, default=float))
        ledger.append({"cell": cell.id, "config_hash": cell.config_hash(), "code_commit": commit,
                       "data_snapshot": snap, "seed": SEED, "status": status,
                       "sharpe": res["sharpe"], "n_trades": res["n_trades"],
                       "note": note})
        rows.append(res)
        print(f"  {s}: sharpe {res['sharpe']:.3f}, trades {res['n_trades']}")

        pass_rows += pass_rates(s, trades, states, m.d0)

    # ---- baselines.md
    cols = [("sharpe", "Sharpe"), ("mean_daily", "Mean daily"), ("sd_daily", "SD daily"),
            ("total_return", "Total return"), ("profit_factor", "Profit factor"),
            ("max_drawdown", "Max DD"), ("hit_rate", "Hit rate"), ("n_trades", "Trades"),
            ("turnover", "Turnover/day"), ("avg_gross", "Avg gross"), ("avg_net", "Avg net"),
            ("beta", "Beta (EW)"), ("n_sessions", "P&L sessions"), ("n_decision_days", "Days with entries")]
    tab = pd.DataFrame([{"Strategy": r["strategy"], **{lab: fmt(r[k], 4 if "daily" in k else 3)
                                                      for k, lab in cols}} for r in rows])
    lines = ["# Unfiltered baselines (research window)", "",
             f"Rendered by `scripts/run_baselines.py` from `results/cells/base_*.json`. Data snapshot "
             f"`{snap}`; code `{commit}`; seed {SEED}.", "",
             f"Used universe {m.n} names. Decisions {m.sessions[m.d0]} to {m.sessions[m.we - 1]}; "
             f"P&L sessions {m.sessions[m.d0 + 1]} to {m.sessions[m.we]}. Costs 10 bp per side on "
             "netted traded notional. Conventions in DECISIONS.md D13 to D18.", "",
             tab.to_markdown(index=False), ""]
    (RESULTS / "baselines.md").write_text("\n".join(lines))

    # ---- pass rates (shared with scripts/pass_rates.py)
    pr = pd.DataFrame(pass_rows)
    pr.to_csv(RESULTS / "pass_rates.csv", index=False)
    (RESULTS / "pass_rates.md").write_text(render(pr, m.sessions[m.d0]) + "\n")
    print("wrote results/baselines.md, results/pass_rates.md")


if __name__ == "__main__":
    # optional: --note "reason for rerun" (recorded in the ledger)
    args = sys.argv[1:]
    main(args[args.index("--note") + 1] if "--note" in args else "Phase 3 baseline")
