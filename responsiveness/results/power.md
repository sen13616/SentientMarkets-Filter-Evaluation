# Noise units and power estimate (Phase 0)

Built from two-session score changes on noise sessions only (sessions in the event period more than two sessions from any candidate event of the stock). No score change around any event was read. Method: see the docstring of `responsiveness/scripts/power.py` and DECISIONS.md.

Data hash `f45f1575e750`; seed 20260512; 1000 null draws.

## Noise sessions per stock

Event-period sessions with a defined two-session change: up to 27 per stock. Noise sessions per stock: min 0, 10th pct 9, median 22, 90th pct 27, max 27.

|        |   0 |   1 |   2 |   3 |   4 |   5 |   6 |   7 |   8 |   9 |   10 |   11 |   12 |   13 |   14 |   15 |   16 |   17 |   18 |   19 |   20 |   21 |   22 |   23 |   24 |   25 |   26 |   27 |
|:-------|----:|----:|----:|----:|----:|----:|----:|----:|----:|----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|
| stocks |   4 |   2 |   2 |   3 |   4 |   4 |   5 |  12 |   7 |  10 |    5 |   13 |   10 |    6 |   16 |   11 |   14 |   33 |   18 |   10 |   18 |   14 |   97 |    7 |    7 |   12 |    8 |  121 |

## Noise units by index

| index                 |   stocks with a noise unit |   SD = 0 |   fewer than 2 changes |   median changes used |   median noise unit (pts) | IQR noise unit (pts)   |
|:----------------------|---------------------------:|---------:|-----------------------:|----------------------:|--------------------------:|:-----------------------|
| score                 |                        467 |        0 |                      6 |                    22 |                      6.72 | 5.63-8.05              |
| score_exo             |                        467 |        0 |                      6 |                    22 |                      9.68 | 8.01-11.73             |
| narrative             |                        466 |        0 |                      7 |                    21 |                     19.32 | 15.74-23.81            |
| influencer            |                        465 |        2 |                      6 |                    22 |                      7.85 | 5.80-10.10             |
| macro                 |                        467 |        0 |                      6 |                    22 |                     15.82 | 14.17-18.12            |
| market (contaminated) |                        466 |        0 |                      7 |                    22 |                     12.39 | 10.95-13.95            |

A stock with no noise unit for an index (SD 0 or fewer than 2 changes) cannot have moves measured on that index; its events drop out of that index's cells.

## Primary cell: score_exo, E1 and E2 pooled

|                                          | E1+E2     |
|:-----------------------------------------|:----------|
| index                                    | score_exo |
| N                                        | 76        |
| placebo rate p0                          | 32.4%     |
| null 95th pct                            | 43.4%     |
| detectable response rate                 | 49.0%     |
| moves at p0                              | 25        |
| detectable accuracy (binomial) at p0     | 77.0%     |
| detectable accuracy (primary rule) at p0 | 77.0%     |
| moves at detectable rate                 | 37        |
| detectable accuracy (binomial)           | 72.5%     |
| detectable accuracy (primary rule)       | 72.5%     |

## All cells: detectable response rate

| index                 | events   |   N | placebo rate p0   | null 95th pct   | detectable response rate   |
|:----------------------|:---------|----:|:------------------|:----------------|:---------------------------|
| score                 | E1       |  55 | 32.6%             | 45.5%           | 52.5%                      |
| score                 | E2       |  21 | 32.6%             | 52.4%           | 64.0%                      |
| score                 | E1+E2    |  76 | 32.6%             | 43.4%           | 49.0%                      |
| score                 | E3       | 119 | 32.6%             | 39.5%           | 44.0%                      |
| score                 | E4       | 543 | 32.6%             | 37.9%           | 40.0%                      |
| score_exo             | E1       |  55 | 32.4%             | 45.5%           | 52.5%                      |
| score_exo             | E2       |  21 | 32.4%             | 52.4%           | 64.0%                      |
| score_exo             | E1+E2    |  76 | 32.4%             | 43.4%           | 49.0%                      |
| score_exo             | E3       | 119 | 32.4%             | 40.3%           | 45.0%                      |
| score_exo             | E4       | 543 | 32.4%             | 35.9%           | 38.0%                      |
| narrative             | E1       |  55 | 32.7%             | 47.3%           | 54.0%                      |
| narrative             | E2       |  21 | 32.7%             | 52.4%           | 64.0%                      |
| narrative             | E1+E2    |  76 | 32.7%             | 44.7%           | 50.5%                      |
| narrative             | E3       | 119 | 32.7%             | 38.7%           | 43.0%                      |
| narrative             | E4       | 536 | 32.7%             | 37.1%           | 39.0%                      |
| influencer            | E1       |  55 | 25.0%             | 41.8%           | 48.5%                      |
| influencer            | E2       |  20 | 25.0%             | 50.0%           | 62.0%                      |
| influencer            | E1+E2    |  75 | 25.0%             | 41.3%           | 47.0%                      |
| influencer            | E3       | 119 | 25.0%             | 34.5%           | 39.0%                      |
| influencer            | E4       | 543 | 25.0%             | 35.5%           | 37.5%                      |
| macro                 | E1       |  55 | 27.5%             | 40.0%           | 47.0%                      |
| macro                 | E2       |  21 | 27.5%             | 42.9%           | 54.5%                      |
| macro                 | E1+E2    |  76 | 27.5%             | 39.5%           | 45.0%                      |
| macro                 | E3       | 119 | 27.5%             | 36.1%           | 40.5%                      |
| macro                 | E4       | 543 | 27.5%             | 33.1%           | 35.0%                      |
| market (contaminated) | E1       |  55 | 32.7%             | 47.3%           | 54.0%                      |
| market (contaminated) | E2       |  21 | 32.7%             | 52.4%           | 64.0%                      |
| market (contaminated) | E1+E2    |  76 | 32.7%             | 44.7%           | 50.5%                      |
| market (contaminated) | E3       | 119 | 32.7%             | 39.5%           | 44.0%                      |
| market (contaminated) | E4       | 543 | 32.7%             | 36.8%           | 39.0%                      |

## All cells: detectable direction accuracy

At 80% power. 'Primary rule' means accuracy >= 60% with the 95% interval wholly above 50%.

| index                 | events   |   moves at p0 | detectable accuracy (binomial) at p0   | detectable accuracy (primary rule) at p0   |   moves at detectable rate | detectable accuracy (binomial)   | detectable accuracy (primary rule)   |
|:----------------------|:---------|--------------:|:---------------------------------------|:-------------------------------------------|---------------------------:|:---------------------------------|:-------------------------------------|
| score                 | E1       |            18 | 82.5%                                  | 82.5%                                      |                         29 | 77.5%                            | 77.5%                                |
| score                 | E2       |             7 | 97.0%                                  | 97.0%                                      |                         13 | 88.0%                            | 88.0%                                |
| score                 | E1+E2    |            25 | 77.0%                                  | 77.0%                                      |                         37 | 72.5%                            | 72.5%                                |
| score                 | E3       |            39 | 74.0%                                  | 74.0%                                      |                         52 | 70.0%                            | 70.0%                                |
| score                 | E4       |           177 | 61.0%                                  | 63.5%                                      |                        217 | 60.0%                            | 63.0%                                |
| score_exo             | E1       |            18 | 82.5%                                  | 82.5%                                      |                         29 | 77.5%                            | 77.5%                                |
| score_exo             | E2       |             7 | 97.0%                                  | 97.0%                                      |                         13 | 88.0%                            | 88.0%                                |
| score_exo             | E1+E2    |            25 | 77.0%                                  | 77.0%                                      |                         37 | 72.5%                            | 72.5%                                |
| score_exo             | E3       |            39 | 74.0%                                  | 74.0%                                      |                         54 | 69.5%                            | 69.5%                                |
| score_exo             | E4       |           176 | 61.0%                                  | 63.0%                                      |                        206 | 60.0%                            | 63.0%                                |
| narrative             | E1       |            18 | 82.5%                                  | 82.5%                                      |                         30 | 75.0%                            | 75.0%                                |
| narrative             | E2       |             7 | 97.0%                                  | 97.0%                                      |                         13 | 88.0%                            | 88.0%                                |
| narrative             | E1+E2    |            25 | 77.0%                                  | 77.0%                                      |                         38 | 73.5%                            | 73.5%                                |
| narrative             | E3       |            39 | 74.0%                                  | 74.0%                                      |                         51 | 69.5%                            | 69.5%                                |
| narrative             | E4       |           175 | 61.0%                                  | 63.0%                                      |                        209 | 60.5%                            | 63.0%                                |
| influencer            | E1       |            14 | 89.0%                                  | 89.0%                                      |                         27 | 79.0%                            | 79.0%                                |
| influencer            | E2       |             5 | n/a                                    | n/a                                        |                         12 | 87.0%                            | 87.0%                                |
| influencer            | E1+E2    |            19 | 83.5%                                  | 83.5%                                      |                         35 | 73.5%                            | 73.5%                                |
| influencer            | E3       |            30 | 75.0%                                  | 75.0%                                      |                         46 | 72.0%                            | 72.0%                                |
| influencer            | E4       |           136 | 62.0%                                  | 63.5%                                      |                        204 | 60.0%                            | 63.0%                                |
| macro                 | E1       |            15 | 84.5%                                  | 84.5%                                      |                         26 | 78.0%                            | 78.0%                                |
| macro                 | E2       |             6 | 96.5%                                  | 96.5%                                      |                         11 | 92.5%                            | 92.5%                                |
| macro                 | E1+E2    |            21 | 81.0%                                  | 81.0%                                      |                         34 | 75.5%                            | 75.5%                                |
| macro                 | E3       |            33 | 74.5%                                  | 74.5%                                      |                         48 | 71.5%                            | 71.5%                                |
| macro                 | E4       |           149 | 61.5%                                  | 63.5%                                      |                        190 | 60.5%                            | 63.0%                                |
| market (contaminated) | E1       |            18 | 82.5%                                  | 82.5%                                      |                         30 | 75.0%                            | 75.0%                                |
| market (contaminated) | E2       |             7 | 97.0%                                  | 97.0%                                      |                         13 | 88.0%                            | 88.0%                                |
| market (contaminated) | E1+E2    |            25 | 77.0%                                  | 77.0%                                      |                         38 | 73.5%                            | 73.5%                                |
| market (contaminated) | E3       |            39 | 74.0%                                  | 74.0%                                      |                         52 | 70.0%                            | 70.0%                                |
| market (contaminated) | E4       |           178 | 61.0%                                  | 63.0%                                      |                        212 | 60.0%                            | 63.0%                                |

## Caveats

- Events are treated as independent. Events cluster in time (e.g. common news days), so the bootstrap over event dates in Phase 2 will give wider intervals than the exact binomial interval used here; the detectable accuracies are optimistic.
- The null here is drawn from noise sessions only. Which sessions the Phase 2 relabelling draws from is fixed in Phase 1 (DECISIONS.md); if it includes sessions near events, its null rate will differ from p0.
- The unexplained-move rate (the primary rule's third condition) is not estimated here: its denominator includes changes around events.

