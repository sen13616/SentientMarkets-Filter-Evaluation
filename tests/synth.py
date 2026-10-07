"""Synthetic markets and states for the engine tests. No real data is used."""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np

from filter_eval.filters import States
from filter_eval.market import Market


def make_market(open_: np.ndarray, close: np.ndarray, ws: int, d0: int | None = None) -> Market:
    n_s = open_.shape[0]
    sessions = [date(2020, 1, 1) + timedelta(days=k) for k in range(n_s)]
    return Market(sessions=sessions, tickers=[f"T{i}" for i in range(open_.shape[1])],
                  open=open_.astype(float), close=close.astype(float), ws=ws, we=n_s - 1,
                  d0=ws if d0 is None else d0)


def random_walk_market(n: int = 100, n_hist: int = 80, n_win: int = 40, vol: float = 0.02,
                       seed: int = 0, drift: float = 0.0) -> Market:
    rng = np.random.default_rng(seed)
    T = n_hist + n_win
    # Overnight and intraday log moves; zero drift => no strategy has an edge.
    on = rng.normal(drift / 2, vol / np.sqrt(2), (T, n))
    intra = rng.normal(drift / 2, vol / np.sqrt(2), (T, n))
    logc = np.cumsum(on + intra, axis=0) + np.log(50)
    logo = logc - intra
    return make_market(np.exp(logo), np.exp(logc), ws=n_hist)


def states_from(index: np.ndarray, conf: np.ndarray | None = None, div_high: np.ndarray | None = None,
                ws: int = 0) -> States:
    n, dw = index.shape
    conf = np.full((n, dw), 90.0) if conf is None else conf
    div_high = np.zeros((n, dw)) if div_high is None else div_high
    names = ("score_exo", "composite", "narrative", "influencer", "macro")
    return States(index={k: index for k in names}, conf=conf, div_high=div_high, ws=ws)
