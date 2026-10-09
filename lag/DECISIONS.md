# Decisions, Experiment 5B

Every interpretive choice made while implementing BRIEF.md, numbered L1, L2, … so that they cannot
be confused with Experiment 5A's. Each is dated and was recorded before the result it could affect.
Amendments after the pilot, if any, are added at the end with their reasons, before the definitive
data is read (BRIEF.md ground rule 1).

## Phase 0 (9 October 2026, before any response was computed)

**L1 The L-E2 bar move is the move from the bar's open to its close.** The brief defines L-E2 by
"the first in-session price bar of a stock whose market-adjusted move exceeds 3 times that stock's
normal move". The move of a bar is read as its own open-to-close return, for the bar being tested
and for the bars that set the normal move. *Reason:* a close-to-close return for the first bar of
a session would include the overnight gap, whose time cannot be fixed to within an hour (the
brief's requirement for every event). With this reading, overnight news that moves the open does
not create an event unless the stock keeps moving in the first bar. The price curve (L7) is a
different quantity and does include gaps.

**L2 The unsmoothed composite is the served `score_raw`.** The pilot tick cache carries `score_raw`
on 100% of ticks (results/tick_check.md), so the rebuild from the four channels at
0.35 / 0.30 / 0.25 / 0.10 is only a fallback, applied per tick where `score_raw` is missing and
renormalised over the channels present (as `score_exo` is). The run metadata reports how many ticks
used the fallback. *Reason:* BRIEF.md section 3; the served value is the one the API's users see.

**L3 A normal move needs at least 10 bars.** The normal move for a stock and time of day is
1.4826 times the median absolute market-adjusted bar move over the period's sessions that are not
earnings reaction sessions for the stock, given at least 10 such bars; otherwise the stock has no
normal move at that time of day and its bars there cannot be L-E2 events (counted in
results/event_counts.md). *Reason:* a median of fewer than 10 values is too unstable to set a
threshold; 10 matches 5A's minimum for noise units (5A DECISIONS.md A3). In the pilot every cell
has 28 bars and none is missing.

**L4 The bar stores keep the first value seen.** A bar already in a store is never changed by a
later download; the count of overlapping bars whose values differ is recorded in the store's
manifest and in the coverage report. *Reason:* the 15-minute store is filled by repeated weekly
downloads, and the data hash in the ledger must identify a fixed input. Yahoo revises intraday
bars rarely and slightly; the count makes any revision visible.

**L5 Excluded event sources.** Analyst rating changes and insider transactions are excluded: the
sources available (yfinance, as in 5A) give a date and no time, so t0 cannot be fixed to within an
hour. News bursts are excluded: the API exposes no article list or publication time
(results/article_times.md). *Reason:* BRIEF.md section 3.

**L6 A before reading must be within 2 hours of t0.** S(t0⁻) is the last tick strictly before t0.
If that tick is more than 2 hours old, the event has no before reading for that index and is
dropped from that index's curves (counted per index). *Reason:* the schedule puts a tick every
15 or 30 minutes; a gap of hours means the system was not scoring, and a change measured across
such a gap would mix the event with the outage. Two hours is four times the longest scheduled gap.
The same rule applies to placebo and relabelled times.

**L7 The price curve uses close-to-close returns, including overnight gaps, read at the last bar
at or before each horizon.** rₑ(h) is the stock's cumulative market-adjusted return from the last
bar close before t0 to the close of the last bar starting at or before t0 + h; between sessions the
price is held at the last close, so the curve is flat outside the session ("counting session time
only"). The market return is the equal-weighted universe return over the same bars. *Reason:* for a
release after the close, the price reaction is the next day's gap, which the curve must contain;
the horizon axis stays in wall-clock hours so that Rₚ(T½) is defined at the score's T½. The first
bar's return in this series is close(previous session) to close(first bar).

**L8 Non-event sessions for placebo and relabelled times.** A session is a non-event session for a
stock if it is more than 2 sessions away from every candidate event of that stock (any status,
including earnings without a time, both of whose possible reaction sessions count). Placebo and
relabelled times are the event's time of day on such sessions, with t0 − 6 h and t0 + 48 h inside
the run's tick range. *Reason:* 5A's rule (A3), so that the relabelling test of 5A is reused as the
brief asks; a 2-session radius clears the 48-hour post-window of any event.

**L9 The relabelling test is 5A's, with its direction permutation.** For each index, K = 1,000
draws relabel, within every stock, as many non-event times as the stock has events (without
replacement where possible), and permute the events' directions across events; M⁽ᵏ⁾ is the mean of
d·Δ(48 h) over the draw. *Reason:* BRIEF.md section 5 names 5A's test; permuting directions as
well as times removes any drift in the index over the period from the null.

**L10 First response uses the relabelling null per horizon.** At each main horizon the event mean
of m(h) is compared with the K relabelled means at that horizon; p = (1 + #{k : mean⁽ᵏ⁾ ≥ mean}) /
(1 + K); Holm across the eight horizons; the first response is the earliest horizon with adjusted
p < 0.05. *Reason:* "significantly above the placebo mean" needs a null distribution for the mean
at each horizon, and the relabelled draws provide one without a further procedure.

**L11 Alignment on hourly session bars, in both runs.** The alignment measure uses the hourly
regular-session bars (7 per full session, the last covering 15:30 to 16:00 New York time). In the
definitive run the 15-minute bars are aggregated to the same hourly bars. The index change over a
bar is S(bar end) − S(bar start). Shifting by k trading hours moves along the stock's sequence of
session bars, across sessions. *Reason:* the brief defines alignment over "every in-session hour";
the same bar grid in both runs makes their k comparable.

**L12 The grid is every 5 minutes from −6 h to +48 h.** S(t) is a step function of the ticks, so
sampling it every 5 minutes, finer than any tick spacing, sees every tick; T½ and T₉₀ are
interpolated on this grid and reported next to the tick spacing. *Reason:* ticks are not aligned
across stocks, so a common grid is needed to average; 5 minutes loses nothing.

**L13 Worktree and branch.** This experiment's code is on branch `lag-5b`, branched from the
`5a-definitive-prereg` tag so that `lag/` can import `responsiveness/`, which is not on `main`.
*Reason:* BRIEF.md section 2 allows importing 5A's code; the import needs it in the tree.

## Amendment after the Phase 0 counts (9 October 2026, before any response was computed)

**L14 L-E2 rarity threshold, and L-E1 and L-E2 as separate primary cells.** Made by the researcher
on reviewing the Phase 0 event counts, with no response computed.

1. *Threshold.* Each bar's market-adjusted move is standardised by the stock's time-of-day robust
   scale, as before (z). The L-E2 threshold is no longer 3 but the value of |z| exceeded by 0.2% of
   in-session bars, pooled across the universe over the run's period (every bar that has a z,
   earnings sessions included; the earnings exclusion applies to events, not to the pooled
   distribution). For the pilot this is **5.1503**, computed from the 92,708 hourly bars of 12 May to
   22 June 2026 and fixed in `config.py`; the counts script recomputes it and stops if the bars give
   a different value. The definitive run applies the same rule to its own 15-minute bars, so its
   value is computed in Phase 4 from prices alone and frozen in `lag/definitive/`. The original
   definition, |z| > 3, is kept as a secondary sensitivity cell with its own event set.
   *Reason:* 3 times the robust scale flagged 2.1% of hourly bars (results/event_counts.md before
   this amendment), mostly noise, because the robust scale sits well below the standard deviation
   of fat-tailed intraday returns. A rarity rule fixes what "large" means as a share of bars rather
   than as a multiple of a scale whose tail behaviour is unknown in advance.
2. *Primary cells.* L-E1 and L-E2 are two separate primary cells for `score_exo` and the unsmoothed
   composite (four primary cells in all). The pooled L-E1 + L-E2 cell becomes secondary.
   *Reason:* in the pilot every L-E1 event is outside the session and every L-E2 event inside it,
   so the pooled cell mixes two mechanisms (an overnight release read at the next ticks, and an
   in-session move read within the hour) and the inside/outside split cannot separate them.

BRIEF.md sections 3 and 5 carry dated amendment notes with the original text kept below them.

## Phase 1 (9 October 2026, while building the measurement on synthetic data; no real response computed)

**L15 Bootstrap handling of "not reached".** In the date bootstrap, a draw whose R(h) does not
reach 0.5 (or 0.9) within 48 hours enters the percentile interval at the 48-hour cap, and the share
of such draws is reported next to the interval. Relabelled times are drawn per event from the
event's own pool (so two events of one stock may land on the same session), while 5A drew within a
stock without replacement; the pools are per event here because each event has its own time of
day. *Reason:* the brief caps T½ and T₉₀ at 48 hours; an interval needs a number for every draw.
Per-event pools follow from the time-of-day rule in BRIEF.md section 5.

**L16 Rₚ(T½) is read at the first grid point where R has reached 0.5.** T½ itself is still the
linearly interpolated crossing. If R never reaches 0.5 within 48 hours, Rₚ(T½) is Rₚ(48 h), which is
1 by construction. *Reason:* the score is a step function of its ticks, so "when the score is half
done" is a grid point, not an interpolated instant. Interpolating both curves between two grid
points would report Rₚ(T½) = 0.5 for an index that copies price in the same bar, where the right
answer is 1 (the price move is complete at the moment the score reaches half). The synthetic test
of the brief ("an index that only copies price ... has Rₚ(T½) near 1") fixes this reading.

## Observations at the Phase 0 checkpoint (not decisions)

- The in-session tick spacing changed on 18 May 2026, from 30 minutes to 15 (results/tick_check.md).
  Events from 13 to 15 May have a 30-minute resolution inside the session.
- L-E2 is not rare under the brief's definition: 1,919 of 92,708 hourly bars (2.1%) exceed 3 times
  the robust normal move, giving 1,261 kept events against 52 L-E1 events. Intraday returns have
  fat tails, and the robust scale (1.4826 × median absolute move) is well below their standard
  deviation, so "3 times normal" is about a 2% tail. The pooled primary cell will be dominated by
  L-E2. The threshold is the brief's and is not changed here; this is noted for the researcher.
- Every L-E1 event is outside the session (releases at 06:00 to 08:00 and 16:00 New York time) and
  every L-E2 event is inside it by construction, so in the pilot the session split coincides with
  the type split.
