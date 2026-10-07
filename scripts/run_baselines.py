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

from filter_eval import filters as F  # noqa: E402
from filter_eval import ledger  # noqa: E402
from filter_eval.config import INPUT_INDICES, RESULTS  # noqa: E402
from filter_eval.evaluate import ALL_STRATEGIES, Cell, run_cell  # noqa: E402
from filter_eval.load import data_snapshot, load_inputs  # noqa: E402
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

        # Pass rates: state lookups and filter rules only; no returns.
        tr = trades[trades["t"] >= m.d0].reset_index(drop=True)
        n = len(tr)
        for ix in INPUT_INDICES:
            v = states.lookup(states.index[ix], tr)
            valid = np.isfinite(v[0])
            g = F.gate_mask(v, tr, s)[0]
            z = F.size_mult(v, tr, s)[0]
            pass_rows.append({"strategy": s, "filter": "gate", "input": ix, "candidates": n,
                              "missing_state": int((~valid).sum()), "pass": int(g.sum()),
                              "fail_with_state": int((valid & ~g).sum())})
            pass_rows.append({"strategy": s, "filter": "size", "input": ix, "candidates": n,
                              "missing_state": int((~valid).sum()), "pass": int((z > 0).sum()),
                              "fail_with_state": int((valid & (z == 0)).sum()),
                              "full_size": int((z >= 1).sum())})
        conf = states.lookup(states.conf, tr)
        div = states.lookup(states.div_high, tr)
        valid = np.isfinite(conf[0]) & np.isfinite(div[0])
        keep = F.veto_mask(conf, div)[0]
        pass_rows.append({"strategy": s, "filter": "veto", "input": "confidence + divergence",
                          "candidates": n, "missing_state": int((~valid).sum()), "pass": int(keep.sum()),
                          "fail_with_state": int((valid & ~keep).sum()),
                          "vetoed_low_conf": int((valid & (conf[0] < 60)).sum()),
                          "vetoed_high_div": int((valid & (div[0] == 1)).sum())})

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

    # ---- pass rates
    pr = pd.DataFrame(pass_rows)
    pr.to_csv(RESULTS / "pass_rates.csv", index=False)
    pr["pass share"] = (pr["pass"] / pr["candidates"]).map(lambda x: f"{100 * x:.1f}%")
    plines = ["# Filter pass rates (counts only; no returns)", "",
              "Rendered by `scripts/run_baselines.py`. Candidates are the unfiltered entries decided "
              f"from {m.sessions[m.d0]}. Gate and size thresholds per INSTRUCTIONS.md section 8; "
              "size 'pass' = multiplier > 0; veto passes when confidence >= 60 and divergence is not "
              "high. `composite` is market-affected (D2).", ""]
    for f in ("gate", "size", "veto"):
        sub = pr[pr["filter"] == f].dropna(axis=1, how="all").drop(columns=["filter"])
        for c in sub.columns:
            if c not in ("strategy", "input", "pass share"):
                sub[c] = sub[c].astype(int)
        plines += [f"## {f.capitalize()}", "", sub.to_markdown(index=False), ""]
    (RESULTS / "pass_rates.md").write_text("\n".join(plines))
    print("wrote results/baselines.md, results/pass_rates.md")


if __name__ == "__main__":
    # optional: --note "reason for rerun" (recorded in the ledger)
    args = sys.argv[1:]
    main(args[args.index("--note") + 1] if "--note" in args else "Phase 3 baseline")
