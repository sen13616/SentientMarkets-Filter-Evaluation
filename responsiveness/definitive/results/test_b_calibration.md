# Test B calibration on synthetic data (Phase 0; DECISIONS.md D14)

E3-like events (drawn toward bigger moves; about 70% agree with the move's sign), flexible price controls with the frozen knots. 1,000 replications per scenario; each test uses K = 1,000 permutations. Seeds: relabelling 101, Freedman-Lane 202. Each cell is the share of replications with p < 0.05 (standard error in brackets).

| scenario | relabelling (P2) | Freedman-Lane (D14) |
|---|---|---|
| no effect, no echo | 0.065 (0.008) | 0.057 (0.007) |
| no effect, linear echo | 0.063 (0.008) | 0.056 (0.007) |
| no effect, saturating echo | 0.062 (0.008) | 0.047 (0.007) |
| no effect, step echo | 0.068 (0.008) | 0.060 (0.008) |
| no effect, date-wide shock (SD 3 points, common to every event on a date) | 0.069 (0.008) | 0.064 (0.008) |
| planted effect of 1 point, no echo | 0.995 (0.002) | 0.995 (0.002) |

## Pre-registered selection rule (DECISIONS.md D14)

Freedman-Lane becomes the primary Test B if its false-positive rate is between 3.6% and 6.4% in every no-effect scenario and its power at 1 point is at least 90%.

- False-positive rates within 3.6% to 6.4% in every no-effect scenario: **yes** (range 4.7% to 6.4%).
- Power at 1 point at least 90%: **yes** (99.5%).
- **Primary Test B: Freedman-Lane.** The other version is reported as secondary.
