"""Phase 1 tests: holdout lock, state selection timing, resumable pull. Synthetic data only."""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from filter_eval import ingest
from filter_eval.api import FetchError
from filter_eval.holdout import HoldoutViolation, assert_locked, drop_after_lock
from filter_eval.panel import (build_state_panel, divergence_spread, label_band,
                               reconstruct_exo, window_sessions)


def row(ts, score=55, exo=None, n=60.0, i=55.0, m=50.0, mk=52.0, conf=90):
    return {"timestamp": ts, "score": score, "score_raw": score, "score_exo": exo, "label": "Neutral",
            "confidence": conf, "missing_layers": [],
            "sub_indices": {"market": mk, "narrative": n, "influencer": i, "macro": m}}


class FakeClient:
    def __init__(self, bodies: dict, fail: dict | None = None):
        self.bodies, self.fail, self.calls = bodies, dict(fail or {}), []

    def get_json(self, path, params=None):
        t = path.split("/")[3]
        self.calls.append(t)
        if self.fail.get(t, 0) > 0:
            self.fail[t] -= 1
            raise FetchError(f"{path}: gave up (HTTP 503)")
        return self.bodies[t], 100, 0.01


# --- holdout lock ------------------------------------------------------------

def test_drop_after_lock_boundary():
    df = pd.DataFrame({"ts": pd.to_datetime(["2026-06-22T23:59:59Z", "2026-06-23T00:00:00Z",
                                             "2026-04-24T23:55:00Z"], utc=True)})
    kept, n = drop_after_lock(df, "ts")
    assert n == 1 and len(kept) == 2
    assert kept["ts"].max() == pd.Timestamp("2026-06-22T23:59:59Z")


def test_assert_locked_raises_on_post_window_rows_and_dates():
    bad = pd.DataFrame({"ts": pd.to_datetime(["2026-07-01T10:00:00Z"], utc=True)})
    with pytest.raises(HoldoutViolation):
        assert_locked(bad, "ts")
    bad_dates = pd.DataFrame({"date": [date(2026, 6, 22), date(2026, 6, 23)]})
    with pytest.raises(HoldoutViolation):
        assert_locked(bad_dates, "date")


def test_pull_never_writes_post_window_rows(tmp_path):
    body = {"ticker": "AAA", "history": [row("2026-10-01T21:00:00Z"), row("2026-06-23T00:00:01Z"),
                                         row("2026-06-22T21:30:05Z"), row("2026-05-01T21:15:00Z")]}
    m = ingest.pull(["AAA"], FakeClient({"AAA": body}), tick_dir=tmp_path / "t",
                    manifest_path=tmp_path / "m.json", days=170, log=lambda s: None)
    stored = pd.read_parquet(tmp_path / "t" / "AAA.parquet")
    assert len(stored) == 2 and stored["ts"].max() <= pd.Timestamp("2026-06-22T23:59:59Z")
    e = m["tickers"]["AAA"]
    assert e["rows_discarded"] == 2 and e["rows_window"] == 2
    # The manifest says nothing about discarded rows beyond their count.
    assert set(e) == {"status", "rows_window", "rows_discarded", "first_ts", "last_ts", "bytes",
                      "seconds", "fetched_at"}
    assert not any(s in str(v) for v in e.values() for s in ("2026-06-23T00:00:01", "2026-10-01T21"))


def test_loader_refuses_planted_post_window_file(tmp_path):
    d = tmp_path / "t"
    d.mkdir()
    pd.DataFrame({"ticker": ["AAA"], "ts": pd.to_datetime(["2026-07-05T21:00:00Z"], utc=True)}) \
        .to_parquet(d / "AAA.parquet")
    with pytest.raises(HoldoutViolation):
        ingest.load_ticks(tick_dir=d)


def test_no_unlock_flag_exists():
    import inspect
    from filter_eval import holdout
    src = inspect.getsource(holdout)
    for word in ("unlock", "allow_holdout", "override", "force"):
        assert word not in src.split('"""', 2)[-1].lower()


# --- resumable pull and failures -------------------------------------------

def test_pull_resumes_and_retries_failures(tmp_path):
    bodies = {t: {"ticker": t, "history": [row("2026-05-01T21:15:00Z")]} for t in ["A", "B", "C"]}
    kw = dict(tick_dir=tmp_path / "t", manifest_path=tmp_path / "m.json", days=170, log=lambda s: None)
    # B fails once (recovers in the retry pass); C fails every time.
    c1 = FakeClient(bodies, fail={"B": 1, "C": 99})
    m = ingest.pull(["A", "B", "C"], c1, **kw)
    assert m["tickers"]["A"]["status"] == "ok" and m["tickers"]["B"]["status"] == "ok"
    assert m["tickers"]["C"]["status"] == "failed" and m["still_failed"] == ["C"]
    assert c1.calls == ["A", "B", "C", "B", "C"]
    # Re-run: only C is fetched again.
    c2 = FakeClient(bodies)
    m = ingest.pull(["A", "B", "C"], c2, **kw)
    assert c2.calls == ["C"] and m["still_failed"] == []


# --- state selection and timing ----------------------------------------------

def _ticks(stamps_scores):
    df = pd.DataFrame([{"ticker": "AAA", "ts": pd.Timestamp(s), "score": sc, "score_raw": sc,
                        "score_exo_served": np.nan, "label": "", "confidence": 90, "market": 50.0,
                        "narrative": float(sc), "influencer": float(sc), "macro": float(sc),
                        "missing_layers": ""} for s, sc in stamps_scores])
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    return df


def test_state_uses_2130_slot_and_ignores_ticks_at_or_after_2145():
    day = date(2026, 5, 4)
    ticks = _ticks([("2026-05-04T21:15:03Z", 50), ("2026-05-04T21:30:04Z", 62),
                    ("2026-05-04T21:45:00Z", 99), ("2026-05-04T23:30:00Z", 10)])
    p = build_state_panel(ticks, ["AAA"], [day])
    assert p.loc[0, "score_exo"] == pytest.approx(62) and p.loc[0, "slot"] == "21:30"
    assert p.loc[0, "lag_2130_s"] == pytest.approx(4.0)


def test_tick_at_2145_cannot_affect_day_t_decision():
    """Look-ahead rule (D3): changing a tick stamped 21:45:00 or later leaves the day-t state unchanged."""
    day = date(2026, 5, 4)
    base = [("2026-05-04T21:00:02Z", 55), ("2026-05-04T21:44:59Z", 58)]
    a = build_state_panel(_ticks(base + [("2026-05-04T21:45:00Z", 5)]), ["AAA"], [day])
    b = build_state_panel(_ticks(base + [("2026-05-04T21:45:00Z", 95), ("2026-05-04T22:00:00Z", 1)]),
                          ["AAA"], [day])
    assert a.loc[0, "score_exo"] == b.loc[0, "score_exo"] == pytest.approx(58)


def test_late_2130_tick_reason_and_no_tick_reason():
    days = [date(2026, 5, 4), date(2026, 5, 5)]
    ticks = _ticks([("2026-05-04T21:15:00Z", 50), ("2026-05-04T21:47:00Z", 60),
                    ("2026-05-05T21:00:00Z", 50)])
    p = build_state_panel(ticks, ["AAA"], days).set_index("day")
    assert p.loc[days[0], "non2130_reason"] == "21:30 tick stamped at or after 21:45"
    assert p.loc[days[1], "non2130_reason"] == "no 21:30 tick"


def test_previous_day_tick_is_not_carried_forward():
    days = [date(2026, 5, 4), date(2026, 5, 5)]
    p = build_state_panel(_ticks([("2026-05-04T21:15:00Z", 50)]), ["AAA"], days).set_index("day")
    assert p.loc[days[0], "has_tick"] and not p.loc[days[1], "has_tick"]
    assert np.isnan(p.loc[days[1], "score_exo"])


def test_nyse_holidays_are_not_sessions():
    s = window_sessions()
    assert len(s) == 40 and s[0] == date(2026, 4, 24) and s[-1] == date(2026, 6, 22)
    assert date(2026, 5, 25) not in s and date(2026, 6, 19) not in s
    # A tick on a holiday never becomes a state.
    p = build_state_panel(_ticks([("2026-05-25T21:15:00Z", 70)]), ["AAA"], s)
    assert not p["has_tick"].any()


def test_window_sessions_refuses_holdout_end():
    with pytest.raises(HoldoutViolation):
        window_sessions(end=date(2026, 7, 10))


# --- state definitions -------------------------------------------------------

def test_reconstruct_exo_weights_and_redistribution():
    df = pd.DataFrame({"narrative": [60.0, np.nan, np.nan], "influencer": [40.0, 40.0, np.nan],
                       "macro": [50.0, 70.0, np.nan]})
    exo = reconstruct_exo(df)
    assert exo[0] == pytest.approx((0.30 * 60 + 0.25 * 40 + 0.10 * 50) / 0.65)
    assert exo[1] == pytest.approx((0.25 * 40 + 0.10 * 70) / 0.35)
    assert np.isnan(exo[2])


def test_divergence_and_bands():
    df = pd.DataFrame({"market": [90.0, 50.0], "narrative": [45.0, np.nan],
                       "influencer": [55.0, 60.0], "macro": [50.0, 52.0]})
    assert list(divergence_spread(df)) == [45.0, 10.0]
    b = label_band(pd.Series([20.4, 20.5, 40.49, 60.5, 80.6, 100.0]))
    assert list(b) == ["Strongly Bearish", "Bearish", "Bearish", "Bullish", "Strongly Bullish",
                       "Strongly Bullish"]
