"""Turn kept events into measured cells (one per index x event group; DECISIONS.md M1, M7)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import GROUPS
from .inference import Cell


@dataclass
class Measured:
    cell: Cell
    dates: np.ndarray            # reaction-session column, for the date bootstrap
    events: pd.DataFrame         # the measured events (local use only; never committed)
    excluded: dict[str, int]     # events dropped from this cell, by reason


def group_events(kept: pd.DataFrame, group: str) -> pd.DataFrame:
    types, dfilt = GROUPS[group]
    ev = kept[kept["type"].isin(types)]
    return ev if dfilt is None else ev[ev["direction"] == dfilt]


def build_cell(ev: pd.DataFrame, bef: np.ndarray, aft: np.ndarray, a: int, sd: np.ndarray,
               tickers: list[str], sessions: list) -> Measured:
    """`ev` holds the group's kept events, with `k` the row of each in `bef`/`aft`
    (n_events x n_indices readings); `sd` is (index x ticker) noise units."""
    tix = {t: i for i, t in enumerate(tickers)}
    six = {d: j for j, d in enumerate(sessions)}
    row = ev["ticker"].map(tix).to_numpy()
    sig = sd[a, row] if len(ev) else np.array([])
    b, f = bef[ev["k"].to_numpy(), a], aft[ev["k"].to_numpy(), a]
    no_unit = np.isnan(sig)
    no_before = ~no_unit & np.isnan(b)
    no_after = ~no_unit & ~no_before & np.isnan(f)
    ok = ~(no_unit | no_before | no_after)
    sub = ev[ok].assign(row=row[ok], before=b[ok], after=f[ok], change=(f - b)[ok], sigma=sig[ok])
    col = sub["R"].map(six).to_numpy(dtype=int)
    cell = Cell(sub["row"].to_numpy(), col, sub["direction"].to_numpy(), sub["change"].to_numpy(),
                sub["sigma"].to_numpy())
    return Measured(cell=cell, dates=col, events=sub,
                    excluded={"no noise unit": int(no_unit.sum()), "no before reading": int(no_before.sum()),
                              "no after reading": int(no_after.sum())})
