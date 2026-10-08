# Event counts (Phase 0)

Event period: reaction sessions from 2026-05-12 to 2026-06-18. Universe: 473 names (the first experiment's used universe). Sources: yfinance (see source_probe.md). Counts only: no score response around any event was computed to produce this file.

Data hash `f45f1575e750`.

## Source coverage

- Tickers fetched: 473 of 473; failed: none.
- Tickers with no rows at all on or before 22 June: earnings 0, ratings 0, insider 2.
- Insider coverage truncated: 1 tickers returned the source's 150-row cap with the oldest row after 2026-05-12, so their insider history does not reach the start of the event period: DELL.

## Events kept, by type and direction

|                  |   up |   down |   total |   stocks |
|:-----------------|-----:|-------:|--------:|---------:|
| E1 earnings      |   27 |     30 |      57 |       57 |
| E2 large move    |   12 |      9 |      21 |       20 |
| E3 rating change |   72 |     50 |     122 |      101 |
| E4 insider       |   38 |    559 |     597 |      254 |
| E1+E2 pooled     |   39 |     39 |      78 |       73 |

**Types with fewer than 30 events: E2 large move.**

## Drops and overlaps (candidates with R in the event period)

Columns: `no_time` earnings release without a time of day; `no_direction` zero market-adjusted return (E1) or zero move (E2); `no_window` R-1 or R+1 outside the session list; `e1_reaction_session` an E2 session that is an E1 reaction session for the stock (excluded by definition); `same_type_overlap` window overlaps an earlier kept event of the same type and stock; `same_type_conflict` a kept event whose window holds a same-type event of the opposite direction (both dropped); `overlap_Ek` window overlaps a kept higher-ranked event Ek on the same stock.

|                  |   candidates |   kept |   e1_reaction_session |   same_type_overlap |   same_type_conflict |   overlap_E1 |   overlap_E2 |   overlap_E3 |
|:-----------------|-------------:|-------:|----------------------:|--------------------:|---------------------:|-------------:|-------------:|-------------:|
| E1 earnings      |           57 |     57 |                     0 |                   0 |                    0 |            0 |            0 |            0 |
| E2 large move    |           45 |     21 |                    22 |                   0 |                    0 |            2 |            0 |            0 |
| E3 rating change |          156 |    122 |                     0 |                  13 |                    2 |           15 |            4 |            0 |
| E4 insider       |          909 |    597 |                     0 |                 280 |                    4 |           10 |            1 |           17 |

## E1 detail

- Releases with R in the period: 57; time of day known: 57; dropped for no time: 0.
- Release times (America/New_York): 06:00 x14, 07:00 x4, 08:00 x1, 16:00 x37, 17:00 x1.
- Cross-check on kept E1 events: market-adjusted return sign agrees with EPS-surprise sign in 25 of 57 with a nonzero surprise (0 with zero or missing surprise).

## Overlaps

- Kept events that displaced at least one lower-ranked event: 43.
- Lower-ranked events dropped for overlap, by (kept type -> dropped type): E1 -> E2 2, E1 -> E3 15, E1 -> E4 10, E2 -> E3 4, E2 -> E4 1, E3 -> E4 17.

## Kept events by week of R

| week of (Monday)   |   E1 |   E2 |   E3 |   E4 |
|:-------------------|-----:|-----:|-----:|-----:|
| 2026-05-11         |    8 |    1 |   17 |  104 |
| 2026-05-18         |   16 |    6 |   21 |  101 |
| 2026-05-25         |   16 |    4 |   20 |   82 |
| 2026-06-01         |   10 |    6 |   26 |  125 |
| 2026-06-08         |    6 |    0 |   21 |  102 |
| 2026-06-15         |    1 |    4 |   17 |   83 |

By direction:

| week of (Monday)   |   E1 up |   E1 down |   E2 up |   E2 down |   E3 up |   E3 down |   E4 up |   E4 down |
|:-------------------|--------:|----------:|--------:|----------:|--------:|----------:|--------:|----------:|
| 2026-05-11         |       6 |         2 |       1 |         0 |       9 |         8 |      11 |        93 |
| 2026-05-18         |       7 |         9 |       5 |         1 |      18 |         3 |       7 |        94 |
| 2026-05-25         |       9 |         7 |       2 |         2 |      14 |         6 |       6 |        76 |
| 2026-06-01         |       4 |         6 |       4 |         2 |       9 |        17 |       5 |       120 |
| 2026-06-08         |       1 |         5 |       0 |         0 |      14 |         7 |       6 |        96 |
| 2026-06-15         |       0 |         1 |       0 |         4 |       8 |         9 |       3 |        80 |

Events with R = 12 May (their 'before' reading is the 11 May state): 25 (E1 5, E3 2, E4 18).

## Events per stock (kept, all types)

- Stocks with at least one kept event: 330 of 473; median 1, max 14.

