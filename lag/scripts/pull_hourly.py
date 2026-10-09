"""Phase 0, step 5: hourly bars for the pilot, 12 May to 22 June 2026.

Downloads regular-session hourly bars for the pilot universe, drops anything outside the allowed
ranges in memory, and merges into `$SM_DATA_DIR/lag/bars_1h.parquet` (never committed). Writes
`lag/results/coverage_1h.md`.

    python -m lag.scripts.pull_hourly
"""

from __future__ import annotations

from datetime import timedelta

from lag import bars
from lag.config import BARS_1H, BARS_1H_MANIFEST, RESULTS, RUNS
from lag.data import sessions, universe


def main() -> None:
    uni = universe("pilot")
    start, end = RUNS["pilot"]["sessions"]
    print(f"pull_hourly: {len(uni)} tickers, {start} to {end}")
    new = bars.download(uni, "1h", start, end + timedelta(days=1))
    print(f"  {len(new):,} bars downloaded; filtering and merging")
    stats = bars.merge_store(new, BARS_1H)
    print("  " + ", ".join(f"{k}={v}" for k, v in stats.items()))
    m = bars.write_manifest(BARS_1H_MANIFEST, stats, {"requested_start": str(start), "requested_end": str(end),
                                                      "tickers_requested": len(uni),
                                                      "tickers_returned": int(new["ticker"].nunique())})
    cov = bars.coverage(bars.load_store(BARS_1H), sessions("pilot"), "1h", uni, through=end)
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "coverage_1h.md").write_text(
        bars.coverage_markdown(cov, "Hourly bar coverage, 12 May to 22 June 2026 (pilot)", BARS_1H.name, m))
    print(f"  store: {cov['bars']:,} bars; {cov['tickers_complete']}/{cov['tickers']} tickers complete")


if __name__ == "__main__":
    main()
