"""Event construction and the bar store, on synthetic data only."""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from responsiveness.events import Calendar

from lag import bars as bars_mod
from lag import events as ev
from lag.data import sessions as real_sessions

NY = "America/New_York"


def synthetic_bars(tickers, sess, rng, bar_minutes=60, scale=0.002):
    """Quiet regular-session bars: 7 hourly bars per session, small random within-bar moves."""
    rows = []
    for d in sess:
        opens = pd.date_range(pd.Timestamp(f"{d} 09:30", tz=NY), pd.Timestamp(f"{d} 15:30", tz=NY),
                              freq=f"{bar_minutes}min")
        for t in tickers:
            px = 100.0
            for ts in opens:
                r = rng.uniform(-scale, scale)      # bounded noise: no bar can exceed 3 x the robust SD by chance
                rows.append({"ticker": t, "ts": ts.tz_convert("UTC"), "session": d, "open": px,
                             "high": px * (1 + abs(r)), "low": px * (1 - abs(r)), "close": px * (1 + r), "volume": 1000})
                px = px * (1 + r)
    return pd.DataFrame(rows)


@pytest.fixture
def world():
    rng = np.random.default_rng(1)
    sess = real_sessions("pilot")                      # 12 May to 22 June 2026, 29 sessions
    # Enough names that one planted move barely shifts the equal-weighted market return.
    tickers = ["AAA", "BBB", "CCC", "DDD"] + [f"T{i:02d}" for i in range(36)]
    b = synthetic_bars(tickers, sess, rng)
    return sess, tickers, b


def plant(b, ticker, session, tod, move):
    ts = pd.Timestamp(f"{session} {tod}", tz=NY).tz_convert("UTC")
    i = b.index[(b["ticker"] == ticker) & (b["ts"] == ts)][0]
    b.loc[i, "close"] = b.loc[i, "open"] * (1 + move)
    return ts


def test_le2_detects_planted_bar_and_first_bar_only(world):
    sess, tickers, b = world
    t_plant = plant(b, "AAA", sess[10], "11:30", 0.05)
    plant(b, "AAA", sess[10], "13:30", 0.05)           # same session, later: not a second candidate
    panel = ev.build_panel(b, tickers, sess)
    normal = ev.normal_move(panel, {})
    assert normal.shape == (7, 40) and normal.notna().all().all()
    e2 = ev.build_le2(panel, normal, {}, Calendar(sess), 3.0)
    aaa = e2[e2["ticker"] == "AAA"]
    assert len(aaa) == 1 and aaa.iloc[0]["t0"] == t_plant and aaa.iloc[0]["direction"] == 1
    assert bool(aaa.iloc[0]["in_session"])
    assert e2.attrs["bars_over_threshold"] >= 2


def test_le2_excludes_earnings_sessions(world):
    sess, tickers, b = world
    plant(b, "BBB", sess[5], "10:30", -0.06)
    panel = ev.build_panel(b, tickers, sess)
    normal = ev.normal_move(panel, {"BBB": {sess[5]}})
    e2 = ev.build_le2(panel, normal, {"BBB": {sess[5]}}, Calendar(sess), 3.0)
    bbb = e2[e2["ticker"] == "BBB"]
    assert len(bbb) == 1 and bbb.iloc[0]["status"] == "earnings_session" and bbb.iloc[0]["direction"] == -1


def test_normal_move_needs_enough_bars(world):
    sess, tickers, b = world
    panel = ev.build_panel(b, tickers, sess)
    # Exclude all but 9 sessions for CCC: fewer than MIN_NORMAL_OBS bars at each time of day.
    normal = ev.normal_move(panel, {"CCC": set(sess[9:])})
    assert normal["CCC"].isna().all() and normal["AAA"].notna().all()


def test_overnight_gap_is_not_an_event(world):
    sess, tickers, b = world
    # A 10% gap into session 8 for DDD, with a quiet first bar: no L-E2.
    m = (b["ticker"] == "DDD") & (b["session"] >= sess[8])
    b.loc[m, ["open", "high", "low", "close"]] *= 1.10
    panel = ev.build_panel(b, tickers, sess)
    e2 = ev.build_le2(panel, ev.normal_move(panel, {}), {}, Calendar(sess), 3.0)
    assert not len(e2) or not (e2["ticker"] == "DDD").any()
    # but the close-to-close series does carry the gap (price curve input)
    first = panel.ts[np.flatnonzero(panel.session == sess[8])[0]]
    assert panel.cc.at[first, "DDD"] > 0.09


def test_cluster_priority_and_window():
    t = pd.Timestamp("2026-05-20 14:30", tz="UTC")
    c = pd.DataFrame({
        "ticker": ["X", "X", "X", "X", "Y"],
        "type": ["L-E2", "L-E1", "L-E2", "L-E2", "L-E2"],
        "t0": [t - pd.Timedelta(hours=10), t, t + pd.Timedelta(hours=47), t + pd.Timedelta(hours=49), t],
        "direction": [1, -1, 1, 1, 1], "status": ["pending"] * 5})
    out = ev.cluster(c)
    assert out["status"].tolist() == ["cluster_dropped_for_L-E1", "kept", "cluster_dropped_for_L-E1", "kept", "kept"]


def test_cluster_earlier_wins_among_equals():
    t = pd.Timestamp("2026-05-20 14:30", tz="UTC")
    c = pd.DataFrame({"ticker": ["X"] * 3, "type": ["L-E2"] * 3,
                      "t0": [t + pd.Timedelta(hours=20), t, t + pd.Timedelta(hours=40)],
                      "direction": [1, 1, 1], "status": ["pending"] * 3})
    out = ev.cluster(c)
    assert out["status"].tolist() == ["cluster_dropped_for_L-E2", "kept", "cluster_dropped_for_L-E2"]


def test_period_filter():
    last = pd.Timestamp("2026-06-22 23:30", tz="UTC")
    c = pd.DataFrame({"ticker": ["X"] * 3, "type": ["L-E1"] * 3,
                      "t0": pd.to_datetime(["2026-05-12 20:00", "2026-05-13 10:00", "2026-06-21 00:00"], utc=True),
                      "direction": [1, 1, 1], "status": ["kept"] * 3})
    out = ev.apply_period(c, date(2026, 5, 13), last)
    assert out["status"].tolist() == ["outside_period", "kept", "outside_period"]


def test_in_session_flag():
    cal = Calendar(real_sessions("pilot"))
    assert ev.in_session_flag(pd.Timestamp("2026-05-20 13:30", tz="UTC"), cal) == (True, date(2026, 5, 20))
    assert ev.in_session_flag(pd.Timestamp("2026-05-20 13:29:59", tz="UTC"), cal)[0] is False
    assert ev.in_session_flag(pd.Timestamp("2026-05-20 20:00", tz="UTC"), cal)[0] is False      # at the close
    assert ev.in_session_flag(pd.Timestamp("2026-05-23 15:00", tz="UTC"), cal)[0] is False      # Saturday
    assert ev.in_session_flag(pd.Timestamp("2026-05-25 15:00", tz="UTC"), cal)[0] is False      # Memorial Day


def test_store_merge_keeps_first_values_and_counts(tmp_path):
    p = tmp_path / "store.parquet"
    rng = np.random.default_rng(2)
    sess = real_sessions("pilot")[:2]
    a = synthetic_bars(["AAA"], sess, rng)
    s1 = bars_mod.merge_store(a, p)
    assert s1["rows_added"] == 14 and s1["rows_in_store"] == 14 and s1["rows_dropped_by_lock"] == 0
    b = a.copy()
    b.loc[0, "close"] += 1.0                          # revised value for a stored bar
    extra = synthetic_bars(["BBB"], sess[:1], rng)     # new ticker
    late = synthetic_bars(["AAA"], [date(2026, 7, 1)], rng)   # reserved period: must be dropped
    s2 = bars_mod.merge_store(pd.concat([b, extra, late]), p)
    assert s2["rows_added"] == 7 and s2["rows_already_present"] == 14
    assert s2["rows_present_with_different_values"] == 1 and s2["rows_dropped_by_lock"] == 7
    st = bars_mod.load_store(p)
    assert len(st) == 21 and st.loc[(st["ticker"] == "AAA"), "close"].iloc[0] == a.loc[0, "close"]


def test_coverage_counts_missing_bars(tmp_path):
    rng = np.random.default_rng(3)
    sess = real_sessions("pilot")[:3]
    b = synthetic_bars(["AAA", "BBB"], sess, rng)
    b = b.drop(b.index[(b["ticker"] == "BBB") & (b["session"] == sess[1])][:3])
    cov = bars_mod.coverage(b, sess, "1h", ["AAA", "BBB", "CCC"], through=sess[-1])
    assert cov["bars_expected"] == 7 * 3 * 3 and cov["bars"] == 42 - 3
    assert cov["tickers_complete"] == 1
    assert cov["per_ticker"].loc["BBB", "bars_missing"] == 3 and cov["per_ticker"].loc["CCC", "bars_missing"] == 21
    assert len(cov["gaps"]) == 1 + 3
    text = bars_mod.coverage_markdown(cov, "t", "store.parquet")
    assert "| CCC |" in text and "| BBB |" in text and "| AAA |" not in text.split("## Tickers with missing bars")[1]


def test_collection_window():
    s, e = bars_mod.collection_window(date(2026, 10, 2), date(2026, 11, 23), today=date(2026, 10, 9))
    assert (s, e) == (date(2026, 10, 2), date(2026, 10, 10))
    s, e = bars_mod.collection_window(date(2026, 10, 2), date(2026, 11, 23), today=date(2026, 12, 15))
    assert (s, e) == (date(2026, 10, 18), date(2026, 11, 24))


def test_rarity_threshold_is_the_pooled_quantile(world):
    sess, tickers, b = world
    panel = ev.build_panel(b, tickers, sess)
    normal = ev.normal_move(panel, {})
    z = ev.z_scores(panel, normal)
    thr = ev.rarity_threshold(z, share=0.002)
    a = np.abs(z.to_numpy().ravel())
    a = a[np.isfinite(a)]
    assert (a > thr).mean() <= 0.002 + 1 / a.size and (a >= thr).mean() >= 0.002 - 1 / a.size   # within one bar
    # A planted move far above the threshold is the only candidate at that level.
    t_plant = plant(b, "AAA", sess[12], "12:30", 0.10)
    panel = ev.build_panel(b, tickers, sess)
    normal = ev.normal_move(panel, {})
    thr = ev.rarity_threshold(ev.z_scores(panel, normal))
    e2 = ev.build_le2(panel, normal, {}, Calendar(sess), thr)
    aaa = e2[e2["ticker"] == "AAA"]
    assert len(aaa) == 1 and aaa.iloc[0]["t0"] == t_plant
    assert aaa.iloc[0]["z"] == e2["z"].abs().max()
