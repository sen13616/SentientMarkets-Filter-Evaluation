"""Phase 2 tests: accounting, strategies, timing, filters, inference. Synthetic data only."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from filter_eval import filters as F
from filter_eval import strategies as S
from filter_eval.engine import build_book, run
from filter_eval.evaluate import Cell, closed_cell_list, run_cell
from filter_eval.inference import (benjamini_hochberg, max_drawdown, perm_pvalue, sharpe,
                                   stationary_bootstrap_indices)

from .synth import make_market, random_walk_market, states_from


def trades_df(rows):
    return pd.DataFrame(rows, columns=S.TRADE_COLS).astype(
        {"tk": int, "t": int, "entry": int, "exit": int, "dir": int, "w": float, "group": str})


# --- cost and P&L accounting -------------------------------------------------

def test_cost_accounting_hand_example():
    # One ticker. Window = sessions 1..4. Long w=1 decided at 1, entered at open 2, exit at open 4.
    O = np.array([[100.0], [100.0], [100.0], [101.0], [101.0]])
    C = np.array([[100.0], [100.0], [102.0], [99.0], [101.0]])
    m = make_market(O, C, ws=1)
    book = build_book(m, trades_df([(0, 1, 2, 4, 1, 1.0, "g")]))
    r = run(book, np.array([1.0])).ret[0]
    # Session 1: nothing held. Session 2 (entry): (102-100)/100 - 10bp on 1.00 notional.
    # Session 3: (99-102)/100. Session 4 (exit at open): (101-99)/100 - 10bp on 1.01 notional.
    expected = [0.0, 0.02 - 0.0010, -0.03, 0.02 - 0.0010 * 1.01]
    assert r == pytest.approx(expected, abs=1e-12)
    # Standalone trade return: 101/100 - 1 - 2 x 10bp.
    assert book.trade_ret[0] == pytest.approx(0.01 - 0.002)


def test_short_trade_and_mark_to_close_at_window_end():
    O = np.array([[50.0], [50.0], [50.0], [48.0]])
    C = np.array([[50.0], [50.0], [49.0], [45.0]])
    m = make_market(O, C, ws=1)
    # Short 0.5 entered at open 2, planned exit beyond the window -> closed at close 3.
    book = build_book(m, trades_df([(0, 1, 2, 9, -1, 0.5, "g")]))
    r = run(book, np.array([-0.5])).ret[0]
    exp2 = -0.5 * (49 - 50) / 50 - 0.001 * 0.5
    exp3 = -0.5 * (45 - 49) / 50 - 0.001 * 0.5 * 45 / 50     # close-out cost at the last close
    assert r == pytest.approx([0.0, exp2, exp3], abs=1e-12)


def test_consecutive_cohorts_in_same_name_net_their_costs():
    O = np.full((6, 1), 100.0)
    C = np.full((6, 1), 100.0)
    m = make_market(O, C, ws=1)
    rows = [(0, 1, 2, 4, 1, 0.5, "a"), (0, 3, 4, 6, 1, 0.5, "b")]  # second enters as first exits
    book = build_book(m, trades_df(rows))
    res = run(book, np.array([0.5, 0.5]))
    # Flat prices: the only P&L is cost. Entry 0.5 at open 2, no trade at the roll (open 4),
    # close-out 0.5 at the last close (session 5).
    assert res.traded[0].tolist() == pytest.approx([0.0, 0.5, 0.0, 0.0, 0.5])
    assert res.ret[0].sum() == pytest.approx(-0.001)


# --- strategies on panels with known answers ---------------------------------

def trend_market(n=10, n_hist=70, n_win=20):
    g = (np.arange(n) - 4.5) * 0.002            # ticker i drifts at g_i per session
    T = n_hist + n_win
    C = 50 * np.exp(np.outer(np.arange(T), g))
    return make_market(C.copy(), C, ws=n_hist)


def test_csm_known_answer():
    m = trend_market()
    tr = S.csm(m)
    assert sorted(tr["t"].unique()) == list(range(m.d0, m.we, 5))
    for t, g in tr.groupby("t"):
        assert sorted(g.loc[g["dir"] == 1, "tk"]) == [8, 9]
        assert sorted(g.loc[g["dir"] == -1, "tk"]) == [0, 1]
        assert np.allclose(g["w"], 0.25) and (g["entry"] == t + 1).all() and (g["exit"] == t + 6).all()


def test_str_known_answer():
    m = trend_market()
    tr = S.str_(m)
    assert sorted(tr["t"].unique()) == list(range(m.d0, m.we))
    for _, g in tr.groupby("t"):
        assert sorted(g["tk"]) == [0, 1] and (g["dir"] == 1).all() and np.allclose(g["w"], 0.1)


def test_tsmom_known_answer_with_one_reversal():
    m = trend_market()
    # Ticker 9 collapses at session d0+5 so its 60-session return turns negative there.
    m.close[m.d0 + 5:, 9] = m.close[m.d0 + 5:, 9] * 0.1
    tr = S.tsmom(m).set_index("tk")
    assert sorted(tr.index) == [5, 6, 7, 8, 9]                  # positive drift names
    assert (tr["t"] == m.d0).all() and (tr["entry"] == m.d0 + 1).all()
    assert tr.loc[9, "exit"] == m.d0 + 6                         # decided at d0+5, out at next open
    assert (tr.drop(9)["exit"] == m.we + 1).all()                # held to the end, marked
    assert np.allclose(tr["w"], 0.1)


def test_brk_known_answer():
    T, ws = 300, 270
    C = np.full((T, 2), 100.0)
    C[ws + 3:, 0] = 120.0                                        # breakout on session ws+3
    m = make_market(C.copy(), C, ws=ws)
    tr = S.brk(m)
    assert tr[["tk", "t", "entry", "exit"]].values.tolist() == [[0, ws + 3, ws + 4, ws + 24]]


def test_brk_ignores_signals_while_held():
    T, ws = 300, 270
    C = np.full((T, 1), 100.0)
    C[ws:, 0] = 100.0 * 1.01 ** np.arange(1, T - ws + 1)          # a new high every session
    m = make_market(C.copy(), C, ws=ws)
    tr = S.brk(m)
    assert tr["t"].tolist() == [ws, ws + 21]                      # re-entry only once flat again
    assert tr["entry"].tolist() == [ws + 1, ws + 22]


def test_rsi_mr_known_answer():
    T, ws = 120, 60
    c = np.full(T, 100.0) * 1.001 ** np.arange(T)                 # gentle rise: RSI high
    drop_t = ws + 2
    c[drop_t:] = c[drop_t:] * 0.80                                # one sharp fall: RSI below 30
    rise_t = ws + 8
    c[rise_t:] = c[rise_t:] * 1.30                                # sharp recovery: RSI above 50
    m = make_market(c[:, None].copy(), c[:, None], ws=ws)
    rsi = S.wilder_rsi(m.close)[:, 0]
    assert rsi[drop_t - 1] >= 30 > rsi[drop_t] and rsi[rise_t - 1] <= 50 < rsi[rise_t]
    tr = S.rsi_mr(m)
    assert tr[["t", "entry", "exit"]].values.tolist() == [[drop_t, drop_t + 1, rise_t + 1]]


def test_rsi_mr_time_stop():
    T, ws = 140, 60
    c = np.full(T, 100.0) * 1.001 ** np.arange(T)
    c[ws + 2:] *= 0.80
    c[ws + 3:] = c[ws + 2]                                        # flat afterwards: never crosses 50
    m = make_market(c[:, None].copy(), c[:, None], ws=ws)
    tr = S.rsi_mr(m)
    assert tr[["t", "entry", "exit"]].values.tolist() == [[ws + 2, ws + 3, ws + 23]]


# --- look-ahead in prices ----------------------------------------------------

@pytest.mark.parametrize("name", list(S.STRATEGIES))
def test_decisions_use_closes_through_t_only(name):
    m = random_walk_market(n=40, n_hist=260, n_win=40, seed=3, drift=0.0005)
    a = S.STRATEGIES[name](m)
    cut = m.d0 + 15
    m2 = random_walk_market(n=40, n_hist=260, n_win=40, seed=3, drift=0.0005)
    rng = np.random.default_rng(9)
    m2.close[cut + 1:] *= np.exp(rng.normal(0, 0.1, m2.close[cut + 1:].shape))
    m2.open[cut + 1:] *= np.exp(rng.normal(0, 0.1, m2.open[cut + 1:].shape))
    b = S.STRATEGIES[name](m2)
    key = ["tk", "t", "entry", "dir", "w"]
    pa = a.loc[a["t"] <= cut, key].reset_index(drop=True)
    pb = b.loc[b["t"] <= cut, key].reset_index(drop=True)
    pd.testing.assert_frame_equal(pa, pb)
    assert (a["entry"] == a["t"] + 1).all()


# --- filters -------------------------------------------------------------------

def test_gate_size_veto_rules():
    tr = trades_df([(0, 0, 1, 2, 1, 1.0, "g"), (1, 0, 1, 2, -1, 1.0, "g"), (2, 0, 1, 2, 1, 1.0, "g")])
    idx = np.array([[60.5, 40.4, np.nan]])
    assert F.gate_mask(idx, tr, "CSM").tolist() == [[True, True, False]]   # 60.5 rounds to 61
    assert F.gate_mask(np.array([[60.4, 40.5, 70]]), tr, "CSM").tolist() == [[False, False, True]]
    assert F.gate_mask(np.array([[41, 41, 40.4]]), tr, "STR").tolist() == [[True, True, False]]
    assert F.size_mult(np.array([[65, 35, np.nan]]), tr, "CSM")[0] == pytest.approx([0.5, 0.5, 0.0])
    assert F.size_mult(np.array([[55, 90, 30]]), tr, "STR")[0] == pytest.approx([0.5, 1.0, 0.0])
    conf = np.array([[59, 60, 90]])
    div = np.array([[0.0, 0.0, 1.0]])
    assert F.veto_mask(conf, div).tolist() == [[False, True, False]]


def test_redistribute_within_group():
    tr = trades_df([(0, 0, 1, 2, 1, 0.25, "a"), (1, 0, 1, 2, 1, 0.25, "a"), (2, 0, 1, 2, 1, 0.5, "b")])
    out = F.redistribute_within_group(np.array([[1.0, 0.0, 0.0]]), tr)
    assert out.tolist() == [[2.0, 0.0, 0.0]]                   # leg a keeps 0.5; leg b in cash


def test_size_filter_matches_unfiltered_gross_each_day():
    m = random_walk_market(n=60, seed=5)
    tr = S.csm(m)
    rng = np.random.default_rng(1)
    st = states_from(rng.uniform(0, 100, (m.n, m.we - m.ws + 1)), ws=m.ws)
    book = build_book(m, tr)
    base = run(book, F.signed_weights(book.trades))
    mult = F.size_mult(st.lookup(st.index["score_exo"], book.trades), book.trades, "CSM")
    sized = run(book, F.signed_weights(book.trades, mult), base.gross[0])
    live = sized.gross[0] > 0
    assert np.allclose(sized.gross[0][live], base.gross[0][live])


# --- inference -----------------------------------------------------------------

def test_inference_helpers():
    assert perm_pvalue(1.0, np.array([0.5, 1.0, 2.0])) == pytest.approx(3 / 4)
    assert benjamini_hochberg(np.array([0.01, 0.04, 0.03])) == pytest.approx([0.03, 0.04, 0.04])
    assert max_drawdown(np.array([0.1, -0.22, 0.05])) == pytest.approx(0.2)
    r = np.array([0.01, -0.01, 0.02])
    assert float(sharpe(r)) == pytest.approx(r.mean() / r.std(ddof=1) * np.sqrt(252))
    idx = stationary_bootstrap_indices(40, 500, 10.0, np.random.default_rng(0))
    runs = (np.diff(idx, axis=1) == 1) | (np.diff(idx, axis=1) == -39)
    assert 1 / (1 - runs.mean()) == pytest.approx(10, rel=0.15)  # mean block length ~ 10


def test_closed_cell_list():
    cells = closed_cell_list()
    assert len(cells) == 72 and len({c.id for c in cells}) == 72
    assert sum(c.filter != "none" for c in cells) == 67
    assert not any(c.index == "market" for c in cells)


# --- null and planted-effect checks ------------------------------------------

def test_null_random_states_give_centred_differences():
    """Random states, zero drift, zero cost, a fresh price path per replication: by symmetry
    E[Sharpe] is zero for the base and for any state-independent subset, so the difference
    must centre on zero. A fresh path per replication matters: conditional on one fixed path
    the base Sharpe is fixed and subset differences need not centre (an earlier version of this
    test held the path fixed and failed for that reason). Cost is set to zero so the symmetry is
    exact; the p-value check below runs with costs on."""
    diffs = []
    rng = np.random.default_rng(123)
    for rep in range(300):
        m = random_walk_market(n=100, seed=1000 + rep)
        tr = S.csm(m)
        st = states_from(rng.uniform(0, 100, (m.n, m.we - m.ws + 1)), ws=m.ws)
        res = run_cell(Cell("t", "CSM", "gate", "score_exo", start=str(m.sessions[m.d0])),
                       m, st, tr, n_perm=1, n_boot=2, seed=rep, cost=0.0)
        diffs.append(res["sharpe_diff"])
    diffs = np.array(diffs)
    se = diffs.std(ddof=1) / np.sqrt(len(diffs))
    print(f"\nnull centring (no cost): mean diff {diffs.mean():+.3f}, se {se:.3f}, n={len(diffs)}")
    assert abs(diffs.mean()) < 3 * se


def test_null_random_states_give_uniform_pvalues():
    """Random states with costs on: permutation p-values should be roughly uniform."""
    ps, diffs = [], []
    rng = np.random.default_rng(456)
    for rep in range(200):
        m = random_walk_market(n=100, seed=5000 + rep)
        tr = S.csm(m)
        st = states_from(rng.uniform(0, 100, (m.n, m.we - m.ws + 1)), ws=m.ws)
        res = run_cell(Cell("t", "CSM", "gate", "score_exo", start=str(m.sessions[m.d0])),
                       m, st, tr, n_perm=199, n_boot=2, seed=rep)
        ps.append(res["p_perm"])
        diffs.append(res["sharpe_diff"])
    ps = np.array(ps)
    ks = stats.kstest(ps, "uniform").pvalue
    print(f"\nnull p-values (10bp cost): KS vs U(0,1) p={ks:.3f}, share p<0.05 = {np.mean(ps < 0.05):.3f}, "
          f"share p<0.10 = {np.mean(ps < 0.10):.3f}, mean diff with costs {np.mean(diffs):+.3f}")
    assert ks > 0.01
    assert np.mean(ps < 0.05) < 0.10


def test_planted_effect_is_detected():
    m = random_walk_market(n=100, seed=21)
    tr = S.csm(m)
    book = build_book(m, tr)
    dw = m.we - m.ws + 1
    idx = np.full((m.n, dw), 50.0)                                 # neutral by default (gated out)
    for (i, t, d), r in zip(book.trades[["tk", "t", "dir"]].values, book.trade_ret):
        if r > 0:                                                  # mark winners as agreeing
            idx[i, t - m.ws] = 80.0 if d > 0 else 20.0
    st = states_from(idx, ws=m.ws)
    res = run_cell(Cell("t", "CSM", "gate", "score_exo", start=str(m.sessions[m.d0])),
                   m, st, tr, n_perm=999, n_boot=200, seed=7)
    print(f"\nplanted effect: sharpe diff {res['sharpe_diff']:+.2f}, p={res['p_perm']:.4f}, "
          f"95% CI [{res['boot_lo']:+.2f}, {res['boot_hi']:+.2f}], retention {res['retention']:.2f}")
    assert res["sharpe_diff"] > 0 and res["p_perm"] < 0.05 and res["boot_lo"] > 0
    assert res["attr_removed_mean"] < 0 < res["attr_kept_mean"]


# --- missing states and the ledger ---------------------------------------------

def test_missing_states_are_skipped_counted_and_trigger_restricted_comparator():
    m = random_walk_market(n=60, seed=31)
    tr = S.csm(m)
    rng = np.random.default_rng(2)
    idx = rng.uniform(0, 100, (m.n, m.we - m.ws + 1))
    idx[:6, :] = np.nan                                            # 10% of names never have a state
    st = states_from(idx, ws=m.ws)
    res = run_cell(Cell("t", "CSM", "gate", "score_exo", start=str(m.sessions[m.d0])),
                   m, st, tr, n_perm=9, n_boot=5)
    assert res["n_missing_state"] == res["attr_removed_missing_n"] > 0
    assert res["missing_share"] > 0.05 and "sharpe_diff_vs_restricted" in res
    assert res["r_n_trades"] == res["n_candidates"] - res["n_missing_state"]


def test_ledger_is_append_only(tmp_path):
    from filter_eval import ledger
    p = tmp_path / "ledger.csv"
    ledger.append({"cell": "a", "seed": 1}, p)
    first = p.read_text()
    ledger.append({"cell": "b", "seed": 1}, p)
    text = p.read_text()
    assert text.startswith(first) and text.count("\n") == 3
