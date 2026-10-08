# Source probe (Phase 0)

yfinance 1.7.0; probed 2026-10-07 on AAPL, JPM, NKE, KO, CRWD. Coverage is shown after the data lock: rows stamped after 2026-06-22 were dropped in memory and only counted.

## Fields

- **earnings**: Ticker.get_earnings_dates(limit=12): index 'Earnings Date' (tz-aware, America/New_York); EPS Estimate, Reported EPS, Surprise(%)
- **ratings**: Ticker.upgrades_downgrades: index GradeDate (naive timestamp); Firm, ToGrade, FromGrade, Action, priceTargetAction, currentPriceTarget, priorPriceTarget
- **insider**: Ticker.insider_transactions: Shares, Value, URL, Text, Insider, Position, Transaction, Start Date, Ownership

## Coverage

| ticker   | source   |   rows returned |   dropped (after lock) | earliest kept   | latest kept   |   rows 12 May-22 Jun |
|:---------|:---------|----------------:|-----------------------:|:----------------|:--------------|---------------------:|
| AAPL     | earnings |              25 |                      2 | 2020-10-29      | 2026-04-30    |                    0 |
| AAPL     | ratings  |             971 |                     35 | 2012-09-12      | 2026-06-22    |                   11 |
| AAPL     | insider  |              80 |                     16 | 2024-10-15      | 2026-06-16    |                    5 |
| JPM      | earnings |              25 |                      2 | 2020-10-13      | 2026-04-14    |                    0 |
| JPM      | ratings  |             445 |                     19 | 2012-02-29      | 2026-04-17    |                    0 |
| JPM      | insider  |             150 |                      8 | 2025-01-21      | 2026-06-22    |                    7 |
| NKE      | earnings |              25 |                      3 | 2020-12-18      | 2026-03-31    |                    0 |
| NKE      | ratings  |             894 |                     61 | 2012-02-08      | 2026-06-10    |                    3 |
| NKE      | insider  |              96 |                     28 | 2024-10-14      | 2026-06-12    |                    3 |
| KO       | earnings |              25 |                      2 | 2020-10-22      | 2026-04-28    |                    0 |
| KO       | ratings  |             301 |                     14 | 2012-02-08      | 2026-06-12    |                    5 |
| KO       | insider  |              95 |                     10 | 2024-11-08      | 2026-06-10    |                   11 |
| CRWD     | earnings |              25 |                      2 | 2020-12-02      | 2026-06-03    |                    1 |
| CRWD     | ratings  |             848 |                     73 | 2019-07-08      | 2026-06-04    |                   45 |
| CRWD     | insider  |             150 |                     65 | 2026-03-06      | 2026-06-22    |                   50 |

## Earnings: times of day present (America/New_York)

- AAPL: 16:00
- JPM: 06:00
- NKE: 16:00
- KO: 06:00, 07:00
- CRWD: 16:00

## Ratings: action labels (kept rows)

- AAPL: main=689, reit=161, down=35, up=33, init=18
- JPM: main=307, down=46, up=44, init=17, reit=12
- NKE: main=632, down=61, up=57, init=54, reit=29
- KO: main=196, init=33, up=27, down=25, reit=6
- CRWD: main=561, reit=102, init=58, down=28, up=26

## Insider: transaction kinds from the Text field (kept rows; the Transaction column is empty)

- AAPL: (blank)=35, Sale=23, Stock Gift=6
- JPM: Sale=63, (blank)=35, Stock Award(Grant)=32, Stock Gift=12
- NKE: Stock Award(Grant)=28, Sale=16, Purchase=11, Stock Gift=9, Conversion of Exercise of derivative sec=3, (blank)=1
- KO: Sale=35, Stock Award(Grant)=25, Conversion of Exercise of derivative sec=20, Stock Gift=4, Purchase=1
- CRWD: Sale=62, Stock Award(Grant)=18, Stock Gift=4, (blank)=1
