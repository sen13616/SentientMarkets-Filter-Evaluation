"""Assemble the inputs every script needs: universe, calendar, prices, events, states."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd

from . import data, events, sources
from .config import (DATA_END, EVENT_DIR, EVENT_END, EVENT_RAW, EVENT_START, MODEL_CHANGE, NOISE_EXCLUDE_TYPES,
                     NOISE_EXCLUSION, PRICE_FILE, TICK_DIR, TYPICAL_MOVE_SESSIONS, UNEXPLAINED_EVENT_RADIUS,
                     UNEXPLAINED_PRICE_MULT)
from .market import Prices, build_prices
from .measure import (TickBook, date_only_changes, noise_sessions, noise_units, state_cube,
                      two_session_changes)

PRICE_START = date(2025, 1, 1)
CANDIDATE_START = date(2026, 4, 27)   # first session with a sentiment state (first experiment, D4)
STATE_START = date(2026, 4, 27)


@dataclass
class Inputs:
    tickers: list[str]
    cal: events.Calendar
    prices: Prices
    cands: pd.DataFrame          # every candidate event with status
    ev_sessions: dict[str, set]  # all types (R9): unexplained moves
    noise_ev_sessions: dict[str, set]   # E1-E3 only (A3): noise and placebo sessions
    data_hash: str


@dataclass
class States:
    sessions: list[date]
    book: TickBook
    cube: np.ndarray             # (index, ticker, session) daily states
    chg: np.ndarray              # two-session state changes (noise units, unexplained moves)
    D: np.ndarray                # date-only changes (relabelling, placebo)
    noise_mask: np.ndarray       # (ticker, session) noise sessions
    period: np.ndarray           # (session,) in the event period with d-1 >= 12 May
    sd: np.ndarray               # (index, ticker) noise units; NaN if undefined
    sd_n: np.ndarray             # (index, ticker) changes behind each noise unit


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
                  ev_sessions=events.event_sessions(cands),
                  noise_ev_sessions=events.event_sessions(cands, NOISE_EXCLUDE_TYPES),
                  data_hash=data_hash(tickers))


def load_states(inp: Inputs, with_date_only: bool = True) -> States:
    sess = data.sessions(STATE_START, DATA_END)
    book = TickBook.from_frame(data.load_ticks(inp.tickers))
    cube = state_cube(book, inp.tickers, sess)
    chg = two_session_changes(cube)
    prev_ok = np.array([j > 0 and sess[j - 1] >= MODEL_CHANGE for j in range(len(sess))])
    chg[..., ~prev_ok] = np.nan                       # no change may span the model change (A1)
    mask = noise_sessions(inp.tickers, sess, (EVENT_START, EVENT_END), inp.noise_ev_sessions, inp.cal,
                          NOISE_EXCLUSION)
    sd, n = noise_units(chg, mask)
    D = date_only_changes(book, inp.tickers, sess) if with_date_only else np.full_like(cube, np.nan)
    period = np.array([EVENT_START <= d <= EVENT_END for d in sess]) & prev_ok
    return States(sessions=sess, book=book, cube=cube, chg=chg, D=D, noise_mask=mask, period=period,
                  sd=sd, sd_n=n)


def near_matrix(tickers: list[str], sessions: list[date], ev_sessions: dict[str, set], cal: events.Calendar,
                radius: int) -> np.ndarray:
    """(ticker, session): some event R within `radius` sessions."""
    out = np.zeros((len(tickers), len(sessions)), dtype=bool)
    for i, t in enumerate(tickers):
        evs = ev_sessions.get(t, set())
        if not evs:
            continue
        for j, d in enumerate(sessions):
            out[i, j] = any(cal.shift(d, k) in evs for k in range(-radius, radius + 1))
    return out


def typical_move(prices: Prices, end: date = MODEL_CHANGE, n: int = TYPICAL_MOVE_SESSIONS) -> pd.Series:
    """Median |market-adjusted return| over the n sessions ending `end` (M6)."""
    j = prices.pos(end)
    return prices.adj.iloc[j - n + 1:j + 1].abs().median(skipna=True)


def price_near_matrix(prices: Prices, tickers: list[str], sessions: list[date],
                      radius: int = UNEXPLAINED_EVENT_RADIUS, mult: float = UNEXPLAINED_PRICE_MULT) -> np.ndarray:
    """(ticker, session): |market-adjusted return| > mult x typical on some session within `radius`."""
    typ = typical_move(prices).reindex(tickers).to_numpy()
    big = (prices.adj[tickers].abs().to_numpy() > mult * typ[None, :])     # (all sessions, ticker)
    out = np.zeros((len(tickers), len(sessions)), dtype=bool)
    for j, d in enumerate(sessions):
        p = prices.pos(d)
        out[:, j] = big[max(p - radius, 0):p + radius + 1].any(axis=0)
    return out


def save_candidates(cands: pd.DataFrame) -> None:
    """Per-event table: local only (DATA root, never committed)."""
    EVENT_DIR.mkdir(parents=True, exist_ok=True)
    out = cands.copy()
    for c in ("R", "R_alt", "R_minus_1", "R_plus_1", "cluster_last_R"):
        if c in out:
            out[c] = out[c].astype(str)
    out.to_parquet(EVENT_DIR / "candidates.parquet", index=False)
