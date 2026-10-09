"""Phase 0, step 4: collect 15-minute bars for the definitive period (2 October to 23 November 2026).

yfinance serves 15-minute bars for about 60 days only, so this is run repeatedly while the period
is live (weekly is enough). Each run downloads what yfinance still serves, keeps only bars from
the period, adds the ones not yet stored to `$SM_DATA_DIR/lag/bars_15m.parquet`, records the run
in `bars_15m_manifest.json` next to it, and rewrites `lag/results/coverage_15m.md`. Bars already
stored are never changed. Nothing else is read, and no sentiment is touched.

    python -m lag.scripts.collect_15m
"""

from __future__ import annotations

import json
import sys

from lag import bars
from lag.config import BARS_15M, BARS_15M_MANIFEST, RESULTS, RUNS
from lag.data import sessions, universe


def report(uni: list[str], manifest: dict | None) -> dict:
    cov = bars.coverage(bars.load_store(BARS_15M), sessions("definitive"), "15m", uni)
    RESULTS.mkdir(exist_ok=True)
    text = bars.coverage_markdown(cov, "15-minute bar coverage, 2 October to 23 November 2026", BARS_15M.name, manifest)
    (RESULTS / "coverage_15m.md").write_text(text)
    print(f"  store: {cov['bars']:,} bars over {cov['sessions_done']} closed sessions; "
          f"{cov['tickers_complete']}/{cov['tickers']} tickers complete; coverage report written")
    return cov


def main(report_only: bool = False) -> None:
    uni = universe("definitive")
    if report_only:
        m = json.loads(BARS_15M_MANIFEST.read_text()) if BARS_15M_MANIFEST.exists() else None
        report(uni, m)
        return
    period = RUNS["definitive"]["sessions"]
    start, end = bars.collection_window(*period)
    print(f"collect_15m: {len(uni)} tickers, requesting {start} to {end} (exclusive)")
    new = bars.download(uni, "15m", start, end)
    print(f"  {len(new):,} bars downloaded; filtering to the period and merging")
    stats = bars.merge_store(new, BARS_15M)
    print("  " + ", ".join(f"{k}={v}" for k, v in stats.items()))
    m = bars.write_manifest(BARS_15M_MANIFEST, stats, {"requested_start": str(start), "requested_end": str(end),
                                                       "tickers_requested": len(uni),
                                                       "tickers_returned": int(new["ticker"].nunique())})
    report(uni, m)


if __name__ == "__main__":
    main(report_only="--report-only" in sys.argv[1:])
