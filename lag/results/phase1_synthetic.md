# Phase 1 synthetic checks

The seven checks of BRIEF.md section 7, Phase 1, on synthetic data only (no real ticks or bars). The full test suite is in results/phase1_tests.txt.

| check | result | |
|---|---|---|
| Data lock, all three ranges | lag/tests/test_lock.py: 27 tests pass (pilot range, reserved range, definitive range for prices and for gated sentiment/events, after 23 November, plain dates, gate) | pass |
| Reading selection around t0 | ticks of 10, 20, 30 at t0 - 15 min, t0, t0 + 15 min: before reading 10, S(t0) 20 | pass |
| Planted step of +10 at t0 + 2 h (11:30 New York, tick spacing 15 min) | M 10.00, T½ 1.96 h, T₉₀ 1.99 h, p(M) 0.010 | pass |
| Planted step of +10 at t0 + 5 h (16:00 New York, tick spacing 30 min) | M 9.99, T½ 4.96 h, T₉₀ 4.99 h, p(M) 0.010 | pass |
| Step at t0 through a 2-hour exponential smoother | T½ 1.75 h (continuous smoother: 2.00 h; the tick-wise smoother runs one 15-minute tick ahead), T₉₀ 6.48 h (6.64 h) | pass |
| Alignment, index change equal to the price return 3 hours earlier | best k 3 (95% interval 3 to 3), correlation 1.00 | pass |
| Alignment, index change equal to the price return 0 hours earlier | best k 0 (95% interval 0 to 0), correlation 1.00 | pass |
| Alignment, index unrelated to price | largest correlation 0.063 at k 12; 95% interval for k -10 to 12 (no settled alignment) | pass |
| No planted response: p-values of M over 150 synthetic worlds (8 stocks, 1 event each, K = 199) | share below 0.05: 0.067; below 0.5: 0.473; Kolmogorov-Smirnov p against uniform 0.07 | pass |
| Index that only copies price (one-bar price step at each event) | best k 0 (correlation 1.00); T½ 0.96 h; Rₚ(T½) 1.05 (95% interval 0.97 to 1.17) | pass |

Resolution note: T½ and T₉₀ are interpolated between 5-minute grid points of a step function, so a step exactly on a tick is reported up to half a tick early; every timing is reported next to the tick spacing.
