# Primary Test B: false-positive rate on synthetic data (Phase 0)

E3-like events (drawn toward bigger moves; about 70% agree with the move's sign), flexible price controls with the frozen knots, no planted effect. 1,000 replications of 199 relabellings each, seed 99. A test that is exactly calibrated rejects 5% of the time at the 0.05 level.

| price echo | share p < 0.05 (SE) | share p < 0.10 | median p | KS vs uniform, p |
|---|---|---|---|---|
| none | 0.063 (0.008) | 0.122 | 0.495 | 0.168 |
| all three | 0.061 (0.008) | 0.120 | 0.495 | 0.193 |

The rate is the same with and without the echo: the price controls absorb the echo. Both sit slightly above 5%. In this design ratings land on bigger moves and often agree with the move's sign, so the real estimate of b varies a little more than the relabelled null allows for (DECISIONS.md D13).
