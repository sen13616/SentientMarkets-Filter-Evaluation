# Are article publication times available from the API? (Phase 0, step 6)

Checked from documentation only, with no data calls: the repository's API contract probe
(`API_FINDINGS.md`, written from the public `/openapi.json` and the documented endpoints on
6 October 2026) and the research document's description of the system.

**Answer: no.** The API exposes no article list and no publication time.

| what the API serves | where | usable as an article time? |
|---|---|---|
| `top_drivers`: signal name, description, direction, magnitude, source layer | current state only (`/v1/sentiment/{ticker}?detail=full`) | no: a summary of the drivers behind the current score, with no article identity, count or time |
| `freshness.narrative_as_of` | current state only | no: the time the narrative channel was last computed, not when any article was published |
| `missing_layers`, `confidence`, `label` | current state and history | no |
| history rows (`/v1/sentiment/{ticker}/history`) | per tick: score, score_raw, score_exo, sub-indices | no article fields at all |

Endpoints listed in `/openapi.json` beyond the documented four: `/health/pipeline`, `/v1/status`
(last run time per job), `/v1/market/overview`, `POST /v1/demo-key`. None serves articles.

The research document (section 3.6) says that articles are stored internally with their metadata
and that text is blanked after 30 days, but that store is not reachable through the API. News
bursts are therefore excluded as an event type for this experiment, as the brief anticipated.
Analyst rating changes and insider transactions are excluded too: their sources (yfinance) give a
date, not a time, and Experiment 5A's probe found the same (DECISIONS.md L5).

If news-burst events are wanted later, they need either an articles endpoint on the API or a paid
news feed with publication times; both are out of scope here.
