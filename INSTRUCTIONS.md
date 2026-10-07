# Build the context-filter evaluation harness for SentientMarkets

You are starting in an empty folder. Your job is to build a small, tested, reproducible research harness and use it to run the research-window half of a pre-specified study. Read this whole brief before writing anything.

## 1. What this is

SentientMarkets is a live API that publishes a per-stock sentiment score (0 to 100, 50 neutral) for large-cap US equities, built from four sub-indices: market (weight 0.35), narrative (0.30), influencer (0.25), macro (0.10). An earlier study showed the score does not predict next-day returns. The current research question is different: **does the sentiment state work as a context filter**, meaning that standard trading rules perform better when their entries are restricted, sized or vetoed by it?

Three hypotheses, each against the null that the filtered and unfiltered variants have the same expected risk-adjusted return:

- **H1 (gate, primary):** taking only entries where sentiment agrees with the trade direction improves net risk-adjusted return.
- **H2 (size):** scaling position size by sentiment strength improves on equal sizing.
- **H3 (veto):** skipping entries when the system reports low confidence or high divergence improves on the unfiltered rule, regardless of direction.

The study has a research window and a holdout. **This task covers the research window only.** The output is a `RESULTS.md` that will be pasted into a research paper, so every number in it must be traceable to an artifact on disk.

## 2. Ground rules

These are not preferences. If one of them blocks you, stop and ask.

1. **The holdout is locked.** No sentiment row and no price bar dated after 22 June 2026 may be stored or analysed, with the single exception in Phase 0. Enforce this in the data loader and cover it with a test. Do not build an unlock flag.
2. **No look-ahead.** A decision for day t uses the sentiment tick at or before 21:30 UTC on day t and closes through day t. Execution is at the open of day t+1. Enforce in code, cover with a test.
3. **Nothing is tuned.** Every threshold, lookback and parameter below is fixed. Do not adjust any of them after seeing a result, and do not add cells beyond the closed list in section 9. If you think the spec is wrong, say so and wait.
4. **Every run is logged.** Each cell you evaluate, including reruns and failures, appends one row to `ledger.csv` (timestamp, cell id, config hash, code commit or "uncommitted", data snapshot hash, seed, headline numbers). The ledger is append-only.
5. **Baselines before filters.** Unfiltered results are produced, written and reviewed by me before any filter code is run on real data.
6. **Numbers come from files.** `RESULTS.md` is rendered by a script from result files. Never type a statistic by hand, and do not describe a result in prose that the tables do not show.
7. **Record interpretive choices.** Where this brief leaves something open, choose the most conventional option, write it in `DECISIONS.md` with a one-line reason, and carry on. Do not choose silently.
8. **I handle git.** Run `git init`, keep a `.gitignore` (data, `.env`, caches), and at each checkpoint stop, list what should be committed with a suggested message, and wait for me.
9. **Be gentle with the API.** It is a small production service. One request at a time, at most 30 per minute, with backoff on 429 and 5xx, and cache every response so nothing is fetched twice.
10. **Secrets.** The key is in `.env` as `SENTIENT_API_KEY`. Never print it, log it or write it to any file.

## 3. Phase 0: API contract probe (checkpoint)

Base URL: `https://sentimentapi-p.up.railway.app`. Auth: `Authorization: Bearer <key>` (Pro tier).

Documented endpoints, which may be out of date:

- `GET /health`
- `GET /v1/tickers`
- `GET /v1/sentiment/{ticker}?detail=full`
- `GET /v1/sentiment/{ticker}/history?days=N&interval=daily|raw` (days max 365; `raw` returns every scoring tick)

Before building anything, probe the live API with three tickers (AAPL, JPM, XOM) and `days=2`, and write `API_FINDINGS.md` answering:

- The exact fields returned by each endpoint, with types and one redacted example.
- Does history `raw` include: smoothed composite, raw composite, the four sub-indices, `score_exo`, confidence, confidence flags, divergence, missing layers, and any replay or backfill marker?
- Is the history `score` integer-rounded? Smoothed or raw?
- Does `/v1/tickers` distinguish seed-universe names from names added later, or expose `delisted_at`?
- How does history behave for a delisted ticker?
- Response size and latency for one ticker at `days=2`, extrapolated to the full pull.
- Anything that differs from the documentation above.

This probe is the only permitted contact with post-22-June data. Use it to inspect the schema and, if `score_exo` is served, to compare it against the reconstruction in section 5. Store nothing from it except `API_FINDINGS.md`.

**Stop here and show me `API_FINDINGS.md`.** If history `raw` is unavailable or cannot reach back to 24 April 2026, stop: the daily interval is not a substitute, because it returns the last tick of the UTC day, which is after the 21:30 cutoff.

## 4. Phase 1: data build

**Sentiment.** Pull history `raw` for every ticker in `/v1/tickers` with enough `days` to reach 24 April 2026. On ingest, discard every row after 22 June 2026 before writing to disk. For each ticker and each NYSE session day t in the window, keep the last tick with timestamp on day t UTC and at or before 21:30 UTC. If there is none, the state for that ticker-day is missing. Write one daily state panel (parquet) and a snapshot hash.

**Prices.** The API does not serve prices. Use `yfinance` daily bars from 1 January 2025 to 22 June 2026, split- and dividend-adjusted open, high, low and close (note ticker symbol differences such as BRK.B). Use a proper NYSE calendar for sessions. Record the download date and a hash.

**Used universe.** A ticker is in the used universe if it has a non-missing sentiment state on at least 90% of window sessions, including at least one in the first five and one in the last five sessions, and a price bar on every window session. Names with no sentiment rows before June 2026 are later additions and are excluded by this rule. Fix the list once, write it to disk, and report the count. The expected count is about 475. If yours is outside 460 to 490, stop and tell me.

**Coverage report.** Before any backtest, produce `results/coverage.md`: sessions in the window, used-universe count, missing-state share per day, and for each input index the share of ticker-days in each label band, plus the share with confidence below 60 and with high divergence. This uses no return data.

## 5. Sentiment state definitions

- **Label bands** (applied to the integer-rounded index): 0-20 Strongly Bearish, 21-40 Bearish, 41-60 Neutral, 61-80 Bullish, 81-100 Strongly Bullish.
- **score_exo** is the composite without the market sub-index: narrative, influencer and macro with weights 0.30, 0.25, 0.10 renormalised to sum to one (about 0.46 / 0.38 / 0.15). If a sub-index is missing, redistribute its weight proportionally over those present. If all three are missing, the state is missing. If the API serves `score_exo` in history for the research window, use the served value and report how closely the reconstruction matches it. If not, use the reconstruction and say so prominently.
- **Divergence** is high when the spread between the highest and lowest present sub-index (all four) exceeds 40. Use the served flag if history provides it, otherwise compute it.
- **Confidence** is the served 0-100 value.
- **Input indices:** `score_exo` (primary), composite, narrative, influencer, macro. Do not use the market sub-index as an input: its values in this window are known to be contaminated. The composite contains it and must be labelled as affected wherever it is reported.

## 6. Timing, costs and accounting

- Decision on day t, entry at the open of t+1, exit at the open of the session after the holding period ends.
- Decisions may be made on any session from 24 April to 22 June 2026. P&L is counted only on sessions inside the window. Positions still open at the last session are marked and closed at that close, with the exit cost charged.
- Daily portfolio return is marked to market: open-to-close on the entry day, close-to-close while held, close-to-open on the exit day.
- Cost is 10 basis points per side on traded notional, identical for every variant. No borrow cost.
- Capital not deployed earns zero. Risk-free rate is zero.
- A missing sentiment state means the filtered variant skips that entry. Count these separately. If more than 5% of candidate entries are skipped for missing state in any cell, also report that cell against an unfiltered comparator restricted to ticker-days with a valid state.

## 7. Base strategies (unfitted, conventional parameters)

| ID | Rule |
|---|---|
| CSM | Cross-sectional momentum. Every fifth session, rank the used universe by 20-session return. Long the top quintile, short the bottom quintile, equal-weighted within each leg, half of capital per leg, held five sessions. |
| STR | Short-term reversal. Every session, long the bottom quintile by 5-session return, equal-weighted, held five sessions. Five overlapping cohorts, one fifth of capital each. |
| TSMOM | Time-series momentum. Per name, long when the 60-session return is positive, flat otherwise, evaluated daily. An entry is a flat-to-long transition. Each name has a fixed 1/N capital slot. |
| BRK | Breakout. Per name, enter long on a close at a new 252-session closing high, hold 20 sessions. Ignore new signals while in a position. Fixed 1/N slot. |
| RSI-MR | RSI mean reversion. Per name, enter long when Wilder RSI(14) crosses below 30. Exit when it crosses above 50 or after 20 sessions. Fixed 1/N slot. |

CSM and STR are the primary strategies. The other three are secondary.

## 8. Filters

All thresholds are fixed in advance.

**Gate (H1).** Take the entry only if the index agrees with the trade.
- Long entries under CSM, TSMOM, BRK, RSI-MR: index at or above 61.
- Short entries under CSM: index at or below 40.
- STR: index at or above 41 (the gate removes losers whose decline the sentiment supports).
- The gate never closes an existing position. A gated-out entry's capital stays in cash at its unfiltered weight.

**Size (H2).** Take every entry, with weight multiplier `clip((index - 50) / 30, 0, 1)` for longs and `clip((50 - index) / 30, 0, 1)` for shorts. For STR use `clip((index - 40) / 30, 0, 1)`. Then rescale so the portfolio's gross exposure on each day equals the unfiltered strategy's.

**Veto (H3).** Take every entry unless confidence is below 60 or divergence is high. Direction-blind and independent of the input index.

## 9. Cells (closed list)

1. Five unfiltered baselines.
2. Gate: 5 strategies x 5 input indices = 25.
3. Size: 5 strategies x 5 input indices = 25.
4. Veto: 5 strategies = 5.
5. Threshold sensitivity, CSM and STR on `score_exo` only: gate bands moved to 56/45 and 66/35 (for STR, 36 and 46); veto confidence threshold 50 and 70. Eight cells.
6. Exposure robustness, CSM and STR gate on `score_exo`: gated-out capital redistributed within the leg instead of held in cash. Two cells.
7. Clean-narrative sub-window, CSM and STR gate on the narrative index, decisions from 12 May 2026 only, each against its own baseline over the same sub-window. Two cells.

The **headline research-window cell** is CSM / gate / `score_exo`. It is a development result, not a confirmation. The confirmation happens later on the holdout and is not part of this task.

## 10. Metrics and inference

For every cell report: annualised Sharpe of daily portfolio returns (mean over standard deviation times sqrt(252)), profit factor, maximum drawdown, hit rate over closed trades, number of trades, turnover, average gross and net exposure, and beta to the equal-weighted used universe.

For every filtered cell also report:

- **Sharpe difference** against the unfiltered variant of the same strategy over the same sessions. This is the primary statistic.
- **Permutation p-value.** Shuffle each ticker's daily state rows across dates (whole rows, so index, confidence and divergence stay together), rerun the filtered strategy, recompute the Sharpe difference. 1,000 permutations, fixed seed, one-sided, p = (1 + count of permuted differences at least as large as observed) / 1,001.
- **Bootstrap interval.** Stationary block bootstrap of the paired daily return series, mean block length 10 sessions, 2,000 resamples, 95% percentile interval on the Sharpe difference.
- **Minimum detectable difference:** the 95th percentile of the permutation null. The window is about 40 sessions, so power is low, and this number says how low.
- **Trade retention:** filtered trade count over unfiltered. A cell below 30% is reported but flagged as failing the non-triviality floor.
- **Attribution** (gate cells): for the entries the gate removed, the distribution of the returns they earned in the unfiltered strategy (count, mean, median, hit rate), next to the same for entries kept.

Across all filtered cells report the total number examined, and Benjamini-Hochberg adjusted p-values alongside the raw ones.

## 11. Phases 2 to 5

**Phase 2: engine and tests (checkpoint).** Build the backtest engine, strategies, filters and inference, vectorised enough that 1,000 permutations per cell is practical. Tests must include: the holdout lock; the look-ahead rule (a state stamped 21:31 UTC on day t must not affect a day-t decision); cost accounting on a hand-computed example; each strategy on a small synthetic panel with a known answer; a null check (random states give a Sharpe difference centred on zero and roughly uniform p-values); and a planted-effect check (states constructed to mark the losing trades produce a significant positive difference). Run all of these on synthetic data only. Stop and show me the test output.

**Phase 3: baselines (checkpoint).** Run the five unfiltered strategies on the research window. Write `results/baselines.md` and the ledger rows. Also write the gate, size and veto pass rates per strategy and input (counts only, no returns). Stop for my review and commit. Do not change any threshold in response to a pass rate.

**Phase 4: filtered cells.** Run the closed list in section 9. Ledger every cell.

**Phase 5: `RESULTS.md`.** Rendered by script, in this order:

1. Run metadata: dates run, data snapshot hashes, price download date, seeds, package versions, final test summary.
2. API findings: a short summary of `API_FINDINGS.md`, including whether `score_exo` was served or reconstructed and the match quality.
3. Data: window, session count, used-universe count and how it was derived, coverage and state-distribution tables.
4. Deviations and decisions: the full content of `DECISIONS.md`.
5. Unfiltered baselines table.
6. Filter pass rates.
7. Headline cell in full, including attribution.
8. All cells: one table per hypothesis with every statistic in section 10, then the sensitivity, exposure-robustness and sub-window cells.
9. Multiple-comparisons summary: cells examined, raw and adjusted p-values, how many pass at 0.05 before and after adjustment.
10. Ledger summary: total rows, including reruns, with reasons for any rerun.
11. Limitations you observed while doing the work, stated plainly.

Report null and negative results with the same prominence as positive ones. Do not write a conclusion about whether the hypotheses hold. That judgement is made elsewhere.

## 12. Out of scope

No holdout computation. No automated or agent-driven search over additional strategies. No parameter optimisation. No direct database access. No changes to the API. If something here seems to require one of these, stop and ask.

Start with Phase 0.