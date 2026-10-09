# Null check of the relabelling test and of the combined gate (before the pilot)

1000 synthetic worlds per variant with no planted response: 8 stocks with one event each at 11:30 New York on a random session, K = 199 relabellings, seed 7 (the scenario of lag/tests/test_inference.py). The agreed band for the share of p-values below 0.05 is 3.6% to 6.4%. The combined gate (DECISIONS.md L17) requires the relabelling p below 0.05 and the date-bootstrap 95% interval for M (B = 2000) wholly above zero.

| variant | relabelling: share p < 0.05 | share < 0.10 | share < 0.50 | KS p (uniform) | in band | bootstrap: share with interval above 0 | combined gate: false-positive rate | seconds |
|---|---|---|---|---|---|---|---|---|
| main: random walk + white noise, pool on any non-event session | 0.068 | 0.124 | 0.521 | 0.057 | NO | 0.086 | **0.048** | 23 |
| white noise only | 0.043 | 0.106 | 0.507 | 0.323 | yes | 0.071 | **0.030** | 23 |
| random walk only | 0.047 | 0.090 | 0.486 | 0.762 | yes | 0.055 | **0.027** | 23 |
| random walk + white noise, pool restricted to the event's weekday | 0.083 | 0.128 | 0.529 | 0.040 | NO | 0.086 | **0.049** | 19 |

Binomial standard error of a share near 0.05 with 1000 worlds: 0.007.

**Headline (main scenario): relabelling alone 6.8% false positives; combined gate 4.8%.** These two rates are quoted in RESULTS.md next to every gate decision.

Reading: the share is about two standard errors above 5% in the main scenario and within the band for white noise alone and for a random walk alone, so the excess appears only when the two are combined; its cause is not pinned down here. Restricting the pool to the event's weekday shrinks each pool to about four sessions and makes the null coarser, not better. The synthetic worlds are a stand-in: how the real ticks move over 48 hours is not known before the run.
