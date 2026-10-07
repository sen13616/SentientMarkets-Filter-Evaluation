# API findings (Phase 0 contract probe)

Probe run 2026-10-06 23:27 UTC against `https://sentimentapi-p.up.railway.app`, Pro-tier key.
Scripts: `scripts/probe_api.py` (contract probe) and `scripts/probe_reachback.py` (one-ticker
reach-back inspection). Both print to stdout only; no response was written to disk. Total
requests: 24, sent one at a time and at most one every 2.5 s, with no 429 or 5xx responses.

## Summary

| Question | Answer |
|---|---|
| Does history `raw` reach 24 April 2026? | **Yes.** AAPL's earliest row is 2026-04-24 23:55 UTC. The research window holds 3,333 rows for AAPL. |
| Is `score_exo` served in the research window? | **No.** It is null on every research-window row. The first non-null value is 2026-06-23 15:00 UTC. **`score_exo` must be reconstructed for the whole window.** |
| How well does the reconstruction match where `score_exo` is served? | On 369 recent rows (3 tickers × 123): median abs diff 0.003, max 0.0085, which is two-decimal rounding. The served `score_exo` is the unsmoothed per-tick renormalised average of narrative, influencer and macro. |
| Does history serve the smoothed composite? | Yes: `score`, an integer. `label` equals the band of `score` on 100% of window rows. |
| Does history serve the raw composite? | Yes: `score_raw`, an integer. It equals round(weighted sub-indices with the divergence cap) on 99.6% of window rows and is within 1 on 100%. |
| Does history serve the four sub-indices? | Yes. Floats with two decimals, nullable; `market`, `narrative`, `influencer`, `macro`. |
| Does history serve confidence? | Yes: `confidence`, an integer 0–100. |
| Does history serve confidence flags? | **No.** They appear only on the current-state endpoint. |
| Does history serve divergence? | **No.** It appears only on the current-state endpoint, so it must be computed from the sub-indices. |
| Does history serve missing layers? | Yes: `missing_layers`, a list of layer names. |
| Is there a replay or backfill marker? | **No field anywhere in the API.** See "Replayed rows" below. |
| Is history `score` integer-rounded? | Yes, and it is the **smoothed** composite (EMA). `score_raw` is the integer raw composite; the sub-indices and `score_exo` are two-decimal floats. |
| Does `/v1/tickers` separate seed names or expose `delisted_at`? | **No.** It returns `ticker`, `name`, `sector` and `in_sp500` only. It lists the 586 active names (503 with `in_sp500=true`) and **omits delisted names** (HES, PXD and ANSS are absent). |
| How does a delisted ticker behave? | Current endpoint: HTTP 200 with `{"status":"delisted","message":"… stopped trading on <date>; successor: <ticker> …"}`. History with `days=2`: HTTP 200 with an empty list. |
| What is the size and latency? | `raw` with `days=2`: about 27.6 KB and 0.5–1.3 s per ticker. `raw` with `days=166` (needed to reach 24 April): **1.9 MB and 0.9–5.9 s per ticker**. |
| What would the full pull cost? | About 586 requests and roughly **1.1 GB transferred**. At the 2.5 s throttle that is 25–60 minutes. About 39% of rows fall in the research window, so roughly 430 MB of JSON survives the date filter. The daily panel will be a few MB. |

## Endpoints and fields

Documented in the brief: `/health`, `/v1/tickers`, `/v1/sentiment/{ticker}` and `/v1/sentiment/{ticker}/history`.

**Not in the brief, but found in `/openapi.json` (public):**
- `interval=hourly` on history.
- `GET /health/pipeline`.
- `GET /v1/status`, which gives the last run time per job.
- `GET /v1/market/overview`.
- `POST /v1/demo-key`.

None of these is needed.

### `GET /health` (no auth)
`{"status": "ok"}` and nothing else.

### `GET /v1/tickers`
```json
{"universe_size": 586,
 "tickers": [{"ticker": "A", "name": "Agilent Technologies Inc.", "sector": "Health Care", "in_sp500": true}, "..."]}
```
Types: `universe_size` int; `ticker` str; `name` str; `sector` str (one of 11 GICS sectors); `in_sp500` bool.
Class shares use a dot: `BRK.B` and `BF.B`. yfinance needs `BRK-B` and `BF-B`.

### `GET /v1/sentiment/{ticker}?detail=full`
Example (AAPL, values shortened, `top_drivers` truncated):
```json
{"ticker": "AAPL", "score": 58, "score_raw": 59, "score_change_1d": 5.11, "score_change_1d_pct": 9.7,
 "universe_percentile": 56.9, "score_raw_z": 0.28, "score_raw_percentile": 60.9, "sector_percentile": 47.7,
 "score_exo": 58.97, "score_exo_percentile": 50.8, "ema_obs_count": 261, "label": "Neutral", "confidence": 100,
 "sub_indices": {"market": 58.99, "narrative": 59.23, "influencer": 56.84, "macro": 63.52},
 "missing_layers": [], "divergence": "aligned",
 "top_drivers": [{"signal": "News sentiment", "description": "…", "direction": "bearish", "magnitude": 0.9578, "source_layer": "narrative"}],
 "explanation": "…",
 "freshness": {"market_as_of": "…Z", "narrative_as_of": "…Z", "influencer_as_of": "…Z", "macro_as_of": "…Z"},
 "confidence_flags": [], "timestamp": "2026-10-06T23:00:04.431416Z", "cache_age_seconds": 1665,
 "market_hours": {"is_open": false, "next_open": "…Z", "last_close": "…Z"}}
```
Types:
- int: `score`, `score_raw`, `confidence`, `ema_obs_count`, `cache_age_seconds`.
- float: the changes, the percentiles, `score_raw_z`, `score_exo` and the sub-indices.
- str: `label`, `divergence` (for example `aligned`), `explanation`, `timestamp` (ISO 8601, Z).
- list[str]: `missing_layers` and `confidence_flags`. XOM returned a non-empty flags list.

This endpoint shows current state only, so it is not usable for the window.

### `GET /v1/sentiment/{ticker}/history?days=N&interval=raw|daily|hourly`
`days` is an integer from 1 to 365 (default 30), counted back from now. There is **no start or end parameter.** Rows come newest first.
```json
{"ticker": "AAPL",
 "history": [{"timestamp": "2026-10-06T23:00:04.431416Z", "score": 58, "score_raw": 59, "score_exo": 58.97,
              "label": "Neutral", "confidence": 100,
              "sub_indices": {"market": 58.99, "narrative": 59.23, "influencer": 56.84, "macro": 63.52},
              "missing_layers": []}, "..."]}
```
Types: `timestamp` str; `score` int; `score_raw` int or null; `score_exo` float or null; `label` str; `confidence` int; each sub-index float or null; `missing_layers` list[str].

`interval=daily` returns one row per UTC day, which is the last tick of the day (observed at 23:00 or 23:30 UTC). That is after the 21:30 cutoff, so `daily` is unusable, as the brief anticipated.

## Research-window detail (AAPL, rows up to 22 June)

- **First day.** The first tick is 2026-04-24 23:55 UTC, so **no ticker can have a valid state on 24 April**, the first window session. Decisions effectively start on 27 April.
- **Coverage.** There are rows on 60 calendar days. 42 are weekdays, and 41 of those have a tick at or before 21:30 UTC; the exception is 24 April.
- **Cadence.**
  - In session, the median gap is 15 minutes; outside the session it is 30 minutes.
  - On the last tick at or before 21:30, the minute stamp was 21:0x on 28 days, 21:1x on 9, 21:2x on 3 and 20:3x on 1.
  - Ticks carry seconds offsets: the tick scheduled for 21:30 is stamped about 21:30:00.0–21:30:30.
- **Irregular early ticks.** 81 ticks arrive less than 5 minutes after the previous one, mostly in the first days after launch. There are no duplicate timestamps.
- **Missing layers.**
  - Overall: none missing on 88%, market only on 9.7%, macro only on 1.0%, and market plus influencer on 0.9%.
  - One row is missing all three non-market layers, which would make `score_exo` missing.
  - Null shares: market 10.9%, narrative 0.1%, influencer 1.1%, macro 1.3%.
- **Confidence.** Median 90, mean 86.7. 2.9% of rows are below 60.
- **Divergence.** Recomputed as spread > 40 across the four sub-indices, it is high on 2.4% of rows. The divergence cap (one sub-index above 85 while another is below 30) never triggered.

## Things that differ from the documentation or the research doc

1. **Rows exist inside the 23 June – 2 July outage.** AAPL has 256 rows there, and 225 of them carry `score_exo`. The research doc says no rows were written. These rows are presumably offline replays, but the API cannot show that. This has no effect on the research window: the last window row is 2026-06-22 23:30.
2. **There is no replay marker.** The research doc says rebuilt rows carry a replay-run identifier and that the harness excludes them by default. The API does not expose that identifier. From the API alone I cannot confirm that the research window contains only live rows. Nothing in the doc says it was replayed, but this cannot be verified, and it matters more for the holdout (August to October) than for this task.
3. **`score_exo` is not served before 23 June.** The research doc says `score_exo` "is also computed and stored", but it was added on 21 July and not backfilled into the window. The reconstruction in section 5 of the brief reproduces the served values to rounding wherever both exist.
4. **History has no divergence or confidence flags.** Both are served on the current-state endpoint only.
5. **`/v1/tickers` omits the 28 delisted seed names** and does not flag the 112 names added on 3 October. It lists 586 = 474 surviving seed names + 112 additions. The expected used-universe count of about 475 matches the 474 surviving seed names. The research doc says the 3 October additions came with "warm-started histories". If that warm-start wrote sentiment rows back into April–June, the brief's rule ("names with no sentiment rows before June are later additions") may not exclude them. Phase 1 will show this; if the used-universe count lands outside 460–490, I will stop as instructed.
6. **History for delisted names.** The current endpoint says their history "remains available via /history", but they are not in `/v1/tickers`, so the Phase 1 pull will not include them. They would fail the used-universe price rule anyway.
7. **Extra endpoints and `interval=hourly`** exist, as listed above.

## Questions for you before Phase 1

1. **Caching vs the holdout lock.** Ground rule 9 says to cache every response, and ground rule 1 says no post-22-June row may be stored. The API has no end-date parameter, so every response contains post-June rows. My proposal is to cache **the date-filtered rows per ticker** (≤ 22 June 2026), never the raw response. A lost cache would then mean one re-fetch, not a breach of the lock.
2. **Which composite?** Served `score_exo` is unsmoothed. History offers the composite in two forms: `score` (smoothed with the 2-hour EMA) and `score_raw` (unsmoothed). Both are integers. The research doc calls the smoothed value "the served score". My default is the smoothed `score`, recorded in `DECISIONS.md` and labelled market-affected. Using `score_raw` would put the composite and `score_exo` on the same smoothing footing. Tell me if you prefer that.
3. **The 21:30 cutoff boundary.** I will apply it strictly: timestamp ≤ 21:30:00.000 UTC. The scoring tick nominally scheduled for 21:30 is stamped a few seconds after 21:30, so it is excluded and the state usually comes from the 21:00–21:15 ticks. This is the conservative reading of the no-look-ahead rule, and I will record it in `DECISIONS.md`.

## Reach-back call (deviation, approved)

As agreed, I made one call beyond the specified `days=2` probe: AAPL with `days=166`, made twice, once in each script. This was the only way to test the Phase 0 stop condition and to check whether `score_exo` is served in the window. The rows were examined in memory; only the statistics above were kept.
