"""Load the research-window inputs from disk (through the holdout lock)."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from . import prices
from .config import DATA, DIVERGENCE_HIGH, INPUT_INDICES, RESULTS
from .filters import States
from .holdout import assert_locked
from .market import Market, build_market

PANEL = DATA / "panel" / "states.parquet"


def used_tickers() -> list[str]:
    return sorted(pd.read_csv(RESULTS / "used_universe.csv")["ticker"])


def data_snapshot() -> str:
    s = json.loads((RESULTS / "snapshot.json").read_text())
    return f"panel:{s['state_panel_sha256'][:12]}+prices:{s['prices_sha256'][:12]}"


def load_inputs() -> tuple[Market, States]:
    tickers = used_tickers()
    m = build_market(prices.load(), tickers)
    panel = pd.read_parquet(PANEL)
    panel["day"] = pd.to_datetime(panel["day"]).dt.date
    assert_locked(panel, "day", "state panel")
    panel = panel[panel["ticker"].isin(tickers)]
    window = m.sessions[m.ws:m.we + 1]

    def arr(col):
        return (panel.pivot(index="ticker", columns="day", values=col)
                .reindex(index=tickers, columns=window).to_numpy(dtype=float))

    div = arr("div_spread")
    div_high = np.where(np.isnan(div), np.nan, (div > DIVERGENCE_HIGH).astype(float))
    states = States(index={ix: arr(ix) for ix in INPUT_INDICES}, conf=arr("confidence"),
                    div_high=div_high, ws=m.ws)
    return m, states
