# Experiment 5B, definitive run: 2 October to 23 November 2026 (pre-registration)

This folder freezes the definitive run of Experiment 5B ("how quickly does the score respond?")
before any of its sentiment is read. The pilot ([../RESULTS.md](../RESULTS.md), 12 May to 22 June
2026, hourly bars, 4-hour smoothing of the published score) is the dress rehearsal; this run covers
the third-quarter earnings season on 15-minute bars with the system's current 2-hour smoothing. The
commit that adds this folder is tagged `5b-definitive-prereg`; nothing in `config.py` changes after it.

## What is frozen

Every pilot definition, threshold and decision carries over ([../BRIEF.md](../BRIEF.md) sections 3
to 5 as amended; [../DECISIONS.md](../DECISIONS.md) L1 to L17), and `config.py` names what this run
adds or re-dates:

| item | value | source |
|---|---|---|
| period | NYSE sessions 2 October to 23 November 2026; events with t0 from 5 October to 48 hours before the last tick | BRIEF.md Phase 3 |
| bars | 15-minute, regular session for events and alignment; pre- and post-market bars stored too | L18 |
| universe | the pilot's 473 names less any without a regular bar on every period session, from this experiment's bar store; compared with 5A definitive's list in Phase 4 | L20 |
| L-E2 threshold | the \|z\| exceeded by 0.2% of regular in-session bars, pooled over universe and period, computed from the period's bars (prices only) and recorded in `run_meta.json`; the 3x rule stays as the sensitivity cell | L14 |
| primary cells | `score_exo` and `score_raw`, each on L-E1 and on L-E2; the pooled cell is secondary | L14 |
| gate for interpreting timings | relabelling p(M) < 0.05 AND the date-bootstrap 95% interval for M above zero, with both gates' synthetic false-positive rates quoted beside every decision | L17 |
| price curve | Rₚ twice for every cell: regular-session bars only (as in the pilot), and all bars from t0 including extended hours (market return leave-one-out over at least 10 other tickers, else unadjusted) | L18 |
| pre-event drift | d·(S(t0⁻) − S(t0 − 6 h)) with its bootstrap interval, every cell, secondary | L19 |
| inference | K = 1,000 relabellings (5A's test, L9), B = 2,000 date bootstrap, 20 placebo times per event, Holm across the eight horizons, Benjamini-Hochberg across secondary cells | BRIEF.md section 5 |
| seed | 20261005 | config.py |
| resolution | 15-minute ticks in session, 30 outside; 15-minute bars | tick_check.md |
| run once | a rerun only to fix a bug, logged with its reason, the original output kept | BRIEF.md Phase 4 |

The relabelling null itself is unchanged (L9); the investigation of why it runs hot on one family of
synthetic ticks is in [../results/null_investigation.md](../results/null_investigation.md) and its
conclusion in DECISIONS.md (open item, closed before this pre-registration).

## Data and the gate

Prices (the 15-minute store, `python -m lag.scripts.collect_15m`, weekly until 24 November) are
collected now. Sentiment and events for the period come from Experiment 5A's definitive Phase 1
pull and are read only once 5A's definitive results (`responsiveness/definitive/RESULTS.md`) are
committed, on or after 24 November 2026; `lag/lock.py` refuses them before that, and
`python -m lag.definitive.run` stops at the gate.

## Phase 4, on or after 24 November 2026

```
python -m lag.scripts.collect_15m        # final collection, then the coverage report is committed
python -m lag.definitive.run             # once: results/ here, ledger rows in ../ledger.csv
python -m lag.scripts.render_results     # (extended for this run in Phase 4) -> RESULTS.md here, with the pilot's figures beside
```

Phase 4 may extend the renderer (tables and charts) but not the measurement: `config.py`,
`../scripts/run_measures.py`, `../measure.py`, `../inference.py`, `../pipeline.py` and `../events.py`
are frozen with this pre-registration. A change needed to fix a bug is an amendment, dated and
recorded in DECISIONS.md before the rerun.
