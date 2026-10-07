# Decisions

Interpretive choices and deviations from INSTRUCTIONS.md, in date order. Each entry states the
decision, who made it, and a one-line reason. Nothing here is changed retroactively; a reversal
is a new dated entry.

## 2026-10-06 (Phase 0)

**D0.1 Reach-back probe beyond `days=2`.** One raw-history call for AAPL with `days=166`, made
once in each of the two probe scripts, examined in memory only. *Reason:* the Phase 0 stop
condition (does `raw` reach 24 April?) cannot be tested with `days=2`. Approved by the
researcher before it ran.

## 2026-10-07 (answers to Phase 0 questions; set by the researcher before any data pull)

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
