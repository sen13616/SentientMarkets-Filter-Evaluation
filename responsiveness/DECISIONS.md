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

## Open questions for the researcher (Phase 0 checkpoint)

**Q1 OPEN: events with R = 12 May.** Their "before" reading is the 11 May state, taken under
the earlier narrative text model, and the noise change for d = 12 May also spans 11 May. There
are 25 such events (E1 5, E3 2, E4 18; no E2). Keep the brief as written, or start the event
period at 13 May?

**Q2 OPEN: E4 reaction session.** The brief sets R to the transaction date. Insider trades
become public through Form 4 filings up to two business days later, so the market usually
cannot trade on them at R. That conflicts with the definition of R as the first session the
market could trade. The filing date is not in the yfinance table. Keep as written?

**Q3 OPEN: minimum noise sessions.** Noise sessions per stock: 4 stocks have 0, 15 have 1–5,
and the median is 22. Noise units built from two to five changes are unreliable. Set a
minimum number of changes (the code currently requires 2), or keep 2?

**Q4 OPEN: same-type rule (R4).** Approve R4, which drops 280 E4, 13 E3 and no E1/E2
candidates as same-type overlaps, or choose another rule?

**Q5 OPEN: E2 below 30.** E2 has 21 kept events (45 candidates, 22 of them on E1 reaction
sessions). As instructed, no threshold or source is changed. E2 is reported alone with this
caveat and pooled with E1 in the primary cell (78 events).
