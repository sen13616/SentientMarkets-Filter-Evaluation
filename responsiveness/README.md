# Experiment 5A: does the score follow real-world sentiment? (pilot)

The SentientMarkets API publishes a 0 to 100 sentiment score per US large-cap stock, built from
four channels: market, narrative, influencer and macro. Anything built on the score assumes that
when sentiment about a stock changes in the real world, the score changes with it, in the right
direction. This experiment checks that assumption end to end, in two directions:

- **Forward:** after a public event with a known direction, did the score move, and the right way?
  (Does the score miss things?)
- **Backward:** when the score made a large move, was there an event or an unusual price move
  behind it? (Does the score invent things?)

There is no trading and no strategy here. Results are in [RESULTS.md](RESULTS.md).

**This run is a pilot.** Its event period, 13 May to 18 June 2026, falls between earnings seasons.
The primary test therefore has only 73 events and can reliably detect only fairly large effects;
[RESULTS.md](RESULTS.md) states the power next to each primary result. The definitive run is
planned on the October 2026 earnings season with the same code and rules.

The test, its thresholds and its pass rule were written down in [BRIEF.md](BRIEF.md) before any
score response was computed. The pass rule was amended once, on power grounds, also before any
response was computed (DECISIONS.md A6). Every later choice and amendment is dated in
[DECISIONS.md](DECISIONS.md), each recorded before the results it could affect.

## Pilot result

In this pilot, `score_exo` (the score without its price-based market channel) moved in the
direction of the market's reaction to earnings releases and large price moves.

| measure (73 events, 13 May to 18 June 2026) | result | random dates | p | detectable with 80% power |
|---|---|---|---|---|
| signed average move | +4.87 points on the 0 to 100 scale (95% interval +2.33 to +7.38) | +0.07 | 0.001 (minimum possible) | 2.95 points |
| response rate (score moved beyond its noise) | 43.8% | 32.2% | 0.025 | 47.0% |
| unexplained share of the score's large moves | 32.4% (36.0% if insider trades are not counted as explanations) | | | |

The primary cell passed its pre-specified rule: both p-values are below 0.05, and fewer than half
of the large moves are unexplained. Full results, including every secondary cell, are in
[RESULTS.md](RESULTS.md).

## What this does not show

- **It does not show that the score carries information beyond price.** The direction of
  earnings and large-move events is taken from the stock's own price reaction. News coverage of a
  large move often reports the move itself, so the narrative channel's response may partly
  restate price. The pilot shows that the score responds to real events, in the direction the
  market took.
- **It does not test whether the score predicts returns.** No trading or forecasting is involved.
- **The response is small.** +4.87 points is 0.24 of one 20-point label band, and the score moved
  beyond its noise after 43.8% of events.
- **Not every channel or event type responds.** After 510 insider sales, `score_exo` moved beyond
  its noise no more often than on random dates (30.4% against 31.9%, p = 0.784), and its signed
  move was not significant (p = 0.117). The macro channel moved against the direction of analyst
  rating changes (direction accuracy 25.0%, q = 0.040); why was not tested.
- **It is a pilot.** It has few events, and the detectable effects above are large. The other
  limitations observed are listed in section 9 of [RESULTS.md](RESULTS.md).

## Method in brief

The full specification is [BRIEF.md](BRIEF.md). Every interpretive choice and every amendment,
each dated and set before the results it could affect, is in [DECISIONS.md](DECISIONS.md).

**Events.** All events come from public data through `yfinance`, for the 473 stocks of the first
experiment's universe:

| type | event | direction |
|---|---|---|
| E1 | earnings release with a time of day | sign of the stock's return minus the universe average, on the first session that could react |
| E2 | close-to-close move larger than 3 x ATR(14), not on an earnings day | sign of the move |
| E3 | analyst upgrade or downgrade | up or down |
| E4 | insider purchase or sale | purchase up, sale down |

Overlapping events on the same stock are resolved by fixed rules. Different types: the
higher-ranked type is kept. The same type: the events collapse into one with a net direction.

**Measurement.**
- **Readings:** the score is read just before the market could react (21:45 UTC on the previous
  session, or the release time if that is earlier), and again at the end of the following session.
- **Noise unit:** the standard deviation of the stock's own two-session change on quiet days.
- **Moves:** a change larger than one noise unit is a *move*; larger than two is a *large move*.
- **Indices:** the published `score`, `score_exo` (the score rebuilt without the market channel,
  which is computed from price) and each of the four channels.

**Tests.**
- **Response and signed move:** within each stock, random sessions are relabelled as events
  1,000 times with a fixed seed. This asks how often random dates show as many moves (response
  rate), or as large a move in the events' direction (signed average move), as the real events.
- **Direction accuracy:** reported with a bootstrap over event dates and an exact binomial test.
- **Primary cell:** `score_exo` on E1 and E2 pooled. It passes if the response test and the
  signed-move test both give p < 0.05, and fewer than half of the score's large moves are
  unexplained.
- **Secondary cells:** 42 cells in all (6 indices x 7 event groups). The secondary cells are
  reported with Benjamini-Hochberg adjusted p-values.

**Data lock.** Nothing dated after 22 June 2026 is stored or analysed. Event downloads are
filtered in memory before anything is written, the loaders refuse later rows, and both are tested.

## Reproducing the run

Requirements: Python 3.14 and the packages in `requirements.txt` at the repository root.

1. **Sentiment ticks and price bars.** These come from the first experiment's data build. The
   sentiment pull needs a SentientMarkets API key with history access, in `.env` as
   `SENTIENT_API_KEY`; the price pull uses yfinance. Both write to `data/` and stop at 22 June 2026.

   ```
   python scripts/pull_sentiment.py
   python scripts/pull_prices.py
   ```

2. **This experiment.** Run from the repository root. Set `SM_DATA_DIR` if the data lives
   somewhere other than `data/`.

   ```
   python -m responsiveness.scripts.probe_sources          # results/source_probe.md (five tickers)
   python -m responsiveness.scripts.fetch_events           # yfinance events, lock-filtered, to data/responsiveness/raw
   python -m responsiveness.scripts.event_counts           # results/event_counts.md, event_counts.csv
   python -m responsiveness.scripts.power                  # results/power.md, power.csv
   python -m pytest responsiveness/tests                   # synthetic-data tests
   python -m responsiveness.scripts.synthetic_summary      # results/phase1_synthetic.md
   python -m responsiveness.scripts.run_cells              # results/cells.csv, unexplained.csv, run_meta.json, nulls/
   python -m responsiveness.scripts.unexplained_sensitivity  # results/unexplained_sensitivity.csv
   python -m responsiveness.scripts.render_results         # RESULTS.md
   ```

Every run appends a row to [ledger.csv](ledger.csv) with its commit, config hash, data hash and
seed. With the same inputs, the scripts give the same numbers: every random draw comes from a
fixed seed (DECISIONS.md M8). Only run timestamps differ.

## What is not in this repository, and why

- **Sentiment ticks** are SentientMarkets data, available through its API. Only aggregates
  derived from them are committed.
- **Price bars and event downloads** are third-party data from Yahoo Finance via `yfinance`. They
  can be downloaded again with the commands above.
- **Per-event tables** (`data/responsiveness/candidates.parquet` and `measured_events.parquet`)
  list individual company events and the score around each. They are kept local; counts and
  aggregate results are committed instead.

A fresh download may not match the one used here. yfinance serves current data, which Yahoo can
revise, and its insider table returns only the most recent 150 rows per stock. The API's history
must also still reach back to May 2026. The data hash in [RESULTS.md](RESULTS.md) and in the
ledger identifies the exact inputs; a run on different inputs reports a different hash.

## Layout

| path | contents |
|---|---|
| `BRIEF.md`, `DECISIONS.md` | the specification and every choice and amendment, dated |
| `config.py` | every fixed constant (thresholds, seeds, periods) |
| `data.py`, `sources.py` | loaders behind the data lock; the yfinance event sources |
| `events.py`, `market.py` | event construction and overlap rules; returns and ATR |
| `measure.py`, `cells.py` | score states, before and after readings, noise units, cells |
| `inference.py` | scorecard, relabelling tests, bootstrap, placebo dates, unexplained moves, BH |
| `scripts/` | the commands above |
| `tests/` | synthetic-data tests (no real data) |
| `results/` | aggregate results; `results/nulls/` holds every relabelled value and bootstrap draw |
| `ledger.csv` | append-only log of every run |
