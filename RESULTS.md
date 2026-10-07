# Results: sentiment as a context filter (research window)

Rendered by `scripts/render_results.py` from the result files. Development results on the research window only; no holdout data was stored or analysed. This document reports results and does not judge whether the hypotheses hold.

† marks cells whose input includes the contaminated market layer: every `composite` cell and every veto using four-layer divergence (D2, D21).

## 1. Run metadata

| item                                            | value                                                            |
|:------------------------------------------------|:-----------------------------------------------------------------|
| Rendered (UTC)                                  | 2026-10-07T05:28:02+00:00                                        |
| Repository HEAD at render                       | 72be171                                                          |
| Code commits in ledger                          | 72be171, uncommitted                                             |
| Sentiment pull completed (UTC)                  | 2026-10-07T04:33:03+00:00                                        |
| Sentiment ticks sha256                          | 6eb4f71e14a8610c2870397433505d7f54cfb98c308d1448da58eec9020e08c7 |
| State panel sha256                              | 1be3214022074334835403f06be27d67a171f31219bf95b9f2b234fcc9a4afd4 |
| Prices sha256                                   | badee479f07f374ee3fd5bcc84d1d5a012bed0a64161837f7ab293a7214c9548 |
| Price download (UTC)                            | 2026-10-07T04:03:54+00:00                                        |
| Price source                                    | yfinance 1.7.0, auto_adjust=True                                 |
| Rows discarded at ingest (after 22 June)        | 2,474,538                                                        |
| Seed (all cells)                                | 20261007                                                         |
| Permutations / bootstrap resamples / mean block | 1000 / 2000 / 10.0                                               |
| Final test run                                  | 45 passed in 7.92s                                               |

| phase                    | first row (UTC)           | last row (UTC)            | ledger rows   |
|:-------------------------|:--------------------------|:--------------------------|:--------------|
| Phase 3 (baselines)      | 2026-10-07T04:42:33+00:00 | 2026-10-07T04:43:17+00:00 | 10            |
| Phase 4 (filtered cells) | 2026-10-07T05:23:27+00:00 | 2026-10-07T05:24:05+00:00 | 72            |

Package versions: numpy 2.5.3, pandas 3.0.6, scipy 1.18.1, pyarrow 25.0.1, exchange_calendars 4.13.2, yfinance 1.7.0, requests 2.34.2, python-dotenv 1.2.4, pytest 9.1.1, tabulate 0.10.0; Python 3.14.6.

## 2. API findings (summary of API_FINDINGS.md)

| Question | Answer |
|---|---|
| Does history `raw` reach 24 April 2026? | **Yes.** AAPL's earliest row is 2026-04-24 23:55 UTC. The research window holds 3,333 rows for AAPL. |
| Is `score_exo` served in the research window? | **No.** It is null on every research-window row. The first non-null value is 2026-06-23 15:00 UTC. **`score_exo` must be reconstructed for the whole window.** |
| How well does the reconstruction match where `score_exo` is served? | On 369 recent rows (3 tickers × 123): median abs diff 0.003, max 0.0085, which is two-decimal rounding. The served `score_exo` is the unsmoothed per-tick renormalised average of narrative, influencer and macro. |
| Does history serve the smoothed composite? | Yes: `score`, an integer. `label` equals the band of `score` on 100% of window rows. |
| Does history serve the raw composite? | Yes: `score_raw`, an integer. It equals round(weighted sub-indices with the divergence cap) on 99.6% of window rows and is within 1 on 100%. |
| Does history serve the four sub-indices? | Yes. Floats with two decimals, nullable; `market`, `narrative`, `influencer`, `macro`. |
| Does history serve confidence? | Yes: `confidence`, an integer 0–100. |
| Does history serve confidence flags? | **No.** They appear only on the current-state endpoint. |
| Does history serve divergence? | **No.** It appears only on the current-state endpoint, so it must be computed from the sub-indices. |
| Does history serve missing layers? | Yes: `missing_layers`, a list of layer names. |
| Is there a replay or backfill marker? | **No field anywhere in the API.** See "Replayed rows" below. |
| Is history `score` integer-rounded? | Yes, and it is the **smoothed** composite (EMA). `score_raw` is the integer raw composite; the sub-indices and `score_exo` are two-decimal floats. |
| Does `/v1/tickers` separate seed names or expose `delisted_at`? | **No.** It returns `ticker`, `name`, `sector` and `in_sp500` only. It lists the 586 active names (503 with `in_sp500=true`) and **omits delisted names** (HES, PXD and ANSS are absent). |
| How does a delisted ticker behave? | Current endpoint: HTTP 200 with `{"status":"delisted","message":"… stopped trading on <date>; successor: <ticker> …"}`. History with `days=2`: HTTP 200 with an empty list. |
| What is the size and latency? | `raw` with `days=2`: about 27.6 KB and 0.5–1.3 s per ticker. `raw` with `days=166` (needed to reach 24 April): **1.9 MB and 0.9–5.9 s per ticker**. |
| What would the full pull cost? | About 586 requests and roughly **1.1 GB transferred**. At the 2.5 s throttle that is 25–60 minutes. About 39% of rows fall in the research window, so roughly 430 MB of JSON survives the date filter. The daily panel will be a few MB. |

## 3. Data

Generated by `scripts/build_panel.py` from stored sentiment ticks and the presence of price bars. No return data is used.

### Window and sessions

- Window: 2026-04-24 to 2026-06-22; NYSE sessions (XNYS calendar): **40**.
- First decision session: 2026-04-27 (no ticker has a state on 2026-04-24; D4).
- 2026-05-25 (Monday) is a weekday but not an NYSE session: 29,158 ticks exist that day and none is used as a state.
- 2026-06-19 (Friday) is a weekday but not an NYSE session: 29,158 ticks exist that day and none is used as a state.
- Holiday check: 2026-05-25 in sessions = False; 2026-06-19 in sessions = False.

### Used universe

| Step                                                                         |   Names |
|:-----------------------------------------------------------------------------|--------:|
| Candidates from seed_universe.csv (D7)                                       |     478 |
| with a successful sentiment pull                                             |     478 |
| with at least one stored tick                                                |     478 |
| with a price bar on every window session                                     |     473 |
| and valid state on >= 90% of sessions                                        |     473 |
| and a valid state in the first five and last five sessions (= used universe) |     473 |

- Dropped for lack of yfinance bars on every window session (5): AVB, EA, EQR, LEG, QRVO. yfinance returned no data at all for: AVB, EA, EQR, LEG, QRVO.
- Dropped by the sentiment coverage rule: none.

### Missing state by session (used universe)

A state is valid when a tick before 21:45 UTC exists and `score_exo` and `confidence` are defined (D10).

| day        |   valid | missing_share   |
|:-----------|--------:|:----------------|
| 2026-04-24 |       0 | 100.0%          |
| 2026-04-27 |     473 | 0.0%            |
| 2026-04-28 |     473 | 0.0%            |
| 2026-04-29 |     473 | 0.0%            |
| 2026-04-30 |     473 | 0.0%            |
| 2026-05-01 |     473 | 0.0%            |
| 2026-05-04 |     473 | 0.0%            |
| 2026-05-05 |     473 | 0.0%            |
| 2026-05-06 |     473 | 0.0%            |
| 2026-05-07 |     473 | 0.0%            |
| 2026-05-08 |     473 | 0.0%            |
| 2026-05-11 |     473 | 0.0%            |
| 2026-05-12 |     473 | 0.0%            |
| 2026-05-13 |     473 | 0.0%            |
| 2026-05-14 |     473 | 0.0%            |
| 2026-05-15 |     473 | 0.0%            |
| 2026-05-18 |     473 | 0.0%            |
| 2026-05-19 |     473 | 0.0%            |
| 2026-05-20 |     473 | 0.0%            |
| 2026-05-21 |     473 | 0.0%            |
| 2026-05-22 |     473 | 0.0%            |
| 2026-05-26 |     473 | 0.0%            |
| 2026-05-27 |     473 | 0.0%            |
| 2026-05-28 |     473 | 0.0%            |
| 2026-05-29 |     473 | 0.0%            |
| 2026-06-01 |     473 | 0.0%            |
| 2026-06-02 |     473 | 0.0%            |
| 2026-06-03 |     473 | 0.0%            |
| 2026-06-04 |     473 | 0.0%            |
| 2026-06-05 |     473 | 0.0%            |
| 2026-06-08 |     473 | 0.0%            |
| 2026-06-09 |     473 | 0.0%            |
| 2026-06-10 |     473 | 0.0%            |
| 2026-06-11 |     473 | 0.0%            |
| 2026-06-12 |     473 | 0.0%            |
| 2026-06-15 |     473 | 0.0%            |
| 2026-06-16 |     473 | 0.0%            |
| 2026-06-17 |     473 | 0.0%            |
| 2026-06-18 |     473 | 0.0%            |
| 2026-06-22 |     473 | 0.0%            |

### State distribution by input index (used universe, all window sessions)

Bands apply to the half-up rounded index (D11). `composite` is the served smoothed score (4-hour EMA in this window) and **contains the contaminated market layer** (D2). `score_exo` is **reconstructed** from the sub-indices (D5); the served value is null throughout the window.

| index                       | Strongly Bearish   | Bearish   | Neutral   | Bullish   | Strongly Bullish   | missing   |
|:----------------------------|:-------------------|:----------|:----------|:----------|:-------------------|:----------|
| score_exo                   | 0.0%               | 3.5%      | 52.2%     | 41.5%     | 0.2%               | 2.5%      |
| composite (market-affected) | 0.0%               | 2.3%      | 66.6%     | 28.6%     | 0.0%               | 2.5%      |
| narrative                   | 1.1%               | 7.5%      | 40.8%     | 38.6%     | 7.3%               | 4.8%      |
| influencer                  | 0.3%               | 13.0%     | 41.9%     | 40.4%     | 1.8%               | 2.5%      |
| macro                       | 0.9%               | 14.8%     | 33.2%     | 47.1%     | 1.4%               | 2.5%      |

- Served `score_exo` values in stored window ticks: 0 of 1,586,106.
- Ticker-days with confidence below 60: 8.0% (of valid states: 8.2%).
- Ticker-days with high divergence (spread > 40, computed; D6): 19.6% (of valid states: 20.1%).

### Which scoring slot supplied the state (D3, D9)

State = last tick stamped before 21:45:00 UTC on the session day. Slot = the tick's stamp floored to 15 minutes.

| slot   |   ticker-days | share   |
|:-------|--------------:|:--------|
| 21:30  |         13717 | 74.4%   |
| 21:15  |          4276 | 23.2%   |
| 21:00  |            85 | 0.5%    |
| 20:45  |            79 | 0.4%    |
| 20:30  |            72 | 0.4%    |
| 20:00  |           218 | 1.2%    |

Stamp lag of the 21:30 slot (stamp minus 21:30:00, seconds), over ticker-days that used it:

|      |   seconds |
|:-----|----------:|
| p0   |      0.04 |
| p5   |      0.92 |
| p25  |      3.21 |
| p50  |      5.85 |
| p75  |      9.37 |
| p95  |    702.19 |
| p99  |    837.2  |
| p100 |    837.9  |

#### Days where the state did not come from the 21:30 slot

Reason per ticker-day (D9): **no 21:30 tick** = no tick in [21:30, 22:00); **21:30 tick late** = no tick in [21:30, 21:45) but one in [21:45, 22:00); **no state** = no tick before 21:45 at all.

|            |   21:30 slot |   21:30 tick late (>= 21:45) |   no state |
|:-----------|-------------:|-----------------------------:|-----------:|
| 2026-04-24 |            0 |                            0 |        473 |
| 2026-04-27 |            0 |                          473 |          0 |
| 2026-04-28 |            0 |                          473 |          0 |
| 2026-04-29 |            0 |                          473 |          0 |
| 2026-04-30 |            0 |                          473 |          0 |
| 2026-05-01 |            0 |                          473 |          0 |
| 2026-05-04 |            0 |                          473 |          0 |
| 2026-05-05 |            0 |                          473 |          0 |
| 2026-05-06 |          473 |                            0 |          0 |
| 2026-05-07 |          473 |                            0 |          0 |
| 2026-05-08 |          473 |                            0 |          0 |
| 2026-05-11 |          473 |                            0 |          0 |
| 2026-05-12 |          473 |                            0 |          0 |
| 2026-05-13 |            0 |                          473 |          0 |
| 2026-05-14 |            0 |                          473 |          0 |
| 2026-05-15 |            0 |                          473 |          0 |
| 2026-05-18 |          473 |                            0 |          0 |
| 2026-05-19 |          473 |                            0 |          0 |
| 2026-05-20 |          473 |                            0 |          0 |
| 2026-05-21 |          473 |                            0 |          0 |
| 2026-05-22 |          473 |                            0 |          0 |
| 2026-05-26 |          473 |                            0 |          0 |
| 2026-05-27 |          473 |                            0 |          0 |
| 2026-05-28 |          473 |                            0 |          0 |
| 2026-05-29 |          473 |                            0 |          0 |
| 2026-06-01 |          473 |                            0 |          0 |
| 2026-06-02 |          473 |                            0 |          0 |
| 2026-06-03 |          473 |                            0 |          0 |
| 2026-06-04 |          473 |                            0 |          0 |
| 2026-06-05 |          473 |                            0 |          0 |
| 2026-06-08 |          473 |                            0 |          0 |
| 2026-06-09 |          473 |                            0 |          0 |
| 2026-06-10 |          473 |                            0 |          0 |
| 2026-06-11 |          473 |                            0 |          0 |
| 2026-06-12 |          473 |                            0 |          0 |
| 2026-06-15 |          473 |                            0 |          0 |
| 2026-06-16 |          473 |                            0 |          0 |
| 2026-06-17 |          473 |                            0 |          0 |
| 2026-06-18 |          473 |                            0 |          0 |
| 2026-06-22 |          473 |                            0 |          0 |
| TOTAL      |        13717 |                         4730 |        473 |

#### Detail for days without a 21:30-slot state

Ticker-days by the slot that supplied the state, and tick timing that day (UTC). In these early weeks the scoring tick did not run on a fixed 15-minute grid, so the late-tick label in D9 describes the stamps, not a known schedule.

| day        |   21:15 |   21:00 |   20:45 |   20:30 |   20:00 | selected tick, median stamp   | selected tick, earliest stamp   | first tick at/after 21:30, median stamp   |
|:-----------|--------:|--------:|--------:|--------:|--------:|:------------------------------|:--------------------------------|:------------------------------------------|
| 2026-04-27 |     473 |       0 |       0 |       0 |       0 | 21:16                         | 21:15                           | 21:47                                     |
| 2026-04-28 |     473 |       0 |       0 |       0 |       0 | 21:16                         | 21:15                           | 21:47                                     |
| 2026-04-29 |     473 |       0 |       0 |       0 |       0 | 21:16                         | 21:15                           | 21:49                                     |
| 2026-04-30 |     473 |       0 |       0 |       0 |       0 | 21:16                         | 21:15                           | 21:47                                     |
| 2026-05-01 |     473 |       0 |       0 |       0 |       0 | 21:16                         | 21:15                           | 21:47                                     |
| 2026-05-04 |     473 |       0 |       0 |       0 |       0 | 21:27                         | 21:27                           | 21:57                                     |
| 2026-05-05 |     473 |       0 |       0 |       0 |       0 | 21:27                         | 21:27                           | 21:57                                     |
| 2026-05-13 |      19 |      85 |      79 |      72 |     218 | 20:36                         | 20:03                           | 21:49                                     |
| 2026-05-14 |     473 |       0 |       0 |       0 |       0 | 21:21                         | 21:21                           | 21:51                                     |
| 2026-05-15 |     473 |       0 |       0 |       0 |       0 | 21:27                         | 21:18                           | 21:48                                     |

### Persistence of states within tickers (decision sessions; states only)

Share of each index's variance explained by ticker means. The permutation null shuffles each ticker's states across dates, so it preserves this between-ticker component.

| index       | between-ticker share of variance   |
|:------------|:-----------------------------------|
| score_exo   | 0.30                               |
| composite † | 0.28                               |
| narrative   | 0.20                               |
| influencer  | 0.37                               |
| macro       | 0.01                               |

## 4. Deviations and decisions (DECISIONS.md, in full)

Interpretive choices and deviations from INSTRUCTIONS.md, in date order. Each entry states the
decision, who made it, and a one-line reason. Nothing here is changed retroactively; a reversal
is a new dated entry.

### 2026-10-06 (Phase 0)

**D0.1 Reach-back probe beyond `days=2`.** One raw-history call for AAPL with `days=166`, made
once in each of the two probe scripts, examined in memory only. *Reason:* the Phase 0 stop
condition (does `raw` reach 24 April?) cannot be tested with `days=2`. Approved by the
researcher before it ran.

### 2026-10-07 (answers to Phase 0 questions; set by the researcher before any data pull)

**D1 Caching under the holdout lock.** API responses are filtered in memory. Only rows stamped
on or before 2026-06-22 23:59:59 UTC are written to disk, and every such tick is kept per
ticker, not just the selected daily tick, so the selection rule can be re-derived without
re-pulling. The raw response is never written. The manifest may record the count of discarded
rows per ticker and nothing else about them. *Reason:* the history endpoint has no end-date
parameter, so every response contains holdout rows. This reconciles ground rule 9 (cache
everything) with ground rule 1 (store nothing after 22 June).

**D2 Composite input is the smoothed `score`.** The "composite" input index is the served
integer `score`, the EMA-smoothed composite. No `score_raw` cells are added, so the cell list
in INSTRUCTIONS.md section 9 stays closed. Note on comparability: throughout the research window
the EMA half-life was **4 hours**; it has been 2 hours since 22 July 2026. `score_exo` (as
reconstructed, see D5) and the four sub-indices are **unsmoothed** per-tick values. The composite
therefore differs from the other inputs both in containing the contaminated market layer and in
being smoothed, and it is labelled market-affected wherever it is reported. *Reason:* the
smoothed score is the system's served score and the one a user of the API would filter on.

**D3 Daily cutoff is the 21:30 scoring slot.** The state for ticker-day t is the last tick
stamped **before 21:45:00 UTC** on day t. The rule "at or before 21:30 UTC" refers to the tick
scheduled for the 21:30 slot, which is stamped a few seconds after 21:30:00. A strict
21:30:00.000 cutoff would drop that tick. The look-ahead test asserts that a tick stamped at
21:45:00 or later cannot affect a day-t decision. `results/coverage.md` reports how many
ticker-days took their state from each 15-minute slot, and the distribution of stamp lag
(stamp minus 21:30:00) for the 21:30 slot. *Reason:* researcher's reading of the spec; the
21:30 tick is the one following the 21:15 end-of-day market snapshot.

**D4 Decisions start on 27 April 2026.** The earliest tick anywhere in the history is
2026-04-24 23:55 UTC, after the cutoff, so no ticker has a usable state on 24 April. The first
decision session is 27 April 2026. The used-universe coverage rules are applied over the window
sessions as written in INSTRUCTIONS.md. *Reason:* forced by the data.

**D5 `score_exo` is reconstructed for the whole window.** The API serves `score_exo` only from
2026-06-23 onward. In the window it is reconstructed from the narrative, influencer and macro
sub-indices with weights 0.30 / 0.25 / 0.10, renormalised over the layers present. Where the API
does serve it, the reconstruction matches to two-decimal rounding (369 rows, max abs diff
0.0085). *Reason:* forced by the data; the method is the one specified in INSTRUCTIONS.md
section 5.

**D6 Divergence is computed.** History does not serve the divergence flag. High divergence is
defined as (max − min) over the present sub-indices, all four, exceeding 40. *Reason:* forced by
the data; the method is the one specified in INSTRUCTIONS.md section 5.

**D7 Universe source.** When `seed_universe.csv` (ticker, added_at, delisted_at) is present, the
candidate set is the names with added_at before 2026-10-03 and delisted_at null or after
2026-06-22. The coverage and price rules of INSTRUCTIONS.md section 4 are then applied. History
is pulled only for candidates, including delisted names that `/v1/tickers` omits. One delisted
ticker is tested first and the endpoint's response is reported before the full pull. Any name
dropped for lack of yfinance bars is listed. The pull does not start until the file exists.
*Reason:* `/v1/tickers` neither flags seed names nor lists delisted ones (API_FINDINGS.md).

### 2026-10-07 (Phase 1 build)

**D8 Observation for the holdout only: delisted names keep receiving unmarked scored rows.**
AVB stopped trading on 2026-08-17, yet its raw history holds scored rows up to 2026-10-03, and
nothing in the API marks them as post-delisting. This has no bearing on the research window,
where every candidate was trading. Holdout work must cut each delisted name's rows at its
`delisted_at` itself. *Recorded at the researcher's request.*

**D9 Telling a late 21:30 tick from a missing one.** The API does not say which slot a tick was
scheduled for. A tick stamped in [21:45:00, 22:00:00) UTC is read as the 21:30-slot tick
arriving late. 22:00 is the next scheduled tick after the session, at the 30-minute
off-session cadence. A ticker-day with no tick in [21:30, 22:00) has "no 21:30 tick". This
classification is used only to explain, in `coverage.md`, why a state came from an earlier
slot. It never affects which tick is selected. *Reason:* the most direct reading of the slot
schedule.

**D10 Valid state for coverage and the used universe.** A ticker-day has a valid state when a
qualifying tick exists (D3) and both the primary index `score_exo` and `confidence` are
defined. The 90% coverage rule of INSTRUCTIONS.md section 4 counts valid states. A filter on
another input index treats that index being null as a missing state (section 6). *Reason:*
the primary index is what the used-universe rule protects, and confidence is needed by the veto.

**D11 Rounding for label bands.** The index is rounded half-up (x.5 rounds up) before band
assignment. Python's default `round` rounds half to even. *Reason:* half-up is the
conventional reading of "integer-rounded". The served integer scores are unaffected.

**D12 yfinance symbols.** API tickers with a class dot (`BRK.B`, `BF.B`) are requested from
yfinance with a dash (`BRK-B`, `BF-B`). Results are stored under the API ticker. *Reason:*
yfinance's symbol convention.

### 2026-10-07 (Phase 2 engine; fixed before any real-data backtest)

**D13 Filters act on the unfiltered trade list.** A filter keeps, drops or re-weights the base
strategy's entries and never creates an entry the base strategy would not make. For TSMOM, BRK
and RSI-MR, a gated-out entry is not re-attempted later in the same long spell, breakout
holding period or RSI episode. *Reason:* it isolates the filter's effect and makes the
attribution of removed versus kept entries exact.

**D14 Size filter gross matching.** After the multipliers are applied, each day's post-trade
open book is scaled by one common factor so its gross exposure equals the unfiltered
strategy's that day. Trades caused by changes in that factor pay the same 10 bp cost. On a
day when every open sized position has multiplier 0, the book is flat. *Reason:* the literal
reading of "gross exposure on each day equals the unfiltered strategy's", without a free
rebalancing advantage.

**D15 Portfolio returns vs trade statistics.** Portfolio daily returns charge 10 bp on traded
notional netted per ticker at each open. A name held in consecutive CSM or STR cohorts trades
only the difference. Hit rate, profit factor and attribution use each trade's standalone
return, net of 10 bp at entry and at exit. Hit rate is unweighted over trades taken. Profit
factor uses trade P&L, meaning capital weight × standalone return; for the size filter the
weight includes the day-of-entry gross factor. Trades still open at the last session count as
closed at that close. *Reason:* netting is the conventional portfolio cost model; per-trade
statistics need a per-trade return.

**D16 Metric conventions.** Capital is a constant 1 with no compounding. A position's notional
drifts with price from its entry weight. The P&L sessions are those from the first possible
entry (28 April 2026; 13 May 2026 for the sub-window cells) to 22 June 2026. Sharpe, drawdown,
turnover, exposure and beta are computed over these sessions, with flat days counted as 0.
- **Sharpe:** mean / sd (ddof 1) × √252. It is reported as undefined if sd is 0.
- **Maximum drawdown:** measured on 1 + cumulative daily return.
- **Turnover:** average daily traded notional, two-sided, including the final close-out.
- **Exposure:** gross and net post-trade exposure at the open.
- **Beta:** OLS slope against the equal-weighted close-to-close return of the used universe.

*Reason:* the conventional choices, given a window too short for compounding to matter.

**D17 Threshold mechanics.** Gate thresholds apply to the half-up rounded index (D11),
consistent with the label bands. The size multiplier uses the unrounded index. The sensitivity
variants pair as follows: the looser setting is long ≥ 56 / short ≤ 45, with STR ≥ 36; the
tighter setting is long ≥ 66 / short ≤ 35, with STR ≥ 46. *Reason:* the pairing keeps each
variant uniformly looser or tighter than the base.

**D18 Strategy mechanics.**
- **Quintiles:** floor(n/5) names each, among names with a defined lookback return, ranked by
  stable sort.
- **CSM:** decides on 27 April and every fifth session after.
- **TSMOM:** starts flat, so names whose 60-session return is positive on 27 April are entries
  that day. A position exits at the next open after the first decision day with a 60-session
  return ≤ 0.
- **BRK:** a breakout is a close strictly above the maximum of the previous 252 closes. "While
  in a position" means the name is held at that day's close, so a new entry is possible from
  the exit session on.
- **RSI-MR:** crossing below 30 means RSI(t−1) ≥ 30 > RSI(t). Crossing above 50 means
  RSI(t−1) ≤ 50 < RSI(t), evaluated from the entry session; the exit is at the next open.
  Wilder smoothing is seeded with the simple average of the first 14 changes from 1 January
  2025.
- **Decisions:** run 27 April to 19 June. A decision on 22 June has no entry session inside
  the window.

*Reason:* the conventional definitions.

**D19 Permutation mechanics.** Each ticker's whole daily state rows (all input indices,
confidence, divergence) are permuted across the 40 window sessions, including 24 April, where
every state is missing. The permutation is independent per ticker and per replication. Each
cell uses the same fixed seed, 20261007, and the bootstrap draws from the same generator after
the permutations. The unfiltered comparator is fixed across permutations. *Reason:* the
literal specification; one seed for all cells keeps every cell reproducible on its own.

**D20 Null-check test design (synthetic only).** The centring check uses zero drift, zero cost
and a fresh price path per replication, where symmetry makes the expected difference zero. The
p-value uniformity check runs with 10 bp costs. A first version held one price path fixed
across replications. Its differences centred on +0.92 (se 0.18), because conditional on one
path the base Sharpe is fixed. That version was replaced. *Reason:* centring is only guaranteed
under symmetry; uniform p-values are the property the inference relies on.

### 2026-10-07 (amendment before Phase 4; set by the researcher after the baseline review and before any filtered strategy ran)

**D21 Amendment: five `veto-exo` cells.** One per strategy. Same rule as the veto (skip the
entry if confidence < 60 or divergence is high), but divergence is the spread across the
narrative, influencer and macro sub-indices only. It is high above 40, and not high when fewer
than two of the three are present. The confidence rule is unchanged, and a missing confidence
is a missing state. The closed list grows from 72 cells to 77, 72 of them filtered. Every
veto cell using four-layer divergence (`veto/*`, `sens/veto-c50/*`, `sens/veto-c70/*`) and
every `composite` cell is labelled market-layer-affected wherever it is reported.
`veto-exo` pass rates are reported alongside the others in `results/pass_rates.md`.
*Reason (researcher):* the four-layer divergence includes the market sub-index, which is
contaminated in this window and is price-derived.

**D22 Extra descriptive columns, no new cells.**
- CSM gate and size cells report entries passed, split into long and short.
- Size cells report the average effective number of positions: the daily
  1 / Σ wᵢ², with wᵢ each position's share of that day's gross open exposure, averaged over
  P&L sessions with a non-empty book.
- "Days on which every multiplier was zero" is reported two ways. The first counts entry days
  on which every candidate entry's multiplier was zero. The second counts P&L sessions on
  which the unfiltered book held positions but every open position's multiplier was zero, so
  the sized book was flat (D14).

*Reason:* the brief's wording fits both readings; the second is the one that matters for gross
matching.

**D23 Flat start confirmed.** Checked on the real trade lists before Phase 4:
- No strategy has a decision before 27 April 2026 or an entry before 28 April.
- Gross exposure is zero on 24 and 27 April.
- TSMOM's initial longs are 245 entries decided on 27 April. Each has a valid state and passes
  through the filters like any other entry.
- BRK and RSI-MR carry no position from pre-window signals. Pre-window data enters only as
  lookback input (closes; RSI on the session before a decision).

*Reason:* researcher's check before running filters.

## 5. Unfiltered baselines

P&L sessions 38; costs 10 bp per side.

| strategy   | Sharpe   | profit factor   | max DD   | hit rate   | trades   | turnover/day   | avg gross   | avg net   | beta   | total return   |
|:-----------|:---------|:----------------|:---------|:-----------|:---------|:---------------|:------------|:----------|:-------|:---------------|
| CSM        | 2.05     | 1.14            | 3.01%    | 49.7%      | 1,504    | 0.196          | 1.005       | 0.004     | 0.08   | 3.63%          |
| STR        | 2.61     | 1.44            | 3.57%    | 52.5%      | 3,572    | 0.341          | 0.952       | 0.952     | 1.21   | 6.74%          |
| TSMOM      | 2.27     | 1.72            | 1.87%    | 38.5%      | 807      | 0.091          | 0.533       | 0.533     | 0.56   | 2.81%          |
| BRK        | 3.42     | 2.58            | 0.73%    | 52.7%      | 207      | 0.024          | 0.185       | 0.185     | 0.17   | 1.76%          |
| RSI-MR     | 0.96     | 1.27            | 0.37%    | 57.3%      | 117      | 0.013          | 0.082       | 0.082     | 0.08   | 0.19%          |

## 6. Filter pass rates

Candidates are the unfiltered entries decided from 2026-04-27. Gate and size thresholds per INSTRUCTIONS.md section 8; size 'pass' = multiplier > 0. Veto passes when confidence >= 60 and divergence is not high; `veto` uses the four-layer divergence (includes the market layer), `veto-exo` the narrative/influencer/macro spread (D21). Rows marked market-affected use the contaminated market layer (D2).

### gate

| strategy   | input                       |   candidates |   missing_state |   pass |   fail_with_state | pass share   |
|:-----------|:----------------------------|-------------:|----------------:|-------:|------------------:|:-------------|
| CSM        | score_exo                   |         1504 |               0 |    461 |              1043 | 30.7%        |
| CSM        | composite (market-affected) |         1504 |               0 |    432 |              1072 | 28.7%        |
| CSM        | narrative                   |         1504 |              56 |    545 |               903 | 36.2%        |
| CSM        | influencer                  |         1504 |               0 |    483 |              1021 | 32.1%        |
| CSM        | macro                       |         1504 |               0 |    533 |               971 | 35.4%        |
| STR        | score_exo                   |         3572 |               0 |   3381 |               191 | 94.7%        |
| STR        | composite (market-affected) |         3572 |               0 |   3317 |               255 | 92.9%        |
| STR        | narrative                   |         3572 |              66 |   2980 |               526 | 83.4%        |
| STR        | influencer                  |         3572 |               0 |   3120 |               452 | 87.3%        |
| STR        | macro                       |         3572 |               0 |   2780 |               792 | 77.8%        |
| TSMOM      | score_exo                   |          807 |               0 |    345 |               462 | 42.8%        |
| TSMOM      | composite (market-affected) |          807 |               0 |    303 |               504 | 37.5%        |
| TSMOM      | narrative                   |          807 |              25 |    350 |               432 | 43.4%        |
| TSMOM      | influencer                  |          807 |               0 |    334 |               473 | 41.4%        |
| TSMOM      | macro                       |          807 |               0 |    498 |               309 | 61.7%        |
| BRK        | score_exo                   |          207 |               0 |    134 |                73 | 64.7%        |
| BRK        | composite (market-affected) |          207 |               0 |    152 |                55 | 73.4%        |
| BRK        | narrative                   |          207 |               3 |    145 |                59 | 70.0%        |
| BRK        | influencer                  |          207 |               0 |     91 |               116 | 44.0%        |
| BRK        | macro                       |          207 |               0 |    132 |                75 | 63.8%        |
| RSI-MR     | score_exo                   |          117 |               0 |     38 |                79 | 32.5%        |
| RSI-MR     | composite (market-affected) |          117 |               0 |      8 |               109 | 6.8%         |
| RSI-MR     | narrative                   |          117 |               3 |     32 |                82 | 27.4%        |
| RSI-MR     | influencer                  |          117 |               0 |     56 |                61 | 47.9%        |
| RSI-MR     | macro                       |          117 |               0 |     69 |                48 | 59.0%        |

### size

| strategy   | input                       |   candidates |   missing_state |   pass |   fail_with_state |   full_size | pass share   |
|:-----------|:----------------------------|-------------:|----------------:|-------:|------------------:|------------:|:-------------|
| CSM        | score_exo                   |         1504 |               0 |    857 |               647 |           4 | 57.0%        |
| CSM        | composite (market-affected) |         1504 |               0 |    957 |               547 |           0 | 63.6%        |
| CSM        | narrative                   |         1504 |              56 |    870 |               578 |         115 | 57.8%        |
| CSM        | influencer                  |         1504 |               0 |    769 |               735 |          10 | 51.1%        |
| CSM        | macro                       |         1504 |               0 |    798 |               706 |          37 | 53.1%        |
| STR        | score_exo                   |         3572 |               0 |   3397 |               175 |         207 | 95.1%        |
| STR        | composite (market-affected) |         3572 |               0 |   3317 |               255 |           7 | 92.9%        |
| STR        | narrative                   |         3572 |              66 |   3016 |               490 |         520 | 84.4%        |
| STR        | influencer                  |         3572 |               0 |   3139 |               433 |         706 | 87.9%        |
| STR        | macro                       |         3572 |               0 |   2791 |               781 |        1487 | 78.1%        |
| TSMOM      | score_exo                   |          807 |               0 |    682 |               125 |           0 | 84.5%        |
| TSMOM      | composite (market-affected) |          807 |               0 |    705 |               102 |           0 | 87.4%        |
| TSMOM      | narrative                   |          807 |              25 |    665 |               117 |          38 | 82.4%        |
| TSMOM      | influencer                  |          807 |               0 |    562 |               245 |          12 | 69.6%        |
| TSMOM      | macro                       |          807 |               0 |    589 |               218 |          14 | 73.0%        |
| BRK        | score_exo                   |          207 |               0 |    196 |                11 |           3 | 94.7%        |
| BRK        | composite (market-affected) |          207 |               0 |    202 |                 5 |           0 | 97.6%        |
| BRK        | narrative                   |          207 |               3 |    194 |                10 |          24 | 93.7%        |
| BRK        | influencer                  |          207 |               0 |    150 |                57 |           3 | 72.5%        |
| BRK        | macro                       |          207 |               0 |    162 |                45 |           3 | 78.3%        |
| RSI-MR     | score_exo                   |          117 |               0 |     84 |                33 |           0 | 71.8%        |
| RSI-MR     | composite (market-affected) |          117 |               0 |     46 |                71 |           0 | 39.3%        |
| RSI-MR     | narrative                   |          117 |               3 |     65 |                49 |           4 | 55.6%        |
| RSI-MR     | influencer                  |          117 |               0 |     83 |                34 |           5 | 70.9%        |
| RSI-MR     | macro                       |          117 |               0 |     86 |                31 |           0 | 73.5%        |

### veto

| strategy   | input                                             |   candidates |   missing_state |   pass |   fail_with_state |   vetoed_low_conf |   vetoed_high_div | pass share   |
|:-----------|:--------------------------------------------------|-------------:|----------------:|-------:|------------------:|------------------:|------------------:|:-------------|
| CSM        | confidence + 4-layer divergence (market-affected) |         1504 |               0 |   1055 |               449 |               151 |               340 | 70.1%        |
| STR        | confidence + 4-layer divergence (market-affected) |         3572 |               0 |   2272 |              1300 |               325 |              1043 | 63.6%        |
| TSMOM      | confidence + 4-layer divergence (market-affected) |          807 |               0 |    525 |               282 |               190 |               108 | 65.1%        |
| BRK        | confidence + 4-layer divergence (market-affected) |          207 |               0 |    156 |                51 |                24 |                30 | 75.4%        |
| RSI-MR     | confidence + 4-layer divergence (market-affected) |          117 |               0 |     57 |                60 |                11 |                52 | 48.7%        |

### veto-exo

| strategy   | input                             |   candidates |   missing_state |   pass |   fail_with_state |   vetoed_low_conf |   vetoed_high_div | pass share   |
|:-----------|:----------------------------------|-------------:|----------------:|-------:|------------------:|------------------:|------------------:|:-------------|
| CSM        | confidence + exo divergence (D21) |         1504 |               0 |   1194 |               310 |               151 |               176 | 79.4%        |
| STR        | confidence + exo divergence (D21) |         3572 |               0 |   2719 |               853 |               325 |               567 | 76.1%        |
| TSMOM      | confidence + exo divergence (D21) |          807 |               0 |    544 |               263 |               190 |                88 | 67.4%        |
| BRK        | confidence + exo divergence (D21) |          207 |               0 |    168 |                39 |                24 |                17 | 81.2%        |
| RSI-MR     | confidence + exo divergence (D21) |          117 |               0 |     87 |                30 |                11 |                21 | 74.4%        |

## 7. Headline research-window cell: CSM / gate / score_exo

A development result on the research window, not a confirmation.

| metric             | filtered   | unfiltered   |
|:-------------------|:-----------|:-------------|
| Sharpe             | 2.894      | 2.051        |
| mean daily return  | 0.00077    | 0.00095      |
| sd daily return    | 0.00424    | 0.00739      |
| total return       | 0.0294     | 0.0363       |
| profit factor      | 1.443      | 1.141        |
| max drawdown       | 0.0190     | 0.0301       |
| hit rate           | 0.512      | 0.497        |
| trades             | 461        | 1,504        |
| long entries       | 415        | 752          |
| short entries      | 46         | 752          |
| turnover/day       | 0.082      | 0.196        |
| avg gross          | 0.306      | 1.005        |
| avg net            | 0.245      | 0.004        |
| beta (EW universe) | 0.287      | 0.079        |
| P&L sessions       | 38         | 38           |

| statistic                                            | value           |
|:-----------------------------------------------------|:----------------|
| Sharpe difference (filtered − unfiltered)            | 0.843           |
| Permutation p-value (one-sided, 1,000 permutations)  | 0.8541          |
| Benjamini-Hochberg adjusted p (72 filtered cells)    | 1.0000          |
| Permutation null mean                                | 1.627           |
| Minimum detectable difference (null 95th percentile) | 2.939           |
| 95% bootstrap interval                               | [-1.095, 3.448] |
| Trade retention                                      | 30.7%           |
| Below 30% floor                                      | no              |
| Candidate entries / missing state                    | 1,504 / 0       |

**Attribution**

| cell               | entries                | n     | mean return   | median return   | hit rate   |
|:-------------------|:-----------------------|:------|:--------------|:----------------|:-----------|
| gate/CSM/score_exo | kept                   | 461   | 1.13%         | 0.22%           | 51.2%      |
| gate/CSM/score_exo | removed (all)          | 1,043 | 0.00%         | -0.12%          | 49.0%      |
| gate/CSM/score_exo | removed: missing state | 0     | n/a           | n/a             | n/a        |

## 8. All filtered cells

### H1: gate

**Inference**

| cell                    | Sharpe filt.   | Sharpe unfilt.   | ΔSharpe   | p (perm)   | p (BH)   | 95% CI (bootstrap)   | null mean   | MDD (null p95)   | retention   | below 30% floor   | missing state   |
|:------------------------|:---------------|:-----------------|:----------|:-----------|:---------|:---------------------|:------------|:-----------------|:------------|:------------------|:----------------|
| gate/CSM/score_exo      | 2.89           | 2.05             | 0.84      | 0.854      | 1.000    | [-1.10, 3.45]        | 1.63        | 2.94             | 30.7%       | no                | 0.0%            |
| gate/CSM/composite †    | 2.41           | 2.05             | 0.35      | 0.983      | 1.000    | [-1.38, 3.72]        | 2.35        | 3.81             | 28.7%       | yes               | 0.0%            |
| gate/CSM/narrative      | 2.19           | 2.05             | 0.14      | 0.977      | 1.000    | [-2.04, 2.10]        | 1.71        | 3.02             | 36.2%       | no                | 3.7%            |
| gate/CSM/influencer     | 3.42           | 2.05             | 1.37      | 0.528      | 1.000    | [-0.19, 3.72]        | 1.42        | 2.67             | 32.1%       | no                | 0.0%            |
| gate/CSM/macro          | 2.96           | 2.05             | 0.91      | 0.206      | 1.000    | [-4.26, 5.02]        | 0.08        | 1.70             | 35.4%       | no                | 0.0%            |
| gate/STR/score_exo      | 2.73           | 2.61             | 0.12      | 0.863      | 1.000    | [-0.09, 0.35]        | 0.22        | 0.35             | 94.7%       | no                | 0.0%            |
| gate/STR/composite †    | 2.85           | 2.61             | 0.24      | 0.456      | 1.000    | [0.01, 0.47]         | 0.23        | 0.36             | 92.9%       | no                | 0.0%            |
| gate/STR/narrative      | 2.62           | 2.61             | 0.01      | 1.000      | 1.000    | [-0.31, 0.46]        | 0.45        | 0.67             | 83.4%       | no                | 1.8%            |
| gate/STR/influencer     | 2.88           | 2.61             | 0.27      | 0.095      | 1.000    | [-0.29, 0.77]        | 0.11        | 0.31             | 87.3%       | no                | 0.0%            |
| gate/STR/macro          | 1.57           | 2.61             | -1.04     | 1.000      | 1.000    | [-2.47, 0.25]        | 0.03        | 0.28             | 77.8%       | no                | 0.0%            |
| gate/TSMOM/score_exo    | 2.72           | 2.27             | 0.46      | 0.667      | 1.000    | [-0.95, 2.22]        | 0.64        | 1.33             | 42.8%       | no                | 0.0%            |
| gate/TSMOM/composite †  | 2.45           | 2.27             | 0.19      | 0.991      | 1.000    | [-1.44, 2.30]        | 1.49        | 2.26             | 37.5%       | no                | 0.0%            |
| gate/TSMOM/narrative    | 2.10           | 2.27             | -0.17     | 0.990      | 1.000    | [-1.67, 1.20]        | 0.93        | 1.60             | 43.4%       | no                | 3.1%            |
| gate/TSMOM/influencer   | 3.08           | 2.27             | 0.81      | 0.070      | 1.000    | [-0.26, 2.56]        | 0.18        | 0.89             | 41.4%       | no                | 0.0%            |
| gate/TSMOM/macro        | 2.79           | 2.27             | 0.53      | 0.106      | 1.000    | [-0.56, 1.54]        | -0.17       | 0.79             | 61.7%       | no                | 0.0%            |
| gate/BRK/score_exo      | 3.43           | 3.42             | 0.01      | 0.776      | 1.000    | [-1.01, 1.45]        | 0.46        | 1.45             | 64.7%       | no                | 0.0%            |
| gate/BRK/composite †    | 3.36           | 3.42             | -0.06     | 0.901      | 1.000    | [-0.83, 1.08]        | 0.85        | 1.98             | 73.4%       | no                | 0.0%            |
| gate/BRK/narrative      | 3.31           | 3.42             | -0.11     | 0.750      | 1.000    | [-1.07, 1.29]        | 0.28        | 1.19             | 70.0%       | no                | 1.4%            |
| gate/BRK/influencer     | 4.55           | 3.42             | 1.13      | 0.118      | 1.000    | [-0.26, 2.98]        | 0.40        | 1.39             | 44.0%       | no                | 0.0%            |
| gate/BRK/macro          | 4.11           | 3.42             | 0.69      | 0.088      | 1.000    | [-0.79, 2.37]        | -0.36       | 0.85             | 63.8%       | no                | 0.0%            |
| gate/RSI-MR/score_exo   | 1.98           | 0.96             | 1.02      | 0.501      | 1.000    | [-1.46, 2.94]        | 1.07        | 2.88             | 32.5%       | no                | 0.0%            |
| gate/RSI-MR/composite † | -3.95          | 0.96             | -4.91     | 1.000      | 1.000    | [-7.97, -1.27]       | 1.51        | 3.92             | 6.8%        | yes               | 0.0%            |
| gate/RSI-MR/narrative   | 3.62           | 0.96             | 2.66      | 0.088      | 1.000    | [-0.32, 5.35]        | 1.20        | 2.93             | 27.4%       | yes               | 2.6%            |
| gate/RSI-MR/influencer  | 2.55           | 0.96             | 1.60      | 0.116      | 1.000    | [-0.11, 3.41]        | 0.48        | 1.97             | 47.9%       | no                | 0.0%            |
| gate/RSI-MR/macro       | 1.06           | 0.96             | 0.11      | 0.486      | 1.000    | [-1.85, 2.81]        | 0.04        | 1.42             | 59.0%       | no                | 0.0%            |

**Performance**

| cell                    | variant   | Sharpe   | profit factor   | max DD   | hit rate   | trades   | long / short   | turnover/day   | avg gross   | avg net   | beta   | sessions   |
|:------------------------|:----------|:---------|:----------------|:---------|:-----------|:---------|:---------------|:---------------|:------------|:----------|:-------|:-----------|
| gate/CSM/score_exo      | filtered  | 2.89     | 1.44            | 1.90%    | 51.2%      | 461      | 415 / 46       | 0.082          | 0.306       | 0.245     | 0.29   | 38         |
| gate/CSM/composite †    | filtered  | 2.41     | 1.37            | 2.35%    | 50.5%      | 432      | 376 / 56       | 0.085          | 0.287       | 0.212     | 0.22   | 38         |
| gate/CSM/narrative      | filtered  | 2.19     | 1.30            | 1.99%    | 51.4%      | 545      | 442 / 103      | 0.100          | 0.363       | 0.225     | 0.30   | 38         |
| gate/CSM/influencer     | filtered  | 3.42     | 1.48            | 1.79%    | 52.0%      | 483      | 363 / 120      | 0.082          | 0.319       | 0.162     | 0.19   | 38         |
| gate/CSM/macro          | filtered  | 2.96     | 1.45            | 1.71%    | 48.8%      | 533      | 456 / 77       | 0.091          | 0.358       | 0.249     | 0.23   | 38         |
| gate/STR/score_exo      | filtered  | 2.73     | 1.46            | 3.30%    | 52.5%      | 3,381    | 3,381 / 0      | 0.326          | 0.902       | 0.902     | 1.13   | 38         |
| gate/STR/composite †    | filtered  | 2.85     | 1.49            | 3.18%    | 52.7%      | 3,317    | 3,317 / 0      | 0.324          | 0.885       | 0.885     | 1.11   | 38         |
| gate/STR/narrative      | filtered  | 2.62     | 1.44            | 2.97%    | 52.0%      | 2,980    | 2,980 / 0      | 0.293          | 0.797       | 0.797     | 0.98   | 38         |
| gate/STR/influencer     | filtered  | 2.88     | 1.51            | 3.10%    | 53.2%      | 3,120    | 3,120 / 0      | 0.303          | 0.834       | 0.834     | 1.03   | 38         |
| gate/STR/macro          | filtered  | 1.57     | 1.24            | 3.40%    | 50.3%      | 2,780    | 2,780 / 0      | 0.275          | 0.733       | 0.733     | 0.84   | 38         |
| gate/TSMOM/score_exo    | filtered  | 2.72     | 2.01            | 1.12%    | 38.6%      | 345      | 345 / 0        | 0.039          | 0.242       | 0.242     | 0.25   | 38         |
| gate/TSMOM/composite †  | filtered  | 2.45     | 1.97            | 1.22%    | 37.3%      | 303      | 303 / 0        | 0.034          | 0.227       | 0.227     | 0.24   | 38         |
| gate/TSMOM/narrative    | filtered  | 2.10     | 1.69            | 0.79%    | 39.7%      | 350      | 350 / 0        | 0.039          | 0.218       | 0.218     | 0.21   | 38         |
| gate/TSMOM/influencer   | filtered  | 3.08     | 2.34            | 1.27%    | 40.4%      | 334      | 334 / 0        | 0.038          | 0.222       | 0.222     | 0.26   | 38         |
| gate/TSMOM/macro        | filtered  | 2.79     | 1.98            | 1.51%    | 35.3%      | 498      | 498 / 0        | 0.056          | 0.410       | 0.410     | 0.37   | 38         |
| gate/BRK/score_exo      | filtered  | 3.43     | 2.92            | 0.58%    | 53.0%      | 134      | 134 / 0        | 0.015          | 0.120       | 0.120     | 0.10   | 38         |
| gate/BRK/composite †    | filtered  | 3.36     | 2.69            | 0.76%    | 50.7%      | 152      | 152 / 0        | 0.017          | 0.137       | 0.137     | 0.13   | 38         |
| gate/BRK/narrative      | filtered  | 3.31     | 2.66            | 0.66%    | 51.0%      | 145      | 145 / 0        | 0.016          | 0.126       | 0.126     | 0.11   | 38         |
| gate/BRK/influencer     | filtered  | 4.55     | 3.59            | 0.32%    | 53.8%      | 91       | 91 / 0         | 0.010          | 0.080       | 0.080     | 0.07   | 38         |
| gate/BRK/macro          | filtered  | 4.11     | 3.63            | 0.57%    | 56.1%      | 132      | 132 / 0        | 0.015          | 0.132       | 0.132     | 0.09   | 38         |
| gate/RSI-MR/score_exo   | filtered  | 1.98     | 1.72            | 0.14%    | 68.4%      | 38       | 38 / 0         | 0.004          | 0.028       | 0.028     | 0.02   | 38         |
| gate/RSI-MR/composite † | filtered  | -3.95    | 0.16            | 0.08%    | 37.5%      | 8        | 8 / 0          | 0.001          | 0.007       | 0.007     | 0.00   | 38         |
| gate/RSI-MR/narrative   | filtered  | 3.62     | 2.53            | 0.10%    | 75.0%      | 32       | 32 / 0         | 0.004          | 0.022       | 0.022     | 0.02   | 38         |
| gate/RSI-MR/influencer  | filtered  | 2.55     | 2.09            | 0.14%    | 66.1%      | 56       | 56 / 0         | 0.006          | 0.039       | 0.039     | 0.04   | 38         |
| gate/RSI-MR/macro       | filtered  | 1.06     | 1.42            | 0.37%    | 62.3%      | 69       | 69 / 0         | 0.008          | 0.059       | 0.059     | 0.05   | 38         |

**Attribution: unfiltered standalone net returns of entries kept and removed**

| cell                    | entries                | n     | mean return   | median return   | hit rate   |
|:------------------------|:-----------------------|:------|:--------------|:----------------|:-----------|
| gate/CSM/score_exo      | kept                   | 461   | 1.13%         | 0.22%           | 51.2%      |
| gate/CSM/score_exo      | removed (all)          | 1,043 | 0.00%         | -0.12%          | 49.0%      |
| gate/CSM/score_exo      | removed: missing state | 0     | n/a           | n/a             | n/a        |
| gate/CSM/composite †    | kept                   | 432   | 1.00%         | 0.17%           | 50.5%      |
| gate/CSM/composite †    | removed (all)          | 1,072 | 0.08%         | -0.08%          | 49.3%      |
| gate/CSM/composite †    | removed: missing state | 0     | n/a           | n/a             | n/a        |
| gate/CSM/narrative      | kept                   | 545   | 0.79%         | 0.20%           | 51.4%      |
| gate/CSM/narrative      | removed (all)          | 959   | 0.10%         | -0.17%          | 48.7%      |
| gate/CSM/narrative      | removed: missing state | 56    | 0.52%         | 0.25%           | 51.8%      |
| gate/CSM/influencer     | kept                   | 483   | 1.17%         | 0.31%           | 52.0%      |
| gate/CSM/influencer     | removed (all)          | 1,021 | -0.04%        | -0.18%          | 48.6%      |
| gate/CSM/influencer     | removed: missing state | 0     | n/a           | n/a             | n/a        |
| gate/CSM/macro          | kept                   | 533   | 1.03%         | -0.23%          | 48.8%      |
| gate/CSM/macro          | removed (all)          | 971   | -0.03%        | 0.04%           | 50.2%      |
| gate/CSM/macro          | removed: missing state | 0     | n/a           | n/a             | n/a        |
| gate/STR/score_exo      | kept                   | 3,381 | 0.90%         | 0.36%           | 52.5%      |
| gate/STR/score_exo      | removed (all)          | 191   | 0.17%         | 0.61%           | 52.9%      |
| gate/STR/score_exo      | removed: missing state | 0     | n/a           | n/a             | n/a        |
| gate/STR/composite †    | kept                   | 3,317 | 0.94%         | 0.38%           | 52.7%      |
| gate/STR/composite †    | removed (all)          | 255   | -0.22%        | 0.07%           | 51.0%      |
| gate/STR/composite †    | removed: missing state | 0     | n/a           | n/a             | n/a        |
| gate/STR/narrative      | kept                   | 2,980 | 0.85%         | 0.27%           | 52.0%      |
| gate/STR/narrative      | removed (all)          | 592   | 0.87%         | 0.84%           | 55.4%      |
| gate/STR/narrative      | removed: missing state | 66    | 0.53%         | 0.32%           | 51.5%      |
| gate/STR/influencer     | kept                   | 3,120 | 0.95%         | 0.43%           | 53.2%      |
| gate/STR/influencer     | removed (all)          | 452   | 0.20%         | -0.26%          | 48.0%      |
| gate/STR/influencer     | removed: missing state | 0     | n/a           | n/a             | n/a        |
| gate/STR/macro          | kept                   | 2,780 | 0.49%         | 0.02%           | 50.3%      |
| gate/STR/macro          | removed (all)          | 792   | 2.15%         | 1.46%           | 60.6%      |
| gate/STR/macro          | removed: missing state | 0     | n/a           | n/a             | n/a        |
| gate/TSMOM/score_exo    | kept                   | 345   | 2.30%         | -1.17%          | 38.6%      |
| gate/TSMOM/score_exo    | removed (all)          | 462   | 1.16%         | -1.09%          | 38.5%      |
| gate/TSMOM/score_exo    | removed: missing state | 0     | n/a           | n/a             | n/a        |
| gate/TSMOM/composite †  | kept                   | 303   | 2.39%         | -1.30%          | 37.3%      |
| gate/TSMOM/composite †  | removed (all)          | 504   | 1.20%         | -1.03%          | 39.3%      |
| gate/TSMOM/composite †  | removed: missing state | 0     | n/a           | n/a             | n/a        |
| gate/TSMOM/narrative    | kept                   | 350   | 1.37%         | -0.96%          | 39.7%      |
| gate/TSMOM/narrative    | removed (all)          | 457   | 1.86%         | -1.22%          | 37.6%      |
| gate/TSMOM/narrative    | removed: missing state | 25    | -2.65%        | -1.27%          | 32.0%      |
| gate/TSMOM/influencer   | kept                   | 334   | 2.94%         | -0.99%          | 40.4%      |
| gate/TSMOM/influencer   | removed (all)          | 473   | 0.73%         | -1.22%          | 37.2%      |
| gate/TSMOM/influencer   | removed: missing state | 0     | n/a           | n/a             | n/a        |
| gate/TSMOM/macro        | kept                   | 498   | 2.55%         | -1.42%          | 35.3%      |
| gate/TSMOM/macro        | removed (all)          | 309   | 0.20%         | -0.76%          | 43.7%      |
| gate/TSMOM/macro        | removed: missing state | 0     | n/a           | n/a             | n/a        |
| gate/BRK/score_exo      | kept                   | 134   | 4.47%         | 0.23%           | 53.0%      |
| gate/BRK/score_exo      | removed (all)          | 73    | 3.18%         | 0.69%           | 52.1%      |
| gate/BRK/score_exo      | removed: missing state | 0     | n/a           | n/a             | n/a        |
| gate/BRK/composite †    | kept                   | 152   | 4.43%         | 0.13%           | 50.7%      |
| gate/BRK/composite †    | removed (all)          | 55    | 2.88%         | 0.92%           | 58.2%      |
| gate/BRK/composite †    | removed: missing state | 0     | n/a           | n/a             | n/a        |
| gate/BRK/narrative      | kept                   | 145   | 3.94%         | 0.21%           | 51.0%      |
| gate/BRK/narrative      | removed (all)          | 62    | 4.19%         | 0.86%           | 56.5%      |
| gate/BRK/narrative      | removed: missing state | 3     | -8.76%        | 0.26%           | 66.7%      |
| gate/BRK/influencer     | kept                   | 91    | 5.87%         | 0.38%           | 53.8%      |
| gate/BRK/influencer     | removed (all)          | 116   | 2.57%         | 0.23%           | 51.7%      |
| gate/BRK/influencer     | removed: missing state | 0     | n/a           | n/a             | n/a        |
| gate/BRK/macro          | kept                   | 132   | 5.82%         | 0.74%           | 56.1%      |
| gate/BRK/macro          | removed (all)          | 75    | 0.85%         | -0.38%          | 46.7%      |
| gate/BRK/macro          | removed: missing state | 0     | n/a           | n/a             | n/a        |
| gate/RSI-MR/score_exo   | kept                   | 38    | 1.62%         | 2.62%           | 68.4%      |
| gate/RSI-MR/score_exo   | removed (all)          | 79    | 0.38%         | 0.63%           | 51.9%      |
| gate/RSI-MR/score_exo   | removed: missing state | 0     | n/a           | n/a             | n/a        |
| gate/RSI-MR/composite † | kept                   | 8     | -4.29%        | -1.91%          | 37.5%      |
| gate/RSI-MR/composite † | removed (all)          | 109   | 1.16%         | 2.02%           | 58.7%      |
| gate/RSI-MR/composite † | removed: missing state | 0     | n/a           | n/a             | n/a        |
| gate/RSI-MR/narrative   | kept                   | 32    | 2.70%         | 4.21%           | 75.0%      |
| gate/RSI-MR/narrative   | removed (all)          | 85    | 0.06%         | 0.12%           | 50.6%      |
| gate/RSI-MR/narrative   | removed: missing state | 3     | -0.99%        | -0.83%          | 33.3%      |
| gate/RSI-MR/influencer  | kept                   | 56    | 2.13%         | 2.98%           | 66.1%      |
| gate/RSI-MR/influencer  | removed (all)          | 61    | -0.45%        | -0.34%          | 49.2%      |
| gate/RSI-MR/influencer  | removed: missing state | 0     | n/a           | n/a             | n/a        |
| gate/RSI-MR/macro       | kept                   | 69    | 1.19%         | 2.97%           | 62.3%      |
| gate/RSI-MR/macro       | removed (all)          | 48    | 0.21%         | -0.07%          | 50.0%      |
| gate/RSI-MR/macro       | removed: missing state | 0     | n/a           | n/a             | n/a        |

### H2: size

**Inference**

| cell                    | Sharpe filt.   | Sharpe unfilt.   | ΔSharpe   | p (perm)   | p (BH)   | 95% CI (bootstrap)   | null mean   | MDD (null p95)   | retention   | below 30% floor   | missing state   |
|:------------------------|:---------------|:-----------------|:----------|:-----------|:---------|:---------------------|:------------|:-----------------|:------------|:------------------|:----------------|
| size/CSM/score_exo      | 3.48           | 2.05             | 1.43      | 0.464      | 1.000    | [-0.94, 3.77]        | 1.37        | 2.20             | 57.0%       | no                | 0.0%            |
| size/CSM/composite †    | 3.15           | 2.05             | 1.10      | 0.965      | 1.000    | [-0.63, 3.08]        | 2.09        | 2.99             | 63.6%       | no                | 0.0%            |
| size/CSM/narrative      | 3.10           | 2.05             | 1.05      | 0.796      | 1.000    | [-0.62, 2.54]        | 1.55        | 2.63             | 57.8%       | no                | 3.7%            |
| size/CSM/influencer     | 3.87           | 2.05             | 1.82      | 0.133      | 1.000    | [0.28, 3.34]         | 1.14        | 2.15             | 51.1%       | no                | 0.0%            |
| size/CSM/macro          | 2.61           | 2.05             | 0.56      | 0.382      | 1.000    | [-4.76, 5.93]        | 0.30        | 1.68             | 53.1%       | no                | 0.0%            |
| size/STR/score_exo      | 2.85           | 2.61             | 0.25      | 0.975      | 1.000    | [-0.24, 0.82]        | 0.48        | 0.69             | 95.1%       | no                | 0.0%            |
| size/STR/composite †    | 2.89           | 2.61             | 0.29      | 1.000      | 1.000    | [-0.44, 0.92]        | 0.76        | 0.97             | 92.9%       | no                | 0.0%            |
| size/STR/narrative      | 2.79           | 2.61             | 0.18      | 1.000      | 1.000    | [-0.37, 0.69]        | 0.83        | 1.08             | 84.4%       | no                | 1.8%            |
| size/STR/influencer     | 2.71           | 2.61             | 0.11      | 0.522      | 1.000    | [-0.52, 0.83]        | 0.12        | 0.36             | 87.9%       | no                | 0.0%            |
| size/STR/macro          | 2.88           | 2.61             | 0.27      | 0.096      | 1.000    | [-0.73, 1.27]        | 0.01        | 0.32             | 78.1%       | no                | 0.0%            |
| size/TSMOM/score_exo    | 2.59           | 2.27             | 0.33      | 0.614      | 1.000    | [-0.72, 1.61]        | 0.40        | 0.88             | 84.5%       | no                | 0.0%            |
| size/TSMOM/composite †  | 2.35           | 2.27             | 0.08      | 0.998      | 1.000    | [-1.04, 1.48]        | 1.10        | 1.60             | 87.4%       | no                | 0.0%            |
| size/TSMOM/narrative    | 2.77           | 2.27             | 0.50      | 0.769      | 1.000    | [-0.55, 1.46]        | 0.76        | 1.34             | 82.4%       | no                | 3.1%            |
| size/TSMOM/influencer   | 2.63           | 2.27             | 0.36      | 0.148      | 1.000    | [-0.74, 1.67]        | -0.02       | 0.56             | 69.6%       | no                | 0.0%            |
| size/TSMOM/macro        | 2.15           | 2.27             | -0.12     | 0.561      | 1.000    | [-0.88, 0.85]        | -0.06       | 0.80             | 73.0%       | no                | 0.0%            |
| size/BRK/score_exo      | 3.58           | 3.42             | 0.15      | 0.651      | 1.000    | [-0.46, 1.07]        | 0.29        | 0.93             | 94.7%       | no                | 0.0%            |
| size/BRK/composite †    | 3.51           | 3.42             | 0.09      | 0.944      | 1.000    | [-0.37, 0.67]        | 0.77        | 1.42             | 97.6%       | no                | 0.0%            |
| size/BRK/narrative      | 3.63           | 3.42             | 0.21      | 0.564      | 1.000    | [-0.38, 1.06]        | 0.28        | 1.04             | 93.7%       | no                | 1.4%            |
| size/BRK/influencer     | 3.95           | 3.42             | 0.53      | 0.302      | 1.000    | [-0.45, 2.00]        | 0.27        | 1.08             | 72.5%       | no                | 0.0%            |
| size/BRK/macro          | 3.48           | 3.42             | 0.06      | 0.365      | 1.000    | [-0.45, 0.64]        | -0.19       | 0.86             | 78.3%       | no                | 0.0%            |
| size/RSI-MR/score_exo   | 2.07           | 0.96             | 1.11      | 0.430      | 1.000    | [-0.41, 2.66]        | 1.01        | 2.16             | 71.8%       | no                | 0.0%            |
| size/RSI-MR/composite † | 1.07           | 0.96             | 0.12      | 0.952      | 1.000    | [-2.28, 2.23]        | 1.42        | 2.80             | 39.3%       | no                | 0.0%            |
| size/RSI-MR/narrative   | 2.37           | 0.96             | 1.41      | 0.358      | 1.000    | [-0.35, 3.47]        | 1.13        | 2.46             | 55.6%       | no                | 2.6%            |
| size/RSI-MR/influencer  | 1.52           | 0.96             | 0.56      | 0.446      | 1.000    | [-0.73, 1.70]        | 0.51        | 1.73             | 70.9%       | no                | 0.0%            |
| size/RSI-MR/macro       | 0.63           | 0.96             | -0.33     | 0.617      | 1.000    | [-1.39, 0.73]        | -0.10       | 1.10             | 73.5%       | no                | 0.0%            |

**Performance**

| cell                    | variant   | Sharpe   | profit factor   | max DD   | hit rate   | trades   | long / short   | turnover/day   | avg gross   | avg net   | beta   | sessions   |
|:------------------------|:----------|:---------|:----------------|:---------|:-----------|:---------|:---------------|:---------------|:------------|:----------|:-------|:-----------|
| size/CSM/score_exo      | filtered  | 3.48     | 1.51            | 4.92%    | 50.9%      | 857      | 679 / 178      | 0.252          | 1.005       | 0.758     | 0.89   | 38         |
| size/CSM/composite †    | filtered  | 3.15     | 1.44            | 5.35%    | 49.4%      | 957      | 683 / 274      | 0.260          | 1.005       | 0.652     | 0.69   | 38         |
| size/CSM/narrative      | filtered  | 3.10     | 1.45            | 4.62%    | 51.5%      | 870      | 657 / 213      | 0.276          | 1.005       | 0.634     | 0.78   | 38         |
| size/CSM/influencer     | filtered  | 3.87     | 1.52            | 4.06%    | 53.2%      | 769      | 529 / 240      | 0.263          | 1.005       | 0.520     | 0.50   | 38         |
| size/CSM/macro          | filtered  | 2.61     | 1.36            | 7.67%    | 47.4%      | 798      | 579 / 219      | 0.267          | 1.005       | 0.564     | 0.61   | 38         |
| size/STR/score_exo      | filtered  | 2.85     | 1.48            | 3.40%    | 52.6%      | 3,397    | 3,397 / 0      | 0.360          | 0.952       | 0.952     | 1.22   | 38         |
| size/STR/composite †    | filtered  | 2.89     | 1.61            | 3.12%    | 52.7%      | 3,317    | 3,317 / 0      | 0.368          | 0.952       | 0.952     | 1.24   | 38         |
| size/STR/narrative      | filtered  | 2.79     | 1.49            | 3.13%    | 51.9%      | 3,016    | 3,016 / 0      | 0.369          | 0.952       | 0.952     | 1.17   | 38         |
| size/STR/influencer     | filtered  | 2.71     | 1.55            | 3.63%    | 53.1%      | 3,139    | 3,139 / 0      | 0.360          | 0.952       | 0.952     | 1.23   | 38         |
| size/STR/macro          | filtered  | 2.88     | 1.04            | 3.40%    | 50.3%      | 2,791    | 2,791 / 0      | 0.415          | 0.952       | 0.952     | 1.29   | 38         |
| size/TSMOM/score_exo    | filtered  | 2.59     | 1.98            | 2.36%    | 38.7%      | 682      | 682 / 0        | 0.096          | 0.533       | 0.533     | 0.56   | 38         |
| size/TSMOM/composite †  | filtered  | 2.35     | 1.90            | 2.52%    | 38.0%      | 705      | 705 / 0        | 0.092          | 0.533       | 0.533     | 0.57   | 38         |
| size/TSMOM/narrative    | filtered  | 2.77     | 2.00            | 1.77%    | 39.2%      | 665      | 665 / 0        | 0.108          | 0.533       | 0.533     | 0.52   | 38         |
| size/TSMOM/influencer   | filtered  | 2.63     | 2.08            | 2.60%    | 39.3%      | 562      | 562 / 0        | 0.102          | 0.533       | 0.533     | 0.61   | 38         |
| size/TSMOM/macro        | filtered  | 2.15     | 1.88            | 2.52%    | 36.0%      | 589      | 589 / 0        | 0.085          | 0.533       | 0.533     | 0.55   | 38         |
| size/BRK/score_exo      | filtered  | 3.58     | 2.70            | 0.85%    | 51.0%      | 196      | 196 / 0        | 0.026          | 0.185       | 0.185     | 0.16   | 38         |
| size/BRK/composite †    | filtered  | 3.51     | 2.72            | 0.87%    | 52.5%      | 202      | 202 / 0        | 0.026          | 0.185       | 0.185     | 0.16   | 38         |
| size/BRK/narrative      | filtered  | 3.63     | 2.80            | 0.83%    | 52.1%      | 194      | 194 / 0        | 0.026          | 0.185       | 0.185     | 0.16   | 38         |
| size/BRK/influencer     | filtered  | 3.95     | 3.00            | 0.90%    | 50.7%      | 150      | 150 / 0        | 0.028          | 0.185       | 0.185     | 0.16   | 38         |
| size/BRK/macro          | filtered  | 3.48     | 2.94            | 0.88%    | 54.9%      | 162      | 162 / 0        | 0.036          | 0.185       | 0.185     | 0.16   | 38         |
| size/RSI-MR/score_exo   | filtered  | 2.07     | 1.85            | 0.32%    | 59.5%      | 84       | 84 / 0         | 0.017          | 0.082       | 0.082     | 0.07   | 38         |
| size/RSI-MR/composite † | filtered  | 1.07     | 1.95            | 0.28%    | 60.9%      | 46       | 46 / 0         | 0.017          | 0.082       | 0.082     | 0.05   | 38         |
| size/RSI-MR/narrative   | filtered  | 2.37     | 1.96            | 0.31%    | 66.2%      | 65       | 65 / 0         | 0.018          | 0.082       | 0.082     | 0.06   | 38         |
| size/RSI-MR/influencer  | filtered  | 1.52     | 1.89            | 0.33%    | 60.2%      | 83       | 83 / 0         | 0.018          | 0.082       | 0.082     | 0.08   | 38         |
| size/RSI-MR/macro       | filtered  | 0.63     | 1.22            | 0.37%    | 58.1%      | 86       | 86 / 0         | 0.018          | 0.082       | 0.082     | 0.07   | 38         |

**Size diagnostics (D22)**

| cell                    | avg eff. N filtered   | avg eff. N unfiltered   | entry days with all multipliers zero   | sessions with sized book empty   |
|:------------------------|:----------------------|:------------------------|:---------------------------------------|:---------------------------------|
| size/CSM/score_exo      | 79.3                  | 187.6                   | 0 of 8                                 | 0                                |
| size/CSM/composite †    | 90.0                  | 187.6                   | 0 of 8                                 | 0                                |
| size/CSM/narrative      | 82.5                  | 187.6                   | 0 of 8                                 | 0                                |
| size/CSM/influencer     | 72.3                  | 187.6                   | 0 of 8                                 | 0                                |
| size/CSM/macro          | 85.6                  | 187.6                   | 0 of 8                                 | 0                                |
| size/STR/score_exo      | 130.2                 | 149.8                   | 0 of 38                                | 0                                |
| size/STR/composite †    | 130.2                 | 149.8                   | 0 of 38                                | 0                                |
| size/STR/narrative      | 123.1                 | 149.8                   | 0 of 38                                | 0                                |
| size/STR/influencer     | 114.0                 | 149.8                   | 0 of 38                                | 0                                |
| size/STR/macro          | 119.1                 | 149.8                   | 0 of 38                                | 0                                |
| size/TSMOM/score_exo    | 162.1                 | 233.0                   | 0 of 38                                | 0                                |
| size/TSMOM/composite †  | 165.7                 | 233.0                   | 0 of 38                                | 0                                |
| size/TSMOM/narrative    | 148.5                 | 233.0                   | 0 of 38                                | 0                                |
| size/TSMOM/influencer   | 123.5                 | 233.0                   | 0 of 38                                | 0                                |
| size/TSMOM/macro        | 180.1                 | 233.0                   | 4 of 38                                | 0                                |
| size/BRK/score_exo      | 65.8                  | 84.4                    | 0 of 37                                | 0                                |
| size/BRK/composite †    | 72.7                  | 84.4                    | 0 of 37                                | 0                                |
| size/BRK/narrative      | 66.4                  | 84.4                    | 0 of 37                                | 0                                |
| size/BRK/influencer     | 47.7                  | 84.4                    | 0 of 37                                | 0                                |
| size/BRK/macro          | 62.1                  | 84.4                    | 7 of 37                                | 0                                |
| size/RSI-MR/score_exo   | 21.3                  | 38.9                    | 2 of 34                                | 0                                |
| size/RSI-MR/composite † | 12.4                  | 38.9                    | 15 of 34                               | 0                                |
| size/RSI-MR/narrative   | 16.1                  | 38.9                    | 7 of 34                                | 0                                |
| size/RSI-MR/influencer  | 22.0                  | 38.9                    | 3 of 34                                | 0                                |
| size/RSI-MR/macro       | 28.6                  | 38.9                    | 8 of 34                                | 0                                |

### H3: veto (four-layer divergence)

**Inference**

| cell          | Sharpe filt.   | Sharpe unfilt.   | ΔSharpe   | p (perm)   | p (BH)   | 95% CI (bootstrap)   | null mean   | MDD (null p95)   | retention   | below 30% floor   | missing state   |
|:--------------|:---------------|:-----------------|:----------|:-----------|:---------|:---------------------|:------------|:-----------------|:------------|:------------------|:----------------|
| veto/CSM †    | 1.67           | 2.05             | -0.38     | 0.714      | 1.000    | [-1.46, 1.64]        | -0.08       | 0.80             | 70.1%       | no                | 0.0%            |
| veto/STR †    | 2.52           | 2.61             | -0.08     | 0.999      | 1.000    | [-1.02, 1.08]        | 0.44        | 0.75             | 63.6%       | no                | 0.0%            |
| veto/TSMOM †  | 1.73           | 2.27             | -0.53     | 0.986      | 1.000    | [-1.70, 0.39]        | 0.16        | 0.59             | 65.1%       | no                | 0.0%            |
| veto/BRK †    | 3.46           | 3.42             | 0.04      | 0.563      | 1.000    | [-0.59, 0.85]        | 0.11        | 0.78             | 75.4%       | no                | 0.0%            |
| veto/RSI-MR † | 1.23           | 0.96             | 0.28      | 0.298      | 1.000    | [-2.41, 3.88]        | -0.08       | 1.04             | 48.7%       | no                | 0.0%            |

**Performance**

| cell          | variant   | Sharpe   | profit factor   | max DD   | hit rate   | trades   | long / short   | turnover/day   | avg gross   | avg net   | beta   | sessions   |
|:--------------|:----------|:---------|:----------------|:---------|:-----------|:---------|:---------------|:---------------|:------------|:----------|:-------|:-----------|
| veto/CSM †    | filtered  | 1.67     | 1.13            | 3.04%    | 50.1%      | 1,055    | 582 / 473      | 0.170          | 0.694       | 0.075     | 0.13   | 38         |
| veto/STR †    | filtered  | 2.52     | 1.42            | 2.99%    | 52.1%      | 2,272    | 2,272 / 0      | 0.230          | 0.594       | 0.594     | 0.74   | 38         |
| veto/TSMOM †  | filtered  | 1.73     | 1.56            | 1.07%    | 38.9%      | 525      | 525 / 0        | 0.059          | 0.292       | 0.292     | 0.36   | 38         |
| veto/BRK †    | filtered  | 3.46     | 2.74            | 0.66%    | 52.6%      | 156      | 156 / 0        | 0.018          | 0.136       | 0.136     | 0.13   | 38         |
| veto/RSI-MR † | filtered  | 1.23     | 1.33            | 0.22%    | 56.1%      | 57       | 57 / 0         | 0.006          | 0.035       | 0.035     | 0.03   | 38         |

### H3 amendment: veto-exo (D21)

**Inference**

| cell            | Sharpe filt.   | Sharpe unfilt.   | ΔSharpe   | p (perm)   | p (BH)   | 95% CI (bootstrap)   | null mean   | MDD (null p95)   | retention   | below 30% floor   | missing state   |
|:----------------|:---------------|:-----------------|:----------|:-----------|:---------|:---------------------|:------------|:-----------------|:------------|:------------------|:----------------|
| veto-exo/CSM    | 1.54           | 2.05             | -0.51     | 0.756      | 1.000    | [-1.14, 0.48]        | -0.20       | 0.58             | 79.4%       | no                | 0.0%            |
| veto-exo/STR    | 2.15           | 2.61             | -0.46     | 1.000      | 1.000    | [-1.16, 0.17]        | 0.22        | 0.49             | 76.1%       | no                | 0.0%            |
| veto-exo/TSMOM  | 1.59           | 2.27             | -0.67     | 0.988      | 1.000    | [-1.76, 0.21]        | 0.03        | 0.44             | 67.4%       | no                | 0.0%            |
| veto-exo/BRK    | 3.59           | 3.42             | 0.16      | 0.367      | 1.000    | [-0.51, 0.99]        | 0.04        | 0.66             | 81.2%       | no                | 0.0%            |
| veto-exo/RSI-MR | 1.26           | 0.96             | 0.30      | 0.279      | 1.000    | [-0.70, 1.61]        | -0.01       | 0.79             | 74.4%       | no                | 0.0%            |

**Performance**

| cell            | variant   | Sharpe   | profit factor   | max DD   | hit rate   | trades   | long / short   | turnover/day   | avg gross   | avg net   | beta   | sessions   |
|:----------------|:----------|:---------|:----------------|:---------|:-----------|:---------|:---------------|:---------------|:------------|:----------|:-------|:-----------|
| veto-exo/CSM    | filtered  | 1.54     | 1.12            | 3.08%    | 50.5%      | 1,194    | 611 / 583      | 0.179          | 0.789       | 0.021     | 0.06   | 38         |
| veto-exo/STR    | filtered  | 2.15     | 1.35            | 3.28%    | 51.8%      | 2,719    | 2,719 / 0      | 0.268          | 0.714       | 0.714     | 0.88   | 38         |
| veto-exo/TSMOM  | filtered  | 1.59     | 1.51            | 1.10%    | 38.4%      | 544      | 544 / 0        | 0.061          | 0.298       | 0.298     | 0.37   | 38         |
| veto-exo/BRK    | filtered  | 3.59     | 2.82            | 0.68%    | 53.0%      | 168      | 168 / 0        | 0.019          | 0.147       | 0.147     | 0.14   | 38         |
| veto-exo/RSI-MR | filtered  | 1.26     | 1.34            | 0.25%    | 56.3%      | 87       | 87 / 0         | 0.010          | 0.059       | 0.059     | 0.05   | 38         |

### Threshold sensitivity (CSM and STR, score_exo)

**Inference**

| cell                          | Sharpe filt.   | Sharpe unfilt.   | ΔSharpe   | p (perm)   | p (BH)   | 95% CI (bootstrap)   | null mean   | MDD (null p95)   | retention   | below 30% floor   | missing state   |
|:------------------------------|:---------------|:-----------------|:----------|:-----------|:---------|:---------------------|:------------|:-----------------|:------------|:------------------|:----------------|
| sens/gate-loose/CSM/score_exo | 2.93           | 2.05             | 0.88      | 0.815      | 1.000    | [-1.53, 3.45]        | 1.39        | 2.28             | 44.9%       | no                | 0.0%            |
| sens/gate-tight/CSM/score_exo | 1.71           | 2.05             | -0.34     | 0.902      | 1.000    | [-2.80, 2.77]        | 1.39        | 3.32             | 16.2%       | yes               | 0.0%            |
| sens/veto-c50/CSM †           | 1.88           | 2.05             | -0.17     | 0.544      | 1.000    | [-1.22, 1.77]        | -0.11       | 0.65             | 77.1%       | no                | 0.0%            |
| sens/veto-c70/CSM †           | 0.74           | 2.05             | -1.32     | 0.957      | 1.000    | [-3.10, 0.79]        | -0.23       | 0.80             | 63.0%       | no                | 0.0%            |
| sens/gate-loose/STR/score_exo | 2.72           | 2.61             | 0.12      | 0.508      | 1.000    | [-0.03, 0.27]        | 0.12        | 0.23             | 97.6%       | no                | 0.0%            |
| sens/gate-tight/STR/score_exo | 2.87           | 2.61             | 0.26      | 0.797      | 1.000    | [-0.10, 0.62]        | 0.35        | 0.53             | 87.2%       | no                | 0.0%            |
| sens/veto-c50/STR †           | 2.31           | 2.61             | -0.30     | 1.000      | 1.000    | [-1.20, 0.89]        | 0.32        | 0.60             | 70.5%       | no                | 0.0%            |
| sens/veto-c70/STR †           | 2.39           | 2.61             | -0.22     | 0.999      | 1.000    | [-1.67, 1.01]        | 0.43        | 0.77             | 57.6%       | no                | 0.0%            |

**Performance**

| cell                          | variant   | Sharpe   | profit factor   | max DD   | hit rate   | trades   | long / short   | turnover/day   | avg gross   | avg net   | beta   | sessions   |
|:------------------------------|:----------|:---------|:----------------|:---------|:-----------|:---------|:---------------|:---------------|:------------|:----------|:-------|:-----------|
| sens/gate-loose/CSM/score_exo | filtered  | 2.93     | 1.40            | 2.56%    | 51.0%      | 676      | 562 / 114      | 0.107          | 0.451       | 0.299     | 0.37   | 38         |
| sens/gate-tight/CSM/score_exo | filtered  | 1.71     | 1.27            | 1.21%    | 49.0%      | 243      | 223 / 20       | 0.050          | 0.162       | 0.135     | 0.17   | 38         |
| sens/veto-c50/CSM †           | filtered  | 1.88     | 1.14            | 3.03%    | 50.0%      | 1,159    | 630 / 529      | 0.190          | 0.767       | 0.070     | 0.15   | 38         |
| sens/veto-c70/CSM †           | filtered  | 0.74     | 1.04            | 3.23%    | 48.7%      | 948      | 533 / 415      | 0.156          | 0.620       | 0.079     | 0.12   | 38         |
| sens/gate-loose/STR/score_exo | filtered  | 2.72     | 1.46            | 3.32%    | 52.6%      | 3,488    | 3,488 / 0      | 0.334          | 0.930       | 0.930     | 1.17   | 38         |
| sens/gate-tight/STR/score_exo | filtered  | 2.87     | 1.49            | 3.07%    | 52.5%      | 3,113    | 3,113 / 0      | 0.305          | 0.832       | 0.832     | 1.02   | 38         |
| sens/veto-c50/STR †           | filtered  | 2.31     | 1.38            | 2.99%    | 51.1%      | 2,519    | 2,519 / 0      | 0.256          | 0.663       | 0.663     | 0.83   | 38         |
| sens/veto-c70/STR †           | filtered  | 2.39     | 1.42            | 2.96%    | 52.5%      | 2,056    | 2,056 / 0      | 0.208          | 0.533       | 0.533     | 0.65   | 38         |

### Exposure robustness (gated-out capital redistributed within the leg)

**Inference**

| cell                                 | Sharpe filt.   | Sharpe unfilt.   | ΔSharpe   | p (perm)   | p (BH)   | 95% CI (bootstrap)   | null mean   | MDD (null p95)   | retention   | below 30% floor   | missing state   |
|:-------------------------------------|:---------------|:-----------------|:----------|:-----------|:---------|:---------------------|:------------|:-----------------|:------------|:------------------|:----------------|
| expo/gate-redistribute/CSM/score_exo | 2.97           | 2.05             | 0.92      | 0.742      | 1.000    | [-0.68, 2.58]        | 1.78        | 3.87             | 30.7%       | no                | 0.0%            |
| expo/gate-redistribute/STR/score_exo | 2.72           | 2.61             | 0.12      | 0.845      | 1.000    | [-0.08, 0.34]        | 0.19        | 0.31             | 94.7%       | no                | 0.0%            |

**Performance**

| cell                                 | variant   | Sharpe   | profit factor   | max DD   | hit rate   | trades   | long / short   | turnover/day   | avg gross   | avg net   | beta   | sessions   |
|:-------------------------------------|:----------|:---------|:----------------|:---------|:-----------|:---------|:---------------|:---------------|:------------|:----------|:-------|:-----------|
| expo/gate-redistribute/CSM/score_exo | filtered  | 2.97     | 1.41            | 3.48%    | 51.2%      | 461      | 415 / 46       | 0.278          | 0.872       | 0.139     | 0.20   | 38         |
| expo/gate-redistribute/STR/score_exo | filtered  | 2.72     | 1.47            | 3.39%    | 52.5%      | 3,381    | 3,381 / 0      | 0.346          | 0.952       | 0.952     | 1.20   | 38         |

**Attribution: unfiltered standalone net returns of entries kept and removed**

| cell                                 | entries                | n     | mean return   | median return   | hit rate   |
|:-------------------------------------|:-----------------------|:------|:--------------|:----------------|:-----------|
| expo/gate-redistribute/CSM/score_exo | kept                   | 461   | 1.13%         | 0.22%           | 51.2%      |
| expo/gate-redistribute/CSM/score_exo | removed (all)          | 1,043 | 0.00%         | -0.12%          | 49.0%      |
| expo/gate-redistribute/CSM/score_exo | removed: missing state | 0     | n/a           | n/a             | n/a        |
| expo/gate-redistribute/STR/score_exo | kept                   | 3,381 | 0.90%         | 0.36%           | 52.5%      |
| expo/gate-redistribute/STR/score_exo | removed (all)          | 191   | 0.17%         | 0.61%           | 52.9%      |
| expo/gate-redistribute/STR/score_exo | removed: missing state | 0     | n/a           | n/a             | n/a        |

### Clean-narrative sub-window (decisions from 12 May 2026; own baseline)

**Inference**

| cell                   | Sharpe filt.   | Sharpe unfilt.   | ΔSharpe   | p (perm)   | p (BH)   | 95% CI (bootstrap)   | null mean   | MDD (null p95)   | retention   | below 30% floor   | missing state   |
|:-----------------------|:---------------|:-----------------|:----------|:-----------|:---------|:---------------------|:------------|:-----------------|:------------|:------------------|:----------------|
| sub/gate/CSM/narrative | 1.30           | 0.01             | 1.29      | 0.854      | 1.000    | [-1.21, 3.84]        | 2.27        | 3.85             | 41.3%       | no                | 2.4%            |
| sub/gate/STR/narrative | 4.42           | 4.19             | 0.23      | 0.584      | 1.000    | [-0.24, 0.69]        | 0.26        | 0.49             | 79.7%       | no                | 1.4%            |

**Performance**

| cell                   | variant    | Sharpe   | profit factor   | max DD   | hit rate   | trades   | long / short   | turnover/day   | avg gross   | avg net   | beta   | sessions   |
|:-----------------------|:-----------|:---------|:----------------|:---------|:-----------|:---------|:---------------|:---------------|:------------|:----------|:-------|:-----------|
| sub/gate/CSM/narrative | filtered   | 1.30     | 1.17            | 2.02%    | 46.6%      | 388      | 310 / 78       | 0.107          | 0.354       | 0.210     | 0.31   | 27         |
| sub/gate/CSM/narrative | unfiltered | 0.01     | 0.97            | 3.12%    | 45.5%      | 940      | 470 / 470      | 0.194          | 0.857       | 0.001     | 0.12   | 27         |
| sub/gate/STR/narrative | filtered   | 4.42     | 1.88            | 2.73%    | 57.4%      | 2,024    | 2,024 / 0      | 0.287          | 0.745       | 0.745     | 0.90   | 27         |
| sub/gate/STR/narrative | unfiltered | 4.19     | 1.82            | 3.53%    | 57.3%      | 2,538    | 2,538 / 0      | 0.351          | 0.933       | 0.933     | 1.15   | 27         |

**Attribution: unfiltered standalone net returns of entries kept and removed**

| cell                   | entries                | n     | mean return   | median return   | hit rate   |
|:-----------------------|:-----------------------|:------|:--------------|:----------------|:-----------|
| sub/gate/CSM/narrative | kept                   | 388   | 0.47%         | -0.36%          | 46.6%      |
| sub/gate/CSM/narrative | removed (all)          | 552   | -0.49%        | -0.56%          | 44.7%      |
| sub/gate/CSM/narrative | removed: missing state | 23    | -0.29%        | 0.33%           | 52.2%      |
| sub/gate/STR/narrative | kept                   | 2,024 | 1.51%         | 0.93%           | 57.4%      |
| sub/gate/STR/narrative | removed (all)          | 514   | 1.15%         | 1.09%           | 57.0%      |
| sub/gate/STR/narrative | removed: missing state | 35    | 0.68%         | 1.46%           | 54.3%      |

## 9. Multiple-comparisons summary

| item                                | value   |
|:------------------------------------|:--------|
| Filtered cells examined             | 72      |
| Raw p < 0.05                        | 0       |
| Raw p < 0.05 and retention >= 30%   | 0       |
| BH-adjusted p < 0.05                | 0       |
| Cells below the 30% retention floor | 4       |
| Smallest raw p                      | 0.0699  |
| Smallest BH-adjusted p              | 1.0000  |

All filtered cells, sorted by raw p-value:

| cell                                 | ΔSharpe   | p (perm)   | p (BH)   | retention   |
|:-------------------------------------|:----------|:-----------|:---------|:------------|
| gate/TSMOM/influencer                | 0.81      | 0.070      | 1.000    | 41.4%       |
| gate/BRK/macro                       | 0.69      | 0.088      | 1.000    | 63.8%       |
| gate/RSI-MR/narrative                | 2.66      | 0.088      | 1.000    | 27.4%       |
| gate/STR/influencer                  | 0.27      | 0.095      | 1.000    | 87.3%       |
| size/STR/macro                       | 0.27      | 0.096      | 1.000    | 78.1%       |
| gate/TSMOM/macro                     | 0.53      | 0.106      | 1.000    | 61.7%       |
| gate/RSI-MR/influencer               | 1.60      | 0.116      | 1.000    | 47.9%       |
| gate/BRK/influencer                  | 1.13      | 0.118      | 1.000    | 44.0%       |
| size/CSM/influencer                  | 1.82      | 0.133      | 1.000    | 51.1%       |
| size/TSMOM/influencer                | 0.36      | 0.148      | 1.000    | 69.6%       |
| gate/CSM/macro                       | 0.91      | 0.206      | 1.000    | 35.4%       |
| veto-exo/RSI-MR                      | 0.30      | 0.279      | 1.000    | 74.4%       |
| veto/RSI-MR †                        | 0.28      | 0.298      | 1.000    | 48.7%       |
| size/BRK/influencer                  | 0.53      | 0.302      | 1.000    | 72.5%       |
| size/RSI-MR/narrative                | 1.41      | 0.358      | 1.000    | 55.6%       |
| size/BRK/macro                       | 0.06      | 0.365      | 1.000    | 78.3%       |
| veto-exo/BRK                         | 0.16      | 0.367      | 1.000    | 81.2%       |
| size/CSM/macro                       | 0.56      | 0.382      | 1.000    | 53.1%       |
| size/RSI-MR/score_exo                | 1.11      | 0.430      | 1.000    | 71.8%       |
| size/RSI-MR/influencer               | 0.56      | 0.446      | 1.000    | 70.9%       |
| gate/STR/composite †                 | 0.24      | 0.456      | 1.000    | 92.9%       |
| size/CSM/score_exo                   | 1.43      | 0.464      | 1.000    | 57.0%       |
| gate/RSI-MR/macro                    | 0.11      | 0.486      | 1.000    | 59.0%       |
| gate/RSI-MR/score_exo                | 1.02      | 0.501      | 1.000    | 32.5%       |
| sens/gate-loose/STR/score_exo        | 0.12      | 0.508      | 1.000    | 97.6%       |
| size/STR/influencer                  | 0.11      | 0.522      | 1.000    | 87.9%       |
| gate/CSM/influencer                  | 1.37      | 0.528      | 1.000    | 32.1%       |
| sens/veto-c50/CSM †                  | -0.17     | 0.544      | 1.000    | 77.1%       |
| size/TSMOM/macro                     | -0.12     | 0.561      | 1.000    | 73.0%       |
| veto/BRK †                           | 0.04      | 0.563      | 1.000    | 75.4%       |
| size/BRK/narrative                   | 0.21      | 0.564      | 1.000    | 93.7%       |
| sub/gate/STR/narrative               | 0.23      | 0.584      | 1.000    | 79.7%       |
| size/TSMOM/score_exo                 | 0.33      | 0.614      | 1.000    | 84.5%       |
| size/RSI-MR/macro                    | -0.33     | 0.617      | 1.000    | 73.5%       |
| size/BRK/score_exo                   | 0.15      | 0.651      | 1.000    | 94.7%       |
| gate/TSMOM/score_exo                 | 0.46      | 0.667      | 1.000    | 42.8%       |
| veto/CSM †                           | -0.38     | 0.714      | 1.000    | 70.1%       |
| expo/gate-redistribute/CSM/score_exo | 0.92      | 0.742      | 1.000    | 30.7%       |
| gate/BRK/narrative                   | -0.11     | 0.750      | 1.000    | 70.0%       |
| veto-exo/CSM                         | -0.51     | 0.756      | 1.000    | 79.4%       |
| size/TSMOM/narrative                 | 0.50      | 0.769      | 1.000    | 82.4%       |
| gate/BRK/score_exo                   | 0.01      | 0.776      | 1.000    | 64.7%       |
| size/CSM/narrative                   | 1.05      | 0.796      | 1.000    | 57.8%       |
| sens/gate-tight/STR/score_exo        | 0.26      | 0.797      | 1.000    | 87.2%       |
| sens/gate-loose/CSM/score_exo        | 0.88      | 0.815      | 1.000    | 44.9%       |
| expo/gate-redistribute/STR/score_exo | 0.12      | 0.845      | 1.000    | 94.7%       |
| gate/CSM/score_exo                   | 0.84      | 0.854      | 1.000    | 30.7%       |
| sub/gate/CSM/narrative               | 1.29      | 0.854      | 1.000    | 41.3%       |
| gate/STR/score_exo                   | 0.12      | 0.863      | 1.000    | 94.7%       |
| gate/BRK/composite †                 | -0.06     | 0.901      | 1.000    | 73.4%       |
| sens/gate-tight/CSM/score_exo        | -0.34     | 0.902      | 1.000    | 16.2%       |
| size/BRK/composite †                 | 0.09      | 0.944      | 1.000    | 97.6%       |
| size/RSI-MR/composite †              | 0.12      | 0.952      | 1.000    | 39.3%       |
| sens/veto-c70/CSM †                  | -1.32     | 0.957      | 1.000    | 63.0%       |
| size/CSM/composite †                 | 1.10      | 0.965      | 1.000    | 63.6%       |
| size/STR/score_exo                   | 0.25      | 0.975      | 1.000    | 95.1%       |
| gate/CSM/narrative                   | 0.14      | 0.977      | 1.000    | 36.2%       |
| gate/CSM/composite †                 | 0.35      | 0.983      | 1.000    | 28.7%       |
| veto/TSMOM †                         | -0.53     | 0.986      | 1.000    | 65.1%       |
| veto-exo/TSMOM                       | -0.67     | 0.988      | 1.000    | 67.4%       |
| gate/TSMOM/narrative                 | -0.17     | 0.990      | 1.000    | 43.4%       |
| gate/TSMOM/composite †               | 0.19      | 0.991      | 1.000    | 37.5%       |
| size/TSMOM/composite †               | 0.08      | 0.998      | 1.000    | 87.4%       |
| veto/STR †                           | -0.08     | 0.999      | 1.000    | 63.6%       |
| sens/veto-c70/STR †                  | -0.22     | 0.999      | 1.000    | 57.6%       |
| gate/STR/narrative                   | 0.01      | 1.000      | 1.000    | 83.4%       |
| gate/STR/macro                       | -1.04     | 1.000      | 1.000    | 77.8%       |
| gate/RSI-MR/composite †              | -4.91     | 1.000      | 1.000    | 6.8%        |
| size/STR/composite †                 | 0.29      | 1.000      | 1.000    | 92.9%       |
| size/STR/narrative                   | 0.18      | 1.000      | 1.000    | 84.4%       |
| sens/veto-c50/STR †                  | -0.30     | 1.000      | 1.000    | 70.5%       |
| veto-exo/STR                         | -0.46     | 1.000      | 1.000    | 76.1%       |

## 10. Ledger summary

| item                | value   |
|:--------------------|:--------|
| Total ledger rows   | 82      |
| Rows with status ok | 82      |
| Failed rows         | 0       |
| Rerun rows          | 5       |

| note                                                                                | rows   |
|:------------------------------------------------------------------------------------|:-------|
| Phase 4                                                                             | 72     |
| Phase 3 baseline                                                                    | 5      |
| rerun: renamed 'Decision days' column to 'Days with entries'; no computation change | 5      |

## 11. Limitations observed

1. **Short window, one regime.** Every cell is evaluated on at most 38 P&L sessions. Over those sessions the equal-weighted used universe returned 3.42% with an annualised Sharpe of 1.92. All five unfiltered baselines have positive Sharpe in this window, and long-only rules carry market beta (section 5).
2. **Low power.** The minimum detectable Sharpe difference (95th percentile of each permutation null) ranges from 0.23 to 3.92 across the filtered cells (median 1.06).
3. **What the permutation null holds fixed.** Shuffling each ticker's states across dates preserves each ticker's state distribution, including the between-ticker component in section 3. The null therefore tests the timing of states within tickers, not the selection of tickers. Null means are reported per cell and are often far from zero. The shuffle also moves the all-missing 24 April row onto decision days (D19), so permuted variants skip some entries for missing state that the observed variant takes.
4. **Gating a long/short strategy changes its net exposure.** CSM is close to market-neutral unfiltered; the CSM gate cells have average net exposure between 0.162 and 0.249, because bullish states are much more common than bearish ones (section 6). Their Sharpe differences mix the effect of sentiment timing with a change in market exposure; the long/short split and average net exposure are reported for every cell.
5. **Market-layer contamination.** The composite and the four-layer divergence contain the market sub-index, which is contaminated in this window; those cells are marked †. `score_exo` is reconstructed, not served, and is unsmoothed, while the composite is a 4-hour EMA (D2, D5).
6. **Irregular scoring ticks early in the window.** On 10 sessions the state did not come from the 21:30 slot because that tick was stamped at or after 21:45; the earliest selected tick on those sessions was stamped 20:03 UTC (section 3).
7. **No replay marker.** The API exposes no flag for rows rebuilt offline, so the research-window rows cannot be verified as live from the API alone (section 2).
8. **Universe and prices.** The used universe excludes seed names delisted inside the window and names without yfinance bars (section 3), a survivorship restriction. Prices come from a single source (yfinance, adjusted) and were not cross-checked against a second source.
9. **Costs.** A flat 10 bp per side on netted traded notional, no borrow cost, no market impact. Trade-level statistics (hit rate, profit factor, attribution) use standalone per-trade returns, which are not netted (D15).
10. **Size filter mechanics.** Few states reach the full-size level (section 6), so under daily gross matching (D14) the size filter acts mostly as a relative re-weighting; effective numbers of positions are reported for every size cell.

