"""The two measures added for the definitive run: pre-event drift (L19) and the extended-hours price curve (L18)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from lag import events as ev_mod
from lag import measure as ms
from lag import pipeline as pl
from lag import synthetic as syn
from lag.tests.test_measure import H, MIN, world


def test_pre_event_drift_and_extended_hours_curve():
    """Drift is the signed change from 6 h before t0 to the before reading. With an extended-hours
    panel, a second price curve moves in pre- and post-market bars; the regular one does not."""
    rng, sess, tickers, stamps, bars = world(n_tickers=6, n_sessions=10)
    values, rows = {}, []
    for i, t in enumerate(tickers):
        t0 = syn.bar_start(sess[3 + i], "16:30")                        # after the close, as an earnings release
        v = 50.0 + np.where(stamps >= t0.value - 4 * H, 3.0, 0.0)       # +3 drift in the four hours before t0
        v = v + syn.step(stamps, t0.value, 30 * MIN, 10.0)              # response 30 minutes after t0
        values[t] = v
        rows.append((t, t0, 1, "L-E1"))
    events = syn.events_frame(rows)
    bars["regular"] = True
    ext_rows = []
    for i, t in enumerate(tickers):
        d = sess[3 + i]
        last = bars[(bars["ticker"] == t) & (bars["session"] == d)].sort_values("ts").iloc[-1]
        px = float(last["close"])
        ext_rows.append({"ticker": t, "ts": syn.bar_start(d, "17:00"), "session": d, "open": px, "high": px * 1.04,
                         "low": px, "close": px * 1.04, "volume": 100, "regular": False})
        m = (bars["ticker"] == t) & (bars["session"] > d)
        bars.loc[m, ["open", "high", "low", "close"]] *= 1.04           # the post-market move persists
    ext = pd.concat([bars, pd.DataFrame(ext_rows)], ignore_index=True)
    ext["ts"] = pd.to_datetime(ext["ts"], utc=True)
    panel = ev_mod.build_panel(ext, tickers, sess)                        # regular bars only
    panel_ext = ev_mod.build_panel(ext, tickers, sess, regular_only=False)
    assert len(panel_ext.ts) == len(panel.ts) + 6
    cand = {r.ticker: {pd.Timestamp(r.t0).tz_convert("America/New_York").date()} for r in events.itertuples()}
    prep = pl.prepare(syn.ticks_frame(values, stamps), events, panel, 60, cand, sess, panel_ext=panel_ext)
    res = pl.measure_cell(prep, np.ones(len(events), bool), 2, k_perm=50, n_boot=100, n_placebo=3)
    assert res["drift"][0] == pytest.approx(3.0, abs=0.01)
    assert res["ci_drift"][0][0] == pytest.approx(3.0, abs=0.01) and res["ci_drift"][0][1] == pytest.approx(3.0, abs=0.01)
    assert 0.4 <= res["t_half"][0] <= 0.6
    # Both price curves are still flat at T½ (30 min after 16:30: the 17:00 bar has not closed).
    assert res["rp_half"][0] == pytest.approx(0.0, abs=1e-9) and res["rp_half_ext"][0] == pytest.approx(0.0, abs=1e-9)
    # By 2 h the extended-hours curve carries the post-market move; the regular curve waits for the next open.
    at_2h = ms.ZERO_IDX + 24
    assert res["mean_r_ext"][at_2h] > 0.03 and res["mean_r"][at_2h] == pytest.approx(0.0, abs=1e-9)
    assert res["Rp_ext"][ms.M_IDX] == pytest.approx(1.0)


def test_without_extended_panel_the_extra_measures_are_nan():
    rng, sess, tickers, stamps, bars = world(n_tickers=3, n_sessions=8)
    values, rows = {}, []
    for i, t in enumerate(tickers):
        t0 = syn.bar_start(sess[3 + i], "11:30")
        values[t] = 50.0 + syn.step(stamps, t0.value, H, 5.0)
        rows.append((t, t0, 1, "L-E2"))
    events = syn.events_frame(rows)
    panel = ev_mod.build_panel(bars, tickers, sess)
    cand = {r.ticker: {pd.Timestamp(r.t0).tz_convert("America/New_York").date()} for r in events.itertuples()}
    prep = pl.prepare(syn.ticks_frame(values, stamps), events, panel, 60, cand, sess)
    res = pl.measure_cell(prep, np.ones(3, bool), 3, k_perm=20, n_boot=20, n_placebo=2)
    assert np.isnan(res["rp_half_ext"]).all() and prep.meta["extended_hours_curve"] is False
    assert res["drift"][0] == pytest.approx(0.0)
    rows_out = pl.cell_rows(res, {"cell": "x"})
    assert "drift_6h" in rows_out[0] and "rp_half_ext" in rows_out[0]
