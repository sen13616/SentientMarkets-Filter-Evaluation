# Decisions (Experiment 5A)

Interpretive choices and deviations from BRIEF.md, in date order. Each entry states the
decision and a one-line reason. Nothing is changed retroactively; a reversal is a new dated
entry. Entries marked **OPEN** await the researcher and are not yet in force beyond what is
stated.

## 2026-10-07 (Phase 0: sources, event construction, counts)

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

## Questions raised at the Phase 0 checkpoint (answered 2026-10-08, below)

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

## 2026-10-08 (researcher's answers; set before any score response was computed)

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

## 2026-10-08 (Phase 1 choices that follow from A1–A7 or that the brief leaves open)

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

## 2026-10-08 (Phase 2 additions, set before the run)

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

## 2026-10-08 (after the Phase 2 run)

**M12 Presentation-only renderer change after the first render.** After the first render of
RESULTS.md, the renderer was changed in three ways:
1. Section 8 lists every secondary result with BH q < 0.05 together with its test and
   direction, so a significant wrong-way result is as visible as the others.
2. The banner shows the detectable signed move to two decimals, matching the table.
3. A p-value equal to 1/1001 is printed as "0.001 (minimum possible)".

No rule, threshold, test or number changed. *Reason:* the first render's list of
significant cells hid that the macro/E3 result goes against the events' direction. Approved
by the researcher.

**M13 Sensitivity: unexplained moves without E4 (reported only).** The unexplained-move
rate is recomputed counting only E1, E2 and E3 candidates and unusual price moves as
explanations, leaving out E4. Everything else follows M6. Both rates are reported side by
side (`results/unexplained_sensitivity.csv`). The primary verdict uses the M6 rate and does
not change. *Reason (researcher):* insider sales are frequent and the score does not respond
to them, so counting them as explanations may flatter the rate.

**M14 Added limitations.** Three limitations requested by the researcher after reviewing the
results are added to RESULTS.md, with their numbers read from the result files:
- price and narrative: E1 and E2 directions come from price, so the narrative response may
  partly restate it;
- the size of the average response relative to a label band;
- the macro channel's wrong-way response to rating changes.

*Reason (researcher):* to state plainly what the pilot does and does not show.
