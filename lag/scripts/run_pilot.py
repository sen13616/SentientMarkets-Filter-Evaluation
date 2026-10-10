"""Phase 2: the pilot run on real data, 12 May to 22 June 2026. The measurement itself is in
run_measures.py, shared with the definitive run.

    python -m lag.scripts.run_pilot
"""

from __future__ import annotations

from lag.scripts.run_measures import main

if __name__ == "__main__":
    main("pilot")
