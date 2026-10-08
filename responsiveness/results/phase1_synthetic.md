# Phase 1 synthetic checks

Synthetic world: 40 stocks, 30 sessions, 2 events per stock (N = 80); scores are unit random walks; noise unit = sqrt(2).

## Null: random event dates, 500 replications (199 relabellings each)

| test | share p < 0.05 | share p < 0.10 | median p | KS vs uniform, p |
|---|---|---|---|---|
| response (test 1) | 0.036 | 0.062 | 0.550 | 0.008 |
| signed move (test 3) | 0.048 | 0.096 | 0.510 | 0.561 |
| direction, exact binomial | 0.024 | 0.072 | 0.612 | 0.000 |

The exact binomial test is discrete and conservative, so it is not expected to be uniform.

## Planted responses (999 relabellings, 2,000 bootstrap draws)

| plant | response rate | direction accuracy (95% CI) | signed move | p response | p signed | p binomial |
|---|---|---|---|---|---|---|
| 0.5 noise units, right way | 0.40 | 0.84 (0.73-0.96) | +0.74 | 0.143 | 0.001 | 0.000113 |
| 0.5 noise units, wrong way | 0.39 | 0.19 (0.08-0.32) | -0.69 | 0.172 | 1.000 | 0.000878 |
| 1.0 noise units, right way | 0.55 | 0.95 (0.89-1.00) | +1.46 | 0.001 | 0.001 | 1.13e-10 |
| 1.0 noise units, wrong way | 0.50 | 0.03 (0.00-0.08) | -1.41 | 0.002 | 1.000 | 7.46e-11 |
| 2.0 noise units, right way | 0.84 | 1.00 (1.00-1.00) | +2.89 | 0.001 | 0.001 | 1.36e-20 |
| 2.0 noise units, wrong way | 0.82 | 0.00 (0.00-0.00) | -2.84 | 0.001 | 1.000 | 2.71e-20 |
