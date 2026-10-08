"""Fixed constants for Experiment 5A. Nothing here is tuned; see BRIEF.md and DECISIONS.md."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import date, time
from pathlib import Path

import pandas as pd

PKG = Path(__file__).resolve().parent
ROOT = PKG.parent
RESULTS = PKG / "results"
LEDGER = PKG / "ledger.csv"

# Local data root. Holds the sentiment tick cache and price bars built by the first
# experiment, plus this experiment's lock-filtered event downloads. Never committed.
# Override with SM_DATA_DIR (e.g. when running from a git worktree).
DATA = Path(os.environ.get("SM_DATA_DIR", ROOT / "data"))
TICK_DIR = DATA / "sentiment" / "ticks"
PRICE_FILE = DATA / "prices" / "daily.parquet"
EVENT_RAW = DATA / "responsiveness" / "raw"        # per-ticker yfinance tables, lock-filtered
EVENT_DIR = DATA / "responsiveness"                # per-event tables (kept out of git)
UNIVERSE_FILE = ROOT / "results" / "used_universe.csv"   # first experiment's used universe

# Data lock (ground rule 2). Same instant as the first experiment's lock.
DATA_START = date(2026, 5, 12)
DATA_END = date(2026, 6, 22)
LOCK_CUTOFF = pd.Timestamp("2026-06-22 23:59:59.999999", tz="UTC")

# Event period: reaction sessions R in [EVENT_START, EVENT_END] (section 3; DECISIONS.md A1).
EVENT_START = date(2026, 5, 13)
EVENT_END = date(2026, 6, 18)
# Narrative model change: no before reading or noise change may reach back before this day (A1).
MODEL_CHANGE = date(2026, 5, 12)

# Daily state: last tick stamped before 21:45 UTC on the session (section 4).
STATE_CUTOFF = time(21, 45)

# Indices (section 3). score_exo weights renormalised over the channels present.
EXO_WEIGHTS = {"narrative": 0.30, "influencer": 0.25, "macro": 0.10}
INDICES = ("score", "score_exo", "narrative", "influencer", "macro", "market")
CONTAMINATED = ("market",)          # reported, flagged, given no weight
PRIMARY_INDEX = "score_exo"
PLUMBING_INDEX = "influencer"       # index of interest for E3 and E4

# Events (section 4).
EVENT_TYPES = ("E1", "E2", "E3", "E4")   # also the overlap priority order
# Event groups reported (A2): each is a cell for every index.
# group -> (event types, direction filter or None)
GROUPS = {"E1": (("E1",), None), "E2": (("E2",), None), "E1+E2": (("E1", "E2"), None),
          "E3": (("E3",), None), "E4": (("E4",), None), "E4 purchase": (("E4",), 1),
          "E4 sale": (("E4",), -1)}
PRIMARY_GROUP = "E1+E2"
ATR_N = 14
E2_ATR_MULT = 3.0

# Moves (section 4) and the unexplained-move rule (section 5).
MOVE_UNITS = 1.0
LARGE_MOVE_UNITS = 2.0
NOISE_EXCLUSION = 2            # noise sessions are > 2 sessions from any E1-E3 event (A3)
NOISE_EXCLUDE_TYPES = ("E1", "E2", "E3")
MIN_NOISE_CHANGES = 10         # A3
UNEXPLAINED_EVENT_RADIUS = 1
UNEXPLAINED_PRICE_MULT = 2.0
TYPICAL_MOVE_SESSIONS = 120    # median |market-adjusted return| over the 120 sessions ending 12 May (M6)

# Inference (section 6).
SEED = 20260512
N_PLACEBO = 20
N_PERM = 1000
N_BOOT = 2000
ALPHA = 0.05
PRIMARY_MAX_UNEXPLAINED = 0.50   # primary rule as amended (A6): response p, signed-move p, this

# Power estimate (Phase 0).
POWER_TARGET = 0.80


def config_dict() -> dict:
    return {k: (str(v) if isinstance(v, (date, time, pd.Timestamp, Path)) else v)
            for k, v in globals().items()
            if k.isupper() and not isinstance(v, Path)}


def config_hash() -> str:
    blob = json.dumps(config_dict(), sort_keys=True, default=str).encode()
    return hashlib.sha256(blob).hexdigest()[:12]
