"""Throttled SentientMarkets API client (ground rules 9 and 10).

One request at a time, at least API_MIN_INTERVAL_S apart, exponential backoff on
429 and 5xx. The key is read from the environment and never logged.
"""

from __future__ import annotations

import os
import time

import requests
from dotenv import load_dotenv

from .config import API_BASE, API_MAX_RETRIES, API_MIN_INTERVAL_S, ROOT


class FetchError(RuntimeError):
    pass


class Client:
    def __init__(self, min_interval: float = API_MIN_INTERVAL_S, max_retries: int = API_MAX_RETRIES,
                 session: requests.Session | None = None, sleep=time.sleep):
        load_dotenv(ROOT / ".env")
        self._key = os.environ.get("SENTIENT_API_KEY")
        if not self._key:
            raise FetchError("SENTIENT_API_KEY not set in .env")
        self.min_interval = min_interval
        self.max_retries = max_retries
        self.session = session or requests.Session()
        self._sleep = sleep
        self._last = 0.0
        self.n_requests = 0

    def get_json(self, path: str, params: dict | None = None) -> tuple[dict, int, float]:
        """GET and return (json, bytes, seconds). Raises FetchError after retries."""
        last_err = ""
        for attempt in range(self.max_retries):
            wait = self.min_interval - (time.monotonic() - self._last)
            if wait > 0:
                self._sleep(wait)
            t0 = time.monotonic()
            try:
                r = self.session.get(API_BASE + path, params=params, timeout=120,
                                     headers={"Authorization": f"Bearer {self._key}"})
            except requests.RequestException as e:  # network error: back off and retry
                self._last = time.monotonic()
                self.n_requests += 1
                last_err = type(e).__name__
                self._sleep(2 ** (attempt + 2))
                continue
            self._last = time.monotonic()
            self.n_requests += 1
            if r.status_code == 429 or r.status_code >= 500:
                ra = r.headers.get("Retry-After")
                last_err = f"HTTP {r.status_code}"
                self._sleep(float(ra) if ra and ra.replace(".", "").isdigit() else 2 ** (attempt + 2))
                continue
            if r.status_code != 200:
                raise FetchError(f"HTTP {r.status_code} for {path}: {r.text[:200]}")
            return r.json(), len(r.content), self._last - t0
        raise FetchError(f"{path}: gave up after {self.max_retries} attempts ({last_err})")
