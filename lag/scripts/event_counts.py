"""Phase 0, step 5: build the pilot's L-E1 and L-E2 events and write results/event_counts.md.

Counts by type, inside and outside the session, by week, with every drop and the clustering. No
response is computed: the only sentiment field read is the stamp of the last tick, which fixes
the end of the event period (t0 + 48 h must not pass it). The per-event table is written to
`$SM_DATA_DIR/lag/events_pilot.parquet` (local; it names company events, so it is not committed).

    python -m lag.scripts.event_counts
"""

from __future__ import annotations

import pandas as pd

from responsiveness.events import Calendar
from responsiveness.market import build_prices

from lag import events as ev_mod
from lag.config import LAG_DATA, RESULTS, RUNS
from lag.data import load_bars, load_daily, load_earnings, load_ticks, sessions, universe


def table(df: pd.DataFrame, rows: str, cols: str) -> str:
    ct = pd.crosstab(df[rows], df[cols], margins=True, margins_name="all")
    head = "| " + rows + " | " + " | ".join(str(c) for c in ct.columns) + " |"
    out = [head, "|" + "---|" * (len(ct.columns) + 1)]
    for r, row in ct.iterrows():
        out.append(f"| {r} | " + " | ".join(str(int(v)) for v in row) + " |")
    return "\n".join(out)


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
    ev, counts = ev_mod.build_events(earn, prices, panel, cal, cfg["event_start"], last_tick)

    LAG_DATA.mkdir(parents=True, exist_ok=True)
    ev.to_parquet(LAG_DATA / f"events_{run}.parquet", index=False)
    kept = ev[ev["status"] == "kept"].copy()
    kept["where"] = kept["in_session"].map({True: "inside session", False: "outside session"})
    kept["week"] = kept["week"].astype(str)

    period_mask = ev["in_period"]
    L = ["# Event counts, pilot (Phase 0, step 5)", "",
         f"Universe: {len(uni)} names. Bars: hourly, {sess[0]} to {sess[-1]} ({len(sess)} sessions; "
         f"{len(bars):,} bars for {bars['ticker'].nunique()} tickers). Event period: t0 from {cfg['event_start']} "
         f"to 48 hours before the last tick ({last_tick:%Y-%m-%d %H:%M} UTC). Earnings tables: Experiment 5A's "
         f"yfinance cache ({len(earn):,} rows, {earn['ticker'].nunique()} tickers).", "",
         "No response has been computed. The only sentiment value read is the stamp of the last tick.", "",
         "## Kept events", "", table(kept, "type", "where"), "",
         "### By week (Monday of the week, New York time)", "", table(kept, "week", "type"), "",
         "### L-E1 release times (New York)", ""]
    e1 = kept[kept["type"] == "L-E1"]
    if len(e1):
        vc = e1["release_et"].dt.strftime("%H:%M").value_counts().sort_index()
        L += ["| time | events |", "|---|---|"] + [f"| {k} | {v} |" for k, v in vc.items()]
    L += ["", "### L-E2 bar start times (New York)", ""]
    e2 = kept[kept["type"] == "L-E2"]
    if len(e2):
        vc = e2["tod"].value_counts().sort_index()
        L += ["| bar start | events | mean z (adjusted move / normal move) |", "|---|---|---|"]
        L += [f"| {k} | {v} | {e2.loc[e2['tod'] == k, 'z'].abs().mean():.1f} |" for k, v in vc.items()]
    L += ["", "## Every candidate, by status", "",
          "Statuses: `kept`; `outside_price_history` (an earnings row from before the bar period; the cache holds several years "
          "per stock); `no_time` (earnings without a time of day); `no_reaction_session`; `no_direction` "
          "(zero or missing market-adjusted return); `earnings_session` (an L-E2 bar in a session that is or may "
          "be an earnings reaction session); `cluster_dropped_for_<type>` (another event of the same stock "
          "within 48 hours, of higher priority or earlier); `outside_period`.", "",
          table(ev, "status", "type"), "",
          "## L-E2 construction", "",
          f"- Bars tested (a normal move exists for the stock and time of day): {counts['e2_attrs']['bars_tested']:,}",
          f"- Bars without a normal move (fewer than 10 non-earnings bars at that time of day): {counts['e2_attrs']['bars_without_normal_move']:,}",
          f"- Bars over 3 x the normal move: {counts['e2_attrs']['bars_over_threshold']:,}",
          f"- Stock-sessions with such a bar (candidates, first bar per session): {int((ev['type'] == 'L-E2').sum()):,}",
          f"- Of those in an earnings reaction session (excluded): {int(((ev['type'] == 'L-E2') & (ev['status'] == 'earnings_session')).sum()):,}",
          f"- Normal-move cells (time of day x ticker): {counts['normal_move_cells']:,} available, {counts['normal_move_cells_missing']:,} missing",
          "", "## Earnings (L-E1) construction", "",
          f"- Rows in the period's calendar range with a time of day: {int(((ev['type'] == 'L-E1') & ev['time_known']).sum())}; without: "
          f"{int(((ev['type'] == 'L-E1') & ~ev['time_known'].astype(bool)).sum())}",
          f"- Stocks with at least one earnings reaction session in the price history: {counts['tickers_with_earnings_sessions']}",
          "", "## Clustering", "",
          f"- Candidates entering clustering (directional, not excluded): "
          f"{int(ev['status'].isin(['kept', 'outside_period']).sum() + ev['status'].str.startswith('cluster_dropped').sum())}",
          f"- Dropped by clustering: {int(ev['status'].str.startswith('cluster_dropped').sum())} "
          f"({', '.join(f'{k.replace('cluster_dropped_for_', 'for ')}: {v}' for k, v in ev['status'][ev['status'].str.startswith('cluster_dropped')].value_counts().items()) or 'none'})",
          f"- Kept but outside the event period: {int((ev['status'] == 'outside_period').sum())}",
          f"- Kept, in period: {len(kept)} ({int((kept['type'] == 'L-E1').sum())} L-E1, {int((kept['type'] == 'L-E2').sum())} L-E2; "
          f"{int(kept['in_session'].sum())} inside the session, {int((~kept['in_session']).sum())} outside)",
          f"- Stocks with a kept event: {kept['ticker'].nunique()}", ""]
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "event_counts.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
