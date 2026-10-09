# Event counts, pilot (Phase 0, step 5)

Universe: 473 names. Bars: hourly, 2026-05-12 to 2026-06-22 (28 sessions; 92,708 bars for 473 tickers). Event period: t0 from 2026-05-13 to 48 hours before the last tick (2026-06-22 23:30 UTC). Earnings tables: Experiment 5A's yfinance cache (10,842 rows, 473 tickers).

No response has been computed. The only sentiment value read is the stamp of the last tick.

## Kept events

| type | inside session | outside session | all |
|---|---|---|---|
| L-E1 | 0 | 52 | 52 |
| L-E2 | 1261 | 0 | 1261 |
| all | 1261 | 52 | 1313 |

### By week (Monday of the week, New York time)

| week | L-E1 | L-E2 | all |
|---|---|---|---|
| 2026-05-11 | 3 | 99 | 102 |
| 2026-05-18 | 16 | 182 | 198 |
| 2026-05-25 | 16 | 158 | 174 |
| 2026-06-01 | 10 | 294 | 304 |
| 2026-06-08 | 6 | 329 | 335 |
| 2026-06-15 | 1 | 199 | 200 |
| all | 52 | 1261 | 1313 |

### L-E1 release times (New York)

| time | events |
|---|---|
| 06:00 | 13 |
| 07:00 | 4 |
| 08:00 | 1 |
| 16:00 | 34 |

### L-E2 bar start times (New York)

| bar start | events | mean z (adjusted move / normal move) |
|---|---|---|
| 09:30 | 161 | 3.7 |
| 10:30 | 191 | 3.7 |
| 11:30 | 219 | 3.9 |
| 12:30 | 207 | 3.9 |
| 13:30 | 176 | 4.0 |
| 14:30 | 194 | 3.9 |
| 15:30 | 113 | 3.7 |

## Every candidate, by status

Statuses: `kept`; `outside_price_history` (an earnings row from before the bar period; the cache holds several years per stock); `no_time` (earnings without a time of day); `no_reaction_session`; `no_direction` (zero or missing market-adjusted return); `earnings_session` (an L-E2 bar in a session that is or may be an earnings reaction session); `cluster_dropped_for_<type>` (another event of the same stock within 48 hours, of higher priority or earlier); `outside_period`.

| status | L-E1 | L-E2 | all |
|---|---|---|---|
| cluster_dropped_for_L-E1 | 0 | 30 | 30 |
| cluster_dropped_for_L-E2 | 0 | 220 | 220 |
| earnings_session | 0 | 36 | 36 |
| kept | 52 | 1261 | 1313 |
| outside_period | 9 | 92 | 101 |
| outside_price_history | 10781 | 0 | 10781 |
| all | 10842 | 1639 | 12481 |

## L-E2 construction

- Bars tested (a normal move exists for the stock and time of day): 92,708
- Bars without a normal move (fewer than 10 non-earnings bars at that time of day): 0
- Bars over 3 x the normal move: 1,919
- Stock-sessions with such a bar (candidates, first bar per session): 1,639
- Of those in an earnings reaction session (excluded): 36
- Normal-move cells (time of day x ticker): 3,311 available, 0 missing

## Earnings (L-E1) construction

- Rows in the period's calendar range with a time of day: 10841; without: 1
- Stocks with at least one earnings reaction session in the price history: 473

## Clustering

- Candidates entering clustering (directional, not excluded): 1664
- Dropped by clustering: 250 (for L-E2: 220, for L-E1: 30)
- Kept but outside the event period: 101
- Kept, in period: 1313 (52 L-E1, 1261 L-E2; 1261 inside the session, 52 outside)
- Stocks with a kept event: 448
