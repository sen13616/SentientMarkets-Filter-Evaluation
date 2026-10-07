"""Phase 4: run every filtered cell in the closed list (INSTRUCTIONS.md section 9 plus D21).

Writes results/cells/<cell>.json and appends one ledger row per cell, including failures.
Refuses to run from uncommitted code, so every ledger row carries a real commit hash.
"""

import json
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from filter_eval import ledger  # noqa: E402
from filter_eval.config import RESULTS  # noqa: E402
from filter_eval.evaluate import closed_cell_list, run_cell  # noqa: E402
from filter_eval.load import data_snapshot, load_inputs  # noqa: E402
from filter_eval.strategies import STRATEGIES  # noqa: E402

CELLS = RESULTS / "cells"
SEED = 20261007
N_PERM, N_BOOT, BLOCK = 1000, 2000, 10.0


def cell_file(cell_id: str) -> Path:
    return CELLS / (cell_id.replace("/", "__") + ".json")


def main(note: str):
    commit = ledger.code_commit()
    if commit == "uncommitted":
        sys.exit("refusing to run: commit filter_eval/, scripts/ and tests/ first")
    m, states = load_inputs()
    snap = data_snapshot()
    trades = {s: f(m) for s, f in STRATEGIES.items()}
    cells = [c for c in closed_cell_list() if c.filter != "none"]
    print(f"{len(cells)} filtered cells; code {commit}; data {snap}")
    failed = []
    for i, c in enumerate(cells, 1):
        base = {"cell": c.id, "config_hash": c.config_hash(), "code_commit": commit,
                "data_snapshot": snap, "seed": SEED}
        try:
            res = run_cell(c, m, states, trades[c.strategy], n_perm=N_PERM, n_boot=N_BOOT,
                           block=BLOCK, seed=SEED)
        except Exception as e:
            ledger.append({**base, "status": "failed", "note": f"{note}; {type(e).__name__}: {e}"[:250]})
            traceback.print_exc()
            failed.append(c.id)
            continue
        res.update({"data_snapshot": snap, "code_commit": commit, "n_perm": N_PERM,
                    "n_boot": N_BOOT, "block": BLOCK})
        cell_file(c.id).write_text(json.dumps(res, indent=1, default=float))
        ledger.append({**base, "status": "ok", "sharpe": res["f_sharpe"], "sharpe_diff": res["sharpe_diff"],
                       "p_perm": res["p_perm"], "n_trades": res["f_n_trades"],
                       "retention": res["retention"], "note": note})
        print(f"[{i:2d}/{len(cells)}] {c.id:42s} diff {res['sharpe_diff']:+.3f}  p {res['p_perm']:.3f}  "
              f"ret {res['retention']:.2f}", flush=True)
    print("failed:", failed)


if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[args.index("--note") + 1] if "--note" in args else "Phase 4")
