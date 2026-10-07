"""Cell definitions (closed list, INSTRUCTIONS.md section 9) and the cell runner."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import date

import numpy as np
import pandas as pd

from . import filters as F
from .config import FIRST_DECISION, INPUT_INDICES, SUBWINDOW_START
from .engine import COST_PER_SIDE, Book, RunResult, build_book, run
from .inference import (beta, bootstrap_sharpe_diff, max_drawdown, perm_pvalue, profit_factor,
                        sharpe)
from .market import Market

PRIMARY = ("CSM", "STR")
ALL_STRATEGIES = ("CSM", "STR", "TSMOM", "BRK", "RSI-MR")


@dataclass(frozen=True)
class Cell:
    id: str
    strategy: str
    filter: str                 # none | gate | size | veto | veto-exo
    index: str | None = None    # input index (gate/size)
    level: str = "base"         # threshold variant
    redistribute: bool = False  # exposure robustness
    start: str = str(FIRST_DECISION)  # first decision session

    def config_hash(self) -> str:
        return hashlib.sha256(json.dumps(asdict(self), sort_keys=True).encode()).hexdigest()[:12]


def closed_cell_list() -> list[Cell]:
    cells = [Cell(f"base/{s}", s, "none") for s in ALL_STRATEGIES]
    cells += [Cell(f"gate/{s}/{ix}", s, "gate", ix) for s in ALL_STRATEGIES for ix in INPUT_INDICES]
    cells += [Cell(f"size/{s}/{ix}", s, "size", ix) for s in ALL_STRATEGIES for ix in INPUT_INDICES]
    cells += [Cell(f"veto/{s}", s, "veto") for s in ALL_STRATEGIES]
    for s in PRIMARY:
        cells += [Cell(f"sens/gate-loose/{s}/score_exo", s, "gate", "score_exo", "loose"),
                  Cell(f"sens/gate-tight/{s}/score_exo", s, "gate", "score_exo", "tight"),
                  Cell(f"sens/veto-c50/{s}", s, "veto", None, "c50"),
                  Cell(f"sens/veto-c70/{s}", s, "veto", None, "c70")]
    cells += [Cell(f"expo/gate-redistribute/{s}/score_exo", s, "gate", "score_exo", redistribute=True)
              for s in PRIMARY]
    cells += [Cell(f"sub/gate/{s}/narrative", s, "gate", "narrative", start=str(SUBWINDOW_START))
              for s in PRIMARY]
    # Amendment D21 (2026-10-07): veto with divergence over the three non-market layers.
    cells += [Cell(f"veto-exo/{s}", s, "veto-exo") for s in ALL_STRATEGIES]
    return cells


def market_affected(cell: Cell) -> bool:
    """Cells whose input includes the contaminated market layer: the composite index and every
    veto that uses four-layer divergence (D2, D21)."""
    return cell.index == "composite" or cell.filter == "veto"


def entry_states(cell: Cell, states: F.States, trades: pd.DataFrame, perm=None):
    """Return (mult (K,T), valid (K,T)) for the cell's filter."""
    if cell.filter in ("veto", "veto-exo"):
        conf = states.lookup(states.conf, trades, perm)
        div = states.lookup(states.div_high if cell.filter == "veto" else states.div_high_exo, trades, perm)
        valid = np.isfinite(conf) & np.isfinite(div)
        return F.veto_mask(conf, div, cell.level).astype(float), valid
    idx = states.lookup(states.index[cell.index], trades, perm)
    valid = np.isfinite(idx)
    if cell.filter == "gate":
        mult = F.gate_mask(idx, trades, cell.strategy, cell.level).astype(float)
        if cell.redistribute:
            mult = F.redistribute_within_group(mult, trades)
        return mult, valid
    if cell.filter == "size":
        return F.size_mult(idx, trades, cell.strategy), valid
    raise ValueError(cell.filter)


def _metrics(book: Book, res: RunResult, k: int, mult: np.ndarray | None, pnl_sl: slice,
             mkt: np.ndarray) -> dict:
    r = res.ret[k, pnl_sl]
    taken = np.ones(len(book.trade_ret), bool) if mult is None else mult[k] > 0
    w_abs = book.trades["w"].to_numpy() * (1.0 if mult is None else mult[k])
    if res.k is not None:  # size filter: weight at entry includes that day's gross factor
        w_abs = w_abs * res.k[k, book.entry_rel]
    tr = book.trade_ret[taken]
    n_s = r.shape[-1]
    return {
        "sharpe": float(sharpe(r)), "mean_daily": float(r.mean()), "sd_daily": float(r.std(ddof=1)),
        "total_return": float(r.sum()), "profit_factor": profit_factor(w_abs[taken] * tr),
        "max_drawdown": max_drawdown(r), "hit_rate": float(np.mean(tr > 0)) if len(tr) else float("nan"),
        "n_trades": int(taken.sum()), "turnover": float(res.traded[k, pnl_sl].sum() / n_s),
        "avg_gross": float(res.gross[k, pnl_sl].mean()), "avg_net": float(res.net[k, pnl_sl].mean()),
        "beta": beta(r, mkt), "n_sessions": int(n_s),
        "n_long": int((taken & (book.trades["dir"].to_numpy() > 0)).sum()),
        "n_short": int((taken & (book.trades["dir"].to_numpy() < 0)).sum()),
        "avg_eff_n": float(np.nanmean(res.eff_n[k, pnl_sl])) if np.isfinite(res.eff_n[k, pnl_sl]).any()
                     else float("nan"),
    }


def ew_market(m: Market) -> np.ndarray:
    C = m.close[m.ws - 1:m.we + 1]
    return np.nanmean(C[1:] / C[:-1] - 1.0, axis=1)


def run_cell(cell: Cell, m: Market, states: F.States, base_trades: pd.DataFrame, *,
             n_perm: int = 1000, n_boot: int = 2000, block: float = 10.0, seed: int = 20261007,
             perm_chunk: int = 100, cost: float = COST_PER_SIDE) -> dict:
    """Evaluate one cell. Returns metrics, comparator metrics and inference."""
    start = date.fromisoformat(cell.start)
    t0 = m.idx(start)
    trades = base_trades[base_trades["t"] >= t0].reset_index(drop=True)
    book = build_book(m, trades, cost)
    pnl_sl = slice(t0 + 1 - m.ws, m.we - m.ws + 1)   # P&L from the first possible entry session
    mkt = ew_market(m)[pnl_sl]
    base_res = run(book, F.signed_weights(book.trades))
    out = {"cell": cell.id, "strategy": cell.strategy, "filter": cell.filter, "index": cell.index,
           "level": cell.level, "redistribute": cell.redistribute, "start": cell.start,
           "config_hash": cell.config_hash(), "seed": seed}
    base_m = _metrics(book, base_res, 0, None, pnl_sl, mkt)
    if cell.filter == "none":
        out.update(base_m)
        return out

    rng = np.random.default_rng(seed)
    mult, valid = entry_states(cell, states, book.trades)
    target = base_res.gross[0] if cell.filter == "size" else None
    W = F.signed_weights(book.trades, mult)
    res = run(book, W, target)
    filt_m = _metrics(book, res, 0, mult, pnl_sl, mkt)
    rf, ru = res.ret[0, pnl_sl], base_res.ret[0, pnl_sl]
    diff = float(sharpe(rf) - sharpe(ru))

    # Permutation null: shuffle each ticker's whole state rows across window sessions.
    n_tk, dw = states.conf.shape
    null = np.empty(n_perm)
    for c0 in range(0, n_perm, perm_chunk):
        k = min(perm_chunk, n_perm - c0)
        perm = np.argsort(rng.random((k, n_tk, dw)), axis=2)
        pm, _ = entry_states(cell, states, book.trades, perm)
        pres = run(book, F.signed_weights(book.trades, pm), target)
        null[c0:c0 + k] = sharpe(pres.ret[:, pnl_sl]) - sharpe(ru)[()]
    lo, hi = bootstrap_sharpe_diff(rf, ru, n_boot, block, rng)

    n_missing = int((~valid[0]).sum())
    out.update({f"f_{k}": v for k, v in filt_m.items()})
    out.update({f"u_{k}": v for k, v in base_m.items()})
    out.update({
        "sharpe_diff": diff, "p_perm": perm_pvalue(diff, null),
        "null_mean": float(np.nanmean(null)), "mdd_95": float(np.nanpercentile(null, 95)),
        "boot_lo": lo, "boot_hi": hi,
        "retention": filt_m["n_trades"] / base_m["n_trades"] if base_m["n_trades"] else float("nan"),
        "n_candidates": int(len(book.trades)), "n_missing_state": n_missing,
        "missing_share": n_missing / len(book.trades) if len(book.trades) else float("nan"),
    })
    out["fails_floor"] = bool(out["retention"] < 0.30)
    out["market_affected"] = market_affected(cell)
    if cell.filter == "size":
        # Entry days on which every candidate's multiplier was zero, and P&L sessions on which the
        # unfiltered book held positions but every open position's multiplier was zero (D22).
        t_rel = book.trades["t"].to_numpy()
        days = np.unique(t_rel)
        out["entry_days_all_zero"] = int(sum((mult[0][t_rel == d] == 0).all() for d in days))
        out["entry_days"] = int(len(days))
        out["sessions_sized_book_empty"] = int(((res.gross[0, pnl_sl] <= 1e-15)
                                                & (base_res.gross[0, pnl_sl] > 1e-15)).sum())

    # Restricted comparator when > 5% of candidate entries lack a state (section 6).
    if out["missing_share"] > 0.05:
        rres = run(book, F.signed_weights(book.trades, valid[0].astype(float)[None, :]))
        rm = _metrics(book, rres, 0, valid[0].astype(float)[None, :], pnl_sl, mkt)
        out["r_sharpe"] = rm["sharpe"]
        out["r_n_trades"] = rm["n_trades"]
        out["sharpe_diff_vs_restricted"] = float(sharpe(rf) - rm["sharpe"])

    # Attribution for gate cells: unfiltered standalone returns of removed vs kept entries.
    if cell.filter == "gate":
        kept = mult[0] > 0
        for name, sel in (("kept", kept), ("removed", ~kept), ("removed_missing", ~valid[0])):
            x = book.trade_ret[sel]
            out[f"attr_{name}_n"] = int(sel.sum())
            out[f"attr_{name}_mean"] = float(x.mean()) if len(x) else float("nan")
            out[f"attr_{name}_median"] = float(np.median(x)) if len(x) else float("nan")
            out[f"attr_{name}_hit"] = float(np.mean(x > 0)) if len(x) else float("nan")
    return out
