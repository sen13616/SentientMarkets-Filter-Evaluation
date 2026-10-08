"""Synthetic-data tests: the data lock and event construction. No real data is read."""

from __future__ import annotations

import json
from datetime import date

import numpy as np
import pandas as pd
import pytest

from responsiveness import data, events, sources
from responsiveness.data import HoldoutViolation
from responsiveness.market import Prices


# --------------------------------------------------------------------------- data lock

def test_sessions_refuse_end_after_lock():
    with pytest.raises(HoldoutViolation):
        data.sessions(date(2026, 6, 1), date(2026, 6, 23))
    assert data.sessions(date(2026, 6, 15), date(2026, 6, 22))[-1] == date(2026, 6, 22)


def test_tick_loader_refuses_post_lock_rows(tmp_path):
    ok = pd.DataFrame({"ticker": ["X", "X"], "ts": pd.to_datetime(["2026-06-22 21:00", "2026-06-22 23:59"],
                                                                    utc=True)})
    for c in ["score", "score_raw", "confidence"]:
        ok[c] = pd.array([50, 50], dtype="Int64")
    for c in ["score_exo_served", "market", "narrative", "influencer", "macro"]:
        ok[c] = 50.0
    ok["label"], ok["missing_layers"] = "Neutral", ""
    ok.to_parquet(tmp_path / "X.parquet")
    assert len(data.load_ticks(["X"], tick_dir=tmp_path)) == 2
    bad = ok.copy()
    bad.loc[1, "ts"] = pd.Timestamp("2026-06-23 00:00:01", tz="UTC")
    bad.to_parquet(tmp_path / "X.parquet")
    with pytest.raises(HoldoutViolation):
        data.load_ticks(["X"], tick_dir=tmp_path)


def test_price_loader_refuses_post_lock_bars(tmp_path):
    p = pd.DataFrame({"ticker": ["X", "X"], "date": [date(2026, 6, 22), date(2026, 6, 23)],
                      "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 1.0})
    p.to_parquet(tmp_path / "daily.parquet")
    with pytest.raises(HoldoutViolation):
        data.load_prices(tmp_path / "daily.parquet")


def test_event_fetch_drops_post_lock_rows_before_writing(tmp_path):
    def fake(ticker):
        return {
            "earnings": pd.DataFrame({
                "release_et": pd.DatetimeIndex(["2026-06-03 16:00", "2026-06-22 20:00", "2026-07-30 16:00"])
                .tz_localize("America/New_York"),       # 22 June 20:00 EDT = 23 June 00:00 UTC: dropped
                "eps_estimate": 1.0, "eps_reported": 1.1, "surprise_pct": 10.0}),
            "ratings": pd.DataFrame({"grade_ts": pd.to_datetime(["2026-06-10 12:00", "2026-06-23 09:00"]),
                                     "firm": "F", "action": "up", "to_grade": "Buy", "from_grade": "Hold"}),
            "insider": pd.DataFrame({"start_date": pd.to_datetime(["2026-06-22", "2026-06-23"]),
                                     "text": ["Sale at price 1", "Purchase at price 1"], "shares": 1.0,
                                     "value": 1.0, "position": "CEO", "ownership": "D"}),
        }
    m = sources.fetch_all(["X"], fetch=fake, raw_dir=tmp_path, pause_s=0, log=lambda s: None)
    e = m["tickers"]["X"]
    assert (e["earnings"]["rows_kept"], e["earnings"]["rows_dropped_after_lock"]) == (1, 2)
    assert (e["ratings"]["rows_kept"], e["ratings"]["rows_dropped_after_lock"]) == (1, 1)
    assert (e["insider"]["rows_kept"], e["insider"]["rows_dropped_after_lock"]) == (1, 1)
    on_disk = pd.read_parquet(tmp_path / "earnings" / "X.parquet")
    assert on_disk["release_et"].max() < pd.Timestamp("2026-06-23", tz="UTC")
    assert "2026-07" not in json.dumps(m)                 # nothing about dropped rows but their count
    with pytest.raises(HoldoutViolation):                 # the cache loader re-checks
        bad = pd.read_parquet(tmp_path / "ratings" / "X.parquet")
        bad.loc[0, "grade_ts"] = pd.Timestamp("2026-07-01")
        bad.to_parquet(tmp_path / "ratings" / "X.parquet")
        sources.load_source("ratings", ["X"], raw_dir=tmp_path)


# --------------------------------------------------------------------------- event construction

CAL = events.Calendar(data.sessions(date(2026, 5, 1), date(2026, 6, 22)))


def et(s):
    return pd.Timestamp(s, tz="America/New_York")


def test_earnings_reaction_session():
    # Before the open and during the session: same session.
    assert events.earnings_reaction_session(et("2026-06-03 06:00"), CAL) == date(2026, 6, 3)
    assert events.earnings_reaction_session(et("2026-06-03 12:00"), CAL) == date(2026, 6, 3)
    # At or after the close: next session.
    assert events.earnings_reaction_session(et("2026-06-03 16:00"), CAL) == date(2026, 6, 4)
    # Friday after close and Saturday: Monday. Thursday 18 June after close: 22 June (19 June holiday).
    assert events.earnings_reaction_session(et("2026-06-05 16:00"), CAL) == date(2026, 6, 8)
    assert events.earnings_reaction_session(et("2026-06-06 09:00"), CAL) == date(2026, 6, 8)
    assert events.earnings_reaction_session(et("2026-06-18 16:00"), CAL) == date(2026, 6, 22)


def test_window_before_uses_earlier_of_release_and_cutoff():
    ev = pd.DataFrame({"ticker": ["X", "X"], "type": ["E1", "E3"], "R": [date(2026, 6, 4), date(2026, 6, 4)],
                       "event_time": [et("2026-06-03 16:00").tz_convert("UTC"), pd.NaT]})
    w = events.add_windows(ev, CAL)
    # After-close release on 3 June: before = release time (20:00 UTC) < 21:45 UTC on 3 June.
    assert w.loc[0, "before_ts"] == pd.Timestamp("2026-06-03 20:00", tz="UTC")
    assert w.loc[1, "before_ts"] == pd.Timestamp("2026-06-03 21:45", tz="UTC")
    assert (w["after_ts"] == pd.Timestamp("2026-06-05 21:45", tz="UTC")).all()


def _cands(rows):
    ev = pd.DataFrame(rows)
    ev["R_alt"] = None
    ev["event_time"] = pd.NaT
    ev["time_known"] = True
    return events.add_windows(ev, CAL)


def test_cross_type_overlap_keeps_higher_rank():
    ev = _cands([{"ticker": "X", "type": "E4", "R": date(2026, 6, 3), "direction": -1},
                 {"ticker": "X", "type": "E3", "R": date(2026, 6, 4), "direction": 1},
                 {"ticker": "X", "type": "E4", "R": date(2026, 6, 9), "direction": -1},   # 3 sessions on
                 {"ticker": "Y", "type": "E4", "R": date(2026, 6, 4), "direction": 1}])
    r = events.resolve(ev)
    assert list(r["status"]) == ["overlap_E3", "kept", "kept", "kept"]
    assert r.loc[1, "overlaps_dropped"] == "E4;"


def test_same_type_overlap_and_conflict():
    ev = _cands([{"ticker": "X", "type": "E4", "R": date(2026, 6, 1), "direction": -1},
                 {"ticker": "X", "type": "E4", "R": date(2026, 6, 2), "direction": -1},
                 {"ticker": "Z", "type": "E3", "R": date(2026, 6, 1), "direction": 1},
                 {"ticker": "Z", "type": "E3", "R": date(2026, 6, 1), "direction": -1}])
    r = events.resolve(ev)
    assert list(r["status"]) == ["kept", "same_type_overlap", "same_type_conflict", "same_type_overlap"]


def test_e2_on_e1_reaction_session_is_not_e2_and_outside_period_flagged():
    ev = _cands([{"ticker": "X", "type": "E1", "R": date(2026, 6, 4), "direction": 1},
                 {"ticker": "X", "type": "E2", "R": date(2026, 6, 4), "direction": 1},
                 {"ticker": "X", "type": "E3", "R": date(2026, 5, 4), "direction": 1}])
    r = events.resolve(ev)
    assert list(r["status"]) == ["kept", "e1_reaction_session", "outside_period"]


def test_e2_threshold_uses_previous_session_atr():
    sess = CAL.sessions[:20]
    close = pd.DataFrame({"X": 100.0}, index=sess)
    close.iloc[16, 0] = 100.0 + 3.01        # 3.01 > 3 x ATR(=1) through the previous session
    close.iloc[18, 0] = close.iloc[17, 0] - 2.9
    atr = pd.DataFrame({"X": 1.0}, index=sess)
    p = Prices(sessions=sess, tickers=["X"], close=close, ret=close.pct_change(), adj=close * 0, atr=atr)
    e2 = events.build_e2(p, events.Calendar(sess), sess[0], sess[-1])
    assert list(e2["R"]) == [sess[16], sess[17]] and list(e2["direction"]) == [1, -1]


def test_insider_kinds():
    assert events.insider_kind("Purchase at price 10.00 per share.") == "purchase"
    assert events.insider_kind("Sale at price 1 - 2 per share.") == "sale"
    for s in ["Stock Gift at price 0.00 per share.", "Stock Award(Grant) at price 1", "", None,
              "Conversion of Exercise of derivative security"]:
        assert events.insider_kind(s) == "other"


def test_wilder_atr_constant_range():
    from responsiveness.market import wilder_atr
    n = 30
    c = np.full(n, 100.0)
    a = wilder_atr(c + 1, c - 1, c)
    assert np.isnan(a[:13]).all() and np.allclose(a[13:], 2.0)
