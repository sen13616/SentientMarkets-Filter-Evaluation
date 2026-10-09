# Event counts, pilot (Phase 0, step 5, as amended by L14)

Universe: 473 names. Bars: 1h, 2026-05-12 to 2026-06-22 (28 sessions; 92,708 bars for 473 tickers). Event period: t0 from 2026-05-13 to 48 hours before the last tick (2026-06-22 23:30 UTC). Earnings tables: Experiment 5A's yfinance cache (10,842 rows, 473 tickers).

No response has been computed. The only sentiment value read is the stamp of the last tick.

## L-E2 rarity threshold (L14)

Pooled over 92,708 in-session bars with a standardised move, the |z| exceeded by 0.2% of bars is **5.1503**; the value fixed in config for this run is 5.1503.
For comparison, |z| > 3 is exceeded by 2.07% of bars.

| |z| quantile | value |
|---|---|
| 0.990 | 3.616 |
| 0.995 | 4.208 |
| 0.998 | 5.150 |
| 0.999 | 5.905 |

Statuses: `kept`; `outside_price_history` (an earnings row from before the bar period; the cache holds several years per stock); `no_time` (earnings without a time of day); `no_reaction_session`; `no_direction` (zero or missing market-adjusted return); `earnings_session` (an L-E2 bar in a session that is or may be an earnings reaction session); `cluster_dropped_for_<type>` (another event of the same stock within 48 hours, of higher priority or earlier); `outside_period`.

## Primary event set (L-E1; L-E2 with the rarity threshold)

L-E2 threshold: |z| > 5.1503, where z is the bar's market-adjusted move over the stock's normal move for that time of day.

### Kept events

| type | inside session | outside session | all |
|---|---|---|---|
| L-E1 | 0 | 52 | 52 |
| L-E2 | 130 | 0 | 130 |
| all | 130 | 52 | 182 |

### By week (Monday of the week, New York time)

| week | L-E1 | L-E2 | all |
|---|---|---|---|
| 2026-05-11 | 3 | 12 | 15 |
| 2026-05-18 | 16 | 14 | 30 |
| 2026-05-25 | 16 | 19 | 35 |
| 2026-06-01 | 10 | 29 | 39 |
| 2026-06-08 | 6 | 31 | 37 |
| 2026-06-15 | 1 | 25 | 26 |
| all | 52 | 130 | 182 |

### L-E1 release times (New York)

| time | events |
|---|---|
| 06:00 | 13 |
| 07:00 | 4 |
| 08:00 | 1 |
| 16:00 | 34 |

### L-E2 bar start times (New York)

| bar start | events | mean |z| |
|---|---|---|
| 09:30 | 12 | 6.2 |
| 10:30 | 15 | 6.0 |
| 11:30 | 23 | 6.7 |
| 12:30 | 18 | 7.3 |
| 13:30 | 31 | 6.3 |
| 14:30 | 23 | 7.0 |
| 15:30 | 8 | 6.3 |

### Every candidate, by status

| status | L-E1 | L-E2 | all |
|---|---|---|---|
| cluster_dropped_for_L-E1 | 0 | 8 | 8 |
| cluster_dropped_for_L-E2 | 0 | 6 | 6 |
| earnings_session | 0 | 16 | 16 |
| kept | 52 | 130 | 182 |
| outside_period | 9 | 9 | 18 |
| outside_price_history | 10781 | 0 | 10781 |
| all | 10842 | 169 | 11011 |

### L-E2 construction

- Bars tested (a normal move exists for the stock and time of day): 92,708
- Bars without a normal move (fewer than 10 non-earnings bars at that time of day): 0
- Bars over the threshold: 186 (0.20% of bars tested)
- Stock-sessions with such a bar (candidates, first bar per session): 169
- Of those in an earnings reaction session (excluded): 16

### Clustering

- Candidates entering clustering (directional, in the price history, not excluded): 214
- Dropped by clustering: 14 (for L-E1: 8, for L-E2: 6)
- Kept but outside the event period: 18
- Kept, in period: 182 (52 L-E1, 130 L-E2; 130 inside the session, 52 outside)
- Stocks with a kept event: 154

### Concentration of L-E2 events across stocks

- Stocks with an L-E2 event: 111; mean per stock 1.17, median 1
- Largest number for one stock: 3 (IBM)
- Share held by the 10 stocks with most events: 16.2% (21 of 130)
- Stocks with 1 event: 93; with 2: 17; with 3 or more: 1

## Sensitivity event set (L-E1; L-E2 with |z| > 3, the original rule)

L-E2 threshold: |z| > 3.0000, where z is the bar's market-adjusted move over the stock's normal move for that time of day.

### Kept events

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

| bar start | events | mean |z| |
|---|---|---|
| 09:30 | 161 | 3.7 |
| 10:30 | 191 | 3.7 |
| 11:30 | 219 | 3.9 |
| 12:30 | 207 | 3.9 |
| 13:30 | 176 | 4.0 |
| 14:30 | 194 | 3.9 |
| 15:30 | 113 | 3.7 |

### Every candidate, by status

| status | L-E1 | L-E2 | all |
|---|---|---|---|
| cluster_dropped_for_L-E1 | 0 | 30 | 30 |
| cluster_dropped_for_L-E2 | 0 | 220 | 220 |
| earnings_session | 0 | 36 | 36 |
| kept | 52 | 1261 | 1313 |
| outside_period | 9 | 92 | 101 |
| outside_price_history | 10781 | 0 | 10781 |
| all | 10842 | 1639 | 12481 |

### L-E2 construction

- Bars tested (a normal move exists for the stock and time of day): 92,708
- Bars without a normal move (fewer than 10 non-earnings bars at that time of day): 0
- Bars over the threshold: 1,919 (2.07% of bars tested)
- Stock-sessions with such a bar (candidates, first bar per session): 1,639
- Of those in an earnings reaction session (excluded): 36

### Clustering

- Candidates entering clustering (directional, in the price history, not excluded): 1664
- Dropped by clustering: 250 (for L-E2: 220, for L-E1: 30)
- Kept but outside the event period: 101
- Kept, in period: 1313 (52 L-E1, 1261 L-E2; 1261 inside the session, 52 outside)
- Stocks with a kept event: 448

### Concentration of L-E2 events across stocks

- Stocks with an L-E2 event: 445; mean per stock 2.83, median 3
- Largest number for one stock: 7 (AAL)
- Share held by the 10 stocks with most events: 5.0% (63 of 1261)
- Stocks with 1 event: 81; with 2: 120; with 3 or more: 244

## Normal moves

- Normal-move cells (time of day x ticker): 3,311 available, 0 missing
- Stocks with at least one earnings reaction session in the price history: 473
