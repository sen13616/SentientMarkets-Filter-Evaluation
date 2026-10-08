# Test B on synthetic data (Phase 0)

Each cell: share of 200 replications with p < 0.05 (199 relabellings each). 60 stocks, 35 sessions. Scores are noise (SD 3 points) plus a price echo at every session, plus a planted effect of `delta` points in the event's direction at event sessions. Echoes: none; linear (100 x r: a 6% move gives 6 points); saturating (6 x tanh(r / 0.02)); step (4 x sign(r)); all three (their sum). Under delta = 0 a valid test rejects about 5% of the time; above 5% means it can be fooled.

## Test B as first specified (now a secondary cell when pooled over E1-E3): price control c x r

| events | echo | delta = 0 | delta = 1 point | delta = 2 points |
|---|---|---|---|---|
| independent: directions unrelated to price (random sessions) | none | 0.065 | 0.965 | 1.000 |
| independent: directions unrelated to price (random sessions) | linear | 0.065 | 0.965 | 1.000 |
| independent: directions unrelated to price (random sessions) | saturating | 0.075 | 0.940 | 1.000 |
| independent: directions unrelated to price (random sessions) | step | 0.060 | 0.835 | 1.000 |
| independent: directions unrelated to price (random sessions) | all three | 0.075 | 0.680 | 0.985 |
| rating_like: like E3: drawn toward bigger moves, about 70% agree with the move's sign | none | 0.040 | 0.995 | 1.000 |
| rating_like: like E3: drawn toward bigger moves, about 70% agree with the move's sign | linear | 0.040 | 0.995 | 1.000 |
| rating_like: like E3: drawn toward bigger moves, about 70% agree with the move's sign | saturating | 0.555 | 1.000 | 1.000 |
| rating_like: like E3: drawn toward bigger moves, about 70% agree with the move's sign | step | 0.815 | 1.000 | 1.000 |
| rating_like: like E3: drawn toward bigger moves, about 70% agree with the move's sign | all three | 0.915 | 1.000 | 1.000 |
| mixed: E1/E2-like (direction = sign of the move) plus independent, as in the pooled E1-E3 cell | none | 0.105 | 0.985 | 1.000 |
| mixed: E1/E2-like (direction = sign of the move) plus independent, as in the pooled E1-E3 cell | linear | 0.105 | 0.985 | 1.000 |
| mixed: E1/E2-like (direction = sign of the move) plus independent, as in the pooled E1-E3 cell | saturating | 0.670 | 1.000 | 1.000 |
| mixed: E1/E2-like (direction = sign of the move) plus independent, as in the pooled E1-E3 cell | step | 0.250 | 0.965 | 1.000 |
| mixed: E1/E2-like (direction = sign of the move) plus independent, as in the pooled E1-E3 cell | all three | 0.615 | 0.980 | 1.000 |
| price_labelled: like E1/E2 only: direction = sign of the move | none | 0.305 | 0.780 | 0.990 |
| price_labelled: like E1/E2 only: direction = sign of the move | linear | 0.305 | 0.780 | 0.990 |
| price_labelled: like E1/E2 only: direction = sign of the move | saturating | 1.000 | 1.000 | 1.000 |
| price_labelled: like E1/E2 only: direction = sign of the move | step | 1.000 | 1.000 | 1.000 |
| price_labelled: like E1/E2 only: direction = sign of the move | all three | 1.000 | 1.000 | 1.000 |

## Test B as amended (primary on E3): price controls r, sign(r) and a linear spline in r with the frozen knots

| events | echo | delta = 0 | delta = 1 point | delta = 2 points |
|---|---|---|---|---|
| independent: directions unrelated to price (random sessions) | none | 0.060 | 0.965 | 1.000 |
| independent: directions unrelated to price (random sessions) | linear | 0.060 | 0.965 | 1.000 |
| independent: directions unrelated to price (random sessions) | saturating | 0.055 | 0.955 | 1.000 |
| independent: directions unrelated to price (random sessions) | step | 0.060 | 0.965 | 1.000 |
| independent: directions unrelated to price (random sessions) | all three | 0.055 | 0.955 | 1.000 |
| rating_like: like E3: drawn toward bigger moves, about 70% agree with the move's sign | none | 0.045 | 0.995 | 1.000 |
| rating_like: like E3: drawn toward bigger moves, about 70% agree with the move's sign | linear | 0.045 | 0.995 | 1.000 |
| rating_like: like E3: drawn toward bigger moves, about 70% agree with the move's sign | saturating | 0.045 | 0.995 | 1.000 |
| rating_like: like E3: drawn toward bigger moves, about 70% agree with the move's sign | step | 0.045 | 0.995 | 1.000 |
| rating_like: like E3: drawn toward bigger moves, about 70% agree with the move's sign | all three | 0.045 | 0.995 | 1.000 |
| mixed: E1/E2-like (direction = sign of the move) plus independent, as in the pooled E1-E3 cell | none | 0.095 | 0.995 | 1.000 |
| mixed: E1/E2-like (direction = sign of the move) plus independent, as in the pooled E1-E3 cell | linear | 0.095 | 0.995 | 1.000 |
| mixed: E1/E2-like (direction = sign of the move) plus independent, as in the pooled E1-E3 cell | saturating | 0.085 | 0.995 | 1.000 |
| mixed: E1/E2-like (direction = sign of the move) plus independent, as in the pooled E1-E3 cell | step | 0.095 | 0.995 | 1.000 |
| mixed: E1/E2-like (direction = sign of the move) plus independent, as in the pooled E1-E3 cell | all three | 0.085 | 0.995 | 1.000 |
| price_labelled: like E1/E2 only: direction = sign of the move | none | not estimable | not estimable | not estimable |
| price_labelled: like E1/E2 only: direction = sign of the move | linear | not estimable | not estimable | not estimable |
| price_labelled: like E1/E2 only: direction = sign of the move | saturating | not estimable | not estimable | not estimable |
| price_labelled: like E1/E2 only: direction = sign of the move | step | not estimable | not estimable | not estimable |
| price_labelled: like E1/E2 only: direction = sign of the move | all three | not estimable | not estimable | not estimable |

