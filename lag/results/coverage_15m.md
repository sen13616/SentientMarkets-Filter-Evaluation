# 15-minute bar coverage, 2 October to 23 November 2026

Store: `$SM_DATA_DIR/lag/bars_15m.parquet` (local, not committed). Coverage is measured against NYSE sessions up to 2026-10-08 (5 of the period's 37 sessions so far).

Last collection: 2026-10-09T10:14:48+00:00 (yfinance 1.7.0); 2 run(s) so far; last run added 28630 bars, found 61405 already stored, 0 of those with different values (the stored values are kept).

| | value |
|---|---|
| tickers | 473 |
| tickers with every expected bar | 471 |
| bars stored (universe, sessions done) | 61,405 |
| bars expected | 61,490 |
| bars missing | 85 |
| extended-hours bars stored (pre- and post-market, L18; not counted above) | 27,786 |

## By session

| session | bars per ticker expected | tickers with bars | tickers complete | bars missing |
|---|---|---|---|---|
| 2026-10-02 | 26 | 473 | 473 | 0 |
| 2026-10-05 | 26 | 473 | 472 | 1 |
| 2026-10-06 | 26 | 472 | 472 | 26 |
| 2026-10-07 | 26 | 472 | 471 | 27 |
| 2026-10-08 | 26 | 472 | 471 | 31 |

## Tickers with missing bars

| ticker | sessions with bars | sessions complete | bars | bars missing |
|---|---|---|---|---|
| WBD | 2 | 2 | 52 | 78 |
| CACC | 5 | 2 | 123 | 7 |

Gaps (ticker-sessions with fewer bars than expected): 6.
