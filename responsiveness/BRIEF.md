# Experiment 5A: does the score follow real-world sentiment?

This is a new experiment in this repository. It is separate from the filter backtest already here (INSTRUCTIONS.md, RESULTS.md), and it involves no trading and no strategy. Read this whole brief before writing anything.

This repository will be made public. Write everything in it (code, READMEs, commit messages, results) for a reader who has never seen the project.

## 1. The question

The SentientMarkets API publishes a 0 to 100 sentiment score per stock, built from four channels (market, narrative, influencer, macro). Everything downstream assumes that when sentiment about a stock changes in the real world, the score changes with it, in the right direction. That has never been checked end to end. This experiment checks it, in two directions:

- **Forward:** after a real event with a known direction, did the score move, and the right way? (Does the score miss things?)
- **Backward:** when the score made a large move, was there a real event behind it? (Does the score invent things?)

The output is `responsiveness/RESULTS.md`, with a clear statement of statistical significance for each test.

## 2. Ground rules

If one of these blocks you, stop and ask.

1. **Keep the experiments apart.** All new code goes in a new package `responsiveness/`, with its own `README.md`, `DECISIONS.md`, `ledger.csv`, `results/` and tests. Do not move, rename or edit the existing experiment's files, except to reuse its loaders by import. Save this brief as `responsiveness/BRIEF.md` and commit it before any result exists.
2. **Data lock.** This run uses 12 May to 22 June 2026 only. Nothing dated after 22 June 2026 may be stored or analysed: no sentiment rows, price bars or events. Enforce it in the loaders and test it. Event sources return later dates; filter them out in memory before writing anything.
3. **Nothing is tuned.** Every threshold below is fixed. Do not change one after seeing a result. If you think the spec is wrong, say so and wait.
4. **Counts before outcomes.** Event counts and the power estimate are produced and reviewed by me before any score response is computed.
5. **Every run is logged** in `responsiveness/ledger.csv` (timestamp, test id, config hash, code commit, data hash, seed, headline numbers). Append-only. Commit code before running so rows carry a real hash.
6. **Numbers come from files.** `RESULTS.md` is rendered by a script. Report nulls and failures as prominently as passes. Do not write a conclusion about whether the score is useful.
7. **Record interpretive choices** in `responsiveness/DECISIONS.md` with a one-line reason.
8. **Public-repository hygiene.** Never print, log or commit the API key. Do not commit raw downloads from third parties or raw sentiment ticks; commit code, aggregated results and counts. Keep per-event tables out of git unless I say otherwise. Make every result reproducible from a documented command.
9. **I handle git.** At each checkpoint, stop, list what to commit with a suggested message, and wait.

## 3. Data

- **Sentiment:** the tick cache already on disk for the research window (all ticks, 24 April to 22 June 2026, 478 names). No API calls should be needed. If the cache is missing, stop and tell me.
- **Indices tested:** `score` (published composite), `score_exo` (reconstructed from narrative, influencer and macro with weights 0.30 / 0.25 / 0.10, renormalised over those present), and each of the four channels. The market channel is computed from price and is known to be contaminated in this period; report it, flagged, and give it no weight.
- **Prices:** the daily bars already cached (adjusted, through 22 June).
- **Events:** public sources, so that outsiders can reproduce the run. Use `yfinance` for earnings dates and surprise, analyst upgrades and downgrades, and insider transactions.
- **Universe:** the used universe of the first experiment (473 names).
- **Event period:** events whose reaction session falls from 12 May to 18 June 2026, so that the "after" reading is inside the window. (Before 12 May the narrative channel used a different text model.)

## 4. Definitions

**Sessions and states.** NYSE sessions. The daily state of a stock is the last tick stamped before 21:45 UTC on that session, as in the first experiment.

**Reaction session R.** The first session in which the market could trade on the event.

**Events and their direction.**

| Type | Event | Direction |
|---|---|---|
| E1 Earnings | An earnings release with a known time of day. R is the same session if released before the close, otherwise the next. Drop releases with no time, and count them. | Sign of the stock's market-adjusted close-to-close return over R (stock return minus the equal-weighted universe return). Cross-check: sign of the EPS surprise. |
| E2 Large move | A session where the absolute close-to-close move exceeds 3 times ATR(14) measured through the previous session, and which is not an E1 reaction session. R is that session. | Sign of the move. |
| E3 Rating change | An analyst action labelled upgrade or downgrade. R is its date, or the next session if not a session. | Up or down. |
| E4 Insider | An insider purchase or sale. R is the transaction date, or the next session. | Purchase up, sale down. |

If two events of different types share a stock and overlapping windows, keep the higher-ranked (E1, then E2, E3, E4) and count the overlaps.

**Before and after.** Before = the last tick stamped before the earlier of (a) the event time and (b) 21:45 UTC on session R−1. For E2, E3 and E4 the event time is (b). After = the daily state of session R+1. Change = after minus before.

**Noise unit.** Per stock and per index: the standard deviation of the two-session change, state(d+1) minus state(d−1), over sessions d in the event period that are not within two sessions of any event for that stock.

**Move.** A change larger than one noise unit in absolute value. A **large move** is larger than two.

**Placebo dates.** For each event, 20 sessions of the same stock drawn at random from its non-event sessions (fewer if fewer exist), measured exactly as a date-only event.

## 5. Scorecard

For every index and every event type, and for E1 and E2 pooled:

- **Response rate:** share of events followed by a move.
- **Direction accuracy:** among those moves, the share in the event's direction.
- **Wrong-way rate** and **miss rate.**
- **Average move:** mean change in points, signed positive when it matches the event.
- **Unexplained-move rate:** of all large two-session changes in the period, the share with no event of any type within one session either side and no market-adjusted price move larger than twice the stock's typical daily move within one session either side.

## 6. Significance tests

1. **Response.** Relabel which sessions are events at random within each stock (same count per stock), 1,000 times with a fixed seed, and recompute the response rate. p = (1 + number of relabellings with a rate at least as high) / 1,001.
2. **Direction.** Direction accuracy with a 95% interval from a bootstrap that resamples event dates (2,000 resamples), plus an exact binomial p-value against 50%.
3. **Average move.** The same relabelling test as (1), on the signed average move with event directions shuffled.

**Primary cell:** `score_exo`, E1 and E2 pooled. The score is taken to follow real-world sentiment if all three hold: response p below 0.05; direction accuracy at least 60% with the interval wholly above 50%; unexplained-move rate below 50%.

Everything else is secondary: report it with the number of cells examined and Benjamini-Hochberg adjusted p-values. For E3 and E4 the index of interest is the influencer channel; these are plumbing checks, since ratings and insider trades are direct inputs.

## 7. Phases

**Phase 0: sources and counts (checkpoint).** Probe `yfinance` on five tickers for each event source: fields, date coverage, whether earnings carry a time of day. Then build the event list for the universe and write `results/event_counts.md`: counts per type and direction, drops and overlaps, by week. Using placebo-style changes on non-event sessions only, estimate the smallest response rate and direction accuracy the sample could detect. Use no event responses. If a source is unusable or a type has fewer than 30 events, say so; do not substitute another source or change a threshold. Stop and show me.

**Phase 1: code and tests (checkpoint).** Build the measurement and inference. Tests on synthetic data only: the data lock; before/after selection around the 21:45 cutoff and an after-close release; a null check (random event dates give roughly uniform p-values); a planted response (detected, with the right direction); a planted wrong-way response. Stop and show me the test output.

**Phase 2: run and report.** Run every cell, ledger each, and render `responsiveness/RESULTS.md` in this order: plain-language summary of the question and method; run metadata; data and event counts; decisions in full; primary cell in full; scorecards by index and event type; unexplained moves; multiple-comparisons summary; limitations observed.

**Phase 3: public README.** Write `responsiveness/README.md` (question, method, how to reproduce, what data is not in the repository and why) and a short top-level `README.md` describing the repository and its two experiments.

## 8. Out of scope

No data after 22 June 2026. No trading, strategies or filters. No lag measurement (that is the next experiment). No direct database access. No changes to the API or to the first experiment's files.

Start with Phase 0.
