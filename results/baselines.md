# Unfiltered baselines (research window)

Rendered by `scripts/run_baselines.py` from `results/cells/base_*.json`. Data snapshot `panel:1be321402207+prices:badee479f07f`; code `uncommitted`; seed 20261007.

Used universe 473 names. Decisions 2026-04-27 to 2026-06-18; P&L sessions 2026-04-28 to 2026-06-22. Costs 10 bp per side on netted traded notional. Conventions in DECISIONS.md D13 to D18.

| Strategy   |   Sharpe |   Mean daily |   SD daily |   Total return |   Profit factor |   Max DD |   Hit rate |   Trades |   Turnover/day |   Avg gross |   Avg net |   Beta (EW) |   P&L sessions |   Days with entries |
|:-----------|---------:|-------------:|-----------:|---------------:|----------------:|---------:|-----------:|---------:|---------------:|------------:|----------:|------------:|---------------:|--------------------:|
| CSM        |    2.051 |       0.001  |     0.0074 |          0.036 |           1.141 |    0.03  |      0.497 |    1,504 |          0.196 |       1.005 |     0.004 |       0.079 |             38 |                   8 |
| STR        |    2.606 |       0.0018 |     0.0108 |          0.067 |           1.439 |    0.036 |      0.525 |    3,572 |          0.341 |       0.952 |     0.952 |       1.207 |             38 |                  38 |
| TSMOM      |    2.265 |       0.0007 |     0.0052 |          0.028 |           1.721 |    0.019 |      0.385 |      807 |          0.091 |       0.533 |     0.533 |       0.564 |             38 |                  38 |
| BRK        |    3.421 |       0.0005 |     0.0021 |          0.018 |           2.58  |    0.007 |      0.527 |      207 |          0.024 |       0.185 |     0.185 |       0.166 |             38 |                  37 |
| RSI-MR     |    0.956 |       0.0001 |     0.0008 |          0.002 |           1.274 |    0.004 |      0.573 |      117 |          0.013 |       0.082 |     0.082 |       0.077 |             38 |                  34 |
