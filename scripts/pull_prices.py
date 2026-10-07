"""Phase 1: download adjusted daily bars for the candidate universe."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from filter_eval import prices  # noqa: E402
from filter_eval.universe import candidates  # noqa: E402

if __name__ == "__main__":
    tickers = candidates()
    df = prices.download(tickers)
    m = prices.save(df, tickers)
    print({k: v for k, v in m.items() if k != "no_data"})
    print("no data from yfinance:", m["no_data"])
