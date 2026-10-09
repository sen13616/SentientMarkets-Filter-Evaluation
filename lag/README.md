# Experiment 5B: how quickly does the score respond?

The SentientMarkets API publishes a 0 to 100 sentiment score per US large-cap stock, updated every
15 minutes during the trading session and every 30 minutes outside it. Experiment 5A
(`responsiveness/`) asks whether the score moves after real events. This experiment asks **how
long it takes**: after something happens to a stock, how long before the published score has made
its move, and how much of the price move has already happened by then?

The answer sets the shortest time scale on which a strategy could sensibly use the score. The
experiment measures; it has no pass or fail, and it says nothing about whether the score is useful.
The full specification is [BRIEF.md](BRIEF.md); every interpretive choice, dated, is in
[DECISIONS.md](DECISIONS.md).

**Status: Phase 0 (setup, price collection and event counts).** No response has been computed.

## What is measured

- **Events with a time.** L-E1: an earnings release with a time of day (time zero is the release
  time). L-E2: the first regular-session bar in which a stock's market-adjusted move exceeds 3 times
  its normal move for that time of day (time zero is the bar's start). At most one event per stock
  in any 48 hours.
- **Response curve.** For each index, the signed change in the score from the last tick before time
  zero to each later tick, averaged over events, divided by its value at 48 hours. T½ and T₉₀ are
  the first times the curve reaches 50% and 90%.
- **Price already moved.** The same curve for the stock's market-adjusted return, read at T½.
- **Alignment with price.** Over every in-session hour of every stock, the correlation between the
  index change and the market-adjusted return, with the index shifted by −12 to +12 trading hours.
- **Indices.** The published `score` (EMA-smoothed), the unsmoothed `score_raw`, `score_exo` (the
  score without its price-based market channel) and each of the four channels. The market channel
  is computed from price and is reported flagged, with no weight.

## Data and the lock

Three date ranges (BRIEF.md section 3), enforced in `lock.py` and tested in `tests/test_lock.py`:

| range | prices | sentiment and events |
|---|---|---|
| up to 22 June 2026 (the pilot) | yes | yes |
| 23 June to 1 October 2026 | never | never |
| 2 October to 23 November 2026 (the definitive run) | yes | only after 5A's definitive results are committed, on or after 24 November 2026 |

Sentiment ticks come from the first experiment's cache (pilot) and from 5A's definitive pull
(definitive run). Intraday bars come from yfinance through this package's own collector and are
kept in a local store that is never committed.

## Commands

Run from the repository root with the packages in `requirements.txt`. Set `SM_DATA_DIR` if the
local data lives somewhere other than `data/`.

```
python -m pytest lag/tests                    # synthetic-data tests (no real data)
python -m lag.scripts.tick_check              # results/tick_check.md: what the tick cache carries, tick spacing
python -m lag.scripts.pull_hourly             # hourly bars for the pilot -> $SM_DATA_DIR/lag/bars_1h.parquet
python -m lag.scripts.collect_15m             # 15-minute bars for 2 Oct to 23 Nov 2026 -> bars_15m.parquet (rerun weekly)
python -m lag.scripts.collect_15m --report-only   # rewrite results/coverage_15m.md without downloading
python -m lag.scripts.event_counts            # results/event_counts.md (no response computed)
```

**The 15-minute collector must be run at least every 8 weeks while the period is live** (weekly is
the plan): yfinance serves 15-minute bars for about 60 days only, and bars not collected in time are
lost. Each run adds only bars not yet stored and never changes a stored bar.

## Layout

| path | contents |
|---|---|
| `BRIEF.md`, `DECISIONS.md` | the specification; every choice and amendment, dated |
| `config.py` | every fixed constant for both runs |
| `lock.py` | the three-range data lock and the 5A gate |
| `data.py` | loaders for ticks, bars, daily prices, earnings tables, universe and calendar |
| `bars.py` | yfinance intraday download, in-memory lock filter, store merge, coverage report |
| `events.py` | L-E1 and L-E2 construction, clustering, period filter |
| `scripts/` | the commands above |
| `tests/` | synthetic-data tests |
| `results/` | committed aggregate outputs (counts, coverage, checks); never raw data |
| `ledger.csv` | append-only log of every run (from Phase 2) |

Measurement, inference and the rendered results arrive in Phases 1 and 2.
