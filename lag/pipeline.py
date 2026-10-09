"""From events and ticks to the measures of one cell (BRIEF.md sections 4 and 5).

`prepare` reads every kept event once: the unsigned response curves on the grid, the price curves,
the placebo pools and the event dates. `measure_cell` then takes any subset of events (a cell) and
returns, per index: n, M and its relabelling p, T½ and T₉₀ with bootstrap intervals, the first
response, Rₚ(T½) with its interval, the response curve, the placebo curve and the price curve.
`alignment` is computed once per index from the hourly session bars.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import numpy as np
import pandas as pd

from .config import ALIGN_K, B_BOOT, INDICES, K_PERM, MAIN_HORIZONS_MIN, N_PLACEBO, NY
from .inference import (alignment_bootstrap, ci, date_bootstrap, first_response, gate, non_event_sessions, placebo_curves,
                        pools, relabel_test)
from .measure import (M_IDX, MAIN_IDX, OFFSETS_H, HourlyBars, PriceSeries, Ticks, alignment_cells, alignment_corr, price_at_half,
                      best_k, event_curves, price_curves, price_response, response_curve, sign_curves, timings,
                      value_at)


@dataclass
class Prepared:
    ticks: Ticks
    events: pd.DataFrame                 # kept events, reset index
    curves: np.ndarray                   # E x G x I, unsigned Δ
    valid: np.ndarray                    # E, before reading exists and is fresh (L6)
    before_age_s: np.ndarray             # E
    rp: np.ndarray                       # E x G, unsigned price curve
    pools: list[np.ndarray]              # per event, placebo instants (ns)
    dates: np.ndarray                    # E, New York date of t0
    indices: tuple[str, ...] = INDICES
    meta: dict = field(default_factory=dict)


def prepare(ticks_df: pd.DataFrame, events: pd.DataFrame, panel, bar_minutes: int,
            cand_sessions: dict[str, set[date]], sessions: list[date], indices: tuple[str, ...] = INDICES) -> Prepared:
    ev = events.reset_index(drop=True).copy()
    ev["t0"] = pd.to_datetime(ev["t0"], utc=True)
    ticks = Ticks.from_frame(ticks_df, indices)
    t0_ns = ev["t0"].to_numpy("datetime64[ns]").astype(np.int64)
    tk = ev["ticker"].to_numpy()
    cur = event_curves(ticks, tk, t0_ns)
    prices = PriceSeries.from_panel(panel, bar_minutes)
    rp = price_curves(prices, tk, t0_ns)
    non_event = non_event_sessions(cand_sessions, sessions)
    pl = pools(ticks, ev, non_event)
    dates = ev["t0"].dt.tz_convert(NY).dt.date.to_numpy()
    meta = {"n_events": len(ev), "n_valid_before": int(cur["valid"].sum()),
            "n_stale_before": int((~cur["valid"]).sum()), "n_without_pool": int(sum(len(p) == 0 for p in pl)),
            "pool_size_median": float(np.median([len(p) for p in pl])) if len(pl) else np.nan,
            "price_bars_missing": int(sum(prices.n_missing.values()))}
    return Prepared(ticks=ticks, events=ev, curves=cur["curves"], valid=cur["valid"], before_age_s=cur["before_age_s"],
                    rp=rp, pools=pl, dates=dates, indices=indices, meta=meta)


def measure_cell(prep: Prepared, mask: np.ndarray, seed: int, k_perm: int = K_PERM, n_boot: int = B_BOOT,
                 n_placebo: int = N_PLACEBO) -> dict:
    """Every measure for the events selected by `mask`, per index. Uses three independent generators
    seeded from `seed` (relabelling, placebo, bootstrap)."""
    sel = np.flatnonzero(np.asarray(mask, bool) & prep.valid)
    I, G = len(prep.indices), prep.curves.shape[1]
    out = {"n": int(len(sel)), "n_masked": int(np.asarray(mask, bool).sum()), "indices": prep.indices,
           "offsets_h": OFFSETS_H}
    if len(sel) == 0:
        return {**out, "empty": True}
    ev = prep.events.iloc[sel].reset_index(drop=True)
    d = ev["direction"].to_numpy(float)
    m = sign_curves(prep.curves[sel], d)                                  # E x G x I
    rp = prep.rp[sel] * d[:, None]                                        # E x G
    rc = response_curve(m)
    tm = timings(rc["R"], rc["M"])
    pr = price_response(rp)
    rp_half = np.array([price_at_half(pr["Rp"], tm["idx_half"][i]) if (np.isfinite(rc["M"][i]) and rc["M"][i] > 0)
                        else np.nan for i in range(I)])
    obs_main = m[:, MAIN_IDX, :]
    rng_rel, rng_pl, rng_bt = (np.random.default_rng([seed, k]) for k in (1, 2, 3))
    rel = relabel_test(prep.ticks, ev, [prep.pools[e] for e in sel], obs_main, k_perm, rng_rel)
    pl = placebo_curves(prep.ticks, ev, [prep.pools[e] for e in sel], n_placebo, rng_pl)
    bt = date_bootstrap(m, rp, prep.dates[sel], n_boot, rng_bt)
    fr = first_response(rel["p_h_holm"], MAIN_HORIZONS_MIN)
    n_per_index = (~np.isnan(m[:, M_IDX, :])).sum(axis=0)
    return {**out, "empty": False, "n_per_index": n_per_index, "mean_m": rc["mean_m"], "M": rc["M"], "R": rc["R"],
            "t_half": tm["t_half"], "t_full": tm["t_full"], "rp_half": rp_half, "Rp": pr["Rp"], "mean_r": pr["mean_r"],
            "Mp": pr["Mp"], "p_M": rel["p_M"], "null_M_mean": rel["null_M_mean"], "p_h": rel["p_h"],
            "p_h_holm": rel["p_h_holm"], "first_response_min": fr, "null_h_mean": rel["null_h_mean"],
            "relabel_n_used": rel["n_used"], "relabel_no_pool": rel["n_no_pool"], "placebo_mean_m": pl["mean_m"],
            "placebo_n": pl["n"], "obs_main_mean": np.nanmean(obs_main, axis=0),
            "ci_M": np.array([ci(bt["M"][:, i]) for i in range(I)]),
            "gate": gate(rel["p_M"], np.array([ci(bt["M"][:, i])[0] for i in range(I)])),
            "ci_t_half": np.array([ci(bt["t_half"][:, i]) for i in range(I)]),
            "ci_t_full": np.array([ci(bt["t_full"][:, i]) for i in range(I)]),
            "ci_rp_half": np.array([ci(bt["rp_half"][:, i]) for i in range(I)]),
            "boot_not_reached_half": np.nanmean(bt["t_half"] >= 48.0 - 1e-9, axis=0),
            "boot_not_reached_full": np.nanmean(bt["t_full"] >= 48.0 - 1e-9, axis=0),
            "boot_n_dates": bt["n_dates"], "null_M": rel["null_M"]}


def cell_rows(res: dict, cell: dict) -> list[dict]:
    """Flatten one cell's result into one row per index."""
    rows = []
    for i, idx in enumerate(res["indices"]):
        row = {**cell, "index": idx, "n": res["n"], "n_masked": res["n_masked"]}
        if res.get("empty"):
            rows.append(row)
            continue
        row.update({
            "n_index": int(res["n_per_index"][i]), "M": res["M"][i], "p_M": res["p_M"][i],
            "M_lo": res["ci_M"][i][0], "M_hi": res["ci_M"][i][1], "gate": bool(res["gate"][i]),
            "null_M_mean": res["null_M_mean"][i], "t_half_h": res["t_half"][i],
            "t_half_lo": res["ci_t_half"][i][0], "t_half_hi": res["ci_t_half"][i][1],
            "t_full_h": res["t_full"][i], "t_full_lo": res["ci_t_full"][i][0], "t_full_hi": res["ci_t_full"][i][1],
            "boot_share_half_over_48h": res["boot_not_reached_half"][i],
            "boot_share_full_over_48h": res["boot_not_reached_full"][i],
            "first_response_min": res["first_response_min"][i], "rp_half": res["rp_half"][i],
            "rp_half_lo": res["ci_rp_half"][i][0], "rp_half_hi": res["ci_rp_half"][i][1], "Mp": res["Mp"],
            "relabel_n_used": res["relabel_n_used"], "placebo_n": res["placebo_n"], "boot_n_dates": res["boot_n_dates"],
        })
        for j, hm in enumerate(MAIN_HORIZONS_MIN):
            row[f"m_{hm}min"] = res["obs_main_mean"][j, i]
            row[f"R_{hm}min"] = res["R"][MAIN_IDX[j], i]
            row[f"placebo_m_{hm}min"] = res["placebo_mean_m"][MAIN_IDX[j], i]
            row[f"p_{hm}min"] = res["p_h"][j, i]
            row[f"p_holm_{hm}min"] = res["p_h_holm"][j, i]
        rows.append(row)
    return rows


def alignment(ticks: Ticks, hb: HourlyBars, index_name: str, n_boot: int = B_BOOT, seed: int = 0,
              ks: tuple[int, ...] = ALIGN_K) -> dict:
    pos = ticks.indices.index(index_name)
    cells = alignment_cells(ticks, hb, pos, ks)
    corr = alignment_corr(cells)
    k = best_k(corr, cells["ks"])
    bt = alignment_bootstrap(cells, n_boot, np.random.default_rng([seed, 4]))
    n_pairs = cells["sums"]["n"].sum(axis=(1, 2))
    return {"index": index_name, "ks": cells["ks"], "corr": corr, "best_k": k, "ci_k": ci(bt["best_k"]),
            "best_corr": float(np.nanmax(corr)) if np.isfinite(corr).any() else np.nan,
            "n_pairs_at_k0": int(n_pairs[int(np.flatnonzero(cells["ks"] == 0)[0])]), "n_stocks": len(hb.tickers),
            "n_sessions": len(hb.sessions), "boot_best_k": bt["best_k"]}
