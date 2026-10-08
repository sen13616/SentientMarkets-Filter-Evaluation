# Experiment 5A: does the score follow real-world sentiment?

Work in progress; the full README is written in Phase 3. The question, rules and method are
in [BRIEF.md](BRIEF.md), and the interpretive choices are in [DECISIONS.md](DECISIONS.md).

## Reproducing Phase 0

The sentiment tick cache and daily price bars come from the first experiment's data build
(`scripts/pull_sentiment.py`, `scripts/pull_prices.py` at the repository root). They are not
in the repository. Point `SM_DATA_DIR` at the directory that holds them (default: `data/`).

```
python -m responsiveness.scripts.probe_sources    # results/source_probe.md (five tickers)
python -m responsiveness.scripts.fetch_events     # yfinance events -> $SM_DATA_DIR/responsiveness/raw
python -m responsiveness.scripts.event_counts     # results/event_counts.md, event_counts.csv
python -m responsiveness.scripts.power            # results/power.md, power.csv
python -m pytest responsiveness/tests             # synthetic-data tests
```

yfinance serves current data, so a later download can differ from the one used here. The
data hash in each results file and in `ledger.csv` identifies the inputs.
