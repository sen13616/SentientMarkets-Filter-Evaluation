"""Phase 1: pull raw sentiment history for the candidate universe (D1, D7). Resumable."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from filter_eval.api import Client  # noqa: E402
from filter_eval.ingest import pull  # noqa: E402
from filter_eval.universe import candidates  # noqa: E402

if __name__ == "__main__":
    tickers = candidates()
    only = sys.argv[1:]  # optional: pull named tickers only (e.g. a one-ticker test)
    if only:
        tickers = [t for t in tickers if t in set(only)]
    client = Client()
    m = pull(tickers, client)
    ok = sum(1 for t in tickers if m["tickers"].get(t, {}).get("status") == "ok")
    print(f"done: {ok}/{len(tickers)} ok, requests={client.n_requests}, still_failed={m['still_failed']}")
