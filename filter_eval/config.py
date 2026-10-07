"""Fixed study constants. Nothing here is tuned; see INSTRUCTIONS.md and DECISIONS.md."""

from __future__ import annotations

from datetime import date, time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RESULTS = ROOT / "results"

# Research window (INSTRUCTIONS.md section 1, 4).
WINDOW_START = date(2026, 4, 24)
WINDOW_END = date(2026, 6, 22)
# Holdout lock: nothing stamped after this instant is stored or analysed (D1).
LOCK_CUTOFF = pd.Timestamp("2026-06-22 23:59:59.999999", tz="UTC")
# First decision session: no state exists on 24 April (D4).
FIRST_DECISION = date(2026, 4, 27)
# Clean-narrative sub-window (section 9, item 7).
SUBWINDOW_START = date(2026, 5, 12)

# Daily state selection: last tick stamped before 21:45:00 UTC on day t (D3).
STATE_CUTOFF = time(21, 45)
SLOT_2130 = time(21, 30)
# A tick in [21:45, 22:00) is read as a late 21:30-slot tick (D9).
LATE_SLOT_END = time(22, 0)

# Prices.
PRICE_START = date(2025, 1, 1)

# API.
API_BASE = "https://sentimentapi-p.up.railway.app"
API_MIN_INTERVAL_S = 2.5   # <= 24 requests/minute (ground rule 9: at most 30)
API_MAX_RETRIES = 5

# Composite weights and the score_exo sub-weights (section 5).
LAYER_WEIGHTS = {"market": 0.35, "narrative": 0.30, "influencer": 0.25, "macro": 0.10}
EXO_LAYERS = ("narrative", "influencer", "macro")
DIVERGENCE_HIGH = 40.0

# Input indices (section 5). "composite" is the served smoothed score (D2).
INPUT_INDICES = ("score_exo", "composite", "narrative", "influencer", "macro")
