# Experiment 5A results: does the score follow real-world sentiment? (PILOT)

> **This is a pilot run.** The event period (13 May to 18 June 2026) falls between earnings seasons, so the primary cell holds only 73 events. Before any response was computed, the power estimate showed this run could detect, with 80% power, a response rate of about 47.0% (against a placebo rate of 32.2%) and a signed average move of about 0.32 noise units (2.95 points). Real effects smaller than that would usually be missed, so a null result here is weak evidence of no effect. The definitive run is planned on the October 2026 earnings season with the same code and rules.

**Primary cell (score_exo, E1 and E2 pooled): PASSES.** Response p = 0.025 (met); signed-move p = 0.001 (minimum possible) (met); unexplained-move rate = 32.4% (met).

## 1. The question and the method

The SentientMarkets API publishes a 0 to 100 sentiment score per stock, built from four channels (market, narrative, influencer, macro). This experiment checks whether the score follows real-world sentiment, in two directions:

- **Forward:** after a public event with a known direction, did the score move, and the right way?
- **Backward:** when the score made a large move, was there an event or a large price move behind it?

Events come from public sources (yfinance): earnings releases (E1, direction = sign of the stock's market-adjusted return on the reaction session), large price moves (E2, more than 3 x ATR(14)), analyst upgrades and downgrades (E3) and insider purchases and sales (E4). For each event the score is read just before the market could react and again at the end of the following session. A change counts as a *move* if it exceeds one *noise unit*, the stock's own typical two-session change on quiet days. Significance comes from relabelling: the same number of sessions per stock is drawn at random 1,000 times and measured the same way, so each p-value says how often random dates do as well as the real events.

The primary cell is `score_exo` (the score rebuilt from the narrative, influencer and macro channels, leaving out the market channel, which is computed from price) on earnings and large moves pooled. It passes if (1) the response rate beats relabelling at p < 0.05, (2) the signed average move beats relabelling at p < 0.05, and (3) fewer than half of the score's large moves are unexplained. This rule was amended before any response was computed (DECISIONS.md A6). Everything else is secondary and is reported with Benjamini-Hochberg adjusted p-values. E3 and E4 are plumbing checks: ratings and insider trades feed the `influencer` channel directly.

## 2. Run metadata

- Command: `python -m responsiveness.scripts.run_cells`, then `python -m responsiveness.scripts.render_results`.
- Code commit `5a9097a`; config hash `fb73e84cff27`; data hash `f45f1575e750`; seed 20260512 (one stream per cell, DECISIONS.md M8).
- Run at 2026-10-08T10:56:14+00:00. Relabellings 1000, bootstrap draws 2000, placebo dates per event up to 20.
- Cells: 42 (6 indices x 7 event groups); ledger rows for this run: 43 in `responsiveness/ledger.csv`.
- Data: sentiment ticks and daily prices to 22 June 2026 (data lock); events whose reaction session is from 2026-05-13 to 2026-06-18. Every relabelled value and bootstrap draw is in `results/nulls/`.

## 3. Data and event counts

Event period: reaction sessions from 2026-05-13 to 2026-06-18. Universe: 473 names (the first experiment's used universe). Sources: yfinance (see source_probe.md). Counts only: no score response around any event was computed to produce this file.

Data hash `f45f1575e750`.

### Source coverage

- Tickers fetched: 473 of 473; failed: none.
- Tickers with no rows at all on or before 22 June: earnings 0, ratings 0, insider 2.
- Insider coverage truncated: 1 tickers returned the source's 150-row cap with the oldest row after 2026-05-13, so their insider history does not reach the start of the event period: DELL.

### Events kept, by type and direction

For E4, up = net insider purchase and down = net insider sale; both are also reported as separate cells (DECISIONS.md A2).

|                  |   up |   down |   total |   stocks |
|:-----------------|-----:|-------:|--------:|---------:|
| E1 earnings      |   24 |     28 |      52 |       52 |
| E2 large move    |   12 |      9 |      21 |       20 |
| E3 rating change |   70 |     50 |     120 |       99 |
| E4 insider       |   37 |    510 |     547 |      247 |
| E1+E2 pooled     |   36 |     37 |      73 |       68 |

**Types with fewer than 30 events: E2 large move.**

### Drops and overlaps (candidates with R in the event period)

Columns: `no_time` earnings release without a time of day; `no_direction` zero market-adjusted return (E1) or zero move (E2); `no_window` R-1 or R+1 outside the session list; `e1_reaction_session` an E2 session that is an E1 reaction session for the stock (excluded by definition); `collapsed_into` merged into an earlier overlapping event of the same type and stock (DECISIONS.md A4); `cluster_tie` the earliest member of a same-type cluster whose net direction is zero (cluster dropped); `overlap_Ek` window overlaps a kept higher-ranked event Ek on the same stock. A kept event may stand for a collapsed cluster.

|                  |   candidates |   kept |   e1_reaction_session |   collapsed_into |   cluster_tie |   overlap_E1 |   overlap_E2 |   overlap_E3 |
|:-----------------|-------------:|-------:|----------------------:|-----------------:|--------------:|-------------:|-------------:|-------------:|
| E1 earnings      |           52 |     52 |                     0 |                0 |             0 |            0 |            0 |            0 |
| E2 large move    |           43 |     21 |                    20 |                0 |             0 |            2 |            0 |            0 |
| E3 rating change |          154 |    120 |                     0 |               13 |             2 |           15 |            4 |            0 |
| E4 insider       |          884 |    547 |                     0 |              310 |             0 |           10 |            1 |           16 |

### Same-type clusters (DECISIONS.md A4)

Overlapping same-type events on a stock become one event at the earliest member, with the net direction (E4: signed shares; otherwise majority). 'Clusters reaching past R+1' have members whose reaction session falls after the measured window of the collapsed event.

| type             |   clusters |   events in clusters |   events collapsed |   clusters dropped (tie) |   clusters kept |   largest cluster |   clusters reaching past R+1 |
|:-----------------|-----------:|---------------------:|-------------------:|-------------------------:|----------------:|------------------:|-----------------------------:|
| E1 earnings      |          0 |                    0 |                  0 |                        0 |               0 |                 0 |                            0 |
| E2 large move    |          0 |                    0 |                  0 |                        0 |               0 |                 0 |                            0 |
| E3 rating change |          8 |                   21 |                 13 |                        2 |               2 |                 6 |                            0 |
| E4 insider       |        148 |                  423 |                310 |                        0 |             143 |                11 |                           20 |

### E1 detail

- Releases with R in the period: 52; time of day known: 52; dropped for no time: 0.
- Release times (America/New_York): 06:00 x13, 07:00 x4, 08:00 x1, 16:00 x34.
- Cross-check on kept E1 events: market-adjusted return sign agrees with EPS-surprise sign in 24 of 52 with a nonzero surprise (0 with zero or missing surprise). This cross-check carries no weight (DECISIONS.md A5): nearly every company beat estimates in the period, so the surprise sign hardly varies.

### Overlaps

- Kept events that displaced at least one lower-ranked event: 41.
- Lower-ranked events dropped for overlap, by (kept type -> dropped type): E1 -> E2 2, E1 -> E3 15, E1 -> E4 10, E2 -> E3 4, E2 -> E4 1, E3 -> E4 16.

### Kept events by week of R

| week of (Monday)   |   E1 |   E2 |   E3 |   E4 |
|:-------------------|-----:|-----:|-----:|-----:|
| 2026-05-11         |    3 |    1 |   15 |   83 |
| 2026-05-18         |   16 |    6 |   21 |   97 |
| 2026-05-25         |   16 |    4 |   20 |   78 |
| 2026-06-01         |   10 |    6 |   26 |  118 |
| 2026-06-08         |    6 |    0 |   21 |   94 |
| 2026-06-15         |    1 |    4 |   17 |   77 |

By direction:

| week of (Monday)   |   E1 up |   E1 down |   E2 up |   E2 down |   E3 up |   E3 down |   E4 up |   E4 down |
|:-------------------|--------:|----------:|--------:|----------:|--------:|----------:|--------:|----------:|
| 2026-05-11         |       3 |         0 |       1 |         0 |       7 |         8 |       9 |        74 |
| 2026-05-18         |       7 |         9 |       5 |         1 |      18 |         3 |       9 |        88 |
| 2026-05-25         |       9 |         7 |       2 |         2 |      14 |         6 |       6 |        72 |
| 2026-06-01         |       4 |         6 |       4 |         2 |       9 |        17 |       6 |       112 |
| 2026-06-08         |       1 |         5 |       0 |         0 |      14 |         7 |       5 |        89 |
| 2026-06-15         |       0 |         1 |       0 |         4 |       8 |         9 |       2 |        75 |

Events that would have been kept with R = 12 May, now outside the period (DECISIONS.md A1): 23.

### Events per stock (kept, all types)

- Stocks with at least one kept event: 322 of 473; median 1, max 10.

### Events measured in each cell

An event drops out of an index's cells if its stock has no noise unit for that index, or if the before or after reading is missing.

| group       |   score |   score_exo |   narrative |   influencer |   macro |   market |
|:------------|--------:|------------:|------------:|-------------:|--------:|---------:|
| E1          |      52 |          52 |          52 |           52 |      52 |       52 |
| E2          |      21 |          21 |          20 |           20 |      21 |       21 |
| E1+E2       |      73 |          73 |          72 |           72 |      73 |       73 |
| E3          |     120 |         120 |         119 |          120 |     120 |      120 |
| E4          |     547 |         547 |         534 |          547 |     547 |      547 |
| E4 purchase |      37 |          37 |          37 |           37 |      37 |       37 |
| E4 sale     |     510 |         510 |         497 |          510 |     510 |      510 |

## 4. Decisions in full

Interpretive choices and deviations from BRIEF.md, in date order. Each entry states the
decision and a one-line reason. Nothing is changed retroactively; a reversal is a new dated
entry. Entries marked **OPEN** await the researcher and are not yet in force beyond what is
stated.

#### 2026-10-07 (Phase 0: sources, event construction, counts)

**R0 Data root.** The tick cache and price bars built by the first experiment, and this
experiment's event downloads, live under a local data directory (`data/` at the repository
root by default, or `SM_DATA_DIR`). None of it is committed. *Reason:* public-repository
hygiene (ground rule 8); `SM_DATA_DIR` lets the code run from a separate checkout.

**R1 Earnings time of day.** yfinance scrapes Yahoo's earnings calendar, which prints every
release with a time to the hour (e.g. "4 PM EDT"). A release stamped exactly 00:00 local is
read as having no time. In the event period none is; every release is stamped 06:00, 07:00,
08:00, 16:00 or 17:00 ET. "Before the close" means strictly before the session's scheduled
close (16:00 ET), so a 16:00 stamp reacts the next session. *Reason:* the source has no
separate "time not supplied" marker. Yahoo's hours look like before-open and after-close
labels rather than exact release times, which is enough to fix R.

**R2 Rating dates.** `upgrades_downgrades` carries a timezone-naive GradeDate. Its calendar
date is used as given (R = that date, or the next session). Only actions labelled `up` or
`down` are E3 events; `main`, `reit` and `init` are not. *Reason:* the brief defines R by date
and E3 by the upgrade/downgrade label; the source does not state the timezone.

**R3 Insider transactions.** The source's `Transaction` column is empty, so the kind is read
from the leading word of `Text`: "Purchase…" is a purchase (up) and "Sale…" is a sale (down).
Gifts, awards, option conversions and blank rows are not E4 events. R is `Start Date` (the
transaction date), or the next session. *Reason:* the only field that names the kind; the
brief fixes R to the transaction date.

**R4 Same-type overlaps.** The brief resolves overlaps between different types only. Within
one stock and type, events are taken in time order, and one whose window overlaps an
already-kept event of that type is dropped (`same_type_overlap`). A kept event whose window
holds a same-type event of the opposite direction is dropped too (`same_type_conflict`). Both
are counted. *Reason:* repeated filings (e.g. a run of daily insider sales) would otherwise
count one window several times; opposite-direction events leave the window's direction
undefined.

**R5 Overlapping windows.** An event's window runs from its "before" instant to 21:45 UTC on
R+1. Two windows overlap when these intervals intersect. In sessions this means R one session
apart or less, except that an after-close earnings release also overlaps an event whose R+1
is the release day. *Reason:* the literal reading of "overlapping windows", using the
brief's own before and after.

**R6 E2 construction.** The move is the close-to-close change in adjusted close, in price
units, compared with Wilder's ATR(14) through R−1. ATR is seeded with the simple mean of the
first 14 true ranges from January 2025. "Not an E1 reaction session" means not the R of any
earnings release with a time on that stock, whatever happened to that release later.
*Reason:* the standard ATR definition, with a burn-in long enough that the seed does not
matter.

**R7 E1 direction.** The market-adjusted return is the stock's close-to-close return over R
minus the mean return of the used universe that session (the stock included). A zero
adjusted return or zero E2 move gives direction 0, and the event is dropped (`no_direction`;
none occurred). *Reason:* the brief's definition; a zero has no sign.

**R8 Lookback before 12 May.** The lock is an upper bound (nothing after 22 June 2026). Data
before 12 May is used only as lookback: the 11 May state as the "before" reading for events
with R = 12 May, price bars for ATR, and candidate events from 27 April for the overlap and
noise-session rules. *Reason:* the brief's definitions (R−1, ATR(14)) require it. See OPEN
Q1 on the narrative model change.

**R9 "Any event".** For noise sessions, the unexplained-move rule and overlap screening, an
event is any candidate of the four types with R from 27 April to 22 June 2026, counted
before any drop. That includes events dropped for overlap or conflict, and both possible
sessions of an earnings release with no time. *Reason:* a dropped event still happened.

**R10 States and before readings.** The daily state is the first experiment's: the last tick
stamped on that UTC day before 21:45 UTC, otherwise missing. The "before" reading is the last
tick stamped strictly before the before-instant, on any day, with no staleness limit. Each
index takes its value from that tick; a channel absent in that tick is missing for that
index. *Reason:* the brief's wording for each.

**R11 Noise units.** Sample standard deviation (ddof 1) of the two-session changes on noise
sessions. It is undefined with fewer than two changes or an SD of 0. A stock without a noise
unit for an index contributes no events to that index's cells; such events are counted. See
OPEN Q3. *Reason:* the minimum the formula allows; no threshold was given.

**P1 Power estimate (Phase 0).** The placebo base rate p0 is the share of noise-session
changes larger than one noise unit, pooled over stocks. The relabelling null is simulated by
drawing, for each stock, as many noise sessions as it has kept events (without replacement,
or with replacement if it has fewer noise sessions), 1,000 times. The detectable response
rate is the smallest rate that exceeds the null's 95th percentile with 80% probability,
treating events as independent. *Reason:* follows the brief's "placebo-style changes on
non-event sessions only".

**P2 Detectable direction accuracy.** For M moves, this is the smallest true accuracy giving
80% power to (a) a two-sided exact binomial test at 0.05, and (b) the primary rule (accuracy
≥ 60% and the 95% interval above 50%), with the exact Clopper-Pearson interval standing in
for the bootstrap. M is taken at N × p0 and at N × the detectable response rate. *Reason:*
the number of moves is unknown before outcomes; these bracket it.

**P3 Two-sided binomial test.** The direction p-value is the two-sided exact binomial
p-value against 50%. *Reason:* the conventional default when the brief does not specify.

#### Questions raised at the Phase 0 checkpoint (answered 2026-10-08, below)

**Q1 (answered): events with R = 12 May.** Their "before" reading is the 11 May state, taken under
the earlier narrative text model, and the noise change for d = 12 May also spans 11 May. There
are 25 such events (E1 5, E3 2, E4 18; no E2). Keep the brief as written, or start the event
period at 13 May?

**Q2 (answered): E4 reaction session.** The brief sets R to the transaction date. Insider trades
become public through Form 4 filings up to two business days later, so the market usually
cannot trade on them at R. That conflicts with the definition of R as the first session the
market could trade. The filing date is not in the yfinance table. Keep as written?

**Q3 (answered): minimum noise sessions.** Noise sessions per stock: 4 stocks have 0, 15 have 1–5,
and the median is 22. Noise units built from two to five changes are unreliable. Set a
minimum number of changes (the code currently requires 2), or keep 2?

**Q4 (answered): same-type rule (R4).** Approve R4, which drops 280 E4, 13 E3 and no E1/E2
candidates as same-type overlaps, or choose another rule?

**Q5 (answered): E2 below 30.** E2 has 21 kept events (45 candidates, 22 of them on E1 reaction
sessions). As instructed, no threshold or source is changed. E2 is reported alone with this
caveat and pooled with E1 in the primary cell (78 events).

#### 2026-10-08 (researcher's answers; set before any score response was computed)

**A1 (Q1) Event period starts 13 May.** Every event needs R−1 ≥ 12 May, so reaction sessions
run from 13 May to 18 June 2026. Any noise-unit change that spans 11 to 12 May is dropped (a
change at session d needs d−1 ≥ 12 May). A "before" reading must come from a tick stamped on
or after 12 May (00:00 UTC); otherwise the event has no before reading for that index and is
counted. Placebo and relabelled sessions follow the same rule. *Reason (researcher):* the
narrative model changed on 12 May, so a before/after pair across that date measures the model
switch, not the event.

**A2 (Q2) E4 reaction session stays the transaction date.** The filing lag (up to two
business days) is recorded as a limitation. Insider purchases and sales are reported
separately as well as together (cells `E4`, `E4 purchase`, `E4 sale`). *Reason
(researcher):* keep the brief as written, and make the asymmetry between purchases and sales
visible.

**A3 (Q3) Noise units need at least 10 non-event sessions.** A stock with fewer than 10
defined two-session changes on noise sessions for an index has no noise unit for that index.
Its events are excluded from that index's cells and counted. Noise and placebo sessions
exclude windows around E1, E2 and E3 candidates only, not E4. Results report how many
placebo sessions fall within an E4 window, meaning the placebo's window (R5) overlaps the
window of an E4 candidate on the same stock. Replaces R11's minimum of 2. *Reason
(researcher):* insider filings are so frequent that excluding them leaves too few clean
sessions.

**A4 (Q4) Overlapping same-type events are collapsed, not dropped.** Within one stock and
type, events whose windows overlap, directly or through a chain of overlaps, form one
cluster. The cluster becomes a single event at its earliest member: its R, its window and
its event time. Its direction is:
- **E4:** the sign of the net signed shares (purchases +, sales −);
- **E3:** the majority of upgrades and downgrades;
- **E1 and E2:** the majority as well (the researcher did not specify; neither type had a
  same-type overlap in Phase 0).

A cluster that nets to zero or ties is dropped. Results report how many events were
collapsed and how many clusters were dropped. Replaces R4. *Reason (researcher):* repeated
filings are one event, and their net says which way it points.

**A5 EPS cross-check carries no weight.** It is reported, with a note that nearly every
company beat estimates in the period, so the surprise sign hardly varies. *Reason
(researcher):* 55 of 57 surprises were positive.

**A6 Primary rule amended on power grounds (no outcomes seen).** The primary cell
(`score_exo`, E1+E2 pooled) passes if all three hold:
1. response p < 0.05 (section 6, test 1);
2. signed-average-move p < 0.05 (section 6, test 3), which uses every event, not only those
   that moved;
3. an unexplained-move rate below 50%.

Direction accuracy and its interval are still reported but are no longer a pass condition.
The power estimate is recomputed for the amended rule. Replaces the primary rule of BRIEF.md
section 6. *Reason (researcher):* the direction criterion used only the events that moved,
and Phase 0 showed it could detect only accuracies of about 72–77%.

**A7 This run is a pilot.** RESULTS.md labels it a pilot, states its power plainly, and says
the definitive run is planned on the October 2026 earnings season with the same code and
rules. *Reason (researcher):* the May–June window holds few earnings events.

#### 2026-10-08 (Phase 1 choices that follow from A1–A7 or that the brief leaves open)

**M1 Event measurement.** Change = after − before, in index points. Before is the reading
under R10 and A1; after is the daily state of R+1. An event with either reading missing for
an index is excluded from that index's cells and counted. *Reason:* the brief's definition.

**M2 Scorecard rates are shares of all measured events.**
- Response rate: moves ÷ events.
- Wrong-way rate: moves against the event's direction ÷ events.
- Miss rate: 1 − response rate.
- Direction accuracy: moves in the event's direction ÷ moves.

A change of exactly zero is never a move. *Reason:* response = right-way + wrong-way, and
miss is the rest, so the three rates add to 1.

**M3 Relabelling (tests 1 and 3).**
- **Sessions drawn:** for each stock, as many sessions as it has events in the cell, without
  replacement, from its eligible sessions. Eligible sessions are event-period sessions whose
  date-only change is defined for the index; this includes the stock's own event sessions,
  so the observed labelling is one of the possible ones. A stock with fewer eligible sessions
  than events draws with replacement.
- **Change at a relabelled session:** measured date-only. Before is the last tick before
  21:45 UTC on d−1, stamped on or after 12 May; after is the state of d+1.
- **Test 3 directions:** the cell's directions are permuted across all its events, which
  keeps the up/down mix.
- **p-values:** 1,000 draws with fixed seed 20260512; p = (1 + #draws ≥ observed) / 1001,
  one-sided upward.

*Reason:* the brief's tests. Measuring every relabelled date the same way keeps the null
comparable, and keeping the up/down mix keeps any common drift in the score inside the null.

**M4 Bootstrap over event dates.** The bootstrap resamples the cell's distinct reaction
dates with replacement, 2,000 times, and takes every event on each drawn date. The 95%
interval is the 2.5th to 97.5th percentile. The same draws also give intervals for the
response rate and the signed average move. A draw with no moves is skipped when computing
accuracy. *Reason:* events on the same date share market-wide news, so dates are the
independent unit.

**M5 Placebo dates.** For each event, up to 20 sessions are drawn without replacement from
the stock's noise sessions (A3) on which the date-only change is defined for the index. They
are measured date-only and given the event's direction. Results report the placebo response
rate, direction accuracy and signed average move. *Reason:* the brief's definition.

**M6 Unexplained moves.**
- **Large changes counted:** every stock with a noise unit for the index, every event-period
  session d with a defined two-session change, where |change| > 2 noise units.
- **Explained:** a change is explained if any candidate event of any type (R9, E4 included)
  has R in [d−1, d+1], or if the stock's market-adjusted return on d−1, d or d+1 exceeds
  twice its typical daily move.
- **Typical daily move:** the median absolute market-adjusted close-to-close return over the
  120 sessions ending 12 May 2026.
- **Reporting:** the rate is unexplained ÷ large, with the explained share split into
  event-only, price-only and both.

*Reason:* a robust "typical" measured before the event period, so the period's own events
cannot inflate it.

**M7 Cells and multiple comparisons.**
- **Cells:** 6 indices × 7 event groups (E1, E2, E1+E2, E3, E4, E4 purchase, E4 sale) = 42.
- **Primary cell:** `score_exo` × E1+E2.
- **Benjamini-Hochberg families:** applied separately to each test (response, signed move,
  direction binomial), over the secondary cells excluding the market channel. Market-channel
  cells are reported with raw p-values only and flagged. The count of cells examined is
  stated.
- **Index of interest:** for E3 and E4 cells, the influencer channel.

*Reason:* the market channel gets no weight (BRIEF.md section 3), and families keep tests of
different questions from diluting each other.

**M8 Random streams per cell.** Each cell draws its relabellings, bootstrap and placebo
dates from its own generator, seeded with (20260512, index position, group position) in the
order of `config.INDICES` and `config.GROUPS`. *Reason:* any single cell can be rerun on its
own and give the same numbers.

#### 2026-10-08 (Phase 2 additions, set before the run)

**M9 The response test is slightly conservative.** The response p-value keeps the brief's
formula, p = (1 + #relabellings with a rate at least as high) / 1,001. The response rate
moves in steps of 1/N, and ties count as "at least as high", so the test rejects a little
less often than its nominal level. On synthetic nulls (500 replications,
`results/phase1_synthetic.md`) 3.6% of p-values fell below 0.05, and a KS test against
uniform gave p = 0.008. The signed-move test, a continuous statistic, gave 4.8% and was
consistent with uniform. *Reason (researcher):* keep the specified formula and state the
property.

**M10 Saved nulls.** Every cell's 1,000 relabelled response rates and signed average moves,
and its 2,000 bootstrap draws (response rate, direction accuracy, signed average move), are
written to `results/nulls/relabel.csv.gz` and `results/nulls/bootstrap.csv.gz`. Gzipped CSV
is used because the repository ignores `*.parquet`. *Reason (researcher):* later questions
can be answered from files without rerunning.

**M11 Detectable effects next to results.** RESULTS.md shows each primary-cell result next
to its minimum detectable effect from the Phase 0 power estimate (`results/power.csv`,
computed at commit 095f4c9 before any response). *Reason (researcher):* a reader can see
whether a null result was ever likely to be anything else.

## 5. Primary cell in full: `score_exo`, E1 and E2 pooled

73 events on 25 distinct reaction dates; excluded: 0 without a noise unit, 0 without a before reading, 0 without an after reading.

Each result sits next to the smallest effect this sample could detect with 80% power, computed in Phase 0 before any response was seen (`results/power.csv`).

| measure | result | 95% interval (date bootstrap) | random dates (relabelling mean) | p | detectable with 80% power | pass condition |
|---|---|---|---|---|---|---|
| response rate | 43.8% (32 of 73) | 31.1% to 55.7% | 32.2% | 0.025 | 47.0% | p < 0.05: met |
| signed average move (points) | +4.87 (+0.53 noise units) | +2.33 to +7.38 | +0.07 | 0.001 (minimum possible) | 2.95 points (0.32 noise units) | p < 0.05: met |
| unexplained-move rate | 32.4% (165 of 509 large moves) | not computed | n/a | n/a | not estimated (needs changes around events) | < 50%: met |
| direction accuracy | 68.8% (22 of 32 moves) | 51.7% to 81.5% | n/a | 0.050 (exact binomial vs 50%) | 75.5% at 34 moves | reported only (A6) |
| wrong-way rate | 13.7% | | | | | reported only |
| miss rate | 56.2% | | | | | reported only |

Placebo dates (up to 20 per event, quiet sessions of the same stock, given the event's direction): 1364 dates; response rate 31.8%, direction accuracy 49.3%, signed average move -0.13 points. Placebo dates inside an E4 window: 251.

**Verdict: the primary cell passes** under the amended rule (DECISIONS.md A6).

## 6. Scorecards by index and event type

p-values are one-sided relabelling p-values (response, signed move) and the two-sided exact binomial (direction); q is the Benjamini-Hochberg adjusted value within each test family (section 8). Intervals are 95% date-bootstrap intervals. 'Detectable' columns are the Phase 0 power estimates. E2 has fewer than 30 events. For E3 and E4 the index of interest is `influencer`.

### score

| events | n | response rate (95% CI) | random dates | p | q | detectable | signed move, pts (95% CI) | random dates | p | q | detectable, pts |
|---|---|---|---|---|---|---|---|---|---|---|---|
| E1 | 52 | 51.9% (38.2% to 63.0%) | 35.3% | 0.004 | 0.045 | 51.5% | +6.48 (+4.44 to +8.77) | +0.01 | 0.001 (minimum possible) | 0.005 | 2.63 |
| E2 | 21 | 61.9% (45.0% to 77.3%) | 35.3% | 0.009 | 0.051 | 64.0% | +7.95 (+6.57 to +9.79) | +0.07 | 0.001 (minimum possible) | 0.005 | 3.81 |
| E1+E2 | 73 | 54.8% (44.1% to 65.3%) | 35.3% | 0.002 | 0.034 | 48.5% | +6.90 (+5.30 to +8.55) | -0.01 | 0.001 (minimum possible) | 0.005 | 2.4 |
| E3 | 120 | 35.8% (27.9% to 43.9%) | 32.2% | 0.225 | 0.509 | 43.5% | +3.70 (+2.28 to +4.96) | -0.05 | 0.001 (minimum possible) | 0.005 | 1.76 |
| E4 | 547 | 28.9% (24.9% to 33.2%) | 32.8% | 0.986 | 0.998 | 38.0% | +0.91 (+0.17 to +1.67) | +0.16 | 0.008 | 0.021 | 0.64 |
| E4 purchase | 37 | 45.9% (25.7% to 65.0%) | 33.7% | 0.082 | 0.253 | 54.5% | +3.22 (+0.40 to +5.73) | +0.12 | 0.008 | 0.021 | 3.05 |
| E4 sale | 510 | 27.6% (23.6% to 32.2%) | 32.9% | 0.997 | 0.998 | 38.5% | +0.75 (-0.17 to +1.62) | +0.23 | 0.035 | 0.066 | 0.71 |

| events | moves | direction accuracy (95% CI) | p (binomial) | q | wrong-way | miss | placebo response | placebo accuracy | placebo signed move | placebo dates in an E4 window |
|---|---|---|---|---|---|---|---|---|---|---|
| E1 | 27 | 88.9% (76.2% to 100.0%) | 4.9e-05 | 5.6e-04 | 5.8% | 48.1% | 33.7% | 42.8% | -0.46 | 205 of 986 |
| E2 | 13 | 100.0% (100.0% to 100.0%) | 2.4e-04 | 0.002 | 0.0% | 38.1% | 35.2% | 45.1% | -0.29 | 44 of 378 |
| E1+E2 | 40 | 92.5% (83.3% to 100.0%) | 1.9e-08 | 6.6e-07 | 4.1% | 45.2% | 33.6% | 43.9% | -0.40 | 248 of 1364 |
| E3 | 43 | 86.0% (75.0% to 94.1%) | 1.6e-06 | 2.8e-05 | 5.0% | 64.2% | 32.7% | 46.8% | -0.30 | 311 of 2201 |
| E4 | 158 | 63.3% (53.4% to 73.6%) | 0.001 | 0.007 | 10.6% | 71.1% | 32.8% | 51.4% | +0.20 | 4178 of 10812 |
| E4 purchase | 17 | 82.4% (61.5% to 100.0%) | 0.013 | 0.043 | 8.1% | 54.1% | 33.6% | 54.9% | +0.24 | 165 of 732 |
| E4 sale | 141 | 61.0% (48.4% to 72.3%) | 0.011 | 0.043 | 10.8% | 72.4% | 32.8% | 50.8% | +0.20 | 4007 of 10080 |

### score_exo

| events | n | response rate (95% CI) | random dates | p | q | detectable | signed move, pts (95% CI) | random dates | p | q | detectable, pts |
|---|---|---|---|---|---|---|---|---|---|---|---|
| E1 | 52 | 50.0% (36.1% to 64.0%) | 33.1% | 0.008 | 0.051 | 51.5% | +4.49 (+1.60 to +7.84) | +0.02 | 0.002 | 0.007 | 3.4 |
| E2 | 21 | 28.6% (5.9% to 50.0%) | 30.6% | 0.657 | 0.977 | 59.0% | +5.80 (+3.24 to +8.05) | +0.08 | 0.003 | 0.009 | 4.86 |
| E1+E2 | 73 | 43.8% (31.1% to 55.7%) | 32.2% | 0.025 | n/a | 47.0% | +4.87 (+2.33 to +7.38) | +0.07 | 0.001 (minimum possible) | n/a | 2.95 |
| E3 | 120 | 36.7% (27.6% to 46.1%) | 32.1% | 0.161 | 0.403 | 43.5% | +3.75 (+1.43 to +6.05) | -0.09 | 0.001 (minimum possible) | 0.005 | 2.34 |
| E4 | 547 | 31.1% (26.4% to 35.2%) | 32.0% | 0.694 | 0.977 | 37.0% | +0.89 (-0.07 to +1.81) | +0.16 | 0.034 | 0.066 | 0.95 |
| E4 purchase | 37 | 40.5% (21.9% to 58.1%) | 31.6% | 0.149 | 0.403 | 52.0% | +3.92 (-0.80 to +8.06) | -0.01 | 0.030 | 0.064 | 4.48 |
| E4 sale | 510 | 30.4% (26.4% to 34.3%) | 31.9% | 0.784 | 0.977 | 37.5% | +0.67 (-0.43 to +1.82) | +0.18 | 0.117 | 0.153 | 0.98 |

| events | moves | direction accuracy (95% CI) | p (binomial) | q | wrong-way | miss | placebo response | placebo accuracy | placebo signed move | placebo dates in an E4 window |
|---|---|---|---|---|---|---|---|---|---|---|
| E1 | 26 | 65.4% (47.6% to 80.0%) | 0.169 | 0.302 | 17.3% | 50.0% | 32.5% | 50.0% | -0.11 | 204 of 986 |
| E2 | 6 | 83.3% (52.9% to 100.0%) | 0.219 | 0.338 | 4.8% | 71.4% | 30.4% | 49.6% | +0.11 | 44 of 378 |
| E1+E2 | 32 | 68.8% (51.7% to 81.5%) | 0.050 | n/a | 13.7% | 56.2% | 31.8% | 49.3% | -0.13 | 251 of 1364 |
| E3 | 44 | 70.5% (56.8% to 84.6%) | 0.010 | 0.041 | 10.8% | 63.3% | 31.8% | 49.7% | -0.10 | 311 of 2201 |
| E4 | 170 | 58.2% (49.5% to 67.0%) | 0.038 | 0.086 | 13.0% | 68.9% | 31.8% | 51.9% | +0.21 | 4138 of 10812 |
| E4 purchase | 15 | 80.0% (57.9% to 100.0%) | 0.035 | 0.086 | 8.1% | 59.5% | 30.6% | 58.9% | +0.66 | 162 of 732 |
| E4 sale | 155 | 56.1% (46.0% to 66.4%) | 0.148 | 0.280 | 13.3% | 69.6% | 31.8% | 50.9% | +0.17 | 4000 of 10080 |

### narrative

| events | n | response rate (95% CI) | random dates | p | q | detectable | signed move, pts (95% CI) | random dates | p | q | detectable, pts |
|---|---|---|---|---|---|---|---|---|---|---|---|
| E1 | 52 | 40.4% (30.6% to 52.5%) | 33.3% | 0.166 | 0.403 | 51.5% | +7.95 (+3.45 to +12.25) | +0.06 | 0.002 | 0.007 | 6.53 |
| E2 | 20 | 25.0% (5.9% to 45.0%) | 31.0% | 0.804 | 0.977 | 62.0% | +9.09 (+6.42 to +12.13) | +0.08 | 0.014 | 0.034 | 9.3 |
| E1+E2 | 72 | 36.1% (27.0% to 47.1%) | 32.4% | 0.273 | 0.545 | 49.0% | +8.27 (+4.62 to +11.95) | -0.02 | 0.001 (minimum possible) | 0.005 | 5.27 |
| E3 | 119 | 32.8% (23.7% to 42.9%) | 31.1% | 0.389 | 0.734 | 42.0% | +6.98 (+2.91 to +11.24) | -0.06 | 0.001 (minimum possible) | 0.005 | 4.39 |
| E4 | 534 | 27.0% (23.6% to 30.2%) | 31.8% | 0.994 | 0.998 | 37.0% | +1.37 (-0.08 to +2.90) | +0.00 | 0.052 | 0.088 | 1.96 |
| E4 purchase | 37 | 27.0% (11.4% to 42.5%) | 31.1% | 0.762 | 0.977 | 52.0% | +8.21 (+2.73 to +14.08) | +0.50 | 0.023 | 0.052 | 9.49 |
| E4 sale | 497 | 27.0% (23.8% to 30.1%) | 32.0% | 0.998 | 0.998 | 37.0% | +0.86 (-0.62 to +2.47) | +0.04 | 0.146 | 0.184 | 1.97 |

| events | moves | direction accuracy (95% CI) | p (binomial) | q | wrong-way | miss | placebo response | placebo accuracy | placebo signed move | placebo dates in an E4 window |
|---|---|---|---|---|---|---|---|---|---|---|
| E1 | 21 | 76.2% (59.3% to 91.3%) | 0.027 | 0.075 | 9.6% | 59.6% | 33.8% | 51.4% | -0.08 | 199 of 968 |
| E2 | 5 | 80.0% (50.0% to 100.0%) | 0.375 | 0.510 | 5.0% | 75.0% | 34.3% | 52.5% | +1.22 | 44 of 356 |
| E1+E2 | 26 | 76.9% (62.5% to 90.5%) | 0.009 | 0.041 | 8.3% | 63.9% | 33.8% | 51.8% | +0.24 | 246 of 1324 |
| E3 | 39 | 69.2% (52.9% to 84.6%) | 0.024 | 0.073 | 10.1% | 67.2% | 30.9% | 52.9% | -0.21 | 312 of 2156 |
| E4 | 144 | 55.6% (48.2% to 62.1%) | 0.211 | 0.338 | 12.0% | 73.0% | 31.6% | 49.2% | +0.11 | 3963 of 10510 |
| E4 purchase | 10 | 80.0% (55.6% to 100.0%) | 0.109 | 0.219 | 5.4% | 73.0% | 30.1% | 54.1% | +0.68 | 161 of 732 |
| E4 sale | 134 | 53.7% (45.7% to 61.8%) | 0.437 | 0.571 | 12.5% | 73.0% | 31.8% | 48.6% | +0.15 | 3814 of 9778 |

### influencer

| events | n | response rate (95% CI) | random dates | p | q | detectable | signed move, pts (95% CI) | random dates | p | q | detectable, pts |
|---|---|---|---|---|---|---|---|---|---|---|---|
| E1 | 52 | 34.6% (19.0% to 50.8%) | 29.7% | 0.246 | 0.522 | 43.5% | +1.81 (-1.31 to +5.78) | +0.04 | 0.088 | 0.136 | 3.53 |
| E2 | 20 | 75.0% (55.0% to 90.9%) | 36.6% | 0.001 (minimum possible) | 0.034 | 57.0% | +1.65 (-5.58 to +7.35) | +0.12 | 0.230 | 0.279 | 4.79 |
| E1+E2 | 72 | 45.8% (32.4% to 58.6%) | 31.9% | 0.015 | 0.073 | 42.0% | +1.76 (-1.71 to +5.55) | +0.02 | 0.066 | 0.107 | 3.05 |
| E3 | 120 | 32.5% (20.8% to 46.2%) | 26.3% | 0.067 | 0.228 | 35.0% | +2.43 (+0.60 to +4.73) | -0.02 | 0.002 | 0.007 | 1.87 |
| E4 | 547 | 30.0% (21.4% to 38.1%) | 25.3% | 0.008 | 0.051 | 29.5% | +0.38 (-0.64 to +1.57) | -0.09 | 0.115 | 0.153 | 0.87 |
| E4 purchase | 37 | 37.8% (15.6% to 58.7%) | 24.2% | 0.039 | 0.147 | 43.5% | +0.29 (-5.17 to +4.98) | +0.10 | 0.453 | 0.496 | 4.05 |
| E4 sale | 510 | 29.4% (21.4% to 37.1%) | 25.5% | 0.024 | 0.102 | 29.5% | +0.38 (-0.96 to +1.77) | -0.12 | 0.100 | 0.148 | 0.9 |

| events | moves | direction accuracy (95% CI) | p (binomial) | q | wrong-way | miss | placebo response | placebo accuracy | placebo signed move | placebo dates in an E4 window |
|---|---|---|---|---|---|---|---|---|---|---|
| E1 | 18 | 55.6% (27.8% to 81.2%) | 0.815 | 0.923 | 15.4% | 65.4% | 26.4% | 41.9% | -0.51 | 204 of 986 |
| E2 | 15 | 46.7% (16.7% to 68.8%) | 1.000 | 1.000 | 40.0% | 25.0% | 27.4% | 37.8% | -0.86 | 45 of 358 |
| E1+E2 | 33 | 51.5% (28.6% to 70.0%) | 1.000 | 1.000 | 22.2% | 54.2% | 26.6% | 39.5% | -0.67 | 250 of 1344 |
| E3 | 39 | 61.5% (44.4% to 78.4%) | 0.200 | 0.338 | 12.5% | 67.5% | 24.5% | 55.2% | +0.13 | 311 of 2201 |
| E4 | 164 | 54.3% (45.8% to 62.7%) | 0.310 | 0.458 | 13.7% | 70.0% | 24.4% | 48.6% | -0.02 | 4167 of 10812 |
| E4 purchase | 14 | 57.1% (12.5% to 85.7%) | 0.791 | 0.923 | 16.2% | 62.2% | 24.6% | 54.4% | +0.20 | 178 of 732 |
| E4 sale | 150 | 54.0% (42.4% to 64.8%) | 0.369 | 0.510 | 13.5% | 70.6% | 24.5% | 46.7% | -0.18 | 3987 of 10080 |

### macro

| events | n | response rate (95% CI) | random dates | p | q | detectable | signed move, pts (95% CI) | random dates | p | q | detectable, pts |
|---|---|---|---|---|---|---|---|---|---|---|---|
| E1 | 52 | 17.3% (6.2% to 31.8%) | 25.6% | 0.941 | 0.998 | 43.5% | +0.80 (-4.29 to +4.47) | +0.27 | 0.403 | 0.456 | 5.86 |
| E2 | 21 | 19.0% (4.8% to 35.3%) | 22.8% | 0.741 | 0.977 | 54.5% | +6.40 (+0.98 to +12.56) | -0.16 | 0.045 | 0.080 | 10.48 |
| E1+E2 | 73 | 17.8% (8.5% to 29.2%) | 24.7% | 0.935 | 0.998 | 40.0% | +2.41 (-1.42 to +5.49) | -0.08 | 0.106 | 0.150 | 5.23 |
| E3 | 120 | 26.7% (15.2% to 39.4%) | 27.9% | 0.661 | 0.977 | 37.5% | -3.28 (-7.07 to +0.14) | -0.22 | 0.977 | 0.977 | 3.84 |
| E4 | 547 | 25.4% (14.8% to 38.0%) | 26.2% | 0.723 | 0.977 | 31.0% | +1.10 (-3.26 to +5.59) | +1.21 | 0.571 | 0.607 | 1.62 |
| E4 purchase | 37 | 21.6% (5.3% to 41.2%) | 26.4% | 0.791 | 0.977 | 49.0% | +0.10 (-7.54 to +6.84) | -0.83 | 0.389 | 0.456 | 7.01 |
| E4 sale | 510 | 25.7% (15.3% to 37.7%) | 26.1% | 0.609 | 0.977 | 31.0% | +1.17 (-3.76 to +6.48) | +1.40 | 0.628 | 0.647 | 1.72 |

| events | moves | direction accuracy (95% CI) | p (binomial) | q | wrong-way | miss | placebo response | placebo accuracy | placebo signed move | placebo dates in an E4 window |
|---|---|---|---|---|---|---|---|---|---|---|
| E1 | 9 | 55.6% (18.2% to 100.0%) | 1.000 | 1.000 | 7.7% | 82.7% | 26.3% | 52.5% | +0.26 | 202 of 986 |
| E2 | 4 | 75.0% (0.0% to 100.0%) | 0.625 | 0.759 | 4.8% | 81.0% | 25.1% | 45.3% | -0.04 | 43 of 378 |
| E1+E2 | 13 | 61.5% (33.3% to 90.9%) | 0.581 | 0.732 | 6.8% | 82.2% | 26.0% | 50.7% | +0.21 | 250 of 1364 |
| E3 | 32 | 25.0% (12.0% to 41.9%) | 0.007 | 0.040 | 20.0% | 73.3% | 28.0% | 49.2% | -0.27 | 310 of 2201 |
| E4 | 139 | 59.0% (32.0% to 80.7%) | 0.041 | 0.088 | 10.4% | 74.6% | 25.8% | 57.9% | +1.07 | 4157 of 10812 |
| E4 purchase | 8 | 50.0% (0.0% to 100.0%) | 1.000 | 1.000 | 10.8% | 78.4% | 27.3% | 45.5% | -0.97 | 171 of 732 |
| E4 sale | 131 | 59.5% (30.0% to 82.9%) | 0.036 | 0.086 | 10.4% | 74.3% | 25.8% | 59.5% | +1.30 | 3997 of 10080 |

### market (market-contaminated; no weight)

| events | n | response rate (95% CI) | random dates | p | q | detectable | signed move, pts (95% CI) | random dates | p | q | detectable, pts |
|---|---|---|---|---|---|---|---|---|---|---|---|
| E1 | 52 | 59.6% (44.4% to 75.0%) | 36.2% | 0.001 (minimum possible) | n/a | 51.5% | +11.86 (+7.95 to +15.66) | -0.08 | 0.001 (minimum possible) | n/a | 4.91 |
| E2 | 21 | 61.9% (44.4% to 81.0%) | 36.7% | 0.022 | n/a | 64.0% | +13.56 (+5.71 to +21.73) | -0.25 | 0.001 (minimum possible) | n/a | 7.0 |
| E1+E2 | 73 | 60.3% (46.4% to 73.4%) | 36.1% | 0.001 (minimum possible) | n/a | 48.5% | +12.35 (+9.51 to +15.69) | +0.06 | 0.001 (minimum possible) | n/a | 4.03 |
| E3 | 120 | 35.0% (26.1% to 44.0%) | 32.9% | 0.333 | n/a | 43.0% | +3.36 (+1.32 to +5.37) | -0.02 | 0.003 | n/a | 3.28 |
| E4 | 547 | 32.5% (28.8% to 36.7%) | 33.2% | 0.640 | n/a | 37.5% | +1.44 (+0.38 to +2.58) | +0.14 | 0.009 | n/a | 1.15 |
| E4 purchase | 37 | 32.4% (13.5% to 51.4%) | 34.8% | 0.695 | n/a | 57.0% | +3.64 (-0.16 to +6.95) | +0.31 | 0.036 | n/a | 4.51 |
| E4 sale | 510 | 32.5% (29.0% to 36.4%) | 33.1% | 0.607 | n/a | 38.0% | +1.28 (+0.02 to +2.60) | +0.21 | 0.026 | n/a | 1.27 |

| events | moves | direction accuracy (95% CI) | p (binomial) | q | wrong-way | miss | placebo response | placebo accuracy | placebo signed move | placebo dates in an E4 window |
|---|---|---|---|---|---|---|---|---|---|---|
| E1 | 31 | 87.1% (73.9% to 96.8%) | 3.4e-05 | n/a | 7.7% | 40.4% | 33.2% | 40.1% | -0.91 | 207 of 986 |
| E2 | 13 | 84.6% (57.1% to 100.0%) | 0.022 | n/a | 9.5% | 38.1% | 34.1% | 43.4% | -0.50 | 44 of 378 |
| E1+E2 | 44 | 86.4% (76.7% to 95.6%) | 9.4e-07 | n/a | 8.2% | 39.7% | 33.3% | 40.7% | -0.83 | 248 of 1364 |
| E3 | 42 | 66.7% (50.0% to 83.9%) | 0.044 | n/a | 11.7% | 65.0% | 32.3% | 46.5% | -0.46 | 313 of 2201 |
| E4 | 178 | 57.3% (51.1% to 63.8%) | 0.061 | n/a | 13.9% | 67.5% | 32.4% | 51.9% | +0.27 | 4143 of 10812 |
| E4 purchase | 12 | 75.0% (42.9% to 100.0%) | 0.146 | n/a | 8.1% | 67.6% | 33.2% | 51.4% | +0.30 | 175 of 732 |
| E4 sale | 166 | 56.0% (48.4% to 64.1%) | 0.140 | n/a | 14.3% | 67.5% | 32.4% | 52.0% | +0.23 | 3974 of 10080 |

## 7. Unexplained moves

A large move is a two-session change of more than two noise units on an event-period session. It is explained if any event of any type (E4 included) has its reaction session within one session, or if the stock's market-adjusted return within one session exceeds twice its typical daily move (DECISIONS.md M6).

| index                                   |   large moves |   unexplained | unexplained rate   |   explained by event only |   by price only |   by both |
|:----------------------------------------|--------------:|--------------:|:-------------------|--------------------------:|----------------:|----------:|
| score                                   |           538 |           125 | 23.2%              |                        21 |             295 |        97 |
| score_exo                               |           509 |           165 | 32.4%              |                        28 |             230 |        86 |
| narrative                               |           496 |           148 | 29.8%              |                        31 |             252 |        65 |
| influencer                              |          1060 |           333 | 31.4%              |                        65 |             463 |       199 |
| macro                                   |           862 |           299 | 34.7%              |                        58 |             405 |       100 |
| market (market-contaminated; no weight) |           516 |            45 | 8.7%               |                         9 |             330 |       132 |

## 8. Multiple comparisons

Cells examined: 42 (6 indices x 7 event groups). One is primary. The 7 market-channel cells are reported with raw p-values only. Benjamini-Hochberg is applied separately to each test over the remaining 34 secondary cells.

| test | cells | raw p < 0.05 | BH q < 0.05 |
|---|---|---|---|
| response (test 1) | 34 | 9 | 3 |
| signed move (test 3) | 34 | 19 | 14 |
| direction (exact binomial) | 34 | 16 | 10 |

Every secondary result with BH q < 0.05. The response and signed-move tests are one-sided, so a significant result there is an excess of moves, or a move in the events' direction. The direction test is two-sided and can be significant in either direction.

| index | events | test | p | q | direction |
|---|---|---|---|---|---|
| score | E1 | response | 0.004 | 0.045 | score moved more often than on random dates |
| score | E1 | signed move | 0.001 (minimum possible) | 0.005 | in the events' direction |
| score | E1 | direction | 4.9e-05 | 5.6e-04 | in the events' direction |
| score | E2 | signed move | 0.001 (minimum possible) | 0.005 | in the events' direction |
| score | E2 | direction | 2.4e-04 | 0.002 | in the events' direction |
| score | E1+E2 | response | 0.002 | 0.034 | score moved more often than on random dates |
| score | E1+E2 | signed move | 0.001 (minimum possible) | 0.005 | in the events' direction |
| score | E1+E2 | direction | 1.9e-08 | 6.6e-07 | in the events' direction |
| score | E3 | signed move | 0.001 (minimum possible) | 0.005 | in the events' direction |
| score | E3 | direction | 1.6e-06 | 2.8e-05 | in the events' direction |
| score | E4 | signed move | 0.008 | 0.021 | in the events' direction |
| score | E4 | direction | 0.001 | 0.007 | in the events' direction |
| score | E4 purchase | signed move | 0.008 | 0.021 | in the events' direction |
| score | E4 purchase | direction | 0.013 | 0.043 | in the events' direction |
| score | E4 sale | direction | 0.011 | 0.043 | in the events' direction |
| score_exo | E1 | signed move | 0.002 | 0.007 | in the events' direction |
| score_exo | E2 | signed move | 0.003 | 0.009 | in the events' direction |
| score_exo | E3 | signed move | 0.001 (minimum possible) | 0.005 | in the events' direction |
| score_exo | E3 | direction | 0.010 | 0.041 | in the events' direction |
| narrative | E1 | signed move | 0.002 | 0.007 | in the events' direction |
| narrative | E2 | signed move | 0.014 | 0.034 | in the events' direction |
| narrative | E1+E2 | signed move | 0.001 (minimum possible) | 0.005 | in the events' direction |
| narrative | E1+E2 | direction | 0.009 | 0.041 | in the events' direction |
| narrative | E3 | signed move | 0.001 (minimum possible) | 0.005 | in the events' direction |
| influencer | E2 | response | 0.001 (minimum possible) | 0.034 | score moved more often than on random dates |
| influencer | E3 | signed move | 0.002 | 0.007 | in the events' direction |
| macro | E3 | direction | 0.007 | 0.040 | **against the events' direction** |

## 9. Limitations observed

- **Power.** This is a pilot. The primary cell has 73 events; see the detectable effects in section 5. E2 has fewer than 30 events. The power estimate treats events as independent, but they cluster on news days.
- **Insider timing.** E4's reaction session is the transaction date (DECISIONS.md A2). Form 4 filings are public up to two business days later, so the market often cannot trade on an E4 event within its window.
- **Insider clusters.** Runs of overlapping insider trades collapse into one event measured over the first member's window (A4); 20 clusters have members after that window.
- **Insider coverage.** yfinance returns at most 150 insider rows per stock; for 1 stock(s) that history does not reach the event period's start.
- **Placebo dates near insider trades.** Noise and placebo sessions exclude E1 to E3 windows only (A3); for `influencer` on E4, 4167 of 10812 placebo dates fall inside an E4 window.
- **Earnings times.** Yahoo labels releases to the hour, mostly 06:00 to 08:00 or 16:00 ET. These look like before-open and after-close labels, not exact release times (DECISIONS.md R1).
- **Rating dates.** The source's timestamp has no stated timezone; its date is used as given (R2).
- **EPS cross-check.** It carries no weight: nearly every company beat estimates in the period (A5).
- **Response test.** The p-value formula counts ties as 'at least as high', which makes test 1 slightly conservative (3.6% false positives at the 5% level on synthetic nulls; DECISIONS.md M9).
- **Market channel.** The market channel is computed from price and is contaminated in this period; it is reported, flagged and given no weight. The published `score` includes it (35% weight in the composite) and is reported as published.
- **Data revisions.** yfinance serves current data; a later download of the same events can differ. The data hash identifies the inputs used.
