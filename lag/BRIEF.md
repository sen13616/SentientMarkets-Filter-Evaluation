# Experiment 5B: how quickly does the score respond?

This is a **new and separate experiment** in this repository. It is the third experiment here, after the filter backtest (`filter_eval/`, INSTRUCTIONS.md, RESULTS.md) and Experiment 5A (`responsiveness/`, the pilot and the definitive run). It answers a different question, with its own code, decisions, ledger and results. Read this whole brief before writing anything.

The repository is public. Write everything (code, READMEs, commit messages, results) for a reader who has never seen the project.

## 1. The question

Experiment 5A asks whether the SentientMarkets score moves after real events. This experiment asks **how long it takes**: after something happens to a stock, how long is it before the published score has made its move, and how much of the price move has already happened by then?

The answer sets the shortest time scale on which any trading strategy can sensibly use the score. A strategy should not make decisions more often than the score can react. These two rules are fixed now, before any result (they are in the research paper, section 5B.4):

1. A strategy should not decide more often than the **full response time** (90% of the eventual move) of the channel it relies on.
2. If most of the price move has already happened by the **half response time**, the score cannot inform a trade on that event; it can only describe the situation afterwards.

| Full response time | Decisions | Holding period |
|---|---|---|
| Under 1 hour | As often as hourly | Hours |
| 1 to 6 hours | Once or twice a day | Overnight to a few days |
| 6 to 24 hours | Once a day | Several days |
| More than a day | Once a day or less | A week or more |

This experiment measures. It has no pass or fail. A short lag would show that the score is timely, not that it is useful. Do not write a conclusion about usefulness.

## 2. Keep the experiments apart

1. All new code goes in a new package, `lag/`, with its own `README.md`, `BRIEF.md` (this file), `DECISIONS.md`, `ledger.csv`, `results/` and tests. Save this brief as `lag/BRIEF.md` first.
2. **Do not change anything in `filter_eval/` or `responsiveness/`**, and above all nothing in `responsiveness/definitive/`. That run is pre-registered (tag `5a-definitive-prereg`), and its files must stay exactly as committed. You may import their loaders, calendar, event-building and inference code. If something you need there has a bug or needs changing, stop and tell me; do not copy it into `lag/` and edit it.
3. Number this experiment's decisions L1, L2, … so that they cannot be confused with 5A's.
4. Do not touch the API repository. One Claude Code session works in each repository.

## 3. Data and the data lock

Three date ranges matter.

| Range | Status for 5B |
|---|---|
| Up to 22 June 2026 | Allowed: the pilot (section 6, Phase 2) |
| 23 June to 1 October 2026 | **Reserved.** Nothing from it may be stored or analysed: no sentiment, no events, no prices |
| 2 October to 23 November 2026 | **Prices only until 5A's definitive run is finished.** No sentiment and no events from this range may be pulled, stored or analysed before then |

The third rule protects Experiment 5A. Its definitive run covers the same weeks and has not been run yet. Looking at how the score behaves around October events now would mean seeing part of 5A's answer before it is run. So, for October and November, this experiment collects prices now, writes its code now, and reads sentiment only after 5A's definitive results are committed, on or after 24 November.

Enforce all three rules in the loaders and test them. History and price sources return data outside the ranges, so filter in memory and discard before anything is written.

**Sentiment.** For the pilot, the tick cache already on disk (24 April to 22 June 2026). For the definitive run, the sentiment pull made by 5A's definitive Phase 1, read only after 5A's Phase 2 results are committed.

**Indices.** The published composite `score` (smoothed with a 4-hour half-life until 22 July 2026, and 2 hours since); the unsmoothed composite (`score_raw` if the tick data carries it, otherwise rebuilt from the channels with weights 0.35 / 0.30 / 0.25 / 0.10); `score_exo` (narrative, influencer and macro, weights 0.30 / 0.25 / 0.10, renormalised over those present, as in 5A); and each of the four channels. The market channel is computed from price, so it will line up with price by construction. Report it, flagged, and give it no weight.

**Prices within the day.**
- Pilot: hourly bars for May and June 2026 (`yfinance` keeps hourly bars for about two years).
- Definitive run: 15-minute bars. `yfinance` keeps these for only about 60 days, so **they must be collected now and kept up to date**, or the start of the period is lost for good. See Phase 0, step 4.

**Events.** Only events whose time can be fixed to within an hour:

| Type | Event | Time zero | Direction |
|---|---|---|---|
| L-E1 Earnings | An earnings release with a time of day (as in 5A, E1) | The release time | Sign of the market-adjusted return from the last close before the release to the first close after it |
| L-E2 Large move within the day | The first in-session price bar of a stock whose market-adjusted move exceeds 3 times that stock's normal move for bars at that time of day. Exclude sessions that are an L-E1 reaction session for that stock | The start of that bar | Sign of the bar's move |

The normal move for a bar is the robust standard deviation (1.4826 × the median absolute value) of the stock's market-adjusted returns for bars at the same time of day, over the period's sessions that are not earnings reaction sessions for that stock. The market return is the equal-weighted universe return for the same bar.

> **Amended on 9 October 2026, after the Phase 0 event counts and before any response was computed (DECISIONS.md L14).** The L-E2 threshold "3 times that stock's normal move" is replaced by a rarity rule: standardise each bar's market-adjusted move by the stock's time-of-day normal move (z), and set the threshold at the |z| exceeded by 0.2% of in-session bars, pooled across the universe over the period. The pilot's value, 5.1503, is fixed from the pilot's bars; the definitive run applies the same rule to its own period's bars. The 3× definition is kept as a secondary sensitivity cell. The original text above is unchanged.

Excluded, with the reason recorded: analyst rating changes and insider transactions (dated, not timed), and bursts of news (these need article publication times; in Phase 0, check from the API's documentation only whether they are exposed, and report).

**Clustering.** At most one event per stock in any 48-hour window. Keep earnings over large moves, then the earlier event. Count what is dropped.

**Universe.** For the pilot, 5A's 473 names. For the definitive run, 5A definitive's universe.

## 4. Measurement

**Readings.** S(t) is a stock's index value at the last tick stamped at or before t. For each event, the before reading is S(t₀⁻), the last tick strictly before time zero t₀. The change at horizon h is Δ(h) = S(t₀ + h) − S(t₀⁻), signed by the event's direction d (so positive means the score moved the way the event pointed): m(h) = d · Δ(h).

**Grid.** Every tick from 6 hours before to 48 hours after t₀. Report the main horizons h = 15 min, 30 min, 1, 2, 4, 8, 24 and 48 hours.

**Eventual move.** M = m(48 h).

**Response curve.** Across events, R(h) = mean of m(h) ÷ mean of M. This is a ratio of averages, not an average of per-event ratios, which are unstable when an event's eventual move is small.

**Half and full response.** T½ is the first horizon at which R(h) reaches 0.5, and T₉₀ the first at which it reaches 0.9, using linear interpolation between ticks. Both are capped at 48 hours and reported as "over 48 hours" if not reached.

**First response.** The first main horizon at which the mean of m(h) is significantly above the placebo mean (section 5), after a Holm adjustment across the eight main horizons.

**Price already moved.** The same curve built from the stock's market-adjusted cumulative return from the last price before t₀, signed by d: Rₚ(h) = mean of d·rₑ(h) ÷ mean of d·rₑ(48 h), counting session time only. Report Rₚ(T½): the share of the eventual price move already done when the score is half done.

**Alignment with price (no events needed).** Over every in-session hour of every stock, take the change in the index over that hour and the stock's market-adjusted return over that hour, each demeaned within stock. Compute their pooled correlation with the index shifted by k trading hours, for k from −12 to +12. The best alignment is the k with the largest correlation. Positive k means the score lags price.

**Splits.** Report everything for L-E1 and L-E2 separately and pooled, and for events inside and outside the trading session separately.

**Resolution.** The tick spacing (check it: 15 minutes in session and 30 outside, in the current schedule) and the bar length (1 hour in the pilot, 15 minutes in the definitive run) limit what can be resolved. Report every time with that limit next to it.

## 5. Inference

- **Is there a move to time at all?** For each index, test M with the relabelling test of 5A (same stock, random non-event times at the same time of day, same count per stock, K = 1,000, fixed seed, p = (1 + #{k : M⁽ᵏ⁾ ≥ M}) / (1 + K)). If an index's eventual move is not significant at 5%, its timings are reported as "no response to time" and not interpreted.
- **Intervals.** 95% intervals for T½, T₉₀, Rₚ(T½) and the best-alignment k come from a bootstrap that resamples event dates (or session dates, for alignment), B = 2,000, fixed seed.
- **Placebo curves.** The same curves at 20 placebo times per event (same stock, same time of day, non-event sessions), shown beside the event curves.
- **Primary measures.**

  > **Amended on 9 October 2026, after the Phase 0 event counts and before any response was computed (DECISIONS.md L14).** For `score_exo` and the unsmoothed composite, L-E1 and L-E2 are **two separate primary cells** (four primary cells in all): T½, T₉₀, the first response and Rₚ(T½), each with its interval. The pooled L-E1 + L-E2 cell is secondary. In the pilot the two types coincide with the outside- and inside-session split, so the pooled cell would mix two different mechanisms. The original text follows.

  As first specified: For `score_exo` and the unsmoothed composite, on L-E1 and L-E2 pooled: T½, T₉₀, the first response and Rₚ(T½), each with its interval. Everything else is secondary. Where a secondary measure has a p-value, report it with the number of cells examined and Benjamini-Hochberg adjusted values.

## 6. Ground rules

1. **Nothing is tuned.** Thresholds and definitions are fixed by this brief and by the decisions recorded before the pilot runs. The pilot may expose something unworkable; any change for the definitive run is recorded as an amendment, with its reason, before the definitive data is read.
2. **Counts before outcomes.** Event counts, drops and the tick-spacing check come to me before any response is computed.
3. **Ledger.** Every run is logged in `lag/ledger.csv` (timestamp, measure id, config hash, code commit, data hash, seed, headline numbers). Append-only. Code is committed before it runs.
4. **Numbers come from files.** `lag/RESULTS.md` is rendered by a script.
5. **Public-repository hygiene.** Never print, log or commit the API key. Do not commit raw third-party downloads (price bars) or raw sentiment ticks. Keep local paths, usernames and emails out of committed files, including test output. Make every result reproducible from a documented command.
6. **I handle git.** At each checkpoint, stop, list what to commit with a suggested message, and wait.

## 7. Phases

**Phase 0: setup, price collection and counts (checkpoint).**
1. Save this brief as `lag/BRIEF.md`.
2. Implement the three-range data lock and test it.
3. Check the pilot tick cache: does it carry `score_raw` and the four channels? What is the actual tick spacing in and out of session, from 12 May to 22 June?
4. **Start the 15-minute price collector now.** It downloads 15-minute bars for the universe, keeps only bars from 2 October to 23 November 2026, merges them into a local store outside git without duplicates, and writes a small coverage report (sessions and bars per ticker, gaps). Run it once now. Give me the one command to rerun it. I will run it weekly until 24 November.
5. Pull hourly bars for 12 May to 22 June 2026 and build the pilot's L-E1 and L-E2 events. Write `lag/results/event_counts.md`: counts by type, inside and outside the session, by week, with drops and clustering. Compute no responses.
6. From the API's documentation only (no data calls), report whether article publication times are available.
7. Stop and show me.

**Phase 1: code and synthetic tests (checkpoint).** Build the measurement and inference. Tests on synthetic data only:
- the data lock (all three ranges);
- reading selection around t₀ (a tick exactly at t₀ is not a before reading);
- a planted step at a known delay is recovered (T½ and T₉₀ within one tick);
- a planted step passed through an exponential smoother with a 2-hour half-life gives T½ of about 2 hours, as the smoothing implies;
- the alignment measure recovers a planted 3-hour offset, and finds none when there is none;
- with no planted response, M has roughly uniform p-values;
- an index that only copies price is aligned at k = 0 and has Rₚ(T½) near 1.
Stop and show me the test output.

**Phase 2: pilot run, 12 May to 22 June 2026 (checkpoint).** Events with t₀ from 13 May 2026 to 48 hours before the last tick of 22 June. Run every measure, log each in the ledger, and render `lag/RESULTS.md`: a plain-language summary, run metadata, counts, decisions, primary measures with intervals, the response curves (charts saved as images in `lag/results/`), alignment, secondary measures and limits. State clearly that the published composite was smoothed with a 4-hour half-life in this period, so its timings are not those of the system today. Stop.

**Phase 3: pre-register the definitive run (checkpoint).** Write `lag/definitive/` with a config that freezes every parameter for 2 October to 23 November 2026 (15-minute bars; events with t₀ from 5 October to 48 hours before the end of 23 November), and any amendments from the pilot with their reasons. Stop for me to commit and tag it (`5b-definitive-prereg`). This must happen before 24 November.

**Phase 4: definitive run (on or after 24 November, after 5A's definitive results are committed).** Read the sentiment pulled by 5A's Phase 1, run once, ledger, render `lag/definitive/RESULTS.md` with the pilot's figures beside it. Stop.

**Phase 5: README.** Update `lag/README.md` and the repository README to describe this experiment alongside the other two. Stop for review.

Start with Phase 0.

## 8. Out of scope

- Any data from 23 June to 1 October 2026.
- Any sentiment or event data from 2 October onward before 5A's definitive results are committed.
- Changes to `filter_eval/`, `responsiveness/` or the API.
- Trading, strategies or filters.
- Paid data. If minute bars or news timestamps turn out to be needed, say so and stop.
