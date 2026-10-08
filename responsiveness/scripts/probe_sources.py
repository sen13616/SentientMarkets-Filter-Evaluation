"""Phase 0 source probe: what each yfinance event source returns, on five tickers.

    python -m responsiveness.scripts.probe_sources

Writes results/source_probe.md. Every table is lock-filtered in memory first, so
coverage is reported only up to 22 June 2026 (with the count of later rows dropped).
Nothing downloaded is written to disk.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from responsiveness import sources
from responsiveness.config import RESULTS
from responsiveness.data import lock_filter_events

PROBE = ["AAPL", "JPM", "NKE", "KO", "CRWD"]
RAW_FIELDS = {"earnings": "Ticker.get_earnings_dates(limit=12): index 'Earnings Date' (tz-aware, "
                          "America/New_York); EPS Estimate, Reported EPS, Surprise(%)",
              "ratings": "Ticker.upgrades_downgrades: index GradeDate (naive timestamp); Firm, ToGrade, "
                         "FromGrade, Action, priceTargetAction, currentPriceTarget, priorPriceTarget",
              "insider": "Ticker.insider_transactions: Shares, Value, URL, Text, Insider, Position, "
                         "Transaction, Start Date, Ownership"}


def main() -> None:
    import yfinance as yf
    lines = ["# Source probe (Phase 0)", "",
             f"yfinance {yf.__version__}; probed {datetime.now(timezone.utc):%Y-%m-%d} on {', '.join(PROBE)}. "
             "Coverage is shown after the data lock: rows stamped after 2026-06-22 were dropped "
             "in memory and only counted.", "", "## Fields", ""]
    lines += [f"- **{k}**: {v}" for k, v in RAW_FIELDS.items()]
    rows = []
    detail = {"earnings": [], "ratings": [], "insider": []}
    for t in PROBE:
        tables = sources.fetch_ticker(t)
        for src, df in tables.items():
            col = sources.TIME_COL[src]
            kept, dropped = lock_filter_events(df, col)
            win = kept[(pd.to_datetime(kept[col]).dt.date >= pd.Timestamp("2026-05-12").date())] \
                if len(kept) else kept
            rows.append({"ticker": t, "source": src, "rows returned": len(df), "dropped (after lock)": dropped,
                         "earliest kept": str(pd.to_datetime(kept[col]).min().date()) if len(kept) else "",
                         "latest kept": str(pd.to_datetime(kept[col]).max().date()) if len(kept) else "",
                         "rows 12 May-22 Jun": len(win)})
            if src == "earnings" and len(kept):
                detail["earnings"] += [f"{t}: " + ", ".join(sorted({f"{ts:%H:%M}" for ts in kept[col]}))]
            if src == "ratings" and len(kept):
                detail["ratings"] += [f"{t}: " + ", ".join(f"{k}={v}" for k, v in
                                                           kept["action"].value_counts().items())]
            if src == "insider" and len(kept):
                kinds = kept["text"].map(lambda s: (s.split(" at ")[0] or "(blank)")[:40]).value_counts()
                detail["insider"] += [f"{t}: " + ", ".join(f"{k}={v}" for k, v in kinds.items())]
    lines += ["", "## Coverage", "", pd.DataFrame(rows).to_markdown(index=False), "",
              "## Earnings: times of day present (America/New_York)", ""]
    lines += [f"- {s}" for s in detail["earnings"]]
    lines += ["", "## Ratings: action labels (kept rows)", ""] + [f"- {s}" for s in detail["ratings"]]
    lines += ["", "## Insider: transaction kinds from the Text field (kept rows; the Transaction column "
              "is empty)", ""] + [f"- {s}" for s in detail["insider"]]
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "source_probe.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
