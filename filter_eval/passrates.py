"""Filter pass rates: counts of candidate entries passing each filter. Uses states only, no returns."""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import filters as F
from .config import INPUT_INDICES

AFFECTED = " (market-affected)"


def pass_rates(strategy: str, trades: pd.DataFrame, states: F.States, d0: int) -> list[dict]:
    tr = trades[trades["t"] >= d0].reset_index(drop=True)
    n = len(tr)
    rows = []
    for ix in INPUT_INDICES:
        v = states.lookup(states.index[ix], tr)
        valid = np.isfinite(v[0])
        g = F.gate_mask(v, tr, strategy)[0]
        z = F.size_mult(v, tr, strategy)[0]
        label = ix + (AFFECTED if ix == "composite" else "")
        rows.append({"strategy": strategy, "filter": "gate", "input": label, "candidates": n,
                     "missing_state": int((~valid).sum()), "pass": int(g.sum()),
                     "fail_with_state": int((valid & ~g).sum())})
        rows.append({"strategy": strategy, "filter": "size", "input": label, "candidates": n,
                     "missing_state": int((~valid).sum()), "pass": int((z > 0).sum()),
                     "fail_with_state": int((valid & (z == 0)).sum()), "full_size": int((z >= 1).sum())})
    conf = states.lookup(states.conf, tr)
    for name, div_arr, label in (("veto", states.div_high, "confidence + 4-layer divergence" + AFFECTED),
                                 ("veto-exo", states.div_high_exo, "confidence + exo divergence (D21)")):
        div = states.lookup(div_arr, tr)
        valid = np.isfinite(conf[0]) & np.isfinite(div[0])
        keep = F.veto_mask(conf, div)[0]
        rows.append({"strategy": strategy, "filter": name, "input": label, "candidates": n,
                     "missing_state": int((~valid).sum()), "pass": int(keep.sum()),
                     "fail_with_state": int((valid & ~keep).sum()),
                     "vetoed_low_conf": int((valid & (conf[0] < 60)).sum()),
                     "vetoed_high_div": int((valid & (div[0] == 1)).sum())})
    return rows


def render(pr: pd.DataFrame, first_decision) -> str:
    pr = pr.copy()
    pr["pass share"] = (pr["pass"] / pr["candidates"]).map(lambda x: f"{100 * x:.1f}%")
    lines = ["# Filter pass rates (counts only; no returns)", "",
             "Candidates are the unfiltered entries decided from "
             f"{first_decision}. Gate and size thresholds per INSTRUCTIONS.md section 8; size 'pass' = "
             "multiplier > 0. Veto passes when confidence >= 60 and divergence is not high; `veto` uses "
             "the four-layer divergence (includes the market layer), `veto-exo` the narrative/influencer/"
             "macro spread (D21). Rows marked market-affected use the contaminated market layer (D2).", ""]
    for f in ("gate", "size", "veto", "veto-exo"):
        sub = pr[pr["filter"] == f].dropna(axis=1, how="all").drop(columns=["filter"])
        for c in sub.columns:
            if c not in ("strategy", "input", "pass share"):
                sub[c] = sub[c].astype(int)
        lines += [f"## {f}", "", sub.to_markdown(index=False), ""]
    return "\n".join(lines)
