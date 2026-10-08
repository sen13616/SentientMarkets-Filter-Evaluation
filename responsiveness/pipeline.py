"""Assemble the inputs every script needs: universe, calendar, prices, events, states."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd

from . import data, events, sources
from .config import (DATA_END, EVENT_DIR, EVENT_END, EVENT_RAW, EVENT_START, NOISE_EXCLUSION, PRICE_FILE,
                     TICK_DIR)
from .market import Prices, build_prices
from .measure import TickBook, noise_sessions, noise_units, state_cube, two_session_changes

PRICE_START = date(2025, 1, 1)
CANDIDATE_START = date(2026, 4, 27)   # first session with a sentiment state (first experiment, D4)
STATE_START = date(2026, 4, 27)


@dataclass
class Inputs:
    tickers: list[str]
    cal: events.Calendar
    prices: Prices
    cands: pd.DataFrame          # every candidate event with status
    ev_sessions: dict[str, set]
    data_hash: str


@dataclass
class States:
    sessions: list[date]
    book: TickBook
    cube: np.ndarray             # (index, ticker, session)
    chg: np.ndarray              # two-session changes
    noise_mask: np.ndarray       # (ticker, session)
    sd: np.ndarray               # (index, ticker)
    sd_n: np.ndarray


def data_hash(tickers: list[str]) -> str:
    files = [PRICE_FILE] + [TICK_DIR / f"{t}.parquet" for t in tickers]
    files += [p for src in sources.SOURCES for p in (EVENT_RAW / src).glob("*.parquet")
              if p.stem in set(tickers)]
    return data.file_hash([f for f in files if f.exists()])


def load_inputs() -> Inputs:
    tickers = data.universe()
    cal = events.Calendar(data.sessions(PRICE_START, DATA_END))
    prices = build_prices(data.load_prices(), tickers, cal.sessions)
    earn = sources.load_source("earnings", tickers)
    rat = sources.load_source("ratings", tickers)
    ins = sources.load_source("insider", tickers)
    cands = events.build_candidates(earn, rat, ins, prices, cal, CANDIDATE_START, DATA_END)
    cands = events.resolve(cands, EVENT_START, EVENT_END)
    return Inputs(tickers=tickers, cal=cal, prices=prices, cands=cands,
                  ev_sessions=events.event_sessions(cands), data_hash=data_hash(tickers))


def load_states(inp: Inputs) -> States:
    sess = data.sessions(STATE_START, DATA_END)
    book = TickBook.from_frame(data.load_ticks(inp.tickers))
    cube = state_cube(book, inp.tickers, sess)
    chg = two_session_changes(cube)
    mask = noise_sessions(inp.tickers, sess, (EVENT_START, EVENT_END), inp.ev_sessions, inp.cal,
                          NOISE_EXCLUSION)
    sd, n = noise_units(chg, mask)
    return States(sessions=sess, book=book, cube=cube, chg=chg, noise_mask=mask, sd=sd, sd_n=n)


def save_candidates(cands: pd.DataFrame) -> None:
    """Per-event table: local only (DATA root, never committed)."""
    EVENT_DIR.mkdir(parents=True, exist_ok=True)
    out = cands.copy()
    for c in ("R", "R_alt", "R_minus_1", "R_plus_1"):
        out[c] = out[c].astype(str)
    out.to_parquet(EVENT_DIR / "candidates.parquet", index=False)
