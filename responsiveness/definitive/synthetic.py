"""Synthetic worlds for Test B (no real data). Used by the tests and by scripts/test_b_synthetic.py.

Each stock has a market-adjusted return r for every session (normal, with occasional jumps)
and a date-only score change D = noise + echo(r) at every session, plus a planted effect
`delta * d` at its event sessions. Two kinds of event:
- price-labelled (like E1 and E2): the stock's largest-|r| sessions, direction d = sign(r);
- independent: random other sessions, direction drawn at random;
- rating_like (like E3): sessions drawn with weight on larger moves, and 40% of directions
  set to the price move's sign (so about 70% agree with it), the rest at random.
"""

from __future__ import annotations

import numpy as np

from .regression import fit, freedman_lane_b, relabel_b

N_STOCKS, N_SESS = 60, 35
SIGMA_R, JUMP_P, JUMP_MU, JUMP_SD = 0.015, 0.04, 0.06, 0.02
SCORE_NOISE = 3.0                     # points
AGREE_P = 0.4                         # rating_like: share of ratings whose direction is the price move's


def echo_none(r):
    return np.zeros_like(r)


def echo_linear(r, k=100.0):
    return k * r                      # a 6% move echoes as 6 points


def echo_saturating(r, k=6.0, s=0.02):
    return k * np.tanh(r / s)         # price echo that levels off for large moves


def echo_step(r, k=4.0):
    return k * np.sign(r)             # the score reacts only to the sign of the move


def echo_all_three(r):
    return echo_linear(r) + echo_saturating(r) + echo_step(r)   # all three forms at once


ECHOES = {"none": echo_none, "linear": echo_linear, "saturating": echo_saturating, "step": echo_step,
          "all three": echo_all_three}


def world(rng, design: str = "independent", echo: str = "none", delta: float = 0.0,
          n_price: int = 2, n_indep: int = 2, date_shock: float = 0.0):
    """Returns (stock, direction, y, r, dates) for the events, and D, R, eligible matrices.
    `date_shock` > 0 adds a shock with that SD, common to every stock on a session, so all
    events on a date share it."""
    R = rng.normal(0, SIGMA_R, (N_STOCKS, N_SESS))
    jump = rng.random((N_STOCKS, N_SESS)) < JUMP_P
    R[jump] += rng.choice([-1, 1], jump.sum()) * rng.normal(JUMP_MU, JUMP_SD, jump.sum())
    D = rng.normal(0, SCORE_NOISE, R.shape) + ECHOES[echo](R)
    if date_shock:
        D += rng.normal(0, date_shock, N_SESS)[None, :]
    st, ss, dd = [], [], []
    for i in range(N_STOCKS):
        taken = set()
        if design in ("price_labelled", "mixed"):
            for j in np.argsort(-np.abs(R[i, 1:-1]))[:n_price] + 1:
                st.append(i); ss.append(j); dd.append(int(np.sign(R[i, j]))); taken.add(j)
        if design in ("independent", "mixed", "rating_like"):
            free = [j for j in range(1, N_SESS - 1) if j not in taken]
            if design == "rating_like":     # ratings land on bigger moves and often follow them
                w = np.abs(R[i, free]) + SIGMA_R
                picks = rng.choice(free, n_indep, replace=False, p=w / w.sum())
            else:
                picks = rng.choice(free, n_indep, replace=False)
            for j in picks:
                follows = design == "rating_like" and rng.random() < AGREE_P
                st.append(i); ss.append(j)
                dd.append(int(np.sign(R[i, j])) if follows else int(rng.choice([-1, 1])))
    st, ss, dd = np.array(st), np.array(ss), np.array(dd)
    np.add.at(D, (st, ss), delta * dd)                 # the response beyond price, at event sessions
    eligible = np.zeros_like(D, dtype=bool)
    eligible[:, 1:-1] = True
    return st, dd, D[st, ss], R[st, ss], ss, D, R, eligible


def one_test(rng, K: int = 199, controls: str = "linear", method: str = "relabel", **kw) -> tuple[float, float]:
    """One synthetic Test B: method "relabel" (random-session relabelling, P2) or
    "freedman_lane" (residual permutation, D14)."""
    st, dd, y, r, dates, D, R, elig = world(rng, **kw)
    b = fit(y, dd, r, controls)[1]
    if method == "freedman_lane":
        return b, freedman_lane_b(y, dd, r, b, K, rng, controls)["p"]
    return b, relabel_b(st, dd, b, D, R, elig, K, rng, controls)["p"]
