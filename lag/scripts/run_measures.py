"""The measurement run, shared by the pilot (Phase 2) and the definitive run (Phase 4).

Builds the events exactly as `event_counts` does, reads the run's ticks, and measures every cell:
each index x event group (L-E1, L-E2, L-E1+L-E2, L-E2 with the 3x sensitivity rule) x where
(all, inside the session, outside the session). Primary cells: score_exo and score_raw on L-E1 and
L-E2 (all). Every cell is logged in the ledger. Alignment is computed once per index.

The definitive run adds (lag/definitive/config.py): the extended-hours price curve for every cell
(L18), the pre-event drift (L19, computed for every run but rendered only for the definitive one),
the universe rule of L20, and reads the sentiment pulled by Experiment 5A's definitive Phase 1,
which the lock allows only once 5A's results are committed.

Outputs (results/ of the run): cells.csv, curves.csv.gz, alignment.csv, alignment_curves.csv,
nulls/<cell>.csv.gz (relabelled values of M), run_meta.json. RESULTS.md is rendered separately.

    python -m lag.scripts.run_pilot          # the pilot
    python -m lag.definitive.run             # the definitive run, on or after 24 November 2026
"""

from __future__ import annotations

import json
import platform
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from responsiveness.events import Calendar
from responsiveness.market import build_prices

from lag import events as ev_mod
from lag import ledger
from lag.config import (B_BOOT, BAR_MINUTES, CONTAMINATED, DEFINITIVE_TICK_DIR, E2_MULT_SENSITIVITY, E2_Z_THRESHOLD, INDICES,
                        K_PERM, LAG_DATA, PILOT_TICK_DIR,
                        N_PLACEBO, NY, PRIMARY_GROUPS, PRIMARY_INDICES, RESULTS, RUNS, config_hash)
from lag.data import file_hash, load_bars, load_daily, load_earnings, load_ticks, sessions, universe
from lag.inference import bh_adjust
from lag.measure import MAIN_IDX, OFFSETS_H, hourly_bars
from lag.pipeline import alignment, cell_rows, measure_cell, prepare

GROUPS = {"L-E1": ("L-E1",), "L-E2": ("L-E2",), "L-E1+L-E2": ("L-E1", "L-E2")}
SENSITIVITY = "L-E2 (3x sensitivity)"
WHERE = ("all", "inside", "outside")


def where_mask(ev: pd.DataFrame, where: str) -> np.ndarray:
    if where == "all":
        return np.ones(len(ev), bool)
    return (ev["in_session"].to_numpy(bool) == (where == "inside"))


def definitive_universe(bars: pd.DataFrame, candidates: list[str], sess: list) -> tuple[list[str], list[str]]:
    """L20: the pilot's names less any without a regular bar on every session of the period."""
    reg = bars[bars["regular"].astype(bool) & bars["ticker"].isin(candidates) & bars["session"].isin(sess)]
    per = reg.groupby("ticker")["session"].nunique()
    keep = sorted(t for t in candidates if per.get(t, 0) == len(sess))
    return keep, sorted(set(candidates) - set(keep))


def main(run: str = "pilot", out_dir=None, ext_hours: bool = False) -> None:
    t_start = time.time()
    cfg = RUNS[run]
    seed = cfg["seed"]
    bar_minutes = BAR_MINUTES[cfg["bar"]]
    out = RESULTS if out_dir is None else out_dir
    sess = sessions(run)
    bars = load_bars(run)
    uni = universe(run)
    dropped_names: list[str] = []
    if run == "definitive":
        uni, dropped_names = definitive_universe(bars, uni, sess)
    daily = load_daily(run)
    all_sessions = sorted(daily["date"].unique())
    cal = Calendar(all_sessions)
    prices = build_prices(daily, uni, all_sessions)
    earn = load_earnings(run, uni)
    panel = ev_mod.build_panel(bars, uni, sess)
    panel_ext = ev_mod.build_panel(bars, uni, sess, regular_only=False) if ext_hours else None
    print("loading ticks")
    ticks_df = load_ticks(run, uni)
    last_tick = ticks_df["ts"].max()

    # Events, exactly as in event_counts (L14: fixed rarity threshold, checked against the bars).
    normal = ev_mod.normal_move(panel, ev_mod.earnings_sessions(earn, cal))
    computed = ev_mod.rarity_threshold(ev_mod.z_scores(panel, normal))
    threshold = E2_Z_THRESHOLD.get(run) or computed
    if E2_Z_THRESHOLD.get(run) is not None and abs(computed - threshold) > 5e-4:
        raise RuntimeError(f"rarity threshold from the bars ({computed:.4f}) differs from the fixed value ({threshold})")
    ev, counts = ev_mod.build_events(earn, prices, panel, cal, cfg["event_start"], last_tick, threshold)
    ev3, _ = ev_mod.build_events(earn, prices, panel, cal, cfg["event_start"], last_tick, E2_MULT_SENSITIVITY)
    kept = ev[ev["status"] == "kept"].reset_index(drop=True)
    kept3 = ev3[(ev3["status"] == "kept") & (ev3["type"] == "L-E2")].reset_index(drop=True)
    saved = LAG_DATA / f"events_{run}.parquet"
    if saved.exists():
        n_saved = int((pd.read_parquet(saved)["status"] == "kept").sum())
        if n_saved != len(kept):
            raise RuntimeError(f"kept events ({len(kept)}) differ from the Phase 0 count ({n_saved})")

    # Candidate sessions for the non-event pools (L8): every primary candidate's t0 session and, for
    # earnings, the reaction session; plus every earnings reaction session (timed or not).
    cand_sessions = {t: set(s) for t, s in ev_mod.earnings_sessions(earn, cal).items()}
    for r in ev.itertuples(index=False):
        s = cand_sessions.setdefault(r.ticker, set())
        s.add(pd.Timestamp(r.t0).tz_convert(NY).date())
        if getattr(r, "R", None) is not None and not pd.isna(r.R):
            s.add(r.R)

    print(f"preparing {len(kept)} primary events and {len(kept3)} sensitivity L-E2 events")
    prep = prepare(ticks_df, kept, panel, bar_minutes, cand_sessions, sess, panel_ext=panel_ext)
    prep3 = prepare(ticks_df, kept3, panel, bar_minutes, cand_sessions, sess, panel_ext=panel_ext)

    tick_dir = PILOT_TICK_DIR if run == "pilot" else DEFINITIVE_TICK_DIR
    tick_files = sorted(tick_dir.glob("*.parquet"))
    data_hash = file_hash([f for f in tick_files if f.stem in set(uni)] + [cfg["bars_file"]])
    meta = {"run": run, "started_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "config_hash": config_hash(), "code_commit": ledger.code_commit(), "data_hash": data_hash, "seed": seed,
            "universe": len(uni), "universe_dropped": dropped_names, "extended_hours_curve": ext_hours,
            "sessions": [str(sess[0]), str(sess[-1]), len(sess)], "bar": cfg["bar"],
            "last_tick_utc": last_tick.isoformat(), "event_start": str(cfg["event_start"]),
            "e2_threshold": threshold, "e2_threshold_computed": computed, "e2_sensitivity_threshold": E2_MULT_SENSITIVITY,
            "events": {"L-E1": int((kept["type"] == "L-E1").sum()), "L-E2": int((kept["type"] == "L-E2").sum()),
                       "L-E2 (3x)": len(kept3), "inside": int(kept["in_session"].sum()),
                       "outside": int((~kept["in_session"]).sum())},
            "prepared_primary": prep.meta, "prepared_sensitivity": prep3.meta,
            "score_raw_rebuilt_ticks": int(ticks_df["score_raw_rebuilt"].sum()), "ticks": int(len(ticks_df)),
            "smoothing_half_life_h": cfg["smoothing_half_life_h"], "k_perm": K_PERM, "b_boot": B_BOOT, "n_placebo": N_PLACEBO,
            "python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__}
    print(json.dumps({k: v for k, v in meta.items() if k in ("events", "prepared_primary", "prepared_sensitivity")}, indent=1))

    # Cells.
    out.mkdir(parents=True, exist_ok=True)
    (out / "nulls").mkdir(exist_ok=True)
    rows, curve_rows, cell_no = [], [], 0
    specs = [(g, w, prep, GROUPS[g]) for g in GROUPS for w in WHERE] + [(SENSITIVITY, w, prep3, ("L-E2",)) for w in WHERE]
    for group, where, pr, types in specs:
        cell_no += 1
        mask = pr.events["type"].isin(types).to_numpy() & where_mask(pr.events, where)
        cell = {"cell": f"{group} | {where}", "group": group, "where": where,
                "primary_group": group in PRIMARY_GROUPS and where == "all"}
        if mask.sum() == 0:
            print(f"cell {cell['cell']}: empty")
            rows += cell_rows({"indices": INDICES, "n": 0, "n_masked": 0, "empty": True}, cell)
            continue
        t0 = time.time()
        res = measure_cell(pr, mask, seed + cell_no)
        rows += cell_rows(res, cell)
        for i, idx in enumerate(INDICES):
            for g_i in range(len(OFFSETS_H)):
                curve_rows.append({"cell": cell["cell"], "index": idx, "offset_h": OFFSETS_H[g_i],
                                   "mean_m": res["mean_m"][g_i, i], "R": res["R"][g_i, i],
                                   "placebo_mean_m": res["placebo_mean_m"][g_i, i],
                                   "mean_r": res["mean_r"][g_i] if i == 0 else np.nan,
                                   "Rp": res["Rp"][g_i] if i == 0 else np.nan})
        pd.DataFrame(res["null_M"], columns=list(INDICES)).to_csv(
            out / "nulls" / (cell["cell"].replace(" | ", "_").replace(" ", "_").replace("(", "").replace(")", "") + ".csv.gz"),
            index=False, float_format="%.6g")
        head = {idx: {"n": int(res["n_per_index"][i]), "M": round(float(res["M"][i]), 3), "p_M": float(res["p_M"][i]),
                      "t_half_h": None if np.isnan(res["t_half"][i]) else round(float(res["t_half"][i]), 3),
                      "t_full_h": None if np.isnan(res["t_full"][i]) else round(float(res["t_full"][i]), 3),
                      "rp_half": None if np.isnan(res["rp_half"][i]) else round(float(res["rp_half"][i]), 3)}
                for i, idx in enumerate(INDICES) if idx in PRIMARY_INDICES}
        ledger.append(f"{run}:{cell['cell']}", data_hash, seed + cell_no, head,
                      note=f"n={res['n']}; primary cell" if cell["primary_group"] else f"n={res['n']}; secondary")
        print(f"cell {cell['cell']}: n={res['n']} in {time.time() - t0:.0f} s; score_exo M={res['M'][INDICES.index('score_exo')]:.2f} "
              f"p={res['p_M'][INDICES.index('score_exo')]:.3f} T½={res['t_half'][INDICES.index('score_exo')]:.2f}")

    cells = pd.DataFrame(rows)
    cells["primary"] = cells["primary_group"] & cells["index"].isin(PRIMARY_INDICES)
    cells["contaminated"] = cells["index"].isin(CONTAMINATED)
    sec = ~cells["primary"] & cells["p_M"].notna()
    cells["p_M_bh"] = np.nan
    cells.loc[sec, "p_M_bh"] = bh_adjust(cells.loc[sec, "p_M"].to_numpy())
    cells["secondary_cells_examined"] = int(sec.sum())
    cells.to_csv(out / "cells.csv", index=False, float_format="%.6g")
    pd.DataFrame(curve_rows).to_csv(out / "curves.csv.gz", index=False, float_format="%.6g")

    # Alignment, once per index.
    print("alignment")
    hb = hourly_bars(bars, uni, sess, bar_minutes)
    al_rows, al_curves = [], []
    for i, idx in enumerate(INDICES):
        a = alignment(prep.ticks, hb, idx, B_BOOT, seed)
        al_rows.append({"index": idx, "best_k": a["best_k"], "k_lo": a["ci_k"][0], "k_hi": a["ci_k"][1],
                        "best_corr": a["best_corr"], "corr_k0": float(a["corr"][list(a["ks"]).index(0)]),
                        "n_pairs_k0": a["n_pairs_at_k0"], "n_stocks": a["n_stocks"], "n_sessions": a["n_sessions"],
                        "contaminated": idx in CONTAMINATED,
                        "boot_share_at_best": float(np.mean(a["boot_best_k"] == a["best_k"]))})
        al_curves += [{"index": idx, "k": int(k), "corr": float(c)} for k, c in zip(a["ks"], a["corr"])]
        ledger.append(f"{run}:alignment:{idx}", data_hash, seed, {"best_k": a["best_k"], "ci": a["ci_k"],
                                                                 "best_corr": round(a["best_corr"], 4)})
        print(f"  {idx}: best k {a['best_k']} ({a['ci_k']}), corr {a['best_corr']:.3f}")
    pd.DataFrame(al_rows).to_csv(out / "alignment.csv", index=False, float_format="%.6g")
    pd.DataFrame(al_curves).to_csv(out / "alignment_curves.csv", index=False, float_format="%.6g")

    meta["finished_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    meta["run_seconds"] = round(time.time() - t_start)
    meta["cells"] = int(cells["cell"].nunique())
    meta["secondary_cells_examined"] = int(sec.sum())
    (out / "run_meta.json").write_text(json.dumps(meta, indent=1, default=str))
    print(f"done in {meta['run_seconds']} s")


if __name__ == "__main__":
    main()
