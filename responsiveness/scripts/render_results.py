"""Render responsiveness/RESULTS.md from the files in responsiveness/results/.

    python -m responsiveness.scripts.render_results

Every number comes from a file written by an earlier script: cells.csv,
unexplained.csv and run_meta.json (run_cells), event_counts.md (event_counts),
power.csv (power, computed before any response) and DECISIONS.md. Nothing is typed in
by hand. No statement about whether the score is useful is generated.
"""

from __future__ import annotations

import json
import re

import pandas as pd

from responsiveness.config import (CONTAMINATED, EVENT_END, EVENT_START, GROUPS, INDICES, LEDGER,
                                   PKG, PLUMBING_INDEX, PRIMARY_GROUP, PRIMARY_INDEX, RESULTS)


def pct(x, d=1):
    return "n/a" if pd.isna(x) else f"{100 * x:.{d}f}%"


def num(x, d=2, sign=False):
    return "n/a" if pd.isna(x) else (f"{x:+.{d}f}" if sign else f"{x:.{d}f}")


def pv(x):
    if pd.isna(x):
        return "n/a"
    if abs(x - 1 / 1001) < 1e-9:
        return "0.001 (minimum possible)"
    return f"{x:.3f}" if x >= 0.001 else f"{x:.1e}"


def ci(lo, hi, f=pct):
    return "n/a" if pd.isna(lo) or pd.isna(hi) else f"{f(lo)} to {f(hi)}"


def demote(md: str, levels: int = 1) -> str:
    return re.sub(r"^(#+)", lambda m: "#" * (len(m.group(1)) + levels), md, flags=re.M)


def body_after_title(md: str) -> str:
    return md.split("\n", 1)[1].strip() if md.startswith("# ") else md.strip()


def cluster_cell(counts_md: str, row: str, column: str) -> str:
    """One value from the same-type cluster table in event_counts.md."""
    sec = counts_md.split("## Same-type clusters", 1)[1].split("\n## ", 1)[0]
    lines = [ln for ln in sec.splitlines() if ln.startswith("|")]
    head = [h.strip() for h in lines[0].strip("|").split("|")]
    for ln in lines[2:]:
        cells = [c.strip() for c in ln.strip("|").split("|")]
        if cells[0] == row:
            return cells[head.index(column)]
    return "n/a"


def ix_label(ix: str) -> str:
    return f"{ix} (market-contaminated; no weight)" if ix in CONTAMINATED else ix


def main() -> None:
    cells = pd.read_csv(RESULTS / "cells.csv")
    un = pd.read_csv(RESULTS / "unexplained.csv")
    meta = json.loads((RESULTS / "run_meta.json").read_text())
    power = pd.read_csv(RESULTS / "power.csv")
    power["index"] = power["index"].str.replace(" (contaminated)", "", regex=False)
    pw = power.set_index(["index", "events"])
    counts_md = (RESULTS / "event_counts.md").read_text()
    decisions_md = (PKG / "DECISIONS.md").read_text()
    ledger = pd.read_csv(LEDGER)

    prim = cells[cells["primary"]].iloc[0]
    up = un[un["index"] == PRIMARY_INDEX].iloc[0]
    pp = pw.loc[(PRIMARY_INDEX, PRIMARY_GROUP)]
    pr = meta["primary"]
    verdict = "PASSES" if pr["pass"] else "DOES NOT PASS"
    cond = pr["conditions"]
    fmt_cond = lambda k: "met" if cond[k] else "**not met**"
    mde_resp = float(str(pp["detectable response rate"]).rstrip("%")) / 100
    mde_sig_pts, mde_sig_u = float(pp["detectable signed move (noise units)"]) * float(pp["mean noise unit (pts)"]), \
        float(pp["detectable signed move (noise units)"])
    signed_u = prim["avg_signed_move"] / float(pp["mean noise unit (pts)"])

    L = ["# Experiment 5A results: does the score follow real-world sentiment? (PILOT)", "",
         "> **This is a pilot run.** The event period (13 May to 18 June 2026) falls between earnings "
         f"seasons, so the primary cell holds only {int(prim['n'])} events. Before any response was computed, "
         f"the power estimate showed this run could detect, with 80% power, a response rate of about "
         f"{pct(mde_resp)} (against a placebo rate of {pp['placebo rate p0']}) and a signed average move of about "
         f"{mde_sig_u:.2f} noise units ({mde_sig_pts:.2f} points). Real effects smaller than that would usually "
         "be missed, so a null result here is weak evidence of no effect. The definitive run is planned on the "
         "October 2026 earnings season with the same code and rules.", "",
         f"**Primary cell ({PRIMARY_INDEX}, E1 and E2 pooled): {verdict}.** Response p = {pv(pr['p_response'])} "
         f"({fmt_cond('response p < 0.05')}); signed-move p = {pv(pr['p_signed'])} "
         f"({fmt_cond('signed-move p < 0.05')}); unexplained-move rate = {pct(pr['unexplained_rate'])} "
         f"({fmt_cond('unexplained-move rate < 50%')}).", "",
         "## 1. The question and the method", "",
         "The SentientMarkets API publishes a 0 to 100 sentiment score per stock, built from four channels "
         "(market, narrative, influencer, macro). This experiment checks whether the score follows real-world "
         "sentiment, in two directions:", "",
         "- **Forward:** after a public event with a known direction, did the score move, and the right way?",
         "- **Backward:** when the score made a large move, was there an event or a large price move behind it?", "",
         "Events come from public sources (yfinance): earnings releases (E1, direction = sign of the stock's "
         "market-adjusted return on the reaction session), large price moves (E2, more than 3 x ATR(14)), "
         "analyst upgrades and downgrades (E3) and insider purchases and sales (E4). For each event the score "
         "is read just before the market could react and again at the end of the following session. A "
         "change counts as a *move* if it exceeds one *noise unit*, the stock's own typical two-session change "
         "on quiet days. Significance comes from relabelling: the same number of sessions per stock is drawn "
         "at random 1,000 times and measured the same way, so each p-value says how often random dates do as "
         "well as the real events.", "",
         f"The primary cell is `{PRIMARY_INDEX}` (the score rebuilt from the narrative, influencer and macro "
         "channels, leaving out the market channel, which is computed from price) on earnings and large "
         "moves pooled. It passes if (1) the response rate beats relabelling at p < 0.05, (2) the signed "
         "average move beats relabelling at p < 0.05, and (3) fewer than half of the score's large moves "
         "are unexplained. This rule was amended before any response was computed (DECISIONS.md A6). "
         "Everything else is secondary and is reported with Benjamini-Hochberg adjusted p-values. E3 and E4 "
         f"are plumbing checks: ratings and insider trades feed the `{PLUMBING_INDEX}` channel directly.", "",
         "## 2. Run metadata", "",
         "- Command: `python -m responsiveness.scripts.run_cells`, then "
         "`python -m responsiveness.scripts.render_results`.",
         f"- Code commit `{meta['code_commit']}`; config hash `{meta['config_hash']}`; data hash "
         f"`{meta['data_hash']}`; seed {meta['seed']} (one stream per cell, DECISIONS.md M8).",
         f"- Run at {meta['run_utc']}. Relabellings {meta['n_perm']}, bootstrap draws {meta['n_boot']}, "
         f"placebo dates per event up to {meta['n_placebo']}.",
         f"- Cells: {meta['cells']} ({len(INDICES)} indices x {len(GROUPS)} event groups); ledger rows for this "
         f"run: {int((ledger['code_commit'] == meta['code_commit']).sum())} in `responsiveness/ledger.csv`.",
         "- Data: sentiment ticks and daily prices to 22 June 2026 (data lock); events whose reaction session "
         f"is from {EVENT_START} to {EVENT_END}. Every relabelled value and bootstrap draw is in "
         "`results/nulls/`.", "",
         "## 3. Data and event counts", "",
         demote(body_after_title(counts_md), 1), "",
         "### Events measured in each cell", "",
         "An event drops out of an index's cells if its stock has no noise unit for that index, or if the "
         "before or after reading is missing.", "",
         cells.pivot_table(index="group", columns="index", values="n", sort=False)
         .reindex(index=list(GROUPS), columns=list(INDICES)).astype("Int64").to_markdown(), "",
         "## 4. Decisions in full", "", demote(body_after_title(decisions_md), 2), "",
         f"## 5. Primary cell in full: `{PRIMARY_INDEX}`, E1 and E2 pooled", "",
         f"{int(prim['n'])} events on {int(prim['distinct dates'])} distinct reaction dates; excluded: "
         f"{int(prim['excluded: no noise unit'])} without a noise unit, {int(prim['excluded: no before reading'])} "
         f"without a before reading, {int(prim['excluded: no after reading'])} without an after reading.", "",
         "Each result sits next to the smallest effect this sample could detect with 80% power, computed in "
         "Phase 0 before any response was seen (`results/power.csv`).", "",
         "| measure | result | 95% interval (date bootstrap) | random dates (relabelling mean) | p | detectable "
         "with 80% power | pass condition |", "|---|---|---|---|---|---|---|",
         f"| response rate | {pct(prim['response_rate'])} ({int(prim['moves'])} of {int(prim['n'])}) | "
         f"{ci(prim['response_ci_lo'], prim['response_ci_hi'])} | {pct(prim['null_response_mean'])} | "
         f"{pv(prim['p_response'])} | {pct(mde_resp)} | p < 0.05: {fmt_cond('response p < 0.05')} |",
         f"| signed average move (points) | {num(prim['avg_signed_move'], sign=True)} "
         f"({signed_u:+.2f} noise units) | {ci(prim['signed_ci_lo'], prim['signed_ci_hi'], lambda x: num(x, sign=True))} "
         f"| {num(prim['null_signed_mean'], sign=True)} | {pv(prim['p_signed'])} | {mde_sig_pts:.2f} points "
         f"({mde_sig_u:.2f} noise units) | p < 0.05: {fmt_cond('signed-move p < 0.05')} |",
         f"| unexplained-move rate | {pct(up['rate'])} ({int(up['unexplained'])} of {int(up['large'])} large "
         f"moves) | not computed | n/a | n/a | not estimated (needs changes around events) | < 50%: "
         f"{fmt_cond('unexplained-move rate < 50%')} |",
         f"| direction accuracy | {pct(prim['direction_accuracy'])} ({int(prim['right'])} of {int(prim['moves'])} "
         f"moves) | {ci(prim['accuracy_ci_lo'], prim['accuracy_ci_hi'])} | n/a | {pv(prim['p_direction_binom'])} "
         f"(exact binomial vs 50%) | {pp['detectable accuracy at that rate']} at {int(pp['moves at detectable rate'])} "
         "moves | reported only (A6) |",
         f"| wrong-way rate | {pct(prim['wrong_way_rate'])} | | | | | reported only |",
         f"| miss rate | {pct(prim['miss_rate'])} | | | | | reported only |", "",
         f"Placebo dates (up to 20 per event, quiet sessions of the same stock, given the event's direction): "
         f"{int(prim['placebo_n'])} dates; response rate {pct(prim['placebo_response_rate'])}, direction accuracy "
         f"{pct(prim['placebo_direction_accuracy'])}, signed average move "
         f"{num(prim['placebo_avg_signed_move'], sign=True)} points. Placebo dates inside an E4 window: "
         f"{int(prim['placebo_in_e4_window'])}.", "",
         f"**Verdict: the primary cell {verdict.lower()}** under the amended rule (DECISIONS.md A6).", "",
         "## 6. Scorecards by index and event type", "",
         "p-values are one-sided relabelling p-values (response, signed move) and the two-sided exact binomial "
         "(direction); q is the Benjamini-Hochberg adjusted value within each test family (section 8). Intervals "
         "are 95% date-bootstrap intervals. 'Detectable' columns are the Phase 0 power estimates. E2 has fewer "
         "than 30 events. For E3 and E4 the index of interest is `influencer`.", ""]

    for ix in INDICES:
        c = cells[cells["index"] == ix].set_index("group").reindex(list(GROUPS))
        L += [f"### {ix_label(ix)}", "",
              "| events | n | response rate (95% CI) | random dates | p | q | detectable | signed move, pts (95% CI) "
              "| random dates | p | q | detectable, pts |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for g, r in c.iterrows():
            p = pw.loc[(ix, g)] if (ix, g) in pw.index else None
            L.append(f"| {g} | {int(r['n'])} | {pct(r['response_rate'])} ({ci(r['response_ci_lo'], r['response_ci_hi'])}) "
                     f"| {pct(r['null_response_mean'])} | {pv(r['p_response'])} | {pv(r['p_response_bh'])} | "
                     f"{p['detectable response rate'] if p is not None else 'n/a'} | "
                     f"{num(r['avg_signed_move'], sign=True)} ({ci(r['signed_ci_lo'], r['signed_ci_hi'], lambda x: num(x, sign=True))}) "
                     f"| {num(r['null_signed_mean'], sign=True)} | {pv(r['p_signed'])} | {pv(r['p_signed_bh'])} | "
                     f"{p['detectable signed move (pts)'] if p is not None else 'n/a'} |")
        L += ["", "| events | moves | direction accuracy (95% CI) | p (binomial) | q | wrong-way | miss | placebo "
              "response | placebo accuracy | placebo signed move | placebo dates in an E4 window |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
        for g, r in c.iterrows():
            L.append(f"| {g} | {int(r['moves'])} | {pct(r['direction_accuracy'])} "
                     f"({ci(r['accuracy_ci_lo'], r['accuracy_ci_hi'])}) | {pv(r['p_direction_binom'])} | "
                     f"{pv(r['p_direction_binom_bh'])} | {pct(r['wrong_way_rate'])} | {pct(r['miss_rate'])} | "
                     f"{pct(r['placebo_response_rate'])} | {pct(r['placebo_direction_accuracy'])} | "
                     f"{num(r['placebo_avg_signed_move'], sign=True)} | {int(r['placebo_in_e4_window'])} of "
                     f"{int(r['placebo_n'])} |")
        L.append("")

    ut = un.assign(index=un["index"].map(ix_label))
    ut["rate"] = ut["rate"].map(pct)
    L += ["## 7. Unexplained moves", "",
          "A large move is a two-session change of more than two noise units on an event-period session. It is "
          "explained if any event of any type (E4 included) has its reaction session within one session, or "
          "if the stock's market-adjusted return within one session exceeds twice its typical daily move "
          "(DECISIONS.md M6).", "",
          ut.rename(columns={"large": "large moves", "unexplained": "unexplained", "rate": "unexplained rate",
                             "event_only": "explained by event only", "price_only": "by price only",
                             "both": "by both"}).drop(columns=["contaminated"]).to_markdown(index=False), ""]

    fam = cells[~cells["primary"] & ~cells["contaminated"]]
    L += ["## 8. Multiple comparisons", "",
          f"Cells examined: {len(cells)} ({len(INDICES)} indices x {len(GROUPS)} event groups). One is primary. "
          f"The {int(cells['contaminated'].sum())} market-channel cells are reported with raw p-values only. "
          f"Benjamini-Hochberg is applied separately to each test over the remaining {len(fam)} secondary cells.",
          "", "| test | cells | raw p < 0.05 | BH q < 0.05 |", "|---|---|---|---|"]
    for col, name in (("p_response", "response (test 1)"), ("p_signed", "signed move (test 3)"),
                      ("p_direction_binom", "direction (exact binomial)")):
        x = fam[col].dropna()
        L.append(f"| {name} | {len(x)} | {int((x < 0.05).sum())} | {int((fam[col + '_bh'] < 0.05).sum())} |")
    sig = []
    for _, r in fam.iterrows():
        for col, name, how in (("p_response", "response", lambda r: "score moved more often than on random dates"),
                               ("p_signed", "signed move", lambda r: "in the events' direction"),
                               ("p_direction_binom", "direction",
                                lambda r: "in the events' direction" if r["direction_accuracy"] > 0.5
                                else "**against the events' direction**")):
            if r[col + "_bh"] < 0.05:
                sig.append(f"| {r['index']} | {r['group']} | {name} | {pv(r[col])} | {pv(r[col + '_bh'])} | {how(r)} |")
    L += ["", "Every secondary result with BH q < 0.05. The response and signed-move tests are one-sided, so a "
          "significant result there is an excess of moves, or a move in the events' direction. The direction "
          "test is two-sided and can be significant in either direction.", "",
          "| index | events | test | p | q | direction |", "|---|---|---|---|---|---|"] + \
        (sig if sig else ["| none | | | | | |"]) + [""]

    trunc = re.search(r"Insider coverage truncated: (\d+)", counts_md)
    reach = cluster_cell(counts_md, "E4 insider", "clusters reaching past R+1")
    e4n = cells[(cells["index"] == PLUMBING_INDEX) & (cells["group"] == "E4")].iloc[0]
    L += ["## 9. Limitations observed", "",
          f"- **Power.** This is a pilot. The primary cell has {int(prim['n'])} events; see the detectable "
          "effects in section 5. E2 has fewer than 30 events. The power estimate treats events as independent, "
          "but they cluster on news days.",
          "- **Insider timing.** E4's reaction session is the transaction date (DECISIONS.md A2). Form 4 "
          "filings are public up to two business days later, so the market often cannot trade on an E4 event "
          "within its window.",
          f"- **Insider clusters.** Runs of overlapping insider trades collapse into one event measured over the "
          f"first member's window (A4); {reach} clusters have members after that "
          "window.",
          f"- **Insider coverage.** yfinance returns at most 150 insider rows per stock; "
          f"for {trunc.group(1) if trunc else 'n/a'} stock(s) that history does not reach the event period's "
          "start.",
          f"- **Placebo dates near insider trades.** Noise and placebo sessions exclude E1 to E3 windows only "
          f"(A3); for `{PLUMBING_INDEX}` on E4, {int(e4n['placebo_in_e4_window'])} of {int(e4n['placebo_n'])} "
          "placebo dates fall inside an E4 window.",
          "- **Earnings times.** Yahoo labels releases to the hour, mostly 06:00 to 08:00 or 16:00 ET. These "
          "look like before-open and after-close labels, not exact release times (DECISIONS.md R1).",
          "- **Rating dates.** The source's timestamp has no stated timezone; its date is used as given (R2).",
          "- **EPS cross-check.** It carries no weight: nearly every company beat estimates in the period (A5).",
          "- **Response test.** The p-value formula counts ties as 'at least as high', which makes test 1 "
          "slightly conservative (3.6% false positives at the 5% level on synthetic nulls; DECISIONS.md M9).",
          "- **Market channel.** The market channel is computed from price and is contaminated in this period; "
          "it is reported, flagged and given no weight. The published `score` includes it (35% weight in the "
          "composite) and is reported as published.",
          "- **Data revisions.** yfinance serves current data; a later download of the same events can differ. "
          "The data hash identifies the inputs used.", ""]

    (PKG / "RESULTS.md").write_text("\n".join(L))
    print(f"wrote {PKG / 'RESULTS.md'} ({len(L)} lines); primary {verdict}")


if __name__ == "__main__":
    main()
