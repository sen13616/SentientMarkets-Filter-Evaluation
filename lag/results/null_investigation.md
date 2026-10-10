# Why the relabelling null runs hot: investigation before Phase 3

Synthetic no-response worlds (8 stocks, one event each at 11:30 New York, K = 199), 5 independent seeds x 1,000 worlds per scenario. Pooled standard error of a share near 0.05: 0.003; per seed 0.007.

## A. Replication across seeds

| scenario | seed 11 | seed 12 | seed 13 | seed 14 | seed 15 | pooled share < 0.05 | pooled share < 0.10 | KS p |
|---|---|---|---|---|---|---|---|---|
| main: walk + white | 0.044 | 0.041 | 0.046 | 0.048 | 0.043 | **0.044** | 0.096 | 0.328 |
| white only | 0.044 | 0.043 | 0.035 | 0.041 | 0.046 | **0.042** | 0.097 | 0.464 |
| walk only | 0.045 | 0.055 | 0.049 | 0.035 | 0.043 | **0.045** | 0.098 | 0.003 |

## B. Mechanism probes (main scenario, all seeds pooled)

Share of worlds with p < 0.05 by the share of the world's eight events whose 48-hour window crosses a weekend (Thursday or Friday events; under a random walk these windows hold fewer ticks and so a smaller variance):

| events with a weekend-crossing window | worlds | share p < 0.05 |
|---|---|---|
| 0.00 to 0.25 | 400 | 0.045 |
| 0.25 to 0.50 | 2228 | 0.044 |
| 0.50 to 0.75 | 2044 | 0.045 |
| 0.75 to 1.00 | 328 | 0.040 |

Spearman correlation of the p-value with the weekend-crossing share: -0.014 (p = 0.324); with the smallest pool size in the world: +nan (p = nan). Pool sizes: mean 23.0 sessions, smallest per world 23.0 on average.

## C. Candidate fixes (main scenario, same seeds)

| variant | seed 11 | seed 12 | seed 13 | seed 14 | seed 15 | pooled share < 0.05 | KS p | mean pool size |
|---|---|---|---|---|---|---|---|---|
| main: walk + white | 0.044 | 0.041 | 0.046 | 0.048 | 0.043 | **0.044** | 0.328 | 23.0 |
| F1: main, pool matched on weekend-crossing class | 0.048 | 0.043 | 0.043 | 0.052 | 0.052 | **0.048** | 0.118 | 12.0 |
| F2: main, non-event radius 1 session | 0.047 | 0.032 | 0.045 | 0.051 | 0.050 | **0.045** | 0.345 | 25.0 |

Run time 6794 s. The reading of these tables is in DECISIONS.md (open item, closed before Phase 3).

## D. Reproduction of the pre-pilot check (10 October 2026)

`python -m lag.scripts.null_check 1000` rerun with the Phase 3 code (seed 7, the single seed of the
pre-pilot check) gives exactly the committed results/null_check.md: 6.8% of relabelling p-values
below 0.05 and 4.8% for the combined gate in the main scenario, and the same figures in every other
variant; only the run-time seconds differ. The 6.8% is therefore a fluctuation of that seed (3.4
pooled standard errors from the five-seed rate above), not a change in the code between the two runs.
