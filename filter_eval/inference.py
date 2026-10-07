"""Metrics and inference (INSTRUCTIONS.md section 10; D15, D16)."""

from __future__ import annotations

import numpy as np

ANN = np.sqrt(252.0)


def sharpe(r: np.ndarray) -> np.ndarray:
    """Annualised Sharpe along the last axis: mean / sd (ddof=1) * sqrt(252); NaN if sd == 0."""
    r = np.asarray(r, dtype=float)
    sd = r.std(axis=-1, ddof=1)
    mu = r.mean(axis=-1)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(sd > 1e-15, mu / sd * ANN, np.nan)


def max_drawdown(r: np.ndarray) -> float:
    """Max peak-to-trough fall of equity 1 + cumsum(r) (constant capital), as a fraction of the peak."""
    eq = 1.0 + np.cumsum(r)
    peak = np.maximum.accumulate(np.concatenate([[1.0], eq]))[1:]
    return float(np.max((peak - eq) / peak)) if len(eq) else float("nan")


def profit_factor(pnl: np.ndarray) -> float:
    gains, losses = pnl[pnl > 0].sum(), -pnl[pnl < 0].sum()
    if losses == 0:
        return float("inf") if gains > 0 else float("nan")
    return float(gains / losses)


def beta(r: np.ndarray, mkt: np.ndarray) -> float:
    v = np.var(mkt, ddof=1)
    return float(np.cov(r, mkt, ddof=1)[0, 1] / v) if v > 0 else float("nan")


def perm_pvalue(observed: float, null: np.ndarray) -> float:
    """One-sided: (1 + #{null >= observed}) / (1 + K). NaN nulls count as not exceeding."""
    null = np.asarray(null, dtype=float)
    return float((1 + np.sum(null >= observed)) / (1 + len(null)))


def stationary_bootstrap_indices(n: int, n_boot: int, mean_block: float, rng: np.random.Generator) -> np.ndarray:
    """Politis-Romano stationary bootstrap index matrix (n_boot, n) with circular wrap."""
    p = 1.0 / mean_block
    idx = np.empty((n_boot, n), dtype=np.int64)
    idx[:, 0] = rng.integers(0, n, n_boot)
    new = rng.random((n_boot, n)) < p
    starts = rng.integers(0, n, (n_boot, n))
    for t in range(1, n):
        idx[:, t] = np.where(new[:, t], starts[:, t], (idx[:, t - 1] + 1) % n)
    return idx


def bootstrap_sharpe_diff(rf: np.ndarray, ru: np.ndarray, n_boot: int, mean_block: float,
                          rng: np.random.Generator) -> tuple[float, float]:
    """95% percentile interval of Sharpe(rf) - Sharpe(ru) under a paired stationary block bootstrap."""
    idx = stationary_bootstrap_indices(len(rf), n_boot, mean_block, rng)
    d = sharpe(rf[idx]) - sharpe(ru[idx])
    d = d[np.isfinite(d)]
    if not len(d):
        return float("nan"), float("nan")
    lo, hi = np.percentile(d, [2.5, 97.5])
    return float(lo), float(hi)


def benjamini_hochberg(p: np.ndarray) -> np.ndarray:
    """BH-adjusted p-values (step-up), NaNs passed through."""
    p = np.asarray(p, dtype=float)
    out = np.full_like(p, np.nan)
    ok = np.isfinite(p)
    q = p[ok]
    m = len(q)
    if not m:
        return out
    order = np.argsort(q)
    ranked = q[order] * m / np.arange(1, m + 1)
    adj = np.minimum.accumulate(ranked[::-1])[::-1]
    res = np.empty(m)
    res[order] = np.minimum(adj, 1.0)
    out[ok] = res
    return out
