"""Sensitivity (reported only): unexplained-move rate without E4 as an explanation.

    SM_DATA_DIR=/path/to/data python -m responsiveness.scripts.unexplained_sensitivity

Same large moves and the same price rule as the main run (DECISIONS.md M6), but only
E1, E2 and E3 candidates count as event explanations (DECISIONS.md M13). Writes
results/unexplained_sensitivity.csv with both rates side by side. The primary verdict
is unchanged by this file.
"""

from __future__ import annotations

import pandas as pd

from responsiveness import events, ledger, pipeline
from responsiveness.config import CONTAMINATED, INDICES, LARGE_MOVE_UNITS, PRIMARY_INDEX, RESULTS, SEED
from responsiveness.inference import unexplained


def main() -> None:
    inp = pipeline.load_inputs()
    st = pipeline.load_states(inp, with_date_only=False)
    price_near = pipeline.price_near_matrix(inp.prices, inp.tickers, st.sessions)
    near_all = pipeline.near_matrix(inp.tickers, st.sessions, inp.ev_sessions, inp.cal, 1)
    near_e123 = pipeline.near_matrix(inp.tickers, st.sessions,
                                     events.event_sessions(inp.cands, ("E1", "E2", "E3")), inp.cal, 1)
    rows = []
    for a, ix in enumerate(INDICES):
        u_all = unexplained(st.chg[a], st.sd[a], st.period, near_all, price_near, LARGE_MOVE_UNITS)
        u_x = unexplained(st.chg[a], st.sd[a], st.period, near_e123, price_near, LARGE_MOVE_UNITS)
        rows.append({"index": ix, "contaminated": ix in CONTAMINATED, "large": u_all["large"],
                     "unexplained (all events)": u_all["unexplained"], "rate (all events)": u_all["rate"],
                     "unexplained (E4 not counted)": u_x["unexplained"], "rate (E4 not counted)": u_x["rate"],
                     "explained only by E4": u_x["unexplained"] - u_all["unexplained"]})
    df = pd.DataFrame(rows)
    df.to_csv(RESULTS / "unexplained_sensitivity.csv", index=False)
    p = df[df["index"] == PRIMARY_INDEX].iloc[0]
    ledger.append("sensitivity_unexplained_no_e4", inp.data_hash, SEED,
                  {"index": PRIMARY_INDEX, "rate_all": round(p["rate (all events)"], 4),
                   "rate_no_e4": round(p["rate (E4 not counted)"], 4)}, note="reported only (DECISIONS.md M13)")
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
