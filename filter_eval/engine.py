"""Backtest engine (INSTRUCTIONS.md section 6; D13-D16).

Accounting on a constant capital base of 1:
- A trade with signed weight w entered at open e holds notional w * P / O[e]
  (buy and hold; notional drifts with price).
- Day d P&L = overnight move of the previous close's holdings to today's open
  + intraday move of the post-trade holdings from open to close. For a single
  trade this is open-to-close on the entry day, close-to-close while held and
  close-to-open on the exit day, as specified.
- Trading happens at the open. Cost = 10 bp x |post-trade - pre-trade| notional
  per ticker (trades are netted per ticker). Open positions at the last window
  session are closed at that close and the exit cost is charged that day.

The map from trade weights to post-trade open notionals is linear, so it is
held as a sparse matrix and many weight vectors (permutations) are evaluated
in one product.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import sparse

from .market import Market

COST_PER_SIDE = 0.0010


@dataclass
class Book:
    """Precomputed linear structure for one trade list over the window."""
    G: sparse.csr_matrix      # (Dw*N, T): open notional per unit signed weight
    dw: int                   # number of window sessions
    n: int
    intraday: np.ndarray      # (Dw, N): C/O - 1 on window sessions (0 where undefined)
    overnight: np.ndarray     # (Dw, N): O[d]/C[d-1] - 1 (row 0: 0)
    c_over_o: np.ndarray      # (Dw, N)
    o_over_prevc: np.ndarray  # (Dw, N)
    trade_ret: np.ndarray     # (T,) standalone net return of each trade (D15)
    entry_rel: np.ndarray     # (T,) window-relative entry session index
    trades: pd.DataFrame
    cost: float = COST_PER_SIDE


def build_book(m: Market, trades: pd.DataFrame, cost: float = COST_PER_SIDE) -> Book:
    """`cost` is per side; only the synthetic null test sets it to zero."""
    ws, we = m.ws, m.we
    dw, n = we - ws + 1, m.n
    O = m.open[ws:we + 1]
    C = m.close[ws:we + 1]
    prevC = m.close[ws - 1:we] if ws > 0 else np.vstack([np.full(n, np.nan), C[:-1]])
    with np.errstate(invalid="ignore", divide="ignore"):
        c_over_o = np.nan_to_num(C / O, nan=1.0)
        o_over_prevc = np.nan_to_num(O / prevC, nan=1.0)
    o_over_prevc[0] = 1.0  # nothing is held before the first window session

    tr = trades[(trades["entry"] >= ws) & (trades["entry"] <= we)].reset_index(drop=True)
    rows, cols, vals = [], [], []
    trade_ret = np.empty(len(tr))
    for j, (i, e, x, d) in enumerate(zip(tr["tk"], tr["entry"], tr["exit"], tr["dir"])):
        last = min(x - 1, we)
        span = np.arange(e, last + 1)
        rows.append((span - ws) * n + i)
        cols.append(np.full(len(span), j))
        vals.append(m.open[span, i] / m.open[e, i])
        exit_px = m.open[x, i] if x <= we else m.close[we, i]
        trade_ret[j] = d * (exit_px / m.open[e, i] - 1.0) - 2 * cost
    if len(tr):
        G = sparse.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))),
                              shape=(dw * n, len(tr)))
    else:
        G = sparse.csr_matrix((dw * n, 0))
    return Book(G=G, dw=dw, n=n, intraday=c_over_o - 1.0, overnight=o_over_prevc - 1.0,
                c_over_o=c_over_o, o_over_prevc=o_over_prevc, trade_ret=trade_ret,
                entry_rel=(tr["entry"].to_numpy() - ws), trades=tr, cost=cost)


def positions(book: Book, W: np.ndarray) -> np.ndarray:
    """Post-trade open notionals, shape (K, Dw, N), for signed weights W of shape (K, T)."""
    P = book.G @ W.T                       # (Dw*N, K)
    return np.ascontiguousarray(P.T).reshape(W.shape[0], book.dw, book.n)


def gross_scale(P: np.ndarray, target_gross: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Rescale each day's book so gross open exposure equals target (size filter, D14).

    Returns the scaled notionals and the daily factor k (K, Dw); k = 0 on days
    where the sized book is empty.
    """
    g = np.abs(P).sum(axis=2)                                   # (K, Dw)
    with np.errstate(invalid="ignore", divide="ignore"):
        k = np.where(g > 1e-15, target_gross[None, :] / g, 0.0)
    return P * k[:, :, None], k


@dataclass
class RunResult:
    ret: np.ndarray        # (K, Dw) daily net returns on window sessions
    gross: np.ndarray      # (K, Dw) post-trade open gross exposure
    net: np.ndarray        # (K, Dw) post-trade open net exposure
    traded: np.ndarray     # (K, Dw) traded notional (incl. the final close-out on the last day)
    k: np.ndarray | None = None  # (K, Dw) size-filter gross factor, if applied
    eff_n: np.ndarray | None = None  # (K, Dw) 1 / sum of squared gross-normalised weights; NaN if flat


def simulate(book: Book, P: np.ndarray) -> RunResult:
    """Daily P&L from post-trade open notionals P (K, Dw, N)."""
    close_hold = P * book.c_over_o[None]                         # holdings at each close
    prev_close = np.concatenate([np.zeros_like(P[:, :1]), close_hold[:, :-1]], axis=1)
    pre_trade = prev_close * book.o_over_prevc[None]             # drifted to today's open
    overnight = (prev_close * book.overnight[None]).sum(axis=2)
    intraday = (P * book.intraday[None]).sum(axis=2)
    traded = np.abs(P - pre_trade).sum(axis=2)
    traded[:, -1] += np.abs(close_hold[:, -1]).sum(axis=1)       # close out at the last close
    ret = overnight + intraday - book.cost * traded
    gross = np.abs(P).sum(axis=2)
    sq = (P ** 2).sum(axis=2)
    with np.errstate(invalid="ignore", divide="ignore"):
        eff_n = np.where(gross > 1e-15, gross ** 2 / sq, np.nan)
    return RunResult(ret=ret, gross=gross, net=P.sum(axis=2), traded=traded, eff_n=eff_n)


def run(book: Book, w_signed: np.ndarray, target_gross: np.ndarray | None = None) -> RunResult:
    """Convenience: weights (T,) or (K, T) -> RunResult (always batched)."""
    W = np.atleast_2d(w_signed)
    P = positions(book, W)
    k = None
    if target_gross is not None:
        P, k = gross_scale(P, target_gross)
    res = simulate(book, P)
    res.k = k
    return res
