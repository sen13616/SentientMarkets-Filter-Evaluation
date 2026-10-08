# SentientMarkets score evaluation

Independent tests of the SentientMarkets sentiment score: a 0 to 100 score per US large-cap stock,
built from four channels (market, narrative, influencer, macro).

Each experiment is pre-specified. Its rules, thresholds and pass criteria are written down before
the results they govern are computed, and every later amendment is dated before the results it
could affect. Every run is logged in an append-only ledger with its code commit and data hash.
Every reported number is rendered from result files by a script.

Both experiments use sentiment data from 24 April to 22 June 2026, with earlier price history as
lookback only. Nothing dated after 22 June 2026 is stored or analysed, and the loaders enforce
this.

## Experiment 1: sentiment as a context filter (repository root)

Asks whether standard trading rules do better when their entries are gated, sized or vetoed by
the sentiment state. Five strategies are tested, each unfiltered and with each filter.

**Result on the research window:** no filter cell was distinguishable from chance.
- Of 72 filtered cells, none had a raw permutation p-value below 0.05; the smallest was 0.0699.
- Every Benjamini-Hochberg adjusted p-value was 1.0000.

A holdout period is kept locked for later.

- Specification: [INSTRUCTIONS.md](INSTRUCTIONS.md)
- Decisions: [DECISIONS.md](DECISIONS.md)
- API probe: [API_FINDINGS.md](API_FINDINGS.md)
- Results: [RESULTS.md](RESULTS.md)
- Code: `filter_eval/`, `scripts/`, `tests/`

## Experiment 5A: does the score follow real-world sentiment? (`responsiveness/`, pilot)

Checks, without any trading, two things: whether the score moves after public events with a known
direction, and whether its large moves have an event or an unusual price move behind them. Events
are earnings releases, large price moves, analyst rating changes and insider trades, all from
public data.

**Pilot result (13 May to 18 June 2026):** the score without its price-based market channel
(`score_exo`) moved in the direction of the market's reaction to earnings releases and large
price moves.
- **Signed average move:** +4.87 points on the 0 to 100 scale across 73 events (p = 0.001, the
  minimum possible).
- **Response rate:** the score moved beyond its noise after 43.8% of events, against 32.2% on
  random dates (p = 0.025).

**What this does not show:**
- **Price:** event directions come from the price reaction, and coverage of a large move often
  reports the move itself. The result therefore does not show that the score carries information
  beyond price.
- **Returns:** it does not test whether the score predicts returns.
- **Power:** this is a pilot with 73 events, able to detect only fairly large effects. The
  definitive run is planned on the October 2026 earnings season with the same code and rules.

- Overview, limitations and how to reproduce: [responsiveness/README.md](responsiveness/README.md)
- Specification: [responsiveness/BRIEF.md](responsiveness/BRIEF.md)
- Decisions: [responsiveness/DECISIONS.md](responsiveness/DECISIONS.md)
- Results: [responsiveness/RESULTS.md](responsiveness/RESULTS.md)

## Data

Sentiment data comes from the SentientMarkets API and needs an API key. Prices and events come
from Yahoo Finance via `yfinance`. Neither raw dataset is committed: the scripts download them into
`data/` (ignored by git), and the committed results record hashes of the inputs they used. Each
experiment's README or specification gives the commands. Requirements are in
[requirements.txt](requirements.txt).
