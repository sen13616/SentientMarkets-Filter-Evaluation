# Pilot tick cache check (Phase 0, step 3)

Tick cache: 478 tickers on disk; 473 in the pilot universe. Rows from 2026-05-12 to 2026-06-22: 1,094,783 ticks, 473 tickers, first 2026-05-12 00:20 UTC, last 2026-06-22 23:30 UTC.

## What the cache carries

| field | share of ticks |
|---|---|
| score_raw served | 100.0% |
| score present | 100.0% |
| narrative present | 97.9% |
| influencer present | 100.0% |
| macro present | 98.5% |
| market present | 99.8% |
| score_exo present | 100.0% |

`score` differs from `score_raw` on 74.1% of ticks (the published score is the EMA-smoothed composite; in this period its half-life was 4 hours).

## Tick spacing (gap to the previous tick of the same stock)

| where | ticks | p5 | p25 | median | p75 | p95 | most common gaps |
|---|---|---|---|---|---|---|---|
| inside the session | 292,460 | 12.2 | 15.0 | 15.0 | 17.5 | 30.1 | 15 min (65.3%), 30 min (13.8%), 12 min (3.7%), 18 min (3.6%), 19 min (2.3%) |
| outside the session | 801,850 | 15.0 | 30.0 | 30.0 | 30.0 | 31.5 | 30 min (80.0%), 15 min (8.0%), 31 min (1.0%), 29 min (0.9%), 32 min (0.9%) |

Median gap by week (minutes):

| week of | inside session | outside session |
|---|---|---|
| 2026-05-11 | 30 | 30 |
| 2026-05-18 | 15 | 30 |
| 2026-05-25 | 15 | 30 |
| 2026-06-01 | 15 | 30 |
| 2026-06-08 | 15 | 30 |
| 2026-06-15 | 15 | 30 |
| 2026-06-22 | 15 | 30 |

Day by day in May (New York dates), to date the change of schedule inside the session:

| day | median gap inside (min) | share of 15-minute gaps inside | median gap outside (min) |
|---|---|---|---|
| 2026-05-11 | nan | nan% | 30 |
| 2026-05-12 | 30 | 0% | 30 |
| 2026-05-13 | 40 | 7% | 30 |
| 2026-05-14 | 30 | 0% | 30 |
| 2026-05-15 | 30 | 0% | 30 |
| 2026-05-16 | nan | nan% | 34 |
| 2026-05-17 | nan | nan% | 30 |
| 2026-05-18 | 15 | 86% | 30 |
| 2026-05-19 | 15 | 88% | 30 |
| 2026-05-20 | 15 | 88% | 30 |
| 2026-05-21 | 15 | 88% | 30 |
| 2026-05-22 | 15 | 88% | 30 |
| 2026-05-23 | nan | nan% | 30 |
| 2026-05-24 | nan | nan% | 30 |
| 2026-05-25 | nan | nan% | 30 |
| 2026-05-26 | 15 | 88% | 30 |
| 2026-05-27 | 15 | 88% | 30 |
| 2026-05-28 | 15 | 88% | 30 |
| 2026-05-29 | 15 | 88% | 30 |

Ticks per ticker-day: median 61, 5th percentile 44, 95th 61.

Resolution for the pilot: inside the session, 30 minutes up to the session before 2026-05-18 and 15 minutes from 2026-05-18; outside the session, 30 minutes throughout; price bars of 60 minutes. Every timing in the pilot is reported next to these limits.
