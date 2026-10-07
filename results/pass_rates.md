# Filter pass rates (counts only; no returns)

Candidates are the unfiltered entries decided from 2026-04-27. Gate and size thresholds per INSTRUCTIONS.md section 8; size 'pass' = multiplier > 0. Veto passes when confidence >= 60 and divergence is not high; `veto` uses the four-layer divergence (includes the market layer), `veto-exo` the narrative/influencer/macro spread (D21). Rows marked market-affected use the contaminated market layer (D2).

## gate

| strategy   | input                       |   candidates |   missing_state |   pass |   fail_with_state | pass share   |
|:-----------|:----------------------------|-------------:|----------------:|-------:|------------------:|:-------------|
| CSM        | score_exo                   |         1504 |               0 |    461 |              1043 | 30.7%        |
| CSM        | composite (market-affected) |         1504 |               0 |    432 |              1072 | 28.7%        |
| CSM        | narrative                   |         1504 |              56 |    545 |               903 | 36.2%        |
| CSM        | influencer                  |         1504 |               0 |    483 |              1021 | 32.1%        |
| CSM        | macro                       |         1504 |               0 |    533 |               971 | 35.4%        |
| STR        | score_exo                   |         3572 |               0 |   3381 |               191 | 94.7%        |
| STR        | composite (market-affected) |         3572 |               0 |   3317 |               255 | 92.9%        |
| STR        | narrative                   |         3572 |              66 |   2980 |               526 | 83.4%        |
| STR        | influencer                  |         3572 |               0 |   3120 |               452 | 87.3%        |
| STR        | macro                       |         3572 |               0 |   2780 |               792 | 77.8%        |
| TSMOM      | score_exo                   |          807 |               0 |    345 |               462 | 42.8%        |
| TSMOM      | composite (market-affected) |          807 |               0 |    303 |               504 | 37.5%        |
| TSMOM      | narrative                   |          807 |              25 |    350 |               432 | 43.4%        |
| TSMOM      | influencer                  |          807 |               0 |    334 |               473 | 41.4%        |
| TSMOM      | macro                       |          807 |               0 |    498 |               309 | 61.7%        |
| BRK        | score_exo                   |          207 |               0 |    134 |                73 | 64.7%        |
| BRK        | composite (market-affected) |          207 |               0 |    152 |                55 | 73.4%        |
| BRK        | narrative                   |          207 |               3 |    145 |                59 | 70.0%        |
| BRK        | influencer                  |          207 |               0 |     91 |               116 | 44.0%        |
| BRK        | macro                       |          207 |               0 |    132 |                75 | 63.8%        |
| RSI-MR     | score_exo                   |          117 |               0 |     38 |                79 | 32.5%        |
| RSI-MR     | composite (market-affected) |          117 |               0 |      8 |               109 | 6.8%         |
| RSI-MR     | narrative                   |          117 |               3 |     32 |                82 | 27.4%        |
| RSI-MR     | influencer                  |          117 |               0 |     56 |                61 | 47.9%        |
| RSI-MR     | macro                       |          117 |               0 |     69 |                48 | 59.0%        |

## size

| strategy   | input                       |   candidates |   missing_state |   pass |   fail_with_state |   full_size | pass share   |
|:-----------|:----------------------------|-------------:|----------------:|-------:|------------------:|------------:|:-------------|
| CSM        | score_exo                   |         1504 |               0 |    857 |               647 |           4 | 57.0%        |
| CSM        | composite (market-affected) |         1504 |               0 |    957 |               547 |           0 | 63.6%        |
| CSM        | narrative                   |         1504 |              56 |    870 |               578 |         115 | 57.8%        |
| CSM        | influencer                  |         1504 |               0 |    769 |               735 |          10 | 51.1%        |
| CSM        | macro                       |         1504 |               0 |    798 |               706 |          37 | 53.1%        |
| STR        | score_exo                   |         3572 |               0 |   3397 |               175 |         207 | 95.1%        |
| STR        | composite (market-affected) |         3572 |               0 |   3317 |               255 |           7 | 92.9%        |
| STR        | narrative                   |         3572 |              66 |   3016 |               490 |         520 | 84.4%        |
| STR        | influencer                  |         3572 |               0 |   3139 |               433 |         706 | 87.9%        |
| STR        | macro                       |         3572 |               0 |   2791 |               781 |        1487 | 78.1%        |
| TSMOM      | score_exo                   |          807 |               0 |    682 |               125 |           0 | 84.5%        |
| TSMOM      | composite (market-affected) |          807 |               0 |    705 |               102 |           0 | 87.4%        |
| TSMOM      | narrative                   |          807 |              25 |    665 |               117 |          38 | 82.4%        |
| TSMOM      | influencer                  |          807 |               0 |    562 |               245 |          12 | 69.6%        |
| TSMOM      | macro                       |          807 |               0 |    589 |               218 |          14 | 73.0%        |
| BRK        | score_exo                   |          207 |               0 |    196 |                11 |           3 | 94.7%        |
| BRK        | composite (market-affected) |          207 |               0 |    202 |                 5 |           0 | 97.6%        |
| BRK        | narrative                   |          207 |               3 |    194 |                10 |          24 | 93.7%        |
| BRK        | influencer                  |          207 |               0 |    150 |                57 |           3 | 72.5%        |
| BRK        | macro                       |          207 |               0 |    162 |                45 |           3 | 78.3%        |
| RSI-MR     | score_exo                   |          117 |               0 |     84 |                33 |           0 | 71.8%        |
| RSI-MR     | composite (market-affected) |          117 |               0 |     46 |                71 |           0 | 39.3%        |
| RSI-MR     | narrative                   |          117 |               3 |     65 |                49 |           4 | 55.6%        |
| RSI-MR     | influencer                  |          117 |               0 |     83 |                34 |           5 | 70.9%        |
| RSI-MR     | macro                       |          117 |               0 |     86 |                31 |           0 | 73.5%        |

## veto

| strategy   | input                                             |   candidates |   missing_state |   pass |   fail_with_state |   vetoed_low_conf |   vetoed_high_div | pass share   |
|:-----------|:--------------------------------------------------|-------------:|----------------:|-------:|------------------:|------------------:|------------------:|:-------------|
| CSM        | confidence + 4-layer divergence (market-affected) |         1504 |               0 |   1055 |               449 |               151 |               340 | 70.1%        |
| STR        | confidence + 4-layer divergence (market-affected) |         3572 |               0 |   2272 |              1300 |               325 |              1043 | 63.6%        |
| TSMOM      | confidence + 4-layer divergence (market-affected) |          807 |               0 |    525 |               282 |               190 |               108 | 65.1%        |
| BRK        | confidence + 4-layer divergence (market-affected) |          207 |               0 |    156 |                51 |                24 |                30 | 75.4%        |
| RSI-MR     | confidence + 4-layer divergence (market-affected) |          117 |               0 |     57 |                60 |                11 |                52 | 48.7%        |

## veto-exo

| strategy   | input                             |   candidates |   missing_state |   pass |   fail_with_state |   vetoed_low_conf |   vetoed_high_div | pass share   |
|:-----------|:----------------------------------|-------------:|----------------:|-------:|------------------:|------------------:|------------------:|:-------------|
| CSM        | confidence + exo divergence (D21) |         1504 |               0 |   1194 |               310 |               151 |               176 | 79.4%        |
| STR        | confidence + exo divergence (D21) |         3572 |               0 |   2719 |               853 |               325 |               567 | 76.1%        |
| TSMOM      | confidence + exo divergence (D21) |          807 |               0 |    544 |               263 |               190 |                88 | 67.4%        |
| BRK        | confidence + exo divergence (D21) |          207 |               0 |    168 |                39 |                24 |                17 | 81.2%        |
| RSI-MR     | confidence + exo divergence (D21) |          117 |               0 |     87 |                30 |                11 |                21 | 74.4%        |

