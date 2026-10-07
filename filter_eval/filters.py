"""Filters (INSTRUCTIONS.md section 8; D13, D17).

Filters act on the unfiltered strategy's trade list: they keep, drop or
re-weight its entries and never create an entry the base strategy does not
make. The state for an entry is the ticker's daily state on the decision
session t. A missing state skips the entry.

All functions are batched: state arrays have shape (K, T), one row per state
assignment (row 0 = actual states, further rows = permutations).
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd

# Gate thresholds (section 8; sensitivity variants per section 9 and D17).
GATE = {
    "base":  {"long": 61, "short": 40, "str": 41},
    "loose": {"long": 56, "short": 45, "str": 36},
    "tight": {"long": 66, "short": 35, "str": 46},
}
VETO_CONF = {"base": 60, "c50": 50, "c70": 70}


@dataclass
class States:
    """Daily state arrays on the window session grid, shape (N, Dw); NaN = missing."""
    index: dict[str, np.ndarray]   # input index name -> values
    conf: np.ndarray
    div_high: np.ndarray           # 1.0 / 0.0, NaN where no sub-index present
    ws: int                        # global index of the first window session
    div_high_exo: np.ndarray | None = None  # narrative/influencer/macro spread > 40 (D21); never NaN

    def lookup(self, arr: np.ndarray, trades: pd.DataFrame, perm: np.ndarray | None = None) -> np.ndarray:
        """State values for each trade's (ticker, decision day): (K, T)."""
        tk = trades["tk"].to_numpy()
        tr = trades["t"].to_numpy() - self.ws
        if perm is None:
            return arr[tk, tr][None, :]
        # perm: (K, N, Dw) column permutation per ticker
        return arr[tk[None, :], perm[:, tk, tr]]


def round_half_up(x: np.ndarray) -> np.ndarray:
    return np.floor(x + 0.5)


def gate_mask(idx: np.ndarray, trades: pd.DataFrame, strategy: str, level: str = "base") -> np.ndarray:
    th = GATE[level]
    r = round_half_up(idx)
    d = trades["dir"].to_numpy()[None, :]
    with np.errstate(invalid="ignore"):
        if strategy == "STR":
            ok = r >= th["str"]
        else:
            ok = np.where(d > 0, r >= th["long"], r <= th["short"])
    return ok & np.isfinite(idx)


def size_mult(idx: np.ndarray, trades: pd.DataFrame, strategy: str) -> np.ndarray:
    d = trades["dir"].to_numpy()[None, :]
    if strategy == "STR":
        m = (idx - 40.0) / 30.0
    else:
        m = np.where(d > 0, (idx - 50.0) / 30.0, (50.0 - idx) / 30.0)
    return np.where(np.isfinite(idx), np.clip(m, 0.0, 1.0), 0.0)


def exo_div_high(narrative: np.ndarray, influencer: np.ndarray, macro: np.ndarray) -> np.ndarray:
    """veto-exo divergence (D21): spread across the three non-market layers > 40;
    not high when fewer than two of them are present."""
    x = np.stack([narrative, influencer, macro])
    n = np.isfinite(x).sum(axis=0)
    with np.errstate(invalid="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # all-NaN slices

        spread = np.nanmax(x, axis=0) - np.nanmin(x, axis=0)
    return np.where((n >= 2) & (spread > 40.0), 1.0, 0.0)


def veto_mask(conf: np.ndarray, div_high: np.ndarray, level: str = "base") -> np.ndarray:
    with np.errstate(invalid="ignore"):
        keep = (conf >= VETO_CONF[level]) & (div_high == 0.0)
    return keep & np.isfinite(conf) & np.isfinite(div_high)


def redistribute_within_group(mult: np.ndarray, trades: pd.DataFrame) -> np.ndarray:
    """Scale kept entries so each leg/cohort keeps its unfiltered capital (exposure robustness)."""
    w = trades["w"].to_numpy()
    codes, _ = pd.factorize(trades["group"])
    G = codes.max() + 1 if len(codes) else 0
    out = np.empty_like(mult, dtype=float)
    for k in range(mult.shape[0]):
        kept = np.bincount(codes, weights=w * mult[k], minlength=G)
        full = np.bincount(codes, weights=w, minlength=G)
        with np.errstate(invalid="ignore", divide="ignore"):
            s = np.where(kept > 0, full / kept, 0.0)
        out[k] = mult[k] * s[codes]
    return out


def signed_weights(trades: pd.DataFrame, mult: np.ndarray | None = None) -> np.ndarray:
    base = (trades["dir"] * trades["w"]).to_numpy(dtype=float)
    return base[None, :] if mult is None else base[None, :] * mult
