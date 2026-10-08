# Decisions (Experiment 5A, definitive run)

Interpretive choices for the definitive run (BRIEF.md in this folder), in date order. Every
pilot decision (`responsiveness/DECISIONS.md` A1 to A7 and M1 to M14) carries over unchanged
unless an entry here says how a date-bound pilot rule is re-dated. The Phase 0 commit, which
contains this file, is the pre-registration.

## 2026-10-08 (Phase 0; before any data from the period exists)

**D1 Lock.** Allowed: anything stamped on or before 2026-06-22 23:59:59.999999 UTC, and
anything from 2026-10-02 00:00 to 2026-11-23 23:59:59.999999 UTC. Timezone-aware stamps are
compared in UTC; naive stamps and plain dates are read as UTC (a date as 00:00 that day).
Writers drop rows outside these ranges in memory and keep only the count; loaders raise
`LockViolation` on any such row. *Reason:* the brief's two ranges, enforced as the pilot's
lock was.

**D2 Re-dated pilot rules.** The pilot's 12 May floor (A1) becomes 2 October: a before reading
must be stamped on or after 2 October 2026, and a noise change at session d needs d−1 on or
after 2 October and d+1 on or before 23 November. The event period is 5 October to 20 November
(BRIEF.md section 2). *Reason:* the same rule at the edges of the new allowed range.

**D3 Universe.** The pilot's 473 names, less any without a daily bar on every NYSE session from
2 October to 23 November 2026; dropped names are listed. No name added to the API on or after
3 October is in it (it is the pilot's universe). *Reason:* BRIEF.md section 2.

**D4 Integrity: gap.** For each session, the stamps of all universe ticks between the NYSE open
and close (UTC, from the exchange calendar, so the 1 November clock change is handled) are
pooled. The open and the close count as end points. A gap is the longest interval with no
stamp, and the session is flagged if it is longer than 2 hours. *Reason:* "the scoring history
for the universe" reads as the system's output as a whole; a stall in one ticker is not a
scheduler failure.

**D5 Integrity: narrative at the 21:30 tick.** For each universe name, the 21:30 tick is the
first tick stamped in [21:30, 21:45) UTC on that day, or if there is none, in [21:45, 22:00)
(pilot D9). A name is missing narrative if it has no such tick or the tick's narrative is null.
The session is flagged if the share missing is more than 20%. *Reason:* the pilot's definition
of the 21:30 tick.

**D6 Integrity: `/v1/status`.** The endpoint reports only the last run time per job
(API_FINDINGS.md), so it cannot show past outages. It is read once at the Phase 1 pull and
saved. Every session after the last successful scoring run it reports is flagged. Outages
earlier in the period are caught by the gap rule. *Reason:* that is all the endpoint can show.

**D7 Integrity exclusions.**
- **Events:** an event is excluded if any session from R−1 to R+1 is flagged (BRIEF.md).
- **Noise, placebo and relabelled sessions:** a session d is excluded on the same rule, applied
  to d−1, d and d+1.
- **Unexplained-move sessions:** the same rule.

Every flagged session and every exclusion is reported. If more than 20% of event-period
sessions are flagged, the run stops before anything is computed. *Reason:* a session's
two-session change spans d−1 to d+1, the same span as an event's window.

**D8 Seed.** 20261005. Each cell has its own stream, seeded with (20261005, index position,
group position), as in pilot M8. *Reason:* fixed in advance, as in the pilot.

**D9 Test B as specified.** Implemented in `regression.py` with the linear price control
(`controls="linear"`):
- **Relabelling:** within each stock, as many eligible sessions as it has events, without
  replacement, given that stock's event directions, using each drawn session's date-only score
  change and actual market-adjusted return.
- **p-value:** (1 + #{b_k ≥ b}) / (K + 1), one-sided.
- **Interval:** date bootstrap for b and c, as in pilot M4.
- **Singular design:** a design with no variation in d, or in r, leaves b undefined, and the
  cell is reported as not estimable.

*Reason:* BRIEF.md section 4.

## Questions raised at the Phase 0 checkpoint (answered 2026-10-08 in P1 to P3, below)

**Q1 (answered, P1): price lookback before 2 October.** Two pilot quantities need price history from
before the event period:
- **ATR(14):** E2 compares the move with ATR(14) measured through R−1, which needs about 14
  sessions before each R. For reaction sessions before about 22 October, those sessions fall in
  the reserved period (23 June to 1 October), which the lock forbids. That is the start of
  earnings season.
- **Typical daily move:** the unexplained-move rule uses the median absolute market-adjusted
  return over the 120 sessions ending 12 May 2026 (pilot M6).

Options:
- (a) Allow daily price bars, and only price bars, from the reserved period as lookback for
  ATR(14) and the typical daily move. No sentiment row from that period would be pulled or
  stored.
- (b) Allow nothing from the reserved period. ATR is built only from bars on or after
  2 October, so E2 events exist only once 14 such sessions have passed (R from about
  22 October). The typical daily move keeps the pilot's literal window (120 sessions ending
  12 May 2026, data the pilot already used).
- (c) As (b), but ATR(14) chains the bars up to 22 June to those from 2 October. This is not
  recommended: the true range across the gap is not defined.

Recommendation: (a) if the reservation is about sentiment data, otherwise (b). The choice
fixes `ATR_LOOKBACK` and `TYPICAL_MOVE_WINDOW` in `config.py`, which are left unset and make
the run refuse to start.

**Q2 (answered, P2): Test B, as specified, can be fooled by a score that only echoes price.**
`results/test_b_synthetic.md` shows the share of 200 synthetic replications with p < 0.05.
Under no effect a valid test gives about 5%.

| events | price echo | as specified (control c·r) | candidate (controls r, sign r, spline) |
|---|---|---|---|
| pooled E1-E3-like | none / linear | 10.5% | 10.0% |
| pooled E1-E3-like | saturating | 67.0% | 7.5% |
| pooled E1-E3-like | step (sign of move) | 25.0% | 10.0% |
| E3-like (ratings) | none / linear | 4.0% | 5.1% |
| E3-like (ratings) | saturating | 55.5% | 4.5% |
| E3-like (ratings) | step | 81.5% | 5.1% |
| E1/E2-like only | any | 30.5% to 100% | not estimable |

Why it happens:
- **Direction comes from price.** For E1 and E2 the event direction is the sign of the price
  move, so d is almost a function of r. A linear control removes a linear echo but not a curved
  one (a score that levels off on big moves, or reacts only to the move's sign), and the curve
  is credited to b.
- **The null is too narrow.** The relabelled sessions pair directions with unrelated returns,
  so the null spread of b is narrower than the real one, even with no echo at all.
- **No regression can fix E1 and E2.** If d is the sign of r, nothing in a regression separates
  "follows the event" from "follows the price".

Options:
- (i) **Keep Test B as specified.** It meets the brief's literal check (a linear echo is not
  detected in the pooled design: 10.5%, the same as with no echo), but it fails the
  saturating-echo and step-echo checks above.
- (ii) **Recommended: Test B on E3 alone, with flexible price controls.** E3 directions come
  from analysts, not from the price move. The controls are r, sign(r) and a linear spline in r
  with knots at ±1%, ±3% and ±6%. In synthetic worlds where ratings follow price 70% of the
  time, it gives 4.5% to 5.1% false positives under every echo tested and detects a 1-point
  effect in 99.5% of replications. The pooled E1-E3 regression and the per-channel and
  noise-unit versions would be reported as secondary, with this caveat.
- (iii) **Pooled E1-E3 with flexible controls.** Echoes no longer fool it, but it stays
  anti-conservative (7.5% to 10%), and b is estimated from the E3 events anyway.

Two notes on (ii):
- **Interpretation:** analyst actions are a direct input to the influencer channel, which is
  part of `score_exo` (weight 0.25). A positive b on E3 shows the score carries
  rating information that the price move does not explain. It does not show that the
  narrative channel does.
- **Rules:** it changes the cell and the controls of section 4. Under ground rule 4 it must be
  decided now, before the Phase 0 commit.

**Q3 (answered, P3): replayed rows.** API_FINDINGS.md records rows inside an earlier outage (23 June to
2 July) that look like offline replays, and the API cannot mark them. A replay that fills a gap
after the fact would hide the gap from D4. Accept this as a limitation, or add a check, for
example that the tick count per session is not unusually uniform? Recommendation: accept and
report as a limitation; the brief adds no such check.

## 2026-10-08 (researcher's decisions; before the pre-registration commit and before any data from the period was pulled)

**P1 (Q1) Price bars from the reserved period may be read; sentiment may not.** Daily price
bars, and only price bars, may be read from the reserved period (23 June to 1 October 2026), for
the lookbacks that ATR(14) and the typical daily move need before 5 October. No sentiment row
and no event from that period is pulled or stored. In practice the two lookbacks need every
reserved-period session:
- **ATR(14):** the pilot's Wilder ATR (R6) is recursive, seeded from 2 January 2025, so it reads
  every bar from then to R−1.
- **Typical daily move:** the window (D10) is 120 sessions ending 2 October, which spans the
  whole reserved period.

The price lock (`lock.py`, kind "prices") allows bars up to 23 November 2026 and refuses later
ones; sentiment and events keep the two-range lock. *Reason (researcher):* the reservation
protects sentiment and filter outcomes, not public prices.

**P2 (Q2) Test B is amended: E3 alone, with flexible price controls.**
- **Primary cell:** `score_exo` on E3 alone. The regression is
  Δ = a + b·d + c·r + e·sign(r) + Σₖ fₖ·max(r − κₖ, 0).
- **Knots κₖ:** fixed by a rule that uses no outcome data. They sit at plus and minus the 50th,
  90th and 99th percentiles of the absolute market-adjusted daily return, pooled over the
  pilot's 473 names and its price history (2 January 2025 to 22 June 2026; 173,116 returns).
  That gives ±0.0091, ±0.0289 and ±0.0737, frozen in `config.py`.
- **Relabelling, p-value and bootstrap:** as specified in section 4. Pass rule: b > 0 and
  p < 0.05.
- **Secondary cells** (BH family, `config.TEST_B_SECONDARY`):
  - the pooled E1-E3 regression with the linear control, as first specified, reported with its
    synthetic result: 10.5% false positives with no effect and 67% with a saturating echo
    (`results/test_b_synthetic.md`);
  - the E3 test on the narrative, influencer and macro channels;
  - the E3 test with Δ in noise units.
- **When:** BRIEF.md section 4 is updated to match, and says this change was made after the
  synthetic check and before any data was pulled.

*Reason (researcher):* on synthetic data the specified test was fooled by price echoes that are
not linear, and E1 and E2 cannot separate event direction from price direction.

**P3 (Q3) Replayed rows: accepted as a limitation.** The integrity rule cannot detect rows
replayed after an outage that fill a scoring gap. This will be reported as a limitation in
RESULTS.md. *Reason (researcher):* the brief adds no such check.

**D10 Typical daily move, re-dated.** The pilot's M6 window (120 sessions ending 12 May 2026,
the first allowed reading day) becomes the 120 sessions ending 2 October 2026, the first
allowed reading day of this run. *Reason:* the same rule at the new period's edge, made possible
by P1.

**D11 Empty spline terms.** In any one fit (observed, relabelled or bootstrap), a spline term
with no observation beyond its knot is an all-zero column. The fit uses the pseudo-inverse,
which gives the same coefficients as leaving that column out (tested). b is reported as not
estimable only if the intercept, d, r and sign(r) columns are collinear. *Reason:* the outer
knots sit at the 99th percentile, so many relabelled draws have no return beyond them; without
this, those draws would be dropped. In synthetic checks before this rule, a third of the null
draws were lost.

**D12 Events before 2 October are not seen.** Event sources are lock-filtered like sentiment,
so no event from the reserved period is stored. E2 candidates are computed only for reaction
sessions from 2 October, even though prices before then are read (P1). Candidate events with R
in late September therefore cannot screen overlaps or noise sessions at the start of the
period. This will be reported as a limitation. *Reason:* P1 allows prices, not events.

**D13 Primary Test B runs slightly hot (recorded, not changed).** On synthetic data,
`results/test_b_calibration.md` measures the primary Test B under no effect, with E3-like events
and 1,000 replications:

| price echo | share of p-values below 0.05 (SE) |
|---|---|
| none | 6.3% (0.8 points) |
| all three forms at once | 6.1% (0.8 points) |

The echo does not change the rate, so the price controls do their job. The excess over 5%
(about 1.2 points) comes from the design: ratings land on bigger moves and often agree with the
move's sign, so the real estimate of b varies a little more than the relabelled null allows for.
The same table at 200 replications gives 4.5% under every echo. The test is kept as decided
in P2. RESULTS.md will state this calibration next to Test B's p-value. *Reason:* the
researcher fixed the design, and the rate is measured, not tuned.
