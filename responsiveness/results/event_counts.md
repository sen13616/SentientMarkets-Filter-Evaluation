# Event counts (Phase 0)

Event period: reaction sessions from 2026-05-13 to 2026-06-18. Universe: 473 names (the first experiment's used universe). Sources: yfinance (see source_probe.md). Counts only: no score response around any event was computed to produce this file.

Data hash `f45f1575e750`.

## Source coverage

- Tickers fetched: 473 of 473; failed: none.
- Tickers with no rows at all on or before 22 June: earnings 0, ratings 0, insider 2.
- Insider coverage truncated: 1 tickers returned the source's 150-row cap with the oldest row after 2026-05-13, so their insider history does not reach the start of the event period: DELL.

## Events kept, by type and direction

For E4, up = net insider purchase and down = net insider sale; both are also reported as separate cells (DECISIONS.md A2).

|                  |   up |   down |   total |   stocks |
|:-----------------|-----:|-------:|--------:|---------:|
| E1 earnings      |   24 |     28 |      52 |       52 |
| E2 large move    |   12 |      9 |      21 |       20 |
| E3 rating change |   70 |     50 |     120 |       99 |
| E4 insider       |   37 |    510 |     547 |      247 |
| E1+E2 pooled     |   36 |     37 |      73 |       68 |

**Types with fewer than 30 events: E2 large move.**

## Drops and overlaps (candidates with R in the event period)

Columns: `no_time` earnings release without a time of day; `no_direction` zero market-adjusted return (E1) or zero move (E2); `no_window` R-1 or R+1 outside the session list; `e1_reaction_session` an E2 session that is an E1 reaction session for the stock (excluded by definition); `collapsed_into` merged into an earlier overlapping event of the same type and stock (DECISIONS.md A4); `cluster_tie` the earliest member of a same-type cluster whose net direction is zero (cluster dropped); `overlap_Ek` window overlaps a kept higher-ranked event Ek on the same stock. A kept event may stand for a collapsed cluster.

|                  |   candidates |   kept |   e1_reaction_session |   collapsed_into |   cluster_tie |   overlap_E1 |   overlap_E2 |   overlap_E3 |
|:-----------------|-------------:|-------:|----------------------:|-----------------:|--------------:|-------------:|-------------:|-------------:|
| E1 earnings      |           52 |     52 |                     0 |                0 |             0 |            0 |            0 |            0 |
| E2 large move    |           43 |     21 |                    20 |                0 |             0 |            2 |            0 |            0 |
| E3 rating change |          154 |    120 |                     0 |               13 |             2 |           15 |            4 |            0 |
| E4 insider       |          884 |    547 |                     0 |              310 |             0 |           10 |            1 |           16 |

## Same-type clusters (DECISIONS.md A4)

Overlapping same-type events on a stock become one event at the earliest member, with the net direction (E4: signed shares; otherwise majority). 'Clusters reaching past R+1' have members whose reaction session falls after the measured window of the collapsed event.

| type             |   clusters |   events in clusters |   events collapsed |   clusters dropped (tie) |   clusters kept |   largest cluster |   clusters reaching past R+1 |
|:-----------------|-----------:|---------------------:|-------------------:|-------------------------:|----------------:|------------------:|-----------------------------:|
| E1 earnings      |          0 |                    0 |                  0 |                        0 |               0 |                 0 |                            0 |
| E2 large move    |          0 |                    0 |                  0 |                        0 |               0 |                 0 |                            0 |
| E3 rating change |          8 |                   21 |                 13 |                        2 |               2 |                 6 |                            0 |
| E4 insider       |        148 |                  423 |                310 |                        0 |             143 |                11 |                           20 |

## E1 detail

- Releases with R in the period: 52; time of day known: 52; dropped for no time: 0.
- Release times (America/New_York): 06:00 x13, 07:00 x4, 08:00 x1, 16:00 x34.
- Cross-check on kept E1 events: market-adjusted return sign agrees with EPS-surprise sign in 24 of 52 with a nonzero surprise (0 with zero or missing surprise). This cross-check carries no weight (DECISIONS.md A5): nearly every company beat estimates in the period, so the surprise sign hardly varies.

## Overlaps

- Kept events that displaced at least one lower-ranked event: 41.
- Lower-ranked events dropped for overlap, by (kept type -> dropped type): E1 -> E2 2, E1 -> E3 15, E1 -> E4 10, E2 -> E3 4, E2 -> E4 1, E3 -> E4 16.

## Kept events by week of R

| week of (Monday)   |   E1 |   E2 |   E3 |   E4 |
|:-------------------|-----:|-----:|-----:|-----:|
| 2026-05-11         |    3 |    1 |   15 |   83 |
| 2026-05-18         |   16 |    6 |   21 |   97 |
| 2026-05-25         |   16 |    4 |   20 |   78 |
| 2026-06-01         |   10 |    6 |   26 |  118 |
| 2026-06-08         |    6 |    0 |   21 |   94 |
| 2026-06-15         |    1 |    4 |   17 |   77 |

By direction:

| week of (Monday)   |   E1 up |   E1 down |   E2 up |   E2 down |   E3 up |   E3 down |   E4 up |   E4 down |
|:-------------------|--------:|----------:|--------:|----------:|--------:|----------:|--------:|----------:|
| 2026-05-11         |       3 |         0 |       1 |         0 |       7 |         8 |       9 |        74 |
| 2026-05-18         |       7 |         9 |       5 |         1 |      18 |         3 |       9 |        88 |
| 2026-05-25         |       9 |         7 |       2 |         2 |      14 |         6 |       6 |        72 |
| 2026-06-01         |       4 |         6 |       4 |         2 |       9 |        17 |       6 |       112 |
| 2026-06-08         |       1 |         5 |       0 |         0 |      14 |         7 |       5 |        89 |
| 2026-06-15         |       0 |         1 |       0 |         4 |       8 |         9 |       2 |        75 |

Events that would have been kept with R = 12 May, now outside the period (DECISIONS.md A1): 23.

## Events per stock (kept, all types)

- Stocks with at least one kept event: 322 of 473; median 1, max 10.

