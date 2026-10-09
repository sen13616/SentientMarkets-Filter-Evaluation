"""Phase 0, step 5 (as amended by L14): build the pilot's L-E1 and L-E2 events and write results/event_counts.md.

Two event sets are built and counted: the primary set, with the L-E2 rarity threshold of L14, and
the sensitivity set, with the original 3x rule. Counts by type, inside and outside the session, by
week, with every drop and the clustering. No response is computed: the only sentiment field read is
the stamp of the last tick, which fixes the end of the event period (t0 + 48 h must not pass it).
The per-event tables are written to `$SM_DATA_DIR/lag/events_<run>.parquet` and
`events_<run>_3x.parquet` (local; they name company events, so they are not committed).

    python -m lag.scripts.event_counts
"""

from __future__ import annotations

import pandas as pd

from responsiveness.events import Calendar
from responsiveness.market import build_prices

from lag import events as ev_mod
from lag.config import E2_MULT_SENSITIVITY, E2_RARITY_SHARE, E2_Z_THRESHOLD, LAG_DATA, RESULTS, RUNS
from lag.data import load_bars, load_daily, load_earnings, load_ticks, sessions, universe


def table(df: pd.DataFrame, rows: str, cols: str) -> str:
    ct = pd.crosstab(df[rows], df[cols], margins=True, margins_name="all")
    head = "| " + rows + " | " + " | ".join(str(c) for c in ct.columns) + " |"
    out = [head, "|" + "---|" * (len(ct.columns) + 1)]
    for r, row in ct.iterrows():
        out.append(f"| {r} | " + " | ".join(str(int(v)) for v in row) + " |")
    return "\n".join(out)


STATUS_NOTE = ("Statuses: `kept`; `outside_price_history` (an earnings row from before the bar period; the cache holds "
               "several years per stock); `no_time` (earnings without a time of day); `no_reaction_session`; "
               "`no_direction` (zero or missing market-adjusted return); `earnings_session` (an L-E2 bar in a session "
               "that is or may be an earnings reaction session); `cluster_dropped_for_<type>` (another event of the "
               "same stock within 48 hours, of higher priority or earlier); `outside_period`.")


def describe_set(name: str, ev: pd.DataFrame, counts: dict, threshold: float) -> list[str]:
    kept = ev[ev["status"] == "kept"].copy()
    kept["where"] = kept["in_session"].map({True: "inside session", False: "outside session"})
    kept["week"] = kept["week"].astype(str)
    e1, e2 = kept[kept["type"] == "L-E1"], kept[kept["type"] == "L-E2"]
    a = counts["e2_attrs"]
    L = [f"## {name}", "", f"L-E2 threshold: |z| > {threshold:.4f}, where z is the bar's market-adjusted move over the "
         f"stock's normal move for that time of day.", "", "### Kept events", "", table(kept, "type", "where"), "",
         "### By week (Monday of the week, New York time)", "", table(kept, "week", "type"), ""]
    if len(e1):
        vc = e1["release_et"].dt.strftime("%H:%M").value_counts().sort_index()
        L += ["### L-E1 release times (New York)", "", "| time | events |", "|---|---|"]
        L += [f"| {k} | {v} |" for k, v in vc.items()] + [""]
    if len(e2):
        vc = e2["tod"].value_counts().sort_index()
        L += ["### L-E2 bar start times (New York)", "", "| bar start | events | mean |z| |", "|---|---|---|"]
        L += [f"| {k} | {v} | {e2.loc[e2['tod'] == k, 'z'].abs().mean():.1f} |" for k, v in vc.items()] + [""]
    L += ["### Every candidate, by status", "", table(ev, "status", "type"), "",
          "### L-E2 construction", "",
          f"- Bars tested (a normal move exists for the stock and time of day): {a['bars_tested']:,}",
          f"- Bars without a normal move (fewer than 10 non-earnings bars at that time of day): {a['bars_without_normal_move']:,}",
          f"- Bars over the threshold: {a['bars_over_threshold']:,} ({a['bars_over_threshold'] / a['bars_tested']:.2%} of bars tested)",
          f"- Stock-sessions with such a bar (candidates, first bar per session): {int((ev['type'] == 'L-E2').sum()):,}",
          f"- Of those in an earnings reaction session (excluded): {int(((ev['type'] == 'L-E2') & (ev['status'] == 'earnings_session')).sum()):,}",
          "", "### Clustering", "",
          f"- Candidates entering clustering (directional, in the price history, not excluded): "
          f"{int(ev['status'].isin(['kept', 'outside_period']).sum() + ev['status'].str.startswith('cluster_dropped').sum())}",
          f"- Dropped by clustering: {int(ev['status'].str.startswith('cluster_dropped').sum())} "
          f"({', '.join(f'{k.replace('cluster_dropped_for_', 'for ')}: {v}' for k, v in ev['status'][ev['status'].str.startswith('cluster_dropped')].value_counts().items()) or 'none'})",
          f"- Kept but outside the event period: {int((ev['status'] == 'outside_period').sum())}",
          f"- Kept, in period: {len(kept)} ({len(e1)} L-E1, {len(e2)} L-E2; "
          f"{int(kept['in_session'].sum())} inside the session, {int((~kept['in_session']).sum())} outside)",
          f"- Stocks with a kept event: {kept['ticker'].nunique()}", ""]
    return L


def main(run: str = "pilot") -> None:
    cfg = RUNS[run]
    uni = universe(run)
    sess = sessions(run)
    daily = load_daily(run)
    all_sessions = sorted(daily["date"].unique())
    cal = Calendar(all_sessions)
    prices = build_prices(daily, uni, all_sessions)
    earn = load_earnings(run, uni)
    bars = load_bars(run)
    panel = ev_mod.build_panel(bars, uni, sess)
    last_tick = load_ticks(run, uni)["ts"].max()

    # The rarity threshold: fixed in config for the pilot, and checked here against the rule on the
    # period's bars; computed by the rule for the definitive run (L14).
    normal = ev_mod.normal_move(panel, ev_mod.earnings_sessions(earn, cal))
    z = ev_mod.z_scores(panel, normal)
    computed = ev_mod.rarity_threshold(z)
    fixed = E2_Z_THRESHOLD.get(run)
    if fixed is None:
        threshold = computed
    else:
        if abs(computed - fixed) > 5e-4:
            raise RuntimeError(f"rarity threshold from the bars ({computed:.4f}) differs from the fixed value ({fixed})")
        threshold = fixed
    n_z = int(z.notna().sum().sum())

    ev, counts = ev_mod.build_events(earn, prices, panel, cal, cfg["event_start"], last_tick, threshold)
    ev3, counts3 = ev_mod.build_events(earn, prices, panel, cal, cfg["event_start"], last_tick, E2_MULT_SENSITIVITY)
    LAG_DATA.mkdir(parents=True, exist_ok=True)
    ev.to_parquet(LAG_DATA / f"events_{run}.parquet", index=False)
    ev3.to_parquet(LAG_DATA / f"events_{run}_3x.parquet", index=False)

    L = [f"# Event counts, {run} (Phase 0, step 5, as amended by L14)", "",
         f"Universe: {len(uni)} names. Bars: {cfg['bar']}, {sess[0]} to {sess[-1]} ({len(sess)} sessions; "
         f"{len(bars):,} bars for {bars['ticker'].nunique()} tickers). Event period: t0 from {cfg['event_start']} "
         f"to 48 hours before the last tick ({last_tick:%Y-%m-%d %H:%M} UTC). Earnings tables: Experiment 5A's "
         f"yfinance cache ({len(earn):,} rows, {earn['ticker'].nunique()} tickers).", "",
         "No response has been computed. The only sentiment value read is the stamp of the last tick.", "",
         "## L-E2 rarity threshold (L14)", "",
         f"Pooled over {n_z:,} in-session bars with a standardised move, the |z| exceeded by {E2_RARITY_SHARE:.1%} of "
         f"bars is **{computed:.4f}**" + (f"; the value fixed in config for this run is {fixed}." if fixed is not None
                                           else "; this run uses the computed value.") + "",
         f"For comparison, |z| > {E2_MULT_SENSITIVITY:.0f} is exceeded by "
         f"{float((z.abs() > E2_MULT_SENSITIVITY).sum().sum()) / n_z:.2%} of bars.", "",
         "| |z| quantile | value |", "|---|---|"]
    a = z.abs().to_numpy().ravel()
    a = a[~pd.isna(a)]
    import numpy as np
    for q in (0.99, 0.995, 0.998, 0.999):
        L.append(f"| {q:.3f} | {np.quantile(a, q):.3f} |")
    L += ["", STATUS_NOTE, ""]
    L += describe_set("Primary event set (L-E1; L-E2 with the rarity threshold)", ev, counts, threshold)
    L += describe_set(f"Sensitivity event set (L-E1; L-E2 with |z| > {E2_MULT_SENSITIVITY:.0f}, the original rule)",
                      ev3, counts3, E2_MULT_SENSITIVITY)
    L += ["## Normal moves", "",
          f"- Normal-move cells (time of day x ticker): {counts['normal_move_cells']:,} available, "
          f"{counts['normal_move_cells_missing']:,} missing",
          f"- Stocks with at least one earnings reaction session in the price history: {counts['tickers_with_earnings_sessions']}", ""]
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "event_counts.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
