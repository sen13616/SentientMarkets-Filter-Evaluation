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

## 2026-10-07 (Phase 1 build)

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

## 2026-10-07 (Phase 2 engine; fixed before any real-data backtest)

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
