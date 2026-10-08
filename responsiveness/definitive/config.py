"""Frozen parameters for the definitive run of Experiment 5A (definitive/BRIEF.md).

Every pilot definition and threshold is imported unchanged from `responsiveness.config`
(BRIEF.md ground rule 1). Only what the definitive brief adds or re-dates is set here.
Nothing in this file may change after the Phase 0 commit (ground rule 4).
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, time
from pathlib import Path

import pandas as pd

from responsiveness import config as pilot
from responsiveness.config import (ALPHA, CONTAMINATED, EXO_WEIGHTS, GROUPS, INDICES,  # noqa: F401 (re-exported)
                                   LARGE_MOVE_UNITS, MIN_NOISE_CHANGES, MOVE_UNITS, N_BOOT, N_PERM, N_PLACEBO,
                                   NOISE_EXCLUDE_TYPES, NOISE_EXCLUSION, PRIMARY_GROUP, PRIMARY_INDEX,
                                   PRIMARY_MAX_UNEXPLAINED, STATE_CUTOFF, E2_ATR_MULT, ATR_N,
                                   UNEXPLAINED_EVENT_RADIUS, UNEXPLAINED_PRICE_MULT, TYPICAL_MOVE_SESSIONS)

PKG = Path(__file__).resolve().parent
RESULTS = PKG / "results"
LEDGER = PKG / "ledger.csv"
DATA = pilot.DATA / "definitive"                 # local only, never committed
TICK_DIR = DATA / "sentiment" / "ticks"
PRICE_FILE = DATA / "prices" / "daily.parquet"
EVENT_RAW = DATA / "raw"

# Data lock (ground rule 2): two allowed ranges, inclusive, by UTC instant.
ALLOWED = (
    (None, pd.Timestamp("2026-06-22 23:59:59.999999", tz="UTC")),                       # the pilot's data
    (pd.Timestamp("2026-10-02 00:00:00", tz="UTC"), pd.Timestamp("2026-11-23 23:59:59.999999", tz="UTC")),
)
RESERVED = (date(2026, 6, 23), date(2026, 10, 1))   # reserved for a later experiment
# Price bars only (DECISIONS.md P1): public daily bars may be read from the reserved period,
# for the ATR(14) and typical-daily-move lookbacks before 5 October. Nothing after 23 November.
PRICE_START = date(2025, 1, 2)
PRICE_ALLOWED_END = pd.Timestamp("2026-11-23 23:59:59.999999", tz="UTC")
PERIOD_START = date(2026, 10, 2)                    # first allowed day of the new range
PERIOD_END = date(2026, 11, 23)                     # last allowed day

# Event period (section 2). Before readings must be stamped on or after FLOOR (pilot A1 analogue).
EVENT_START = date(2026, 10, 5)
EVENT_END = date(2026, 11, 20)
FLOOR = PERIOD_START

# Universe (section 2): the pilot's used universe, less names without a bar on every period session.
UNIVERSE_FILE = pilot.UNIVERSE_FILE

# Integrity rule (section 3).
INTEGRITY_MAX_GAP = pd.Timedelta(hours=2)          # universe-wide scoring gap within the trading session
INTEGRITY_NARRATIVE_MISSING = 0.20                  # share of the universe without narrative at the 21:30 tick
SLOT_2130 = time(21, 30)
SLOT_2130_LATE_END = time(22, 0)                    # pilot D9: a 21:30 tick may arrive until 22:00
INTEGRITY_STOP_SHARE = 0.20                         # more flagged sessions than this: stop before running

# Test B (section 4 as amended; DECISIONS.md P2).
TEST_B_INDEX = "score_exo"
TEST_B_TYPES = ("E3",)                      # primary cell: E3 alone
TEST_B_CONTROLS = "flexible"                # r, sign(r) and a linear spline in r
# Knot rule (no outcome data): symmetric knots at the 50th, 90th and 99th percentiles of the
# absolute market-adjusted daily return, pooled over the pilot's 473 names and its price history
# (2 January 2025 to 22 June 2026; 173,116 returns). Computed 8 October 2026, rounded to 4 dp.
SPLINE_KNOTS = (-0.0737, -0.0289, -0.0091, 0.0091, 0.0289, 0.0737)
TEST_B_SECONDARY = (
    # (cell id, event types, index, controls, units)
    ("pooled E1-E3, as first specified", ("E1", "E2", "E3"), "score_exo", "linear", "points"),
    ("E3, narrative", ("E3",), "narrative", "flexible", "points"),
    ("E3, influencer", ("E3",), "influencer", "flexible", "points"),
    ("E3, macro", ("E3",), "macro", "flexible", "points"),
    ("E3, noise units", ("E3",), "score_exo", "flexible", "noise units"),
)
# Synthetic result reported next to the pooled secondary cell (results/test_b_synthetic.md).
POOLED_SYNTHETIC_FALSE_POSITIVES = {"no effect, no echo": 0.105, "saturating echo": 0.670}
TEST_B_K = 1000
TEST_B_BOOT = 2000

SEED = 20261005

# Price lookbacks (DECISIONS.md P1, D10). ATR(14) is the pilot's (R6): Wilder smoothing seeded with
# the first 14 true ranges from PRICE_START. The typical daily move is the pilot's (M6), re-dated:
# the median |market-adjusted return| over the 120 sessions ending 2 October 2026.
ATR_LOOKBACK = PRICE_START
TYPICAL_MOVE_WINDOW = (TYPICAL_MOVE_SESSIONS, date(2026, 10, 2))


def config_dict() -> dict:
    out = {}
    for k, v in {**{f"pilot.{k}": getattr(pilot, k) for k in dir(pilot) if k.isupper()},
                 **{k: v for k, v in globals().items() if k.isupper()}}.items():
        if isinstance(v, Path):
            continue
        out[k] = v if isinstance(v, (int, float, str, bool, type(None))) else str(v)
    return out


def config_hash() -> str:
    return hashlib.sha256(json.dumps(config_dict(), sort_keys=True).encode()).hexdigest()[:12]


# Pilot constants carried over unchanged and re-exported for the definitive modules.
__all__ = ["ALPHA", "CONTAMINATED", "EXO_WEIGHTS", "GROUPS", "INDICES", "LARGE_MOVE_UNITS", "MIN_NOISE_CHANGES",
           "MOVE_UNITS", "N_BOOT", "N_PERM", "N_PLACEBO", "NOISE_EXCLUDE_TYPES", "NOISE_EXCLUSION", "PRIMARY_GROUP",
           "PRIMARY_INDEX", "PRIMARY_MAX_UNEXPLAINED", "STATE_CUTOFF", "E2_ATR_MULT", "ATR_N",
           "UNEXPLAINED_EVENT_RADIUS", "UNEXPLAINED_PRICE_MULT", "TYPICAL_MOVE_SESSIONS"]
