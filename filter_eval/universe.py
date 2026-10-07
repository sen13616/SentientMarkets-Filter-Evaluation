"""Candidate and used universe (INSTRUCTIONS.md section 4; D7, D10)."""

from __future__ import annotations

import pandas as pd

from .config import ROOT

SEED_FILE = ROOT / "seed_universe.csv"


def candidates(path=SEED_FILE) -> list[str]:
    """Names added before 2026-10-03 with delisted_at null or after 2026-06-22."""
    d = pd.read_csv(path)
    added = pd.to_datetime(d["added_at"])
    delisted = pd.to_datetime(d["delisted_at"])
    keep = (added < pd.Timestamp("2026-10-03")) & (delisted.isna() | (delisted > pd.Timestamp("2026-06-22")))
    return sorted(d.loc[keep, "ticker"].tolist())


def used_universe(panel: pd.DataFrame, price_ok: pd.Series, sessions: list) -> pd.DataFrame:
    """Apply the coverage and price rules. Returns one row per candidate with the reasons.

    panel: state panel (ticker, day, state_valid). price_ok: bool per ticker, True when a
    price bar exists on every window session.
    """
    first5, last5 = set(sessions[:5]), set(sessions[-5:])
    g = panel.groupby("ticker")
    out = pd.DataFrame({
        "valid_share": g["state_valid"].mean(),
        "valid_first5": g.apply(lambda x: bool(x.loc[x["day"].isin(first5), "state_valid"].any())),
        "valid_last5": g.apply(lambda x: bool(x.loc[x["day"].isin(last5), "state_valid"].any())),
    })
    out["price_ok"] = price_ok.reindex(out.index).fillna(False).astype(bool)
    out["used"] = (out["valid_share"] >= 0.90) & out["valid_first5"] & out["valid_last5"] & out["price_ok"]
    return out.reset_index()
