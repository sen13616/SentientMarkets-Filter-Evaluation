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

# Event period: reaction sessions R in [EVENT_START, EVENT_END] (section 3).
EVENT_START = date(2026, 5, 12)
EVENT_END = date(2026, 6, 18)

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
ATR_N = 14
E2_ATR_MULT = 3.0

# Moves (section 4) and the unexplained-move rule (section 5).
MOVE_UNITS = 1.0
LARGE_MOVE_UNITS = 2.0
NOISE_EXCLUSION = 2            # noise sessions are > 2 sessions from any event
UNEXPLAINED_EVENT_RADIUS = 1
UNEXPLAINED_PRICE_MULT = 2.0

# Inference (section 6).
SEED = 20260512
N_PLACEBO = 20
N_PERM = 1000
N_BOOT = 2000
ALPHA = 0.05
PRIMARY_MIN_ACCURACY = 0.60
PRIMARY_MAX_UNEXPLAINED = 0.50

# Power estimate (Phase 0).
POWER_TARGET = 0.80


def config_dict() -> dict:
    return {k: (str(v) if isinstance(v, (date, time, pd.Timestamp, Path)) else v)
            for k, v in globals().items()
            if k.isupper() and not isinstance(v, Path)}


def config_hash() -> str:
    blob = json.dumps(config_dict(), sort_keys=True, default=str).encode()
    return hashlib.sha256(blob).hexdigest()[:12]
