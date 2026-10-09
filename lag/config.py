"""Fixed constants for Experiment 5B. Nothing here is tuned; see BRIEF.md and DECISIONS.md.

Two runs share this file: the pilot (12 May to 22 June 2026, hourly bars) and the definitive run
(2 October to 23 November 2026, 15-minute bars). `RUNS` holds what differs between them; the
definitive entries are frozen again, with any amendments, in `lag/definitive/config.py` (Phase 3).
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import date, time
from pathlib import Path

import pandas as pd

from responsiveness import config as r5a
from responsiveness.definitive import config as r5a_def

PKG = Path(__file__).resolve().parent
ROOT = PKG.parent
RESULTS = PKG / "results"
LEDGER = PKG / "ledger.csv"

# Local data root, shared with the other experiments; never committed. Override with SM_DATA_DIR.
DATA = Path(os.environ.get("SM_DATA_DIR", ROOT / "data"))
LAG_DATA = DATA / "lag"
BARS_1H = LAG_DATA / "bars_1h.parquet"            # pilot: hourly bars, 12 May to 22 June 2026
BARS_15M = LAG_DATA / "bars_15m.parquet"          # definitive: 15-minute store, 2 October to 23 November 2026
BARS_15M_MANIFEST = LAG_DATA / "bars_15m_manifest.json"
BARS_1H_MANIFEST = LAG_DATA / "bars_1h_manifest.json"
EVENT_DIR = LAG_DATA                              # per-event tables (kept out of git)

# Inputs built by the other experiments (read only).
PILOT_TICK_DIR = r5a.TICK_DIR                     # sentiment ticks, 24 April to 22 June 2026
PILOT_DAILY = r5a.PRICE_FILE                      # daily bars to 22 June 2026
PILOT_EARNINGS_RAW = r5a.EVENT_RAW                # 5A's lock-filtered yfinance tables
PILOT_UNIVERSE_FILE = r5a.UNIVERSE_FILE           # 473 names
DEFINITIVE_TICK_DIR = r5a_def.TICK_DIR            # written by 5A's definitive Phase 1; read only after its Phase 2
DEFINITIVE_DAILY = r5a_def.PRICE_FILE
DEFINITIVE_EARNINGS_RAW = r5a_def.EVENT_RAW

# ----------------------------------------------------------------------------- data lock (BRIEF.md section 3)
PILOT_END = pd.Timestamp("2026-06-22 23:59:59.999999", tz="UTC")           # allowed: the pilot
RESERVED_START = pd.Timestamp("2026-06-23 00:00:00", tz="UTC")               # reserved: nothing at all
RESERVED_END = pd.Timestamp("2026-10-01 23:59:59.999999", tz="UTC")
DEFINITIVE_START = pd.Timestamp("2026-10-02 00:00:00", tz="UTC")             # prices now; sentiment and events gated
DEFINITIVE_END = pd.Timestamp("2026-11-23 23:59:59.999999", tz="UTC")
# The gate: 5A's definitive results must be committed, and the date must be 24 November 2026 or later.
GATE_FILE = "responsiveness/definitive/RESULTS.md"
GATE_DATE = date(2026, 11, 24)

# ----------------------------------------------------------------------------- runs
RUNS = {
    "pilot": {
        "sessions": (date(2026, 5, 12), date(2026, 6, 22)),      # price and tick period
        "event_start": date(2026, 5, 13),                        # first ET calendar day of t0
        "period_end": PILOT_END,                                 # t0 + 48 h must not pass the last tick
        "bar": "1h",
        "bars_file": BARS_1H,
        "smoothing_half_life_h": 4.0,                            # the published score's EMA in this period
        "seed": 20260513,
    },
    "definitive": {
        "sessions": (date(2026, 10, 2), date(2026, 11, 23)),
        "event_start": date(2026, 10, 5),
        "period_end": DEFINITIVE_END,
        "bar": "15m",
        "bars_file": BARS_15M,
        "smoothing_half_life_h": 2.0,
        "seed": 20261005,
    },
}
BAR_MINUTES = {"1h": 60, "15m": 15}

# ----------------------------------------------------------------------------- indices (section 3)
INDICES = ("score", "score_raw", "score_exo", "narrative", "influencer", "macro", "market")
PRIMARY_INDICES = ("score_exo", "score_raw")
CONTAMINATED = ("market",)                        # computed from price; reported, flagged, given no weight
COMPOSITE_WEIGHTS = {"market": 0.35, "narrative": 0.30, "influencer": 0.25, "macro": 0.10}
EXO_WEIGHTS = r5a.EXO_WEIGHTS                     # 0.30 / 0.25 / 0.10, renormalised over those present

# ----------------------------------------------------------------------------- events (section 3)
EVENT_TYPES = ("L-E1", "L-E2")                    # also the clustering priority
E2_MULT = 3.0                                     # bar move > 3 x normal move
ROBUST_SD_FACTOR = 1.4826                         # robust SD = 1.4826 x median |return|
MIN_NORMAL_OBS = 10                               # bars at that time of day needed for a normal move (L3)
CLUSTER_WINDOW = pd.Timedelta(hours=48)
NON_EVENT_RADIUS = 2                              # placebo and relabel sessions are > 2 sessions from any event (L8)
MAX_BEFORE_AGE = pd.Timedelta(hours=2)            # a before reading older than this is a missing reading (L6)
NY = "America/New_York"

# ----------------------------------------------------------------------------- measurement (section 4)
PRE_WINDOW = pd.Timedelta(hours=6)
POST_WINDOW = pd.Timedelta(hours=48)
GRID_STEP = pd.Timedelta(minutes=5)               # finer than any tick spacing, so every tick is seen
MAIN_HORIZONS_MIN = (15, 30, 60, 120, 240, 480, 1440, 2880)
HALF_LEVEL = 0.5
FULL_LEVEL = 0.9
ALIGN_K = tuple(range(-12, 13))                   # shift in trading hours; positive = score lags price

# ----------------------------------------------------------------------------- inference (section 5)
K_PERM = 1000
B_BOOT = 2000
N_PLACEBO = 20
ALPHA = 0.05


def config_dict() -> dict:
    out = {}
    for k, v in globals().items():
        if not k.isupper() or isinstance(v, Path) or k in ("NY",):
            continue
        out[k] = json.loads(json.dumps(v, default=str, sort_keys=True))
    return out


def config_hash() -> str:
    return hashlib.sha256(json.dumps(config_dict(), sort_keys=True).encode()).hexdigest()[:12]
