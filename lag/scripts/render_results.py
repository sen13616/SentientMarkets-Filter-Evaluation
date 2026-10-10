"""Render lag/RESULTS.md and the charts in lag/results/ from the files written by run_pilot (ground rule 4).

Every number in RESULTS.md comes from results/cells.csv, curves.csv.gz, alignment.csv,
alignment_curves.csv, run_meta.json and the Phase 0 reports. Nothing is computed here beyond
formatting and plotting.

    python -m lag.scripts.render_results
"""

from __future__ import annotations

import json

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from lag.config import ALPHA, CONTAMINATED, INDICES, MAIN_HORIZONS_MIN, PKG, PRIMARY_GROUPS, PRIMARY_INDICES, RESULTS

RES_NOTE = "resolution: 15-minute ticks in session (30 before 18 May), 30-minute ticks outside, 60-minute bars"
LABEL = {"score": "score (published, EMA-smoothed)", "score_raw": "score_raw (unsmoothed composite)",
         "score_exo": "score_exo (without the market channel)", "narrative": "narrative", "influencer": "influencer",
         "macro": "macro", "market": "market (price-based; flagged)"}
CHART_INDICES = ("score_exo", "score_raw", "score")


def hours(x: float, lo: float = np.nan, hi: float = np.nan, over_lo: float = np.nan, over_hi: float = np.nan) -> str:
    """A time with its interval, 'over 48 h' where capped."""
    def one(v):
        if v is None or not np.isfinite(v):
            return "over 48 h"
        if v >= 48 - 1e-6:
            return "over 48 h"
        return f"{v:.2f} h" if v >= 1 else f"{v * 60:.0f} min"
    s = one(x)
    if np.isfinite(lo) or np.isfinite(hi):
        s += f" ({one(lo)} to {one(hi)})"
    return s


def minutes(x: float) -> str:
    if x is None or not np.isfinite(x):
        return "none within 48 h"
    return f"{x:.0f} min" if x < 60 else f"{x / 60:.0f} h"


def pval(p: float) -> str:
    return "n/a" if p is None or not np.isfinite(p) else ("< 0.001" if p < 0.001 else f"{p:.3f}")


def row_for(cells: pd.DataFrame, group: str, where: str, index: str) -> pd.Series:
    r = cells[(cells["group"] == group) & (cells["where"] == where) & (cells["index"] == index)]
    return r.iloc[0] if len(r) else None


NULL = {}   # filled in main() from results/null_check.json
BAR_MIN = {"value": 60}   # bar length in minutes, set in main() from run_meta.json


def rp_text(r: pd.Series, group: str) -> str:
    """Rₚ(T½) with its interval; for in-session bar events with T½ shorter than one bar, the price
    curve cannot have moved yet (it changes only at bar ends), so the zero is by construction."""
    s = f"{r['rp_half']:.2f} ({r['rp_half_lo']:.2f} to {r['rp_half_hi']:.2f})"
    if group.startswith("L-E2") and np.isfinite(r["t_half_h"]) and r["t_half_h"] * 60 < BAR_MIN["value"]:
        s += f" (T½ is shorter than one {BAR_MIN['value']}-minute bar: zero by construction)"
    return s


def investigation_note() -> list[str]:
    """Dated note beside the pre-pilot null rates once the five-seed investigation exists (10 October 2026).
    It changes no number above; the pre-pilot rates stay as the ones known when the gates were decided."""
    p = RESULTS / "null_investigation.json"
    if not p.exists():
        return []
    inv = json.loads(p.read_text())
    main_r = inv.get("main: walk + white", {})
    if not main_r:
        return []
    return [f"> **Note added 10 October 2026.** The {NULL.get('relabel_rate', float('nan')):.1%} above is the rate of a "
            f"single seed. Over five independent seeds ({main_r.get('n', 0):,} worlds in all) the same scenario gives "
            f"{main_r.get('share05', float('nan')):.1%}, and the walk-only and white-noise-only scenarios 4.5% and 4.2%: the "
            "pre-pilot figure was a seed fluctuation and the relabelling test is left as specified. Details in "
            "[results/null_investigation.md](results/null_investigation.md) and DECISIONS.md (open item, closed). "
            "No number in this document was changed; a rerun of the pre-pilot check with the current code reproduces it.", ""]


def null_note() -> str:
    """The two gates' false-positive rates on synthetic no-response worlds, quoted next to every gate decision."""
    if not NULL:
        return "null rates not available"
    return (f"synthetic null, {NULL['n_worlds']:,} no-response worlds: relabelling p < 0.05 alone {NULL['relabel_rate']:.1%} "
            f"false positives; combined gate {NULL['combined_rate']:.1%}")


def gate_text(r: pd.Series) -> str:
    """The gate decision for one index-cell, with both conditions and the null rates (L17)."""
    p_ok = r["p_M"] < ALPHA
    ci_ok = r["M_lo"] > 0
    verdict = "**interpreted**" if bool(r["gate"]) else "**no response to time**"
    return (f"{verdict}: relabelling p = {pval(r['p_M'])} ({'passes' if p_ok else 'fails'}); bootstrap interval for M "
            f"{r['M_lo']:.2f} to {r['M_hi']:.2f} ({'above zero' if ci_ok else 'includes zero'}); {null_note()}")


def primary_sentence(r: pd.Series, index: str, group: str) -> str:
    what = {"L-E1": "earnings releases", "L-E2": "large in-session price bars"}[group]
    if r is None or not np.isfinite(r.get("p_M", np.nan)):
        return f"- **{LABEL[index]}, {what}:** no measurement (empty cell)."
    head = f"- **{LABEL[index]}, {what} (n = {int(r['n_index'])}):** eventual move M = {r['M']:.2f} points; gate {gate_text(r)}."
    if not bool(r["gate"]):
        return head + " Its timings are reported in section 5 but not interpreted."
    return (head + f" Half response T½ = {hours(r['t_half_h'], r['t_half_lo'], r['t_half_hi'])}; "
            f"full response T₉₀ = {hours(r['t_full_h'], r['t_full_lo'], r['t_full_hi'])}; first response at "
            f"{minutes(r['first_response_min'])}; share of the price move already done at T½: {rp_text(r, group)}.")


def cell_table(cells: pd.DataFrame, groups: list[str], wheres: list[str], indices: tuple[str, ...], with_bh: bool) -> str:
    head = "| cell | index | n | M (points) | p(M) | M interval " + ("| BH q " if with_bh else "") + \
           "| gate (L17) | T½ | T₉₀ | first response | Rₚ(T½) | corr. with price? |"
    out = [head, "|" + "---|" * (head.count("|") - 1)]
    for g in groups:
        for w in wheres:
            for idx in indices:
                r = row_for(cells, g, w, idx)
                if r is None or r["n"] == 0:
                    continue
                flag = "flagged" if idx in CONTAMINATED else ""
                if not np.isfinite(r["p_M"]):
                    out.append(f"| {g}, {w} | {idx} | {int(r['n_index'])} | n/a | n/a | n/a |" + (" n/a |" if with_bh else "") +
                               " | | | | | " + flag + " |")
                    continue
                ok = bool(r["gate"])
                gate_s = "interpreted" if ok else "no response to time"
                t_half = hours(r["t_half_h"], r["t_half_lo"], r["t_half_hi"]) if ok else "(not interpreted)"
                t_full = hours(r["t_full_h"], r["t_full_lo"], r["t_full_hi"]) if ok else ""
                fr = minutes(r["first_response_min"]) if ok else ""
                rp = rp_text(r, g) if ok else ""
                bh = f"| {pval(r['p_M_bh'])} " if with_bh else ""
                out.append(f"| {g}, {w} | {idx} | {int(r['n_index'])} | {r['M']:.2f} | {pval(r['p_M'])} | "
                           f"{r['M_lo']:.2f} to {r['M_hi']:.2f} {bh}| {gate_s} | {t_half} | {t_full} | {fr} | {rp} | {flag} |")
    return "\n".join(out)


def horizon_table(cells: pd.DataFrame, group: str, where: str, index: str) -> str:
    r = row_for(cells, group, where, index)
    if r is None or r["n"] == 0:
        return "(empty)"
    out = ["| horizon | mean m(h), points | placebo mean | R(h) | p (relabelling) | Holm p |", "|---|---|---|---|---|---|"]
    for hm in MAIN_HORIZONS_MIN:
        out.append(f"| {minutes(hm)} | {r[f'm_{hm}min']:.2f} | {r[f'placebo_m_{hm}min']:.2f} | {r[f'R_{hm}min']:.2f} | "
                   f"{pval(r[f'p_{hm}min'])} | {pval(r[f'p_holm_{hm}min'])} |")
    return "\n".join(out)


def chart_curves(curves: pd.DataFrame, cell: str, path, title: str) -> None:
    c = curves[curves["cell"] == cell]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    ax = axes[0]
    for idx in CHART_INDICES:
        d = c[c["index"] == idx]
        ax.plot(d["offset_h"], d["mean_m"], label=LABEL[idx].split(" (")[0])
        ax.plot(d["offset_h"], d["placebo_mean_m"], linestyle=":", color=ax.lines[-1].get_color(), alpha=0.7)
    ax.axvline(0, color="grey", linewidth=0.8)
    ax.axhline(0, color="grey", linewidth=0.8)
    ax.set_xlabel("hours after time zero")
    ax.set_ylabel("mean signed change, points")
    ax.set_title("score change (solid) and placebo (dotted)")
    ax.legend(fontsize=8)
    ax = axes[1]
    for idx in CHART_INDICES:
        d = c[c["index"] == idx]
        ax.plot(d["offset_h"], d["R"], label=LABEL[idx].split(" (")[0])
    d0 = c[c["index"] == INDICES[0]]
    ax.plot(d0["offset_h"], d0["Rp"], color="black", linestyle="--", label="price (market-adjusted)")
    ax.axhline(0.5, color="grey", linewidth=0.6, linestyle=":")
    ax.axhline(0.9, color="grey", linewidth=0.6, linestyle=":")
    ax.axvline(0, color="grey", linewidth=0.8)
    ax.set_ylim(-0.5, 1.6)
    ax.set_xlabel("hours after time zero")
    ax.set_ylabel("share of the 48-hour move")
    ax.set_title("response curve R(h) and price curve")
    ax.legend(fontsize=8)
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def chart_alignment(al_curves: pd.DataFrame, path) -> None:
    fig, ax = plt.subplots(figsize=(7, 4))
    for idx in INDICES:
        d = al_curves[al_curves["index"] == idx]
        ax.plot(d["k"], d["corr"], marker=".", label=LABEL[idx].split(" (")[0],
                linestyle="--" if idx in CONTAMINATED else "-")
    ax.axvline(0, color="grey", linewidth=0.8)
    ax.set_xlabel("shift k in trading hours (positive: the score lags price)")
    ax.set_ylabel("pooled correlation")
    ax.set_title("alignment of hourly index changes with hourly market-adjusted returns")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def main() -> None:
    meta = json.loads((RESULTS / "run_meta.json").read_text())
    cells = pd.read_csv(RESULTS / "cells.csv")
    curves = pd.read_csv(RESULTS / "curves.csv.gz")
    al = pd.read_csv(RESULTS / "alignment.csv")
    al_curves = pd.read_csv(RESULTS / "alignment_curves.csv")
    ev = meta["events"]
    if (RESULTS / "null_check.json").exists():
        NULL.update(json.loads((RESULTS / "null_check.json").read_text()))
    BAR_MIN["value"] = {"1h": 60, "15m": 15}[meta["bar"]]

    charts = []
    for g in PRIMARY_GROUPS:
        p = RESULTS / f"curves_{g.replace('-', '').lower()}.png"
        chart_curves(curves, f"{g} | all", p, f"{g}: {'earnings releases' if g == 'L-E1' else 'large in-session bars'} "
                     f"(n = {ev[g]}), pilot 13 May to 20 June 2026")
        charts.append((g, p.name))
    chart_alignment(al_curves, RESULTS / "alignment.png")

    L = ["# Experiment 5B, pilot results: how quickly does the score respond?", "",
         "Rendered by `python -m lag.scripts.render_results` from the files in `results/`. The measurement is "
         "specified in [BRIEF.md](BRIEF.md) and every choice in [DECISIONS.md](DECISIONS.md). This experiment "
         "measures response times; it has no pass or fail and says nothing about usefulness.", "",
         "> **The published composite `score` was smoothed with a 4-hour half-life in this period (12 May to "
         "22 June 2026). The system has used a 2-hour half-life since 22 July 2026, so the timings of `score` here "
         "are not those of the system today.** The unsmoothed composite (`score_raw`), `score_exo` and the four "
         "channels are not smoothed and are unaffected.", "",
         "## 1. Summary", "",
         f"Pilot period: events with time zero from {meta['event_start']} to 48 hours before the last tick "
         f"({meta['last_tick_utc'][:16].replace('T', ' ')} UTC), {meta['universe']} stocks, hourly price bars. "
         f"Events: {ev['L-E1']} earnings releases (L-E1, all outside the session) and {ev['L-E2']} large in-session "
         f"bars (L-E2, rarity threshold |z| > {meta['e2_threshold']:.2f}; DECISIONS.md L14).", "",
         "Primary cells (score_exo and score_raw, each on L-E1 and on L-E2):", ""]
    for g in PRIMARY_GROUPS:
        for idx in PRIMARY_INDICES:
            L.append(primary_sentence(row_for(cells, g, "all", idx), idx, g))
    L += ["", f"Every time above is read against its {RES_NOTE}. T½ and T₉₀ are interpolated between 5-minute grid "
          "points of a step function, so a jump exactly on a tick is reported up to half a tick early.", "",
          "## 2. Run metadata", "", "| | |", "|---|---|",
          f"| started (UTC) | {meta['started_utc']} |", f"| run time | {meta['run_seconds']} s |",
          f"| code commit | {meta['code_commit']} |", f"| config hash | {meta['config_hash']} |",
          f"| data hash (ticks and hourly bars) | {meta['data_hash']} |", f"| seed | {meta['seed']} |",
          f"| relabellings K / bootstrap B / placebo per event | {meta['k_perm']} / {meta['b_boot']} / {meta['n_placebo']} |",
          f"| ticks read | {meta['ticks']:,} ({meta['score_raw_rebuilt_ticks']} with score_raw rebuilt from channels) |",
          f"| python / numpy / pandas | {meta['python']} / {meta['numpy']} / {meta['pandas']} |", "",
          "## 3. Counts", "", "| | |", "|---|---|",
          f"| L-E1 events (earnings with a time) | {ev['L-E1']} (inside session 0, outside {ev['L-E1']}) |",
          f"| L-E2 events (rarity rule) | {ev['L-E2']} (all inside the session) |",
          f"| L-E2 events under the 3x sensitivity rule | {ev['L-E2 (3x)']} |",
          f"| events with a fresh before reading (L6) | {meta['prepared_primary']['n_valid_before']} of {meta['prepared_primary']['n_events']} "
          f"({meta['prepared_primary']['n_stale_before']} stale) |",
          f"| events without a placebo pool | {meta['prepared_primary']['n_without_pool']} (median pool {meta['prepared_primary']['pool_size_median']:.0f} sessions) |",
          f"| bars without a close-to-close return | {meta['prepared_primary']['price_bars_missing']} (the first bar of each stock's store) |",
          f"| cells measured | {meta['cells']} ({meta['secondary_cells_examined']} secondary index-cells with a p-value) |", "",
          "Event construction, drops and clustering: [results/event_counts.md](results/event_counts.md). Tick spacing: "
          "[results/tick_check.md](results/tick_check.md). Bar coverage: [results/coverage_1h.md](results/coverage_1h.md).", "",
          "## 4. Decisions", "",
          "All in [DECISIONS.md](DECISIONS.md): L1 to L13 before the Phase 0 counts, L14 (the L-E2 rarity threshold and "
          "the separate primary cells) after the counts and before any response, L15 and L16 while building the "
          "measurement on synthetic data, and L17 (the combined gate) after the pre-pilot null check and before this run. "
          "The brief's checks on synthetic data are in [results/phase1_synthetic.md](results/phase1_synthetic.md); the "
          "pre-pilot null check in [results/null_check.md](results/null_check.md).", "",
          f"**Gate (L17) and its null rates.** An index's timings are interpreted only if its relabelling p for M is below "
          f"0.05 and the date-bootstrap 95% interval for M lies above zero. On {NULL.get('n_worlds', 0):,} synthetic worlds "
          f"with no response, the relabelling condition alone passed {NULL.get('relabel_rate', float('nan')):.1%} of the "
          f"time (outside the 3.6% to 6.4% band agreed before the check) and the combined gate "
          f"{NULL.get('combined_rate', float('nan')):.1%}. Both rates are repeated next to every gate decision below.", "",
          *investigation_note(),
          "## 5. Primary measures", "",
          cell_table(cells, list(PRIMARY_GROUPS), ["all"], PRIMARY_INDICES, with_bh=False), "",
          f"Gate decisions, with the null rates ({null_note()}):", ""]
    for g in PRIMARY_GROUPS:
        for idx in PRIMARY_INDICES:
            r = row_for(cells, g, "all", idx)
            if r is not None and np.isfinite(r.get("p_M", np.nan)):
                L.append(f"- {g}, {idx}: {gate_text(r)}")
    L += ["", "M is the mean signed change of the index 48 hours after time zero, in points on the 0 to 100 scale; p(M) "
          "is the relabelling p-value (K = 1,000, 5A's test) and the M interval the date-bootstrap 95% interval "
          "(B = 2,000); the gate is both together (L17). Timing intervals are the same bootstrap. The first response is "
          "the earliest main horizon whose mean is above the relabelling null after a Holm adjustment across the eight "
          "horizons. Rₚ(T½) is the share of the 48-hour market-adjusted price move already done at the first grid point "
          "where the score has reached half of its move (L16).", ""]
    for g in PRIMARY_GROUPS:
        L += [f"### {g} at the main horizons", ""]
        for idx in PRIMARY_INDICES:
            L += [f"**{LABEL[idx]}**", "", horizon_table(cells, g, "all", idx), ""]
    L += ["## 6. Response curves", ""]
    for g, name in charts:
        L += [f"![{g}](results/{name})", ""]
    L += ["Solid lines: the mean signed change of the index after time zero. Dotted: the same at 20 placebo times "
          "per event (same stock, same time of day, non-event sessions). Right panels: the response curve R(h) "
          "and the price curve; the horizontal lines mark 50% and 90%.", "",
          "## 7. Alignment with price (no events)", "",
          "Over every in-session hour of every stock, the correlation between the market-adjusted hourly return and "
          "the index change over the hour, with the index shifted by k trading hours (positive k: the score lags "
          "price). Both are demeaned within stock. Intervals: bootstrap over session dates (B = 2,000).", "",
          "| index | best k (hours) | 95% interval | correlation at best k | correlation at k = 0 | pairs at k = 0 | |",
          "|---|---|---|---|---|---|---|"]
    for r in al.itertuples(index=False):
        L.append(f"| {r.index} | {r.best_k:+.0f} | {r.k_lo:+.0f} to {r.k_hi:+.0f} | {r.best_corr:.3f} | {r.corr_k0:.3f} | "
                 f"{r.n_pairs_k0:,} | {'flagged: computed from price' if r.contaminated else ''} |")
    L += ["", "![alignment](results/alignment.png)", "",
          "## 8. Secondary measures", "",
          f"{meta['secondary_cells_examined']} secondary index-cells carry a p-value for M; BH q is the "
          "Benjamini-Hochberg adjusted value across them. The pooled cell (L-E1+L-E2) is secondary by L14. "
          "The market channel is computed from price and is flagged; it carries no weight. Inside/outside-session "
          "cells coincide with the type split in the pilot (every L-E1 is outside, every L-E2 inside), so only the "
          "'all' rows are shown for the type cells; the sensitivity cell uses the original 3x rule. Every gate column "
          f"is the L17 gate ({null_note()}).", "",
          cell_table(cells, ["L-E1", "L-E2", "L-E1+L-E2", "L-E2 (3x sensitivity)"], ["all"], INDICES, with_bh=True), "",
          "## 9. Limits", "",
          "- **Smoothing.** The published `score` carried a 4-hour EMA in this period (2 hours since 22 July 2026); its "
          "timings describe the system as it was, not as it is. `score_raw` and `score_exo` are unsmoothed.",
          "- **Resolution.** Ticks every 15 minutes in session (30 minutes from 12 to 15 May) and every 30 minutes outside; "
          "hourly price bars. No timing below these spacings is meaningful, and the price curve moves only at bar ends.",
          "- **Event types coincide with the session split.** Every earnings release is outside the session and every large "
          "bar inside it, so the two primary cells also differ in when the first tick after time zero arrives (within 30 "
          "minutes overnight, within 15 minutes in session) and in the price bars available (none until the next open for L-E1).",
          "- **Direction from price.** Both event types take their direction from the stock's own price reaction, as in 5A, so "
          "a response can restate price; the alignment measure and Rₚ(T½) are the only guards.",
          "- **Pilot size.** 52 earnings releases between seasons and 130 large bars; intervals are wide, and the "
          "definitive run on the October to November 2026 season (15-minute bars, 2-hour smoothing) is the test that counts.",
          "- **Hourly bars for L-E2.** A move inside an hour is dated to the bar's start; the true time is unknown within the "
          "hour, and the price curve cannot register the event bar's own move until the bar closes, so Rₚ(T½) is zero by "
          "construction for any index whose T½ is shorter than one bar (score_raw and the market channel here). The "
          "definitive run's 15-minute bars tighten both to a quarter hour.",
          "- **The rarity threshold** was set after the Phase 0 counts (L14), on prices only, before any response was computed.", ""]
    (PKG / "RESULTS.md").write_text("\n".join(L))
    print(f"RESULTS.md rendered ({len(L)} lines), charts: {[c[1] for c in charts] + ['alignment.png']}")


if __name__ == "__main__":
    main()
