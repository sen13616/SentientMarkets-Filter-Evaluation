"""Phase 0, step 3: what the pilot tick cache carries, and the actual tick spacing in and out of
the trading session from 12 May to 22 June 2026. Writes results/tick_check.md. No response is computed.

    python -m lag.scripts.tick_check
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from datetime import date

from lag.config import RESULTS, RUNS
from lag.data import load_ticks, sessions, session_bounds, universe


def session_mask(ts: pd.Series, sess: list) -> np.ndarray:
    """True where the stamp falls inside a regular NYSE session."""
    bounds = pd.DataFrame([(o, c) for o, c in (session_bounds(d) for d in sess)], columns=["open", "close"])
    t = ts.to_numpy()
    o = bounds["open"].to_numpy()
    c = bounds["close"].to_numpy()
    i = np.searchsorted(o, t, side="right") - 1
    ok = i >= 0
    out = np.zeros(len(t), dtype=bool)
    out[ok] = t[ok] < c[i[ok]]
    return out


def resolution_note(by_day: pd.DataFrame) -> str:
    """Name the first day on which most in-session gaps were 15 minutes."""
    share = by_day.get(("<lambda_0>", True))
    switch = next((d for d, s in share.items() if pd.notna(s) and s >= 0.5), None) if share is not None else None
    if switch is None:
        return "Resolution for the pilot: 30 minutes inside and outside the session, with a 60-minute price bar."
    return (f"Resolution for the pilot: inside the session, 30 minutes up to the session before {switch} and 15 minutes "
            f"from {switch}; outside the session, 30 minutes throughout; price bars of 60 minutes. Every timing in the "
            "pilot is reported next to these limits.")


def main() -> None:
    uni = universe("pilot")
    sess = sessions("pilot")
    start, end = RUNS["pilot"]["sessions"]
    ticks = load_ticks("pilot", uni)
    lo = pd.Timestamp(start, tz="UTC")
    hi = pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)
    d = ticks[(ticks["ts"] >= lo) & (ticks["ts"] < hi)].sort_values(["ticker", "ts"]).copy()

    # What the cache carries.
    raw_files = sorted(p.stem for p in __import__("lag.config", fromlist=["PILOT_TICK_DIR"]).PILOT_TICK_DIR.glob("*.parquet"))
    cols = {"score_raw served": 1.0 - d["score_raw_rebuilt"].mean()}
    for c in ("score", "narrative", "influencer", "macro", "market", "score_exo"):
        cols[f"{c} present"] = d[c].notna().mean()

    # Spacing.
    d["gap_min"] = d.groupby("ticker")["ts"].diff().dt.total_seconds() / 60
    d["in_session"] = session_mask(d["ts"], sess)
    g = d.dropna(subset=["gap_min"])

    def q(x):
        return {k: round(float(np.percentile(x, p)), 1) for k, p in (("p5", 5), ("p25", 25), ("median", 50), ("p75", 75), ("p95", 95))}

    def modes(x, n=5):
        vc = x.round(0).value_counts(normalize=True).head(n)
        return ", ".join(f"{int(k)} min ({v:.1%})" for k, v in vc.items())

    ins, outs = g[g["in_session"]], g[~g["in_session"]]
    ny = d["ts"].dt.tz_convert("America/New_York")
    d["day"] = ny.dt.date
    d["week"] = (ny - pd.to_timedelta(ny.dt.weekday, unit="D")).dt.date
    g = d.dropna(subset=["gap_min"])
    by_week = g.groupby(["week", "in_session"])["gap_min"].median().unstack("in_session")
    by_week.columns = ["outside session" if not c else "inside session" for c in by_week.columns]
    # Day by day for the first weeks, to date the change of schedule inside the session.
    first = g[g["day"] <= date(2026, 5, 29)]
    by_day = first.groupby(["day", "in_session"])["gap_min"].agg(["median", lambda x: (x.round() == 15).mean()]).unstack("in_session")
    ticks_per_day = d.groupby(["ticker", d["ts"].dt.date]).size()

    lines = ["# Pilot tick cache check (Phase 0, step 3)", "",
             f"Tick cache: {len(raw_files)} tickers on disk; {len(uni)} in the pilot universe. "
             f"Rows from {start} to {end}: {len(d):,} ticks, {d['ticker'].nunique()} tickers, "
             f"first {d['ts'].min():%Y-%m-%d %H:%M} UTC, last {d['ts'].max():%Y-%m-%d %H:%M} UTC.", "",
             "## What the cache carries", "", "| field | share of ticks |", "|---|---|"]
    lines += [f"| {k} | {v:.1%} |" for k, v in cols.items()]
    lines += ["", f"`score` differs from `score_raw` on {(d['score'] != d['score_raw']).mean():.1%} of ticks "
              "(the published score is the EMA-smoothed composite; in this period its half-life was 4 hours).", "",
              "## Tick spacing (gap to the previous tick of the same stock)", "",
              "| where | ticks | p5 | p25 | median | p75 | p95 | most common gaps |", "|---|---|---|---|---|---|---|---|"]
    for name, x in (("inside the session", ins), ("outside the session", outs)):
        s = q(x["gap_min"])
        lines.append(f"| {name} | {len(x):,} | {s['p5']} | {s['p25']} | {s['median']} | {s['p75']} | {s['p95']} | {modes(x['gap_min'])} |")
    lines += ["", "Median gap by week (minutes):", "", "| week of | inside session | outside session |", "|---|---|---|"]
    for w, r in by_week.iterrows():
        lines.append(f"| {w} | {r.get('inside session', float('nan')):.0f} | {r.get('outside session', float('nan')):.0f} |")
    lines += ["", "Day by day in May (New York dates), to date the change of schedule inside the session:", "",
              "| day | median gap inside (min) | share of 15-minute gaps inside | median gap outside (min) |", "|---|---|---|---|"]
    for day, r in by_day.iterrows():
        med_in = r.get(("median", True), float("nan"))
        sh_in = r.get(("<lambda_0>", True), float("nan"))
        med_out = r.get(("median", False), float("nan"))
        lines.append(f"| {day} | {med_in:.0f} | {sh_in:.0%} | {med_out:.0f} |")
    lines += ["", f"Ticks per ticker-day: median {ticks_per_day.median():.0f}, "
              f"5th percentile {ticks_per_day.quantile(0.05):.0f}, 95th {ticks_per_day.quantile(0.95):.0f}.", "",
              resolution_note(by_day), ""]
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "tick_check.md").write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
