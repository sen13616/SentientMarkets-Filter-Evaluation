"""Download the three yfinance event sources for the universe into the local cache.

    SM_DATA_DIR=/path/to/data python -m responsiveness.scripts.fetch_events

Rows stamped after 22 June 2026 are dropped in memory before anything is written.
Resumable: tickers already fetched are skipped.
"""

from __future__ import annotations

from responsiveness import data, sources


def main() -> None:
    m = sources.fetch_all(data.universe())
    failed = [t for t, e in m["tickers"].items() if e.get("status") != "ok"]
    print(f"done: {len(m['tickers'])} tickers, {len(failed)} failed {failed}")


if __name__ == "__main__":
    main()
