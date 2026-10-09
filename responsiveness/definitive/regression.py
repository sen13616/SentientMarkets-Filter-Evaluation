"""Test B, response beyond price (definitive/BRIEF.md section 4).

For each event e: delta_e = a + b * d_e + (price controls) + error, fitted by least squares.
delta_e is the change in score (points, or noise units), d_e the event direction (+1/-1)
and r_e the stock's market-adjusted close-to-close return over the reaction session.

Price controls:
- "linear" (as specified in the brief): c * r_e.
- "flexible" (the primary cell's controls, DECISIONS.md P2): r_e, sign(r_e) and a linear
  spline in r_e with the knots frozen in config.py, so that b is estimated only from what no
  function of the price move explains.

Relabelling (as specified): within each stock, draw as many eligible sessions as it has
events (without replacement; with replacement if too few), give them that stock's event
directions, take each session's date-only change and actual market-adjusted return,
refit, and record b. p = (1 + #{b_k >= b}) / (K + 1).
"""

from __future__ import annotations

import numpy as np

from .config import SPLINE_KNOTS

CONTROLS = ("linear", "flexible")


def design(d: np.ndarray, r: np.ndarray, controls: str = "linear") -> np.ndarray:
    """Design matrix (... x n x p): [1, d, r] or [1, d, r, sign(r), spline terms]."""
    cols = [np.ones_like(r), d, r]
    if controls == "flexible":
        cols += [np.sign(r)] + [np.maximum(r - k, 0.0) for k in SPLINE_KNOTS]
    elif controls != "linear":
        raise ValueError(controls)
    return np.stack(cols, axis=-1)


def fit_batch(y: np.ndarray, d: np.ndarray, r: np.ndarray, w: np.ndarray | None = None,
              controls: str = "linear") -> np.ndarray:
    """Weighted least squares for each row of (K x n) arrays. Returns (K x p) coefficients
    with b in column 1 (and c, the linear price slope, in column 2); NaN where singular."""
    y, d, r = np.atleast_2d(y), np.atleast_2d(d), np.atleast_2d(r)
    w = np.ones_like(y) if w is None else np.atleast_2d(w)
    X = design(d, r, controls)
    XtX = np.einsum("kni,kn,knj->kij", X, w, X)
    Xty = np.einsum("kni,kn,kn->ki", X, w, y)
    p = X.shape[-1]
    core = 4 if controls == "flexible" else 3          # [1, d, r] (+ sign(r)): must be full rank
    out = np.full((len(y), p), np.nan)
    ok = np.linalg.matrix_rank(XtX[:, :core, :core], hermitian=True) == core
    if ok.any():
        # A spline term with no observation beyond its knot is an all-zero column; the
        # pseudo-inverse gives the fit with that column left out (DECISIONS.md D11).
        out[ok] = (np.linalg.pinv(XtX[ok], hermitian=True) @ Xty[ok][..., None])[..., 0]
    return out


def fit(y, d, r, controls: str = "linear") -> np.ndarray:
    return fit_batch(np.asarray(y, float), np.asarray(d, float), np.asarray(r, float), controls=controls)[0]


def relabel_b(stock: np.ndarray, direction: np.ndarray, b_obs: float, D: np.ndarray, R: np.ndarray,
              eligible: np.ndarray, K: int, rng: np.random.Generator, controls: str = "linear") -> dict:
    """The specified relabelling null for b. D and R are (stock x session) date-only score
    changes and market-adjusted returns; eligible marks sessions that may be drawn."""
    ys, ds, rs = [], [], []
    for i in np.unique(stock):
        dirs = direction[stock == i]
        k = len(dirs)
        pool = np.flatnonzero(eligible[i] & ~np.isnan(D[i]) & ~np.isnan(R[i]))
        if len(pool) == 0:
            raise ValueError(f"stock row {i} has events but no eligible sessions")
        pick = (np.argsort(rng.random((K, len(pool))), axis=1)[:, :k] if k <= len(pool)
                else rng.integers(0, len(pool), size=(K, k)))
        ys.append(D[i, pool[pick]])
        rs.append(R[i, pool[pick]])
        ds.append(np.tile(dirs.astype(float), (K, 1)))
    null_b = fit_batch(np.hstack(ys), np.hstack(ds), np.hstack(rs), controls=controls)[:, 1]
    null_b = null_b[~np.isnan(null_b)]
    if np.isnan(b_obs) or not len(null_b):
        return {"p": np.nan, "null_b": null_b}
    p = float((1 + np.sum(null_b >= b_obs - 1e-12)) / (len(null_b) + 1))
    return {"p": p, "null_b": null_b}


def freedman_lane_b(y, d, r, b_obs: float, K: int, rng: np.random.Generator,
                    controls: str = "flexible") -> dict:
    """Freedman-Lane permutation test for b (DECISIONS.md D14). Fit the reduced model (y on
    the price terms only, without d), permute its residuals across events, add them back to
    its fitted values, refit the full model and record b. p = (1 + #{b_k >= b}) / (K + 1)."""
    y, d, r = (np.asarray(v, float) for v in (y, d, r))
    X0 = np.delete(design(d, r, controls), 1, axis=-1)            # the full design without d
    beta0 = np.linalg.pinv(X0.T @ X0, hermitian=True) @ (X0.T @ y)
    fitted, resid = X0 @ beta0, y - X0 @ beta0
    perm = np.argsort(rng.random((K, len(y))), axis=1)
    null_b = fit_batch(fitted[None, :] + resid[perm], np.tile(d, (K, 1)), np.tile(r, (K, 1)),
                       controls=controls)[:, 1]
    null_b = null_b[~np.isnan(null_b)]
    if np.isnan(b_obs) or not len(null_b):
        return {"p": np.nan, "null_b": null_b}
    return {"p": float((1 + np.sum(null_b >= b_obs - 1e-12)) / (len(null_b) + 1)), "null_b": null_b}


def date_bootstrap_bc(y, d, r, dates, B: int, rng: np.random.Generator, controls: str = "linear") -> dict:
    """Resample distinct event dates with replacement (pilot M4); refit with the draw
    counts as weights. Returns 95% percentile intervals for b and c, and the draws."""
    y, d, r = (np.asarray(v, float) for v in (y, d, r))
    uniq, inv = np.unique(np.asarray(dates), return_inverse=True)
    G = len(uniq)
    counts = np.apply_along_axis(np.bincount, 1, rng.integers(0, G, size=(B, G)), minlength=G)   # B x G
    w = counts[:, inv].astype(float)                                                           # B x n
    coef = fit_batch(np.tile(y, (B, 1)), np.tile(d, (B, 1)), np.tile(r, (B, 1)), w, controls)
    ci = lambda x: tuple(np.nanpercentile(x, [2.5, 97.5])) if np.isfinite(x).any() else (np.nan, np.nan)
    return {"b": ci(coef[:, 1]), "c": ci(coef[:, 2]), "draws": coef}
