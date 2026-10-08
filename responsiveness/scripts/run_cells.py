"""Phase 2: measure every cell, run the tests, ledger each cell.

    SM_DATA_DIR=/path/to/data python -m responsiveness.scripts.run_cells

Writes aggregate results only: results/cells.csv (one row per index x event group),
results/unexplained.csv (one row per index), results/run_meta.json, and under
results/nulls/ every cell's 1,000 relabelled values (relabel.csv.gz) and 2,000
bootstrap draws (bootstrap.csv.gz). The per-event
table goes to the local data root and is never committed.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from responsiveness import events, ledger, pipeline
from responsiveness.cells import build_cell, group_events
from responsiveness.config import (CONTAMINATED, EVENT_DIR, GROUPS, INDICES, LARGE_MOVE_UNITS, N_BOOT, N_PERM,
                                   N_PLACEBO, PRIMARY_GROUP, PRIMARY_INDEX, RESULTS, SEED, config_hash)
from responsiveness.inference import (bh_adjust, binom_p, date_bootstrap, placebo, primary_verdict,
                                      relabel_tests, scorecard, unexplained)
from responsiveness.measure import event_readings


def cell_rng(a: int, g: int) -> np.random.Generator:
    """Each cell's own stream from the fixed seed (DECISIONS.md M8)."""
    return np.random.default_rng([SEED, a, g])


def main() -> None:
    inp = pipeline.load_inputs()
    st = pipeline.load_states(inp)
    kept = inp.cands[(inp.cands["status"] == "kept")].reset_index(drop=True)
    kept["k"] = np.arange(len(kept))
    bef, aft = event_readings(st.book, kept)
    any_near = pipeline.near_matrix(inp.tickers, st.sessions, inp.ev_sessions, inp.cal, 1)
    e4_win = pipeline.near_matrix(inp.tickers, st.sessions, events.event_sessions(inp.cands, ("E4",)), inp.cal, 1)
    price_near = pipeline.price_near_matrix(inp.prices, inp.tickers, st.sessions)

    rows, urows, measured, nulls, boots, ledger_rows = [], [], [], [], [], []
    for a, ix in enumerate(INDICES):
        u = unexplained(st.chg[a], st.sd[a], st.period, any_near, price_near, LARGE_MOVE_UNITS)
        urows.append({"index": ix, "contaminated": ix in CONTAMINATED, **u})
        eligible = st.period[None, :] & ~np.isnan(st.D[a])
        for gi, g in enumerate(GROUPS):
            rng = cell_rng(a, gi)
            m = build_cell(group_events(kept, g), bef, aft, a, st.sd, inp.tickers, st.sessions)
            sc = scorecard(m.cell)
            rt = relabel_tests(m.cell, st.D[a], eligible, st.sd[a], N_PERM, rng)
            ci = date_bootstrap(m.cell, m.dates, N_BOOT, rng)
            pl = placebo(m.cell, st.D[a], st.noise_mask, st.sd[a], N_PLACEBO, rng)
            psc = pl["scorecard"]
            row = {"index": ix, "group": g, "contaminated": ix in CONTAMINATED,
                   "primary": ix == PRIMARY_INDEX and g == PRIMARY_GROUP, **sc,
                   **{f"excluded: {k}": v for k, v in m.excluded.items()},
                   "distinct dates": int(len(np.unique(m.dates))),
                   "p_response": rt["p_response"], "null_response_mean": rt["null_response_mean"],
                   "p_signed": rt["p_signed"], "null_signed_mean": rt["null_signed_mean"],
                   "p_direction_binom": binom_p(sc["right"], sc["moves"]),
                   "response_ci_lo": ci["response_rate"][0], "response_ci_hi": ci["response_rate"][1],
                   "accuracy_ci_lo": ci["direction_accuracy"][0], "accuracy_ci_hi": ci["direction_accuracy"][1],
                   "signed_ci_lo": ci["avg_signed_move"][0], "signed_ci_hi": ci["avg_signed_move"][1],
                   "placebo_n": psc["n"], "placebo_response_rate": psc["response_rate"],
                   "placebo_direction_accuracy": psc["direction_accuracy"],
                   "placebo_avg_signed_move": psc["avg_signed_move"],
                   "placebo_in_e4_window": int(sum(e4_win[s, j] for s, j in pl["picks"])),
                   "unexplained_rate_index": u["rate"]}
            rows.append(row)
            measured.append(m.events.assign(index=ix, group=g))
            nulls.append(pd.DataFrame({"index": ix, "group": g, "draw": np.arange(len(rt["null_response"])),
                                       "null_response_rate": rt["null_response"],
                                       "null_avg_signed_move": rt["null_signed"]}))
            b = pd.DataFrame(ci["draws"], columns=["response_rate", "direction_accuracy", "avg_signed_move"])
            boots.append(b.assign(index=ix, group=g, draw=np.arange(len(b))))
            ledger_rows.append((f"cell:{ix}:{g}", f"{SEED}/{a}/{gi}",
                          {k: (round(v, 4) if isinstance(v, float) else v) for k, v in
                           [("n", sc["n"]), ("response_rate", sc["response_rate"]), ("p_response", rt["p_response"]),
                            ("avg_signed_move", sc["avg_signed_move"]), ("p_signed", rt["p_signed"]),
                            ("direction_accuracy", sc["direction_accuracy"])]}))

    df = pd.DataFrame(rows)
    # Benjamini-Hochberg per test family over secondary cells, market channel excluded (M7).
    fam = ~df["primary"] & ~df["contaminated"]
    for col in ("p_response", "p_signed", "p_direction_binom"):
        df[f"{col}_bh"] = np.nan
        df.loc[fam, f"{col}_bh"] = bh_adjust(df.loc[fam, col].to_numpy())
    prim = df[df["primary"]].iloc[0]
    u_prim = next(r for r in urows if r["index"] == PRIMARY_INDEX)
    verdict = primary_verdict(prim["p_response"], prim["p_signed"], u_prim["rate"])

    RESULTS.mkdir(parents=True, exist_ok=True)
    df.to_csv(RESULTS / "cells.csv", index=False)
    (RESULTS / "nulls").mkdir(exist_ok=True)
    pd.concat(nulls, ignore_index=True).to_csv(RESULTS / "nulls" / "relabel.csv.gz", index=False,
                                               float_format="%.6g")
    bcols = ["index", "group", "draw", "response_rate", "direction_accuracy", "avg_signed_move"]
    pd.concat(boots, ignore_index=True)[bcols].to_csv(RESULTS / "nulls" / "bootstrap.csv.gz", index=False,
                                                      float_format="%.6g")
    pd.DataFrame(urows).to_csv(RESULTS / "unexplained.csv", index=False)
    meta = {"run_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "code_commit": ledger.code_commit(), "config_hash": config_hash(), "data_hash": inp.data_hash,
            "seed": SEED, "n_perm": N_PERM, "n_boot": N_BOOT, "n_placebo": N_PLACEBO,
            "cells": int(len(df)), "secondary_cells_in_bh": int(fam.sum()),
            "primary": {"index": PRIMARY_INDEX, "group": PRIMARY_GROUP, **verdict,
                        "p_response": prim["p_response"], "p_signed": prim["p_signed"],
                        "unexplained_rate": u_prim["rate"]}}
    (RESULTS / "run_meta.json").write_text(json.dumps(meta, indent=1, default=str))
    EVENT_DIR.mkdir(parents=True, exist_ok=True)
    out = pd.concat(measured, ignore_index=True)
    for c in ("R", "R_alt", "R_minus_1", "R_plus_1", "cluster_last_R"):
        out[c] = out[c].astype(str)
    out.to_parquet(EVENT_DIR / "measured_events.parquet", index=False)
    # Ledger only once every output is written, so a failed run leaves no partial rows.
    for test_id, seed, head in ledger_rows:
        ledger.append(test_id, inp.data_hash, seed, head)
    ledger.append("primary_verdict", inp.data_hash, SEED, meta["primary"])
    print(json.dumps(meta, indent=1, default=str))


if __name__ == "__main__":
    main()
