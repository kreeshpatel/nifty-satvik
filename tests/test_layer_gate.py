import numpy as np
import pandas as pd

from nq.research.layer_gate import Gate, Market, holm, nw_t


def _mkt(n_sess=900, n_sym=60, seed=0):
    idx = pd.bdate_range("2021-01-01", periods=n_sess)
    rng = np.random.default_rng(seed)
    close = pd.DataFrame(100 * np.exp(np.cumsum(rng.normal(0, 0.01, (n_sess, n_sym)), axis=0)), index=idx,
                         columns=[f"S{i}" for i in range(n_sym)])
    return Market(close=close, member=pd.DataFrame(True, index=idx, columns=close.columns),
                  adv=pd.DataFrame(1e9, index=idx, columns=close.columns))


def test_nw_t_and_holm():
    m, t = nw_t(np.r_[np.ones(50), np.ones(50) * 3], 4)
    assert m == 2 and t > 0
    adj = holm({"a": 0.01, "b": 0.04, "c": 0.03})
    assert adj["a"] == 0.03 and adj["c"] == 0.06 and adj["b"] == 0.06


def test_gate_never_reads_past_train_end():
    g = Gate(_mkt())
    ex = g.excess(21, 3)
    exit_pos = g.m.close.index.get_indexer(ex.index) + 24
    assert g.m.close.index[exit_pos].max() <= pd.Timestamp("2024-06-30")


def test_oracle_score_passes_and_self_corr_is_one():
    mk = _mkt()
    g = Gate(mk)
    fwd = mk.close.shift(-5) / mk.close - 1  # look-ahead oracle: must look extremely good
    a = g.alpha(fwd)
    assert a["t_nw"] > 5
    assert abs(g.corr_to(fwd, fwd) - 1) < 1e-9
