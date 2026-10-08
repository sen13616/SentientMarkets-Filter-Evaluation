# Noise units and power estimate (Phase 0, amended rules)

Built from two-session score changes on noise sessions only: event-period sessions (13 May to 18 June 2026) more than two sessions from any E1, E2 or E3 candidate of the stock (DECISIONS.md A1, A3). No score change around any event was read. Method: see the docstring of `responsiveness/scripts/power.py`.

Data hash `f45f1575e750`; seed 20260512; 1000 null draws.

## Noise sessions per stock

Noise sessions per stock (out of up to 26): min 11, 10th pct 21, median 26, 90th pct 26, max 26. Stocks with fewer than 10: 0.

|        |   11 |   13 |   14 |   15 |   16 |   17 |   18 |   19 |   20 |   21 |   22 |   23 |   24 |   25 |   26 |
|:-------|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|
| stocks |    1 |    4 |    2 |    3 |    7 |    3 |    5 |    6 |    8 |  105 |    8 |    7 |    9 |    5 |  300 |

## Noise units by index

| index                 |   stocks with a noise unit |   excluded: fewer than 10 changes |   excluded: SD = 0 |   median changes used |   median noise unit (pts) | IQR noise unit (pts)   |
|:----------------------|---------------------------:|----------------------------------:|-------------------:|----------------------:|--------------------------:|:-----------------------|
| score                 |                        473 |                                 0 |                  0 |                    26 |                      6.76 | 5.68-7.91              |
| score_exo             |                        473 |                                 0 |                  0 |                    26 |                      9.73 | 8.02-11.61             |
| narrative             |                        470 |                                 3 |                  0 |                    26 |                     19.24 | 15.61-23.51            |
| influencer            |                        471 |                                 0 |                  2 |                    26 |                      8.34 | 6.31-10.29             |
| macro                 |                        473 |                                 0 |                  0 |                    26 |                     16.12 | 15.33-18.47            |
| market (contaminated) |                        472 |                                 1 |                  0 |                    26 |                     12.44 | 11.14-13.91            |

A stock without a noise unit for an index contributes no events to that index's cells.

## Primary cell: score_exo, E1+E2 pooled (amended rule, DECISIONS.md A6)

The cell passes if response p < 0.05, signed-average-move p < 0.05 and the unexplained-move rate is below 50%. The smallest effects detectable with 80% power at the 0.05 level:

|                                      | E1+E2     |
|:-------------------------------------|:----------|
| index                                | score_exo |
| N                                    | 73        |
| placebo rate p0                      | 32.2%     |
| response null 95th pct               | 41.1%     |
| detectable response rate             | 47.0%     |
| detectable signed move (noise units) | 0.32      |
| detectable signed move (pts)         | 2.95      |
| mean noise unit (pts)                | 9.21      |
| moves at p0                          | 24        |
| detectable accuracy at p0            | 80.0%     |
| moves at detectable rate             | 34        |
| detectable accuracy at that rate     | 75.5%     |

## All cells: response and signed move

| index                 | events      |   N | placebo rate p0   | response null 95th pct   | detectable response rate   |   detectable signed move (noise units) |   detectable signed move (pts) |   mean noise unit (pts) |
|:----------------------|:------------|----:|:------------------|:-------------------------|:---------------------------|---------------------------------------:|-------------------------------:|------------------------:|
| score                 | E1          |  52 | 32.8%             | 44.2%                    | 51.5%                      |                                   0.42 |                           2.63 |                    6.24 |
| score                 | E2          |  21 | 32.8%             | 52.4%                    | 64.0%                      |                                   0.59 |                           3.81 |                    6.44 |
| score                 | E1+E2       |  73 | 32.8%             | 42.5%                    | 48.5%                      |                                   0.38 |                           2.4  |                    6.3  |
| score                 | E3          | 120 | 32.8%             | 39.2%                    | 43.5%                      |                                   0.26 |                           1.76 |                    6.7  |
| score                 | E4          | 547 | 32.8%             | 36.0%                    | 38.0%                      |                                   0.09 |                           0.64 |                    6.79 |
| score                 | E4 purchase |  37 | 32.8%             | 45.9%                    | 54.5%                      |                                   0.39 |                           3.05 |                    7.81 |
| score                 | E4 sale     | 510 | 32.8%             | 36.3%                    | 38.5%                      |                                   0.11 |                           0.71 |                    6.72 |
| score_exo             | E1          |  52 | 32.2%             | 44.2%                    | 51.5%                      |                                   0.37 |                           3.4  |                    9.14 |
| score_exo             | E2          |  21 | 32.2%             | 47.6%                    | 59.0%                      |                                   0.52 |                           4.86 |                    9.37 |
| score_exo             | E1+E2       |  73 | 32.2%             | 41.1%                    | 47.0%                      |                                   0.32 |                           2.95 |                    9.21 |
| score_exo             | E3          | 120 | 32.2%             | 39.2%                    | 43.5%                      |                                   0.24 |                           2.34 |                    9.69 |
| score_exo             | E4          | 547 | 32.2%             | 35.1%                    | 37.0%                      |                                   0.1  |                           0.95 |                    9.54 |
| score_exo             | E4 purchase |  37 | 32.2%             | 43.2%                    | 52.0%                      |                                   0.38 |                           4.48 |                   11.66 |
| score_exo             | E4 sale     | 510 | 32.2%             | 35.3%                    | 37.5%                      |                                   0.1  |                           0.98 |                    9.38 |
| narrative             | E1          |  52 | 32.0%             | 44.2%                    | 51.5%                      |                                   0.36 |                           6.53 |                   17.91 |
| narrative             | E2          |  20 | 32.0%             | 50.0%                    | 62.0%                      |                                   0.51 |                           9.3  |                   18.19 |
| narrative             | E1+E2       |  72 | 32.0%             | 43.1%                    | 49.0%                      |                                   0.29 |                           5.27 |                   17.99 |
| narrative             | E3          | 120 | 32.0%             | 37.5%                    | 42.0%                      |                                   0.22 |                           4.39 |                   19.5  |
| narrative             | E4          | 540 | 32.0%             | 35.0%                    | 37.0%                      |                                   0.11 |                           1.96 |                   18.49 |
| narrative             | E4 purchase |  37 | 32.0%             | 43.2%                    | 52.0%                      |                                   0.42 |                           9.49 |                   22.75 |
| narrative             | E4 sale     | 503 | 32.0%             | 35.0%                    | 37.0%                      |                                   0.11 |                           1.97 |                   18.17 |
| influencer            | E1          |  52 | 23.5%             | 36.5%                    | 43.5%                      |                                   0.45 |                           3.53 |                    7.84 |
| influencer            | E2          |  20 | 23.5%             | 45.0%                    | 57.0%                      |                                   0.74 |                           4.79 |                    6.47 |
| influencer            | E1+E2       |  72 | 23.5%             | 36.1%                    | 42.0%                      |                                   0.41 |                           3.05 |                    7.46 |
| influencer            | E3          | 120 | 23.5%             | 30.8%                    | 35.0%                      |                                   0.24 |                           1.87 |                    7.91 |
| influencer            | E4          | 547 | 23.5%             | 27.6%                    | 29.5%                      |                                   0.1  |                           0.87 |                    8.71 |
| influencer            | E4 purchase |  37 | 23.5%             | 35.1%                    | 43.5%                      |                                   0.41 |                           4.05 |                    9.8  |
| influencer            | E4 sale     | 510 | 23.5%             | 27.6%                    | 29.5%                      |                                   0.1  |                           0.9  |                    8.63 |
| macro                 | E1          |  52 | 27.4%             | 36.5%                    | 43.5%                      |                                   0.34 |                           5.86 |                   17.35 |
| macro                 | E2          |  21 | 27.4%             | 42.9%                    | 54.5%                      |                                   0.56 |                          10.48 |                   18.65 |
| macro                 | E1+E2       |  73 | 27.4%             | 34.2%                    | 40.0%                      |                                   0.3  |                           5.23 |                   17.72 |
| macro                 | E3          | 120 | 27.4%             | 33.3%                    | 37.5%                      |                                   0.23 |                           3.84 |                   16.94 |
| macro                 | E4          | 547 | 27.4%             | 29.1%                    | 31.0%                      |                                   0.1  |                           1.62 |                   16.77 |
| macro                 | E4 purchase |  37 | 27.4%             | 40.5%                    | 49.0%                      |                                   0.4  |                           7.01 |                   17.52 |
| macro                 | E4 sale     | 510 | 27.4%             | 29.0%                    | 31.0%                      |                                   0.1  |                           1.72 |                   16.71 |
| market (contaminated) | E1          |  52 | 32.8%             | 44.2%                    | 51.5%                      |                                   0.42 |                           4.91 |                   11.56 |
| market (contaminated) | E2          |  21 | 32.8%             | 52.4%                    | 64.0%                      |                                   0.59 |                           7    |                   11.8  |
| market (contaminated) | E1+E2       |  73 | 32.8%             | 42.5%                    | 48.5%                      |                                   0.35 |                           4.03 |                   11.63 |
| market (contaminated) | E3          | 120 | 32.8%             | 38.3%                    | 43.0%                      |                                   0.26 |                           3.28 |                   12.57 |
| market (contaminated) | E4          | 547 | 32.8%             | 35.5%                    | 37.5%                      |                                   0.09 |                           1.15 |                   12.5  |
| market (contaminated) | E4 purchase |  37 | 32.8%             | 48.6%                    | 57.0%                      |                                   0.39 |                           4.51 |                   11.59 |
| market (contaminated) | E4 sale     | 510 | 32.8%             | 35.9%                    | 38.0%                      |                                   0.1  |                           1.27 |                   12.56 |

## All cells: direction accuracy (reported only; not a pass condition)

| index                 | events      |   moves at p0 | detectable accuracy at p0   |   moves at detectable rate | detectable accuracy at that rate   |
|:----------------------|:------------|--------------:|:----------------------------|---------------------------:|:-----------------------------------|
| score                 | E1          |            17 | 81.5%                       |                         27 | 79.0%                              |
| score                 | E2          |             7 | 97.0%                       |                         13 | 88.0%                              |
| score                 | E1+E2       |            24 | 80.0%                       |                         35 | 73.5%                              |
| score                 | E3          |            39 | 74.0%                       |                         52 | 70.0%                              |
| score                 | E4          |           179 | 61.0%                       |                        208 | 60.0%                              |
| score                 | E4 purchase |            12 | 87.0%                       |                         20 | 80.0%                              |
| score                 | E4 sale     |           167 | 61.0%                       |                        196 | 60.5%                              |
| score_exo             | E1          |            17 | 81.5%                       |                         27 | 79.0%                              |
| score_exo             | E2          |             7 | 97.0%                       |                         12 | 87.0%                              |
| score_exo             | E1+E2       |            24 | 80.0%                       |                         34 | 75.5%                              |
| score_exo             | E3          |            39 | 74.0%                       |                         52 | 70.0%                              |
| score_exo             | E4          |           176 | 61.0%                       |                        202 | 60.5%                              |
| score_exo             | E4 purchase |            12 | 87.0%                       |                         19 | 83.5%                              |
| score_exo             | E4 sale     |           164 | 61.5%                       |                        191 | 60.5%                              |
| narrative             | E1          |            17 | 81.5%                       |                         27 | 79.0%                              |
| narrative             | E2          |             6 | 96.5%                       |                         12 | 87.0%                              |
| narrative             | E1+E2       |            23 | 79.0%                       |                         35 | 73.5%                              |
| narrative             | E3          |            38 | 73.5%                       |                         50 | 70.5%                              |
| narrative             | E4          |           173 | 61.0%                       |                        200 | 60.5%                              |
| narrative             | E4 purchase |            12 | 87.0%                       |                         19 | 83.5%                              |
| narrative             | E4 sale     |           161 | 61.5%                       |                        186 | 60.5%                              |
| influencer            | E1          |            12 | 87.0%                       |                         23 | 79.0%                              |
| influencer            | E2          |             5 | n/a                         |                         11 | 92.5%                              |
| influencer            | E1+E2       |            17 | 81.5%                       |                         30 | 75.0%                              |
| influencer            | E3          |            28 | 76.5%                       |                         42 | 71.5%                              |
| influencer            | E4          |           128 | 63.0%                       |                        161 | 61.5%                              |
| influencer            | E4 purchase |             9 | 91.0%                       |                         16 | 85.5%                              |
| influencer            | E4 sale     |           120 | 63.5%                       |                        150 | 62.0%                              |
| macro                 | E1          |            14 | 89.0%                       |                         23 | 79.0%                              |
| macro                 | E2          |             6 | 96.5%                       |                         11 | 92.5%                              |
| macro                 | E1+E2       |            20 | 80.0%                       |                         29 | 77.5%                              |
| macro                 | E3          |            33 | 74.5%                       |                         45 | 71.5%                              |
| macro                 | E4          |           150 | 62.0%                       |                        170 | 61.5%                              |
| macro                 | E4 purchase |            10 | 92.0%                       |                         18 | 82.5%                              |
| macro                 | E4 sale     |           140 | 62.5%                       |                        158 | 61.5%                              |
| market (contaminated) | E1          |            17 | 81.5%                       |                         27 | 79.0%                              |
| market (contaminated) | E2          |             7 | 97.0%                       |                         13 | 88.0%                              |
| market (contaminated) | E1+E2       |            24 | 80.0%                       |                         35 | 73.5%                              |
| market (contaminated) | E3          |            39 | 74.0%                       |                         52 | 70.0%                              |
| market (contaminated) | E4          |           179 | 61.0%                       |                        205 | 60.5%                              |
| market (contaminated) | E4 purchase |            12 | 87.0%                       |                         21 | 81.0%                              |
| market (contaminated) | E4 sale     |           167 | 61.0%                       |                        194 | 60.5%                              |

## Caveats

- Events are treated as independent. Events cluster in time (common news days), so the real tests will be somewhat less powerful than shown.
- The null here is drawn from noise sessions only. The Phase 2 relabelling draws from every eligible event-period session of the stock, including sessions near E4 and other events (DECISIONS.md M3), so its null rate can differ from p0.
- The signed-move estimate assumes a response of the same size in noise units for every event; a response concentrated in a few events needs a larger average to be detected.
- The unexplained-move rate (the third condition) is not estimated here: its denominator includes changes around events.

