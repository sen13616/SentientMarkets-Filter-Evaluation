# Experiment 5A, definitive run: October to November 2026

This is the confirmatory run of Experiment 5A ("does the score follow real-world sentiment?"). The pilot (responsiveness/BRIEF.md, RESULTS.md) passed on 73 events from May to June 2026. This run repeats it with the same code and rules, on live data from the repaired system, covering the third-quarter earnings season. It adds one test.

The repository is public. Everything in it must make sense to a reader who has never seen the project.

**Timing.** Phase 0 is done now and committed before 13 October 2026, before the earnings season starts and before any data from the period has been pulled. That commit is the pre-registration. Phases 1 and 2 happen on or after 24 November 2026, once.

## 1. Ground rules

1. **Same code, same rules.** Reuse the `responsiveness` package. Every definition, threshold and decision of the pilot carries over unchanged: BRIEF.md sections 4 to 6, and DECISIONS.md A1 to A7 and M1 to M14. Do not alter the pilot's results or files. New outputs go in `responsiveness/definitive/`, with their own DECISIONS.md, ledger.csv and results/.
2. **Data lock.** Two date ranges are allowed: what the pilot already used (up to 22 June 2026), and 2 October to 23 November 2026. Nothing dated 23 June to 1 October 2026 may be stored or analysed; that period is reserved for a later experiment. The API returns history counted back from today, so filter in memory and discard before writing anything. Nothing after 23 November is used either. Enforce both rules in the loaders and test them.
3. **Run once.** The Phase 2 run is made once. A rerun is allowed only to fix a bug; it is logged with the reason, and the original output is kept.
4. **Nothing tuned.** No threshold or definition changes after Phase 0 is committed. If something turns out to be unworkable, stop and ask.
5. **Counts before outcomes.** Event counts, integrity exclusions and power are reviewed by me before any response is computed.
6. Ledger, numbers from files, interpretive choices recorded, public-repository hygiene, and git handled by me: all as in the pilot brief.

## 2. Fixed parameters

- **Event period:** reaction sessions from 5 October to 20 November 2026. Every reading before an event is then on or after 2 October, and every reading after it is on or before 23 November.
- **Universe:** the pilot's 473 names, less any that do not trade on every session of the period; record any dropped. Names added to the API on 3 October are excluded, as in the pilot.
- **Indices, events, measurements, noise units, placebo dates and tests:** identical to the pilot.
- **Market channel:** repaired on 3 October but still computed from price. It is reported and given no weight, as in the pilot.

## 3. Live-data integrity rule (new)

The system has failed silently before (10 August to 2 October). A session is flagged if any of these holds:

- the scoring history for the universe has a gap of more than 2 hours during the trading session;
- more than 20% of the universe is missing the narrative channel at the 21:30 tick;
- `/v1/status` or the history shows a scheduler outage covering the session.

Any event whose window (sessions R−1 to R+1) touches a flagged session is excluded, and so is any noise or placebo session that is flagged. Report every flagged session and every exclusion. If more than 20% of sessions are flagged, stop and tell me before running anything.

## 4. Added test: response beyond price

> **Amended on 8 October 2026, after the Phase 0 synthetic check and before any data from the
> period was pulled** (DECISIONS.md P2). On synthetic data, the test as first specified was
> fooled by a score that only echoes price, whenever the echo is not linear. Pooled over E1 to
> E3 it gave 10.5% false positives with no effect and 67% with a saturating echo
> (results/test_b_synthetic.md). For E1 and E2 the event direction is the sign of the price
> move, so no regression can separate the two. The original text is kept below the amendment.

For each event e, fit by least squares:

Δₑ = a + b·dₑ + c·rₑ + e·sign(rₑ) + Σₖ fₖ·max(rₑ − κₖ, 0) + εₑ

Here Δₑ is the change in score (pilot definition, in points), dₑ is the event direction (+1 or −1), and rₑ is the stock's market-adjusted close-to-close return over the reaction session Rₑ. The terms in r, sign(r) and the linear spline with knots κₖ absorb any response to the price move that is a function of the move, linear or not. The coefficient b measures how far the score moves with the event's direction beyond what the price move explains.

- **Knots:** ±0.0091, ±0.0289 and ±0.0737, the 50th, 90th and 99th percentiles of the absolute market-adjusted daily return over the pilot's universe and price history (2 January 2025 to 22 June 2026). They were fixed by that rule before any data from the period was pulled, and frozen in config.py.
- **Cell:** score_exo, E3 alone. Analyst actions carry a direction that does not come from the price move.
- **Test (primary, from 9 October 2026):** a Freedman-Lane permutation test. Fit the reduced model (Δ on the intercept, r, sign(r) and the spline terms, without d), permute its residuals across the E3 events, add them back to its fitted values, refit the full model and record b⁽ᵏ⁾. Use K = 1,000 and a fixed seed. p = (1 + number of k with b⁽ᵏ⁾ ≥ b) / 1,001. It was chosen by a rule pre-registered on 9 October 2026 (DECISIONS.md D14), before any data from the period was pulled. On synthetic data its false-positive rate was 4.7% to 6.4% across five no-effect scenarios, and its power at 1 point was 99.5% (results/test_b_calibration.md; D17).
- **Test (secondary):** the pilot's relabelling procedure. Within each stock, draw the same number of random eligible sessions as it has events and give them that stock's event directions. Compute r for those sessions from actual prices, refit, and record b⁽ᵏ⁾. Use K = 1,000 and a fixed seed. p = (1 + number of k with b⁽ᵏ⁾ ≥ b) / 1,001. This was the primary test of the 8 October amendment; on synthetic data it ran at 6.2% to 6.9% false positives.
- **Interval:** the pilot's date bootstrap (B = 2,000) for b and c.
- **Secondary**, in the secondary family with Benjamini-Hochberg adjustment:
  - the E3 test with the relabelling null (above);
  - the regression as first specified (linear control only), pooled over E1, E2 and E3, reported next to its synthetic result (10.5% false positives with no effect, 67% with a saturating echo);
  - the E3 test on the narrative, influencer and macro channels separately;
  - the E3 test with Δₑ in noise units.

**As first specified (superseded, kept for the record):** Δₑ = a + b·dₑ + c·rₑ + εₑ, with the cell score_exo, E1, E2 and E3 pooled. The test and interval were as above. Secondary: the same regression for each channel separately, for E3 alone, and with Δₑ in noise units.

## 5. Primary rules

There are two primary tests. They answer different questions, so each is judged at the 5% level on its own.

- **Test A, responsiveness (repeats the pilot).** score_exo, E1 and E2 pooled. Passes if the response p is below 0.05, the signed-move p is below 0.05 and the unexplained-move rate is below 50%.
- **Test B, beyond price (new).** score_exo, E3 alone, with the price controls of section 4 (as amended on 8 October 2026). Passes if b > 0 and its relabelling p is below 0.05.

Report the pilot's figures next to this run's for every primary measure.

## 6. Phases

**Phase 0, now, before 13 October (checkpoint).**

1. Save this brief as `responsiveness/definitive/BRIEF.md`.
2. Write a config file that freezes every parameter above.
3. Implement the integrity rule, the extended data lock and the regression test.
4. Run synthetic tests only:
   - the extended lock refuses 23 June to 1 October and anything after 23 November;
   - the integrity rule flags planted gaps;
   - with no effect, b has roughly uniform p-values;
   - a planted effect beyond price is detected;
   - **a planted score that only echoes price** (Δ proportional to r, with nothing from d) is not detected. This is the test that matters most: if Test B can be fooled by a score that only reflects price, it cannot answer its question.
5. Stop and show me the test output.

Nothing from the period is pulled in this phase.

**Phase 1, on or after 24 November (checkpoint).**

1. Pull sentiment ticks with the lock applied.
2. Pull prices and events.
3. Apply the integrity rule.
4. Write event counts, exclusions and power for both primary tests. Compute no responses.
5. Stop and show me.

**Phase 2: run once (checkpoint).** Run every cell, ledger each one, and render `responsiveness/definitive/RESULTS.md`. Put the pilot comparison and the two primary verdicts first, then the secondary results, integrity exclusions and limitations. Save null distributions and bootstrap draws, as in the pilot. Stop.

**Phase 3: READMEs.** Update `responsiveness/README.md` and the root README with the definitive result, and keep the pilot described as a pilot. Stop for review before committing.

## 7. Out of scope

- No data from 23 June to 1 October 2026, and none after 23 November.
- No new event types, indices or thresholds beyond section 4.
- No lag measurement and no trading experiments.
- No changes to the API or to the pilot's outputs.

Start with Phase 0.
