"""Scorecard and significance tests (BRIEF.md sections 5 and 6; DECISIONS.md A6, M2-M7).

Everything here works on plain arrays, so the synthetic tests exercise exactly the
code the real run uses. Conventions:

- A cell is a set of measured events: the stock (row index), the reaction session
  (column index), the event direction (+1/-1), the change in points and the stock's
  noise unit.
- `D` is the (stock x session) matrix of date-only changes for the same index and
  `eligible` marks the sessions a relabelling may draw from.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import stats

from .config import ALPHA, MOVE_UNITS, PRIMARY_MAX_UNEXPLAINED


@dataclass
class Cell:
    stock: np.ndarray        # int, row in D
    session: np.ndarray      # int, column in D (reaction session R)
    direction: np.ndarray    # +1 / -1
    change: np.ndarray       # after - before, points
    sigma: np.ndarray        # the stock's noise unit, points

    def __post_init__(self):
        self.stock = np.asarray(self.stock, dtype=int)
        self.session = np.asarray(self.session, dtype=int)
        self.direction = np.asarray(self.direction, dtype=int)
        self.change = np.asarray(self.change, dtype=float)
        self.sigma = np.asarray(self.sigma, dtype=float)

    @property
    def n(self) -> int:
        return len(self.change)


def classify(change, sigma, direction, units: float = MOVE_UNITS):
    """moved: |change| > units x sigma; right: moved in the event's direction; wrong: moved against it."""
    change, sigma, direction = np.asarray(change, float), np.asarray(sigma, float), np.asarray(direction)
    moved = np.abs(change) > units * sigma
    right = moved & (np.sign(change) == direction)
    return moved, right, moved & ~right


def scorecard(cell: Cell) -> dict:
    n = cell.n
    if n == 0:
        return {"n": 0, "moves": 0, "right": 0, "wrong": 0, "response_rate": np.nan, "direction_accuracy": np.nan,
                "wrong_way_rate": np.nan, "miss_rate": np.nan, "avg_signed_move": np.nan}
    moved, right, wrong = classify(cell.change, cell.sigma, cell.direction)
    m = int(moved.sum())
    return {"n": n, "moves": m, "right": int(right.sum()), "wrong": int(wrong.sum()),
            "response_rate": m / n, "direction_accuracy": (right.sum() / m) if m else np.nan,
            "wrong_way_rate": wrong.sum() / n, "miss_rate": 1 - m / n,
            "avg_signed_move": float(np.mean(cell.change * cell.direction))}


def perm_p(null: np.ndarray, observed: float) -> float:
    """(1 + #null >= observed) / (B + 1), one-sided upward."""
    return float((1 + np.sum(null >= observed - 1e-12)) / (len(null) + 1))


def relabel_tests(cell: Cell, D: np.ndarray, eligible: np.ndarray, sigma_by_stock: np.ndarray,
                  n_perm: int, rng: np.random.Generator) -> dict:
    """Tests 1 and 3. Each draw relabels, within every stock, as many eligible sessions as
    the stock has events (without replacement; with replacement if too few), measures
    their date-only changes, and for test 3 permutes the cell's directions across events."""
    obs = scorecard(cell)
    if cell.n == 0:
        return {"p_response": np.nan, "p_signed": np.nan, "null_response_mean": np.nan,
                "null_signed_mean": np.nan, "null_response": np.array([]), "null_signed": np.array([])}
    cols_C, cols_s = [], []
    for i in np.unique(cell.stock):
        k = int((cell.stock == i).sum())
        pool = np.flatnonzero(eligible[i] & ~np.isnan(D[i]))
        if len(pool) == 0:
            raise ValueError(f"stock row {i} has events but no eligible sessions")
        if k <= len(pool):
            pick = np.argsort(rng.random((n_perm, len(pool))), axis=1)[:, :k]
        else:
            pick = rng.integers(0, len(pool), size=(n_perm, k))
        cols_C.append(D[i, pool[pick]])
        cols_s.append(np.full((n_perm, k), sigma_by_stock[i]))
    C = np.hstack(cols_C)
    S = np.hstack(cols_s)
    dirs = rng.permuted(np.tile(cell.direction, (n_perm, 1)), axis=1)
    null_resp = (np.abs(C) > MOVE_UNITS * S).mean(axis=1)
    null_signed = (C * dirs).mean(axis=1)
    return {"p_response": perm_p(null_resp, obs["response_rate"]),
            "p_signed": perm_p(null_signed, obs["avg_signed_move"]),
            "null_response_mean": float(null_resp.mean()), "null_signed_mean": float(null_signed.mean()),
            "null_response": null_resp, "null_signed": null_signed}


def binom_p(right: int, moves: int) -> float:
    """Two-sided exact binomial p-value against 50% (DECISIONS.md P3)."""
    return float(stats.binomtest(int(right), int(moves), 0.5).pvalue) if moves else np.nan


def date_bootstrap(cell: Cell, dates: np.ndarray, n_boot: int, rng: np.random.Generator) -> dict:
    """95% percentile intervals from resampling the cell's distinct event dates (M4)."""
    nan = {k: (np.nan, np.nan) for k in ("response_rate", "direction_accuracy", "avg_signed_move")}
    if cell.n == 0:
        return nan
    moved, right, _ = classify(cell.change, cell.sigma, cell.direction)
    uniq, inv = np.unique(np.asarray(dates), return_inverse=True)
    G = len(uniq)
    per = lambda x: np.bincount(inv, weights=np.asarray(x, float), minlength=G)
    n_d, m_d, r_d, s_d = per(np.ones(cell.n)), per(moved), per(right), per(cell.change * cell.direction)
    W = np.apply_along_axis(np.bincount, 1, rng.integers(0, G, size=(n_boot, G)), minlength=G)
    n_b, m_b = W @ n_d, W @ m_d
    with np.errstate(invalid="ignore", divide="ignore"):
        resp, acc, avg = m_b / n_b, np.where(m_b > 0, (W @ r_d) / m_b, np.nan), (W @ s_d) / n_b
    ci = lambda x: tuple(np.nanpercentile(x, [2.5, 97.5])) if np.isfinite(x).any() else (np.nan, np.nan)
    return {"response_rate": ci(resp), "direction_accuracy": ci(acc), "avg_signed_move": ci(avg)}


def placebo(cell: Cell, D: np.ndarray, pool_mask: np.ndarray, sigma_by_stock: np.ndarray, n_placebo: int,
            rng: np.random.Generator) -> dict:
    """Up to `n_placebo` placebo sessions per event from its stock's noise sessions,
    measured date-only and given the event's direction (M5). Returns the placebo
    scorecard and the (stock, session) pairs drawn."""
    st, ss, dr = [], [], []
    for i, d in zip(cell.stock, cell.direction):
        pool = np.flatnonzero(pool_mask[i] & ~np.isnan(D[i]))
        if len(pool) == 0:
            continue
        sel = rng.choice(pool, size=min(n_placebo, len(pool)), replace=False)
        st += [i] * len(sel)
        ss += list(sel)
        dr += [d] * len(sel)
    st, ss = np.array(st, dtype=int), np.array(ss, dtype=int)
    pc = Cell(st, ss, dr, D[st, ss] if len(st) else [], sigma_by_stock[st] if len(st) else [])
    return {"scorecard": scorecard(pc), "picks": list(zip(st.tolist(), ss.tolist()))}


def unexplained(chg: np.ndarray, sigma: np.ndarray, period: np.ndarray, event_near: np.ndarray,
                price_near: np.ndarray, units: float) -> dict:
    """Large two-session changes (|chg| > units x sigma) on period sessions, and how many
    have neither an event nor a large price move nearby (M6). chg, event_near and
    price_near are (stock x session); sigma is per stock; period is per session."""
    with np.errstate(invalid="ignore"):
        large = (np.abs(chg) > units * sigma[:, None]) & period[None, :] & ~np.isnan(sigma)[:, None]
    ev, pr = event_near & large, price_near & large
    n = int(large.sum())
    un = int((large & ~event_near & ~price_near).sum())
    return {"large": n, "unexplained": un, "rate": un / n if n else np.nan,
            "event_only": int((ev & ~pr).sum()), "price_only": int((pr & ~ev).sum()),
            "both": int((ev & pr).sum())}


def bh_adjust(p: np.ndarray) -> np.ndarray:
    """Benjamini-Hochberg adjusted p-values (NaN entries stay NaN)."""
    p = np.asarray(p, float)
    out = np.full_like(p, np.nan)
    ok = ~np.isnan(p)
    q = p[ok]
    m = len(q)
    if m == 0:
        return out
    order = np.argsort(q)
    adj = q[order] * m / np.arange(1, m + 1)
    adj = np.minimum.accumulate(adj[::-1])[::-1]
    res = np.empty(m)
    res[order] = np.minimum(adj, 1.0)
    out[ok] = res
    return out


def primary_verdict(p_response: float, p_signed: float, unexplained_rate: float) -> dict:
    """The amended primary rule (DECISIONS.md A6): all three must hold."""
    conds = {"response p < 0.05": bool(p_response < ALPHA),
             "signed-move p < 0.05": bool(p_signed < ALPHA),
             "unexplained-move rate < 50%": bool(unexplained_rate < PRIMARY_MAX_UNEXPLAINED)}
    return {"conditions": conds, "pass": all(conds.values())}
