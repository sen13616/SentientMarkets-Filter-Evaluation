"""Frozen parameters of the definitive run of Experiment 5B (BRIEF.md Phase 3; pre-registered before
24 November 2026, tag `5b-definitive-prereg`).

Everything the pilot fixed is imported unchanged from `lag.config`; this file names what the
definitive run adds or re-dates, with the amendment that introduced each item. Nothing here may
change after the pre-registration commit. The run reads sentiment only once the lock's gate is open
(5A's definitive results committed, on or after 24 November 2026).
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

import pandas as pd

from lag import config as pilot
from lag.config import (ALPHA, B_BOOT, CLUSTER_WINDOW, DEFINITIVE_END, DEFINITIVE_START, E2_MULT_SENSITIVITY,  # noqa: F401
                        E2_RARITY_SHARE, EXO_WEIGHTS, FULL_LEVEL, GRID_STEP, HALF_LEVEL, INDICES, K_PERM,
                        MAIN_HORIZONS_MIN, MAX_BEFORE_AGE, MIN_NORMAL_OBS, N_PLACEBO, NON_EVENT_RADIUS,
                        POST_WINDOW, PRE_WINDOW, PRIMARY_GROUPS, PRIMARY_INDICES, ROBUST_SD_FACTOR,
                        SECONDARY_GROUPS, ALIGN_K, COMPOSITE_WEIGHTS, CONTAMINATED)

PKG = Path(__file__).resolve().parent
RESULTS = PKG / "results"
RUN = "definitive"

# ----------------------------------------------------------------------------- period and data (BRIEF.md section 3, Phase 3)
PERIOD_SESSIONS = pilot.RUNS[RUN]["sessions"]            # 2 October to 23 November 2026 (NYSE sessions)
EVENT_START = pilot.RUNS[RUN]["event_start"]             # t0 on or after 5 October 2026 (New York date)
PERIOD_END = pilot.RUNS[RUN]["period_end"]               # t0 + 48 h at or before the last tick, itself <= 23 November 23:59:59 UTC
BAR = pilot.RUNS[RUN]["bar"]                             # 15-minute bars
BAR_MINUTES = pilot.BAR_MINUTES[BAR]
SEED = pilot.RUNS[RUN]["seed"]                           # 20261005
SMOOTHING_HALF_LIFE_H = pilot.RUNS[RUN]["smoothing_half_life_h"]   # the published score's EMA: 2 hours since 22 July 2026
BARS_FILE = pilot.BARS_15M                               # collected weekly since 9 October 2026; extended hours from L18
TICK_DIR = pilot.DEFINITIVE_TICK_DIR                     # Experiment 5A's definitive pull; gated
DAILY_FILE = pilot.DEFINITIVE_DAILY                      # 5A's definitive daily bars (reserved-period rows dropped in memory)
EARNINGS_RAW = pilot.DEFINITIVE_EARNINGS_RAW             # 5A's definitive earnings tables; gated

# ----------------------------------------------------------------------------- universe (L20)
# The pilot's 473 names less any without a regular 15-minute bar on every session of the period,
# determined from this experiment's own bar store (prices only, so it can be checked before the gate
# opens). Any difference from 5A definitive's own universe list is reported in Phase 4.
UNIVERSE_RULE = "pilot 473 less names without a regular bar on every period session (from bars_15m)"

# ----------------------------------------------------------------------------- events (L14, applied to this period's bars)
# The L-E2 rarity threshold is the |z| exceeded by E2_RARITY_SHARE (0.2%) of regular in-session
# 15-minute bars, pooled over the universe and the period, computed from the period's bars in
# Phase 4 (prices only) and recorded in run_meta.json; the 3x rule stays as the sensitivity cell.
E2_THRESHOLD_RULE = "rarity: |z| exceeded by 0.2% of regular in-session bars, pooled over universe and period"

# ----------------------------------------------------------------------------- measures added for this run
EXTENDED_HOURS_CURVE = True        # L18: Rₚ reported twice for every cell: regular-session bars, and all bars from t0
EXT_LOO_MIN_OTHERS = 10            # L18: market return of an extended bar is leave-one-out over >= 10 other tickers, else 0
PRE_EVENT_DRIFT = True             # L19: d·(S(t0⁻) - S(t0 - 6 h)) with its date-bootstrap interval, every cell (secondary)

# ----------------------------------------------------------------------------- inference (L9, L10, L15, L17; unchanged)
GATE = "relabelling p(M) < 0.05 AND date-bootstrap 95% interval for M above zero (L17)"
RESOLUTION_NOTE = "15-minute ticks in session, 30 outside; 15-minute bars"

# ----------------------------------------------------------------------------- cells
CELLS = {
    "primary": [(idx, g, "all") for g in PRIMARY_GROUPS for idx in PRIMARY_INDICES],
    "secondary": "every other index x group x where cell, with Benjamini-Hochberg across their p(M)",
}
RUN_ONCE = True                    # a rerun only to fix a bug, logged with its reason; the original output is kept


def config_dict() -> dict:
    out = {f"pilot.{k}": v for k, v in pilot.config_dict().items()}
    for k, v in globals().items():
        if k.isupper() and not isinstance(v, Path):
            out[k] = json.loads(json.dumps(v, default=str, sort_keys=True))
    return out


def config_hash() -> str:
    return hashlib.sha256(json.dumps(config_dict(), sort_keys=True).encode()).hexdigest()[:12]
