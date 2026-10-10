"""The definitive run's frozen configuration, its gate, and the universe rule (L20)."""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from lag import synthetic as syn
from lag.definitive import config as dcfg
from lag.definitive.run import run as definitive_run
from lag.lock import LockViolation
from lag.scripts.run_measures import definitive_universe


def test_frozen_values():
    assert dcfg.PERIOD_SESSIONS == (date(2026, 10, 2), date(2026, 11, 23))
    assert dcfg.EVENT_START == date(2026, 10, 5)
    assert dcfg.BAR == "15m" and dcfg.BAR_MINUTES == 15
    assert dcfg.SEED == 20261005 and dcfg.SMOOTHING_HALF_LIFE_H == 2.0
    assert dcfg.EXTENDED_HOURS_CURVE and dcfg.PRE_EVENT_DRIFT and dcfg.EXT_LOO_MIN_OTHERS == 10
    assert dcfg.E2_RARITY_SHARE == 0.002 and dcfg.E2_MULT_SENSITIVITY == 3.0
    assert dcfg.K_PERM == 1000 and dcfg.B_BOOT == 2000 and dcfg.N_PLACEBO == 20
    assert len(dcfg.CELLS["primary"]) == 4
    h = dcfg.config_hash()
    assert len(h) == 12 and h == dcfg.config_hash()           # deterministic
    assert "pilot.E2_Z_THRESHOLD" in dcfg.config_dict()


def test_definitive_run_is_gated_before_24_november(monkeypatch):
    monkeypatch.setattr("lag.definitive.run.gate_open", lambda: False)
    with pytest.raises(LockViolation, match="gated"):
        definitive_run()


def test_universe_rule_drops_names_missing_a_session():
    rng = np.random.default_rng(4)
    sess = syn.sessions(5)
    bars = syn.quiet_bars(["AAA", "BBB", "CCC"], sess, rng, bar_minutes=15)
    bars["regular"] = True
    bars = bars[~((bars["ticker"] == "BBB") & (bars["session"] == sess[2]))]           # BBB misses one session
    ext = bars[(bars["ticker"] == "CCC")].iloc[:1].copy()
    ext["regular"] = False                                                                   # an extended bar does not count
    bars = pd.concat([bars, ext], ignore_index=True)
    keep, dropped = definitive_universe(bars, ["AAA", "BBB", "CCC", "DDD"], sess)
    assert keep == ["AAA", "CCC"] and dropped == ["BBB", "DDD"]
