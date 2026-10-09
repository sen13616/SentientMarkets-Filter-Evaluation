"""Append-only run ledger (BRIEF.md ground rule 3). Same shape as Experiment 5A's."""

from __future__ import annotations

import csv
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .config import LEDGER, ROOT, config_hash

FIELDS = ["timestamp_utc", "measure_id", "config_hash", "code_commit", "data_hash", "seed", "status",
          "headline", "note"]
CODE_PATHS = ["lag", "responsiveness", "filter_eval"]


def code_commit() -> str:
    """HEAD short hash, or 'uncommitted' if any code path differs from HEAD or is untracked."""
    try:
        head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True,
                              text=True, check=True).stdout.strip()
        existing = [p for p in CODE_PATHS if (ROOT / p).exists()]
        dirty = subprocess.run(["git", "status", "--porcelain", "--", *existing], cwd=ROOT,
                               capture_output=True, text=True, check=True).stdout.strip()
        # Result files and the ledger itself change during a run; only code counts as dirty.
        dirty = "\n".join(l for l in dirty.splitlines()
                          if not any(s in l for s in ("/results/", "ledger.csv", "RESULTS.md", ".md")))
        return "uncommitted" if dirty else head
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "uncommitted"


def append(measure_id: str, data_hash: str, seed, headline: dict, status: str = "ok", note: str = "",
           path: Path = LEDGER) -> dict:
    """Append one row; existing rows are never rewritten."""
    row = {"timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "measure_id": measure_id, "config_hash": config_hash(), "code_commit": code_commit(),
           "data_hash": data_hash, "seed": seed, "status": status,
           "headline": json.dumps(headline, sort_keys=True, default=str), "note": note}
    new = not path.exists()
    with path.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow(row)
    return row
