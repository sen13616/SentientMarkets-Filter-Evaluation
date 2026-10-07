"""Phase 5: render RESULTS.md from result files (ground rule 6). No statistic is typed by hand.

Sources: results/cells/*.json, ledger.csv, results/snapshot.json, results/coverage.md,
results/pass_rates.md, DECISIONS.md, API_FINDINGS.md, the state panel (descriptive state
statistics only), the stored prices (equal-weighted universe return for the limitations), and a
fresh run of the test suite.
"""

import json
import subprocess
import sys
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from filter_eval.config import ROOT, RESULTS  # noqa: E402
from filter_eval.evaluate import closed_cell_list, ew_market, market_affected  # noqa: E402
from filter_eval.inference import benjamini_hochberg, sharpe  # noqa: E402
from filter_eval.load import PANEL, load_inputs  # noqa: E402

CELLS = RESULTS / "cells"
MA = "†"   # market-layer-affected marker
PACKAGES = ["numpy", "pandas", "scipy", "pyarrow", "exchange_calendars", "yfinance", "requests",
            "python-dotenv", "pytest", "tabulate"]


# ------------------------------------------------------------------ helpers
def f(x, nd=3):
    if x is None:
        return "n/a"
    if isinstance(x, (bool, np.bool_)):
        return "yes" if x else "no"
    if isinstance(x, (int, np.integer)):
        return f"{x:,}"
    if isinstance(x, float):
        if np.isnan(x):
            return "n/a"
        if np.isinf(x):
            return "inf" if x > 0 else "-inf"
        return f"{x:.{nd}f}"
    return str(x)


def pct(x, nd=1):
    return "n/a" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{100 * x:.{nd}f}%"


def shift_headings(md: str, by: int = 1, drop_title: bool = True) -> str:
    out = []
    for i, line in enumerate(md.splitlines()):
        if line.startswith("#"):
            if drop_title and i == 0 and line.startswith("# "):
                continue
            line = "#" * by + line
        out.append(line)
    return "\n".join(out).strip()


def table(rows: list[dict]) -> str:
    return pd.DataFrame(rows).to_markdown(index=False, disable_numparse=True) if rows else "_(none)_"


def label(cell_id: str, cells: dict) -> str:
    return cell_id + (f" {MA}" if market_affected(cells[cell_id]) else "")


# ------------------------------------------------------------------ load results
def load_cells():
    spec = {c.id: c for c in closed_cell_list()}
    res = {}
    for p in CELLS.glob("*.json"):
        r = json.loads(p.read_text())
        res[r["cell"]] = r
    missing = [c for c in spec if c not in res]
    if missing:
        sys.exit(f"missing cell results: {missing}")
    filtered = [c for c in spec.values() if c.filter != "none"]
    p = np.array([res[c.id]["p_perm"] for c in filtered])
    for c, q in zip(filtered, benjamini_hochberg(p)):
        res[c.id]["p_bh"] = float(q)
    return spec, res, filtered


def run_tests() -> str:
    out = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests/"], cwd=ROOT,
                         capture_output=True, text=True)
    (RESULTS / "final_tests.txt").write_text(out.stdout + out.stderr)
    lines = [ln for ln in out.stdout.strip().splitlines() if ln.strip()]
    return lines[-1] if lines else "test run produced no output"


# ------------------------------------------------------------------ section builders
def inference_rows(ids, res, spec):
    rows = []
    for cid in ids:
        r = res[cid]
        row = {"cell": label(cid, spec), "Sharpe filt.": f(r["f_sharpe"], 2), "Sharpe unfilt.": f(r["u_sharpe"], 2),
               "ΔSharpe": f(r["sharpe_diff"], 2), "p (perm)": f(r["p_perm"], 3), "p (BH)": f(r["p_bh"], 3),
               "95% CI (bootstrap)": f"[{f(r['boot_lo'], 2)}, {f(r['boot_hi'], 2)}]",
               "null mean": f(r["null_mean"], 2), "MDD (null p95)": f(r["mdd_95"], 2),
               "retention": pct(r["retention"]), "below 30% floor": f(r["fails_floor"]),
               "missing state": pct(r["missing_share"])}
        if "sharpe_diff_vs_restricted" in r:
            row["ΔSharpe vs restricted"] = f(r["sharpe_diff_vs_restricted"], 2)
        rows.append(row)
    return rows


def performance_rows(ids, res, spec, with_unfiltered=False):
    rows = []
    for cid in ids:
        r = res[cid]
        for pre, who in (("f_", "filtered"), ("u_", "unfiltered")) if with_unfiltered else (("f_", "filtered"),):
            rows.append({"cell": label(cid, spec), "variant": who, "Sharpe": f(r[pre + "sharpe"], 2),
                         "profit factor": f(r[pre + "profit_factor"], 2), "max DD": pct(r[pre + "max_drawdown"], 2),
                         "hit rate": pct(r[pre + "hit_rate"]), "trades": f(r[pre + "n_trades"]),
                         "long / short": f"{f(r[pre + 'n_long'])} / {f(r[pre + 'n_short'])}",
                         "turnover/day": f(r[pre + "turnover"], 3), "avg gross": f(r[pre + "avg_gross"], 3),
                         "avg net": f(r[pre + "avg_net"], 3), "beta": f(r[pre + "beta"], 2),
                         "sessions": f(r[pre + "n_sessions"])})
    return rows


def size_rows(ids, res, spec):
    return [{"cell": label(cid, spec), "avg eff. N filtered": f(res[cid]["f_avg_eff_n"], 1),
             "avg eff. N unfiltered": f(res[cid]["u_avg_eff_n"], 1),
             "entry days with all multipliers zero": f"{f(res[cid]['entry_days_all_zero'])} of {f(res[cid]['entry_days'])}",
             "sessions with sized book empty": f(res[cid]["sessions_sized_book_empty"])} for cid in ids]


def attribution_rows(ids, res, spec):
    rows = []
    for cid in ids:
        r = res[cid]
        for grp, name in (("kept", "kept"), ("removed", "removed (all)"), ("removed_missing", "removed: missing state")):
            rows.append({"cell": label(cid, spec), "entries": name, "n": f(r[f"attr_{grp}_n"]),
                         "mean return": pct(r[f"attr_{grp}_mean"], 2), "median return": pct(r[f"attr_{grp}_median"], 2),
                         "hit rate": pct(r[f"attr_{grp}_hit"])})
    return rows


def hypothesis_block(title, ids, res, spec, size=False, gate=False, unfilt=False):
    out = [f"### {title}", "", "**Inference**", "", table(inference_rows(ids, res, spec)), "",
           "**Performance**", "", table(performance_rows(ids, res, spec, unfilt)), ""]
    if size:
        out += ["**Size diagnostics (D22)**", "", table(size_rows(ids, res, spec)), ""]
    if gate:
        out += ["**Attribution: unfiltered standalone net returns of entries kept and removed**", "",
                table(attribution_rows(ids, res, spec)), ""]
    return out


# ------------------------------------------------------------------ main
def main():
    spec, res, filtered = load_cells()
    snap = json.loads((RESULTS / "snapshot.json").read_text())
    led = pd.read_csv(ROOT / "ledger.csv")
    tests = run_tests()
    rendered = datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True,
                              text=True).stdout.strip()
    except FileNotFoundError:
        head = "unknown"
    any_cell = res[filtered[0].id]
    L = ["# Results: sentiment as a context filter (research window)", "",
         "Rendered by `scripts/render_results.py` from the result files. Development results on the "
         "research window only; no holdout data was stored or analysed. This document reports results "
         "and does not judge whether the hypotheses hold.", "",
         f"{MA} marks cells whose input includes the contaminated market layer: every `composite` "
         "cell and every veto using four-layer divergence (D2, D21).", ""]

    # 1 metadata
    phases = led.assign(phase=np.where(led["note"].str.contains("Phase 4"), "Phase 4 (filtered cells)",
                                       "Phase 3 (baselines)"))
    runs = phases.groupby("phase")["timestamp_utc"].agg(["min", "max", "size"]).reset_index()
    runs.columns = ["phase", "first row (UTC)", "last row (UTC)", "ledger rows"]
    commits = ", ".join(sorted(led["code_commit"].astype(str).unique()))
    L += ["## 1. Run metadata", "",
          table([{"item": k, "value": v} for k, v in [
              ("Rendered (UTC)", rendered), ("Repository HEAD at render", head),
              ("Code commits in ledger", commits),
              ("Sentiment pull completed (UTC)", snap["sentiment_pull_completed_utc"]),
              ("Sentiment ticks sha256", snap["sentiment_ticks_sha256"]),
              ("State panel sha256", snap["state_panel_sha256"]),
              ("Prices sha256", snap["prices_sha256"]),
              ("Price download (UTC)", snap["price_download_utc"]), ("Price source", snap["price_source"]),
              ("Rows discarded at ingest (after 22 June)", f(snap["rows_discarded_after_lock"])),
              ("Seed (all cells)", str(any_cell["seed"])),
              ("Permutations / bootstrap resamples / mean block", f"{any_cell['n_perm']} / {any_cell['n_boot']} / {any_cell['block']}"),
              ("Final test run", tests)]]), "",
          table(runs.to_dict("records")), "",
          "Package versions: " + ", ".join(f"{p} {metadata.version(p)}" for p in PACKAGES) +
          f"; Python {sys.version.split()[0]}.", ""]

    # 2 API findings
    api = (ROOT / "API_FINDINGS.md").read_text()
    summary = api.split("## Summary", 1)[1].split("\n## ", 1)[0].strip()
    L += ["## 2. API findings (summary of API_FINDINGS.md)", "", summary, ""]

    # 3 data
    m, states = load_inputs()
    cov = (RESULTS / "coverage.md").read_text()
    between = []
    for ix, a in states.index.items():
        x = a[:, 1:]
        between.append({"index": ix + (f" {MA}" if ix == "composite" else ""),
                        "between-ticker share of variance": f(float(np.nanvar(np.nanmean(x, axis=1)) / np.nanvar(x)), 2)})
    L += ["## 3. Data", "", shift_headings(cov), "",
          "### Persistence of states within tickers (decision sessions; states only)", "",
          "Share of each index's variance explained by ticker means. The permutation null shuffles each "
          "ticker's states across dates, so it preserves this between-ticker component.", "",
          table(between), ""]

    # 4 decisions
    L += ["## 4. Deviations and decisions (DECISIONS.md, in full)", "",
          shift_headings((ROOT / "DECISIONS.md").read_text()), ""]

    # 5 baselines
    base_ids = [c.id for c in spec.values() if c.filter == "none"]
    L += ["## 5. Unfiltered baselines", "",
          f"P&L sessions {res[base_ids[0]]['n_sessions']}; costs 10 bp per side.", "",
          table([{"strategy": res[b]["strategy"], "Sharpe": f(res[b]["sharpe"], 2),
                  "profit factor": f(res[b]["profit_factor"], 2), "max DD": pct(res[b]["max_drawdown"], 2),
                  "hit rate": pct(res[b]["hit_rate"]), "trades": f(res[b]["n_trades"]),
                  "turnover/day": f(res[b]["turnover"], 3), "avg gross": f(res[b]["avg_gross"], 3),
                  "avg net": f(res[b]["avg_net"], 3), "beta": f(res[b]["beta"], 2),
                  "total return": pct(res[b]["total_return"], 2)} for b in base_ids]), ""]

    # 6 pass rates
    L += ["## 6. Filter pass rates", "", shift_headings((RESULTS / "pass_rates.md").read_text()), ""]

    # 7 headline
    h = "gate/CSM/score_exo"
    r = res[h]
    pair = [("Sharpe", "sharpe", 3), ("mean daily return", "mean_daily", 5), ("sd daily return", "sd_daily", 5),
            ("total return", "total_return", 4), ("profit factor", "profit_factor", 3),
            ("max drawdown", "max_drawdown", 4), ("hit rate", "hit_rate", 3), ("trades", "n_trades", 0),
            ("long entries", "n_long", 0), ("short entries", "n_short", 0), ("turnover/day", "turnover", 3),
            ("avg gross", "avg_gross", 3), ("avg net", "avg_net", 3), ("beta (EW universe)", "beta", 3),
            ("P&L sessions", "n_sessions", 0)]
    L += ["## 7. Headline research-window cell: CSM / gate / score_exo", "",
          "A development result on the research window, not a confirmation.", "",
          table([{"metric": a, "filtered": f(r["f_" + k], nd) if nd else f(r["f_" + k]),
                  "unfiltered": f(r["u_" + k], nd) if nd else f(r["u_" + k])} for a, k, nd in pair]), "",
          table([{"statistic": a, "value": v} for a, v in [
              ("Sharpe difference (filtered − unfiltered)", f(r["sharpe_diff"], 3)),
              ("Permutation p-value (one-sided, 1,000 permutations)", f(r["p_perm"], 4)),
              ("Benjamini-Hochberg adjusted p (72 filtered cells)", f(r["p_bh"], 4)),
              ("Permutation null mean", f(r["null_mean"], 3)),
              ("Minimum detectable difference (null 95th percentile)", f(r["mdd_95"], 3)),
              ("95% bootstrap interval", f"[{f(r['boot_lo'], 3)}, {f(r['boot_hi'], 3)}]"),
              ("Trade retention", pct(r["retention"])), ("Below 30% floor", f(r["fails_floor"])),
              ("Candidate entries / missing state", f"{f(r['n_candidates'])} / {f(r['n_missing_state'])}")]]), "",
          "**Attribution**", "", table(attribution_rows([h], res, spec)), ""]

    # 8 all cells
    def ids(pred):
        return [c.id for c in filtered if pred(c)]
    L += ["## 8. All filtered cells", ""]
    L += hypothesis_block("H1: gate", ids(lambda c: c.id.startswith("gate/")), res, spec, gate=True)
    L += hypothesis_block("H2: size", ids(lambda c: c.id.startswith("size/")), res, spec, size=True)
    L += hypothesis_block("H3: veto (four-layer divergence)", ids(lambda c: c.id.startswith("veto/")), res, spec)
    L += hypothesis_block("H3 amendment: veto-exo (D21)", ids(lambda c: c.id.startswith("veto-exo/")), res, spec)
    L += hypothesis_block("Threshold sensitivity (CSM and STR, score_exo)", ids(lambda c: c.id.startswith("sens/")),
                          res, spec, gate=False)
    L += hypothesis_block("Exposure robustness (gated-out capital redistributed within the leg)",
                          ids(lambda c: c.id.startswith("expo/")), res, spec, gate=True)
    L += hypothesis_block("Clean-narrative sub-window (decisions from 12 May 2026; own baseline)",
                          ids(lambda c: c.id.startswith("sub/")), res, spec, gate=True, unfilt=True)

    # 9 multiple comparisons
    p = np.array([res[c.id]["p_perm"] for c in filtered])
    q = np.array([res[c.id]["p_bh"] for c in filtered])
    floor = np.array([res[c.id]["fails_floor"] for c in filtered])
    L += ["## 9. Multiple-comparisons summary", "",
          table([{"item": a, "value": v} for a, v in [
              ("Filtered cells examined", f(len(filtered))),
              ("Raw p < 0.05", f(int((p < 0.05).sum()))),
              ("Raw p < 0.05 and retention >= 30%", f(int(((p < 0.05) & ~floor).sum()))),
              ("BH-adjusted p < 0.05", f(int((q < 0.05).sum()))),
              ("Cells below the 30% retention floor", f(int(floor.sum()))),
              ("Smallest raw p", f(float(p.min()), 4)), ("Smallest BH-adjusted p", f(float(q.min()), 4))]]), "",
          "All filtered cells, sorted by raw p-value:", "",
          table([{"cell": label(c.id, spec), "ΔSharpe": f(res[c.id]["sharpe_diff"], 2),
                  "p (perm)": f(res[c.id]["p_perm"], 3), "p (BH)": f(res[c.id]["p_bh"], 3),
                  "retention": pct(res[c.id]["retention"])}
                 for c in sorted(filtered, key=lambda c: res[c.id]["p_perm"])]), ""]

    # 10 ledger
    reruns = led[led["note"].astype(str).str.startswith("rerun")]
    L += ["## 10. Ledger summary", "",
          table([{"item": a, "value": v} for a, v in [
              ("Total ledger rows", f(len(led))), ("Rows with status ok", f(int((led["status"] == "ok").sum()))),
              ("Failed rows", f(int((led["status"] != "ok").sum()))), ("Rerun rows", f(len(reruns)))]]), "",
          table([{"note": n, "rows": f(int(k))} for n, k in led["note"].value_counts().items()]), ""]

    # 11 limitations (numbers computed from files)
    mk = ew_market(m)[m.d0 + 1 - m.ws:]
    csm_gate = [res[c] for c in ids(lambda c: c.id.startswith("gate/CSM/"))]
    net_lo, net_hi = min(x["f_avg_net"] for x in csm_gate), max(x["f_avg_net"] for x in csm_gate)
    mdds = np.array([res[c.id]["mdd_95"] for c in filtered])
    panel = pd.read_parquet(PANEL, columns=["ticker", "day", "ts", "slot"])
    panel = panel[panel["ticker"].isin(set(m.tickers)) & panel["ts"].notna()]
    early = panel[panel["slot"] != "21:30"]
    n_early_days = int(early["day"].nunique())
    earliest = early["ts"].dt.strftime("%H:%M").min() if len(early) else "n/a"
    L += ["## 11. Limitations observed", "",
          f"1. **Short window, one regime.** Every cell is evaluated on at most {res[base_ids[0]]['n_sessions']} P&L "
          f"sessions. Over those sessions the equal-weighted used universe returned {pct(float(mk.sum()), 2)} with an "
          f"annualised Sharpe of {f(float(sharpe(mk)), 2)}. All five unfiltered baselines have positive Sharpe in this "
          "window, and long-only rules carry market beta (section 5).",
          f"2. **Low power.** The minimum detectable Sharpe difference (95th percentile of each permutation null) "
          f"ranges from {f(float(mdds.min()), 2)} to {f(float(mdds.max()), 2)} across the filtered cells "
          f"(median {f(float(np.median(mdds)), 2)}).",
          "3. **What the permutation null holds fixed.** Shuffling each ticker's states across dates preserves each "
          "ticker's state distribution, including the between-ticker component in section 3. The null therefore tests "
          "the timing of states within tickers, not the selection of tickers. Null means are reported per cell and "
          "are often far from zero. The shuffle also moves the all-missing 24 April row onto decision days (D19), so "
          "permuted variants skip some entries for missing state that the observed variant takes.",
          f"4. **Gating a long/short strategy changes its net exposure.** CSM is close to market-neutral unfiltered; "
          f"the CSM gate cells have average net exposure between {f(net_lo, 3)} and {f(net_hi, 3)}, because bullish "
          "states are much more common than bearish ones (section 6). Their Sharpe differences mix the effect of "
          "sentiment timing with a change in market exposure; the long/short split and average net exposure are "
          "reported for every cell.",
          "5. **Market-layer contamination.** The composite and the four-layer divergence contain the market "
          f"sub-index, which is contaminated in this window; those cells are marked {MA}. `score_exo` is "
          "reconstructed, not served, and is unsmoothed, while the composite is a 4-hour EMA (D2, D5).",
          f"6. **Irregular scoring ticks early in the window.** On {n_early_days} sessions the state did not come "
          "from the 21:30 slot because that tick was stamped at or after 21:45; the earliest selected tick on those "
          f"sessions was stamped {earliest} UTC (section 3).",
          "7. **No replay marker.** The API exposes no flag for rows rebuilt offline, so the research-window rows "
          "cannot be verified as live from the API alone (section 2).",
          "8. **Universe and prices.** The used universe excludes seed names delisted inside the window and names "
          "without yfinance bars (section 3), a survivorship restriction. Prices come from a single source "
          "(yfinance, adjusted) and were not cross-checked against a second source.",
          "9. **Costs.** A flat 10 bp per side on netted traded notional, no borrow cost, no market impact. Trade-"
          "level statistics (hit rate, profit factor, attribution) use standalone per-trade returns, which are not "
          "netted (D15).",
          "10. **Size filter mechanics.** Few states reach the full-size level (section 6), so under daily gross "
          "matching (D14) the size filter acts mostly as a relative re-weighting; effective numbers of positions are "
          "reported for every size cell.",
          ""]

    (ROOT / "RESULTS.md").write_text("\n".join(L) + "\n")
    print(f"wrote RESULTS.md ({len(L)} lines); tests: {tests}")


if __name__ == "__main__":
    main()
