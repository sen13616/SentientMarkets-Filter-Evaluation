"""Append-only experiment ledger (ground rule 4)."""

from __future__ import annotations

import csv
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .config import ROOT

LEDGER = ROOT / "ledger.csv"
FIELDS = ["timestamp_utc", "cell", "config_hash", "code_commit", "data_snapshot", "seed", "status",
          "sharpe", "sharpe_diff", "p_perm", "n_trades", "retention", "note"]


def code_commit() -> str:
    """HEAD commit, or 'uncommitted' if tracked or untracked source files differ from it."""
    try:
        head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True,
                              text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "--", "filter_eval", "scripts", "tests"],
                               cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
        return "uncommitted" if dirty else head
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "uncommitted"


def append(row: dict, path: Path = LEDGER) -> None:
    """Append one row; never rewrites existing rows."""
    new = not path.exists()
    with path.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        if new:
            w.writeheader()
        out = {k: row.get(k, "") for k in FIELDS}
        out["timestamp_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        w.writerow(out)
