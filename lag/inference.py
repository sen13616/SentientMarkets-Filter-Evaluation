"""Inference (BRIEF.md section 5; DECISIONS.md L8 to L10, L15).

- Non-event sessions: per stock, the sessions more than NON_EVENT_RADIUS sessions from any
  candidate event session of that stock (L8).
- Relabelling test of 5A (L9): K draws; each gives every event a random non-event session at the
  event's own time of day, and permutes the events' directions across events. The draw's mean of
  d·Δ at 48 h is M⁽ᵏ⁾; p = (1 + #{k : M⁽ᵏ⁾ >= M}) / (1 + K). The same draws give a null for the mean
  of m(h) at each main horizon (first response, L10, Holm across the eight horizons).
- Placebo curves: up to N_PLACEBO non-event sessions per event, at the event's time of day, with the
  event's direction; their mean curves sit beside the event curves.
- Bootstrap over event dates (B draws) for T½, T₉₀ and Rₚ(T½); over session dates for the
  best-alignment k. Timings not reached within 48 h enter the bootstrap at the 48-hour cap (L15).
"""

from __future__ import annotations

from datetime import date, datetime, time

import numpy as np
import pandas as pd

from responsiveness.inference import bh_adjust, perm_p

from .config import ALPHA, B_BOOT, K_PERM, N_PLACEBO, NON_EVENT_RADIUS, NY, POST_WINDOW, PRE_WINDOW
from .measure import (M_IDX, MAIN_IDX, OFFSETS_NS, Ticks, alignment_corr, best_k, crossing_index, crossing_time, event_curves, price_at_half,
                      price_response, response_curve, sign_curves, timings, value_at, weighted_mean)

__all__ = ["bh_adjust", "perm_p", "holm", "non_event_sessions", "same_time_on", "pools", "relabel_test",
           "placebo_curves", "date_bootstrap", "alignment_bootstrap", "ci"]

CAP_H = POST_WINDOW / pd.Timedelta(hours=1)


def holm(p: np.ndarray) -> np.ndarray:
    """Holm step-down adjusted p-values (NaN entries stay NaN)."""
    p = np.asarray(p, float)
    out = np.full_like(p, np.nan)
    ok = ~np.isnan(p)
    q = p[ok]
    m = len(q)
    if m == 0:
        return out
    order = np.argsort(q)
    adj = q[order] * (m - np.arange(m))
    adj = np.maximum.accumulate(adj)
    res = np.empty(m)
    res[order] = np.minimum(adj, 1.0)
    out[ok] = res
    return out


# --------------------------------------------------------------------------- non-event sessions and placebo instants

def non_event_sessions(cand_sessions: dict[str, set[date]], sessions: list[date],
                       radius: int = NON_EVENT_RADIUS) -> dict[str, list[date]]:
    """Per ticker, the sessions more than `radius` sessions away from every candidate session."""
    pos = {d: i for i, d in enumerate(sessions)}
    out = {}
    for t, cs in cand_sessions.items():
        near = set()
        for d in cs:
            if d in pos:
                i = pos[d]
                near.update(sessions[max(0, i - radius):i + radius + 1])
            else:
                # a candidate on a non-session day: block the sessions around its calendar position
                after = [s for s in sessions if s > d]
                before = [s for s in sessions if s < d]
                near.update(after[:radius])
                near.update(before[-radius:])
        out[t] = [s for s in sessions if s not in near]
    return out


def same_time_on(t0: pd.Timestamp, days: list[date]) -> np.ndarray:
    """t0's New York time of day on each of `days`, as int64 ns UTC."""
    tod = t0.tz_convert(NY).time()
    stamps = [pd.Timestamp(datetime.combine(d, tod)).tz_localize(NY).tz_convert("UTC").value for d in days]
    return np.array(stamps, dtype=np.int64)


def pools(ticks: Ticks, events: pd.DataFrame, non_event: dict[str, list[date]],
          pre_ns: int = int(PRE_WINDOW.value), post_ns: int = int(POST_WINDOW.value)) -> list[np.ndarray]:
    """Per event, the candidate placebo instants (ns): the event's time of day on the stock's
    non-event sessions, keeping only instants whose -6 h / +48 h window lies within the stock's ticks."""
    out = []
    for r in events.itertuples(index=False):
        span = ticks.span(r.ticker)
        days = non_event.get(r.ticker, [])
        if span is None or not days:
            out.append(np.array([], dtype=np.int64))
            continue
        inst = same_time_on(pd.Timestamp(r.t0), days)
        ok = (inst - pre_ns >= span[0]) & (inst + post_ns <= span[1])
        out.append(inst[ok])
    return out


def _main_readings(ticks: Ticks, ticker: str, instants: np.ndarray) -> np.ndarray:
    """Unsigned Δ at the main horizons for each instant (P x 8 x I); NaN rows where there is no valid before reading."""
    cur = event_curves(ticks, np.array([ticker] * len(instants)), instants)
    return cur["curves"][:, MAIN_IDX, :]


# --------------------------------------------------------------------------- relabelling test

def relabel_test(ticks: Ticks, events: pd.DataFrame, event_pools: list[np.ndarray], obs_main: np.ndarray,
                 k_perm: int = K_PERM, rng: np.random.Generator | None = None) -> dict:
    """5A's relabelling test for M and for the mean of m(h) at each main horizon.

    `obs_main` is the observed signed Δ at the main horizons (E x 8 x I). Each draw gives every event
    a random instant from its pool (an event with an empty pool is left out of the null, and counted)
    and permutes the directions across events. Returns p-values (I,) for M, p-values (8 x I) per
    horizon with Holm adjustment, the null means, and the null draws of M (K x I)."""
    rng = rng or np.random.default_rng(0)
    E, H, I = obs_main.shape
    usable = [e for e in range(E) if len(event_pools[e]) > 0]
    obs_mean = weighted_mean(obs_main)                                     # 8 x I
    if not usable:
        nan8 = np.full((H, I), np.nan)
        return {"p_M": np.full(I, np.nan), "p_h": nan8, "p_h_holm": nan8, "null_M_mean": np.full(I, np.nan),
                "null_h_mean": nan8, "null_M": np.full((k_perm, I), np.nan), "n_used": 0, "n_no_pool": E}
    tickers = events["ticker"].to_numpy()
    direction = events["direction"].to_numpy(float)[usable]
    null = np.empty((k_perm, len(usable), H, I))
    for j, e in enumerate(usable):
        D = _main_readings(ticks, tickers[e], event_pools[e])                 # P x 8 x I
        pick = rng.integers(0, len(event_pools[e]), size=k_perm)
        null[:, j] = D[pick]
    perm = rng.permuted(np.tile(direction, (k_perm, 1)), axis=1)             # K x E'
    null_signed = null * perm[:, :, None, None]
    null_mean = np.nanmean(null_signed, axis=1)                               # K x 8 x I
    p_h = np.full((H, I), np.nan)
    for h in range(H):
        for i in range(I):
            if np.isfinite(obs_mean[h, i]) and np.isfinite(null_mean[:, h, i]).any():
                p_h[h, i] = perm_p(null_mean[:, h, i][np.isfinite(null_mean[:, h, i])], obs_mean[h, i])
    p_h_holm = np.column_stack([holm(p_h[:, i]) for i in range(I)])
    m_col = int(np.flatnonzero(MAIN_IDX == M_IDX)[0])
    return {"p_M": p_h[m_col], "p_h": p_h, "p_h_holm": p_h_holm, "null_M_mean": np.nanmean(null_mean[:, m_col, :], axis=0),
            "null_h_mean": np.nanmean(null_mean, axis=0), "null_M": null_mean[:, m_col, :],
            "n_used": len(usable), "n_no_pool": E - len(usable)}


def first_response(p_h_holm: np.ndarray, horizons_min: tuple[int, ...], alpha: float = ALPHA) -> np.ndarray:
    """Per index, the first main horizon (minutes) with Holm-adjusted p < alpha; NaN if none."""
    out = np.full(p_h_holm.shape[1], np.nan)
    for i in range(p_h_holm.shape[1]):
        hit = np.flatnonzero(p_h_holm[:, i] < alpha)
        if len(hit):
            out[i] = horizons_min[int(hit[0])]
    return out


# --------------------------------------------------------------------------- placebo curves

def placebo_curves(ticks: Ticks, events: pd.DataFrame, event_pools: list[np.ndarray], n_placebo: int = N_PLACEBO,
                   rng: np.random.Generator | None = None) -> dict:
    """Mean signed curve over up to `n_placebo` placebo instants per event (G x I), with the number of
    placebo pseudo-events and of events without a pool."""
    rng = rng or np.random.default_rng(0)
    tk, inst, dirs = [], [], []
    for e, r in enumerate(events.itertuples(index=False)):
        p = event_pools[e]
        if len(p) == 0:
            continue
        sel = rng.choice(p, size=min(n_placebo, len(p)), replace=False)
        tk += [r.ticker] * len(sel)
        inst += list(sel)
        dirs += [r.direction] * len(sel)
    if not inst:
        G, I = len(OFFSETS_NS), len(ticks.indices)
        return {"mean_m": np.full((G, I), np.nan), "n": 0, "n_no_pool": len(events)}
    cur = event_curves(ticks, np.array(tk), np.array(inst, dtype=np.int64))
    m = sign_curves(cur["curves"], np.array(dirs))
    return {"mean_m": weighted_mean(m), "n": int(cur["valid"].sum()),
            "n_no_pool": int(sum(len(p) == 0 for p in event_pools))}


# --------------------------------------------------------------------------- bootstraps

def date_bootstrap(m: np.ndarray, rp: np.ndarray, dates: np.ndarray, n_boot: int = B_BOOT,
                   rng: np.random.Generator | None = None) -> dict:
    """Resample the distinct event dates; per draw and index recompute R, T½, T₉₀ and Rₚ(T½).
    Timings not reached are capped at 48 h. Returns draws (B x I) for each quantity."""
    rng = rng or np.random.default_rng(0)
    E, G, I = m.shape
    uniq, inv = np.unique(np.asarray(dates), return_inverse=True)
    D = len(uniq)
    W = np.apply_along_axis(np.bincount, 1, rng.integers(0, D, size=(n_boot, D)), minlength=D)   # B x D
    ew = W[:, inv].astype(float)                                                                  # B x E
    t_half, t_full, rp_half = (np.full((n_boot, I), np.nan) for _ in range(3))
    ok_m = ~np.isnan(m)
    ok_r = ~np.isnan(rp)
    m0, r0 = np.where(ok_m, m, 0.0), np.where(ok_r, rp, 0.0)
    for i in range(I):
        num = ew @ m0[:, :, i]
        den = ew @ ok_m[:, :, i].astype(float)
        with np.errstate(invalid="ignore", divide="ignore"):
            mean_m = num / den                                   # B x G
            R = mean_m / mean_m[:, [M_IDX]]
        numr = ew @ r0
        denr = ew @ ok_r.astype(float)
        with np.errstate(invalid="ignore", divide="ignore"):
            Rp = (numr / denr) / (numr / denr)[:, [M_IDX]]
        for b in range(n_boot):
            if not np.isfinite(mean_m[b, M_IDX]) or mean_m[b, M_IDX] <= 0:
                continue
            th = crossing_time(R[b], 0.5)
            tf = crossing_time(R[b], 0.9)
            t_half[b, i] = CAP_H if np.isnan(th) else th
            t_full[b, i] = CAP_H if np.isnan(tf) else tf
            j = crossing_index(R[b], 0.5)
            rp_half[b, i] = price_at_half(Rp[b], -1 if j is None else j)
    return {"t_half": t_half, "t_full": t_full, "rp_half": rp_half, "n_dates": D}


def alignment_bootstrap(cells: dict, n_boot: int = B_BOOT, rng: np.random.Generator | None = None) -> dict:
    """Resample session dates; return the best-k draws (B,) and the correlation draws (B x K)."""
    rng = rng or np.random.default_rng(0)
    S = cells["sums"]["n"].shape[2]
    W = np.apply_along_axis(np.bincount, 1, rng.integers(0, S, size=(n_boot, S)), minlength=S).astype(float)
    corr = alignment_corr(cells, W)
    ks = cells["ks"]
    best = np.array([best_k(c, ks) for c in corr], dtype=float)
    return {"best_k": best, "corr": corr}


def ci(draws: np.ndarray, lo: float = 2.5, hi: float = 97.5) -> tuple[float, float]:
    x = np.asarray(draws, float)
    x = x[np.isfinite(x)]
    if len(x) == 0:
        return (np.nan, np.nan)
    return tuple(float(v) for v in np.percentile(x, [lo, hi]))
