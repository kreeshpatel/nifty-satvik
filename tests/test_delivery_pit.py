"""PIT / truncation guard for the delivery features (nq.data.delivery) — 0017's lesson as spec.

The features feed the 0118 label screen (and any later selection use), so they MUST be trailing-only:
deriving on a panel truncated at date D must reproduce every past value byte-identically. Any
forward-looking op (centered window, full-sample z, bfill) breaks this test.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from nq.data.delivery import FEATURES, apply_alias_map, derive_delivery_features


def _synth(n_days: int = 320, n_sym: int = 4) -> pd.DataFrame:
    rng = np.random.default_rng(11)
    dates = pd.bdate_range("2023-01-02", periods=n_days)
    rows = []
    for s in range(n_sym):
        dp = np.clip(rng.normal(45, 15, n_days), 5, 95)
        ret = rng.normal(0, 0.02, n_days)
        for i, d in enumerate(dates):
            rows.append((f"SYM{s}", d, dp[i], ret[i]))
    return pd.DataFrame(rows, columns=["symbol", "date", "deliv_pct", "ret"])


def test_truncation_invariance():
    panel = _synth()
    D = panel["date"].sort_values().unique()[200]
    full = derive_delivery_features(panel)
    trunc = derive_delivery_features(panel[panel["date"] <= D])
    f = full[full["date"] <= D].reset_index(drop=True)
    t = trunc.reset_index(drop=True)
    pd.testing.assert_frame_equal(f, t)


def test_features_present_and_trailing_nan_head():
    out = derive_delivery_features(_synth(60, 1))
    for c in FEATURES:
        assert c in out.columns
    # warmup rows are NaN (rolling min_periods) — no bfill contamination
    assert out["dlv_med21"].iloc[:9].isna().all()
    assert out["dlv_med21_z"].iloc[:60].isna().all()  # 252-day z can't exist in 60 rows


def test_alias_map_passthrough(tmp_path):
    raw = _synth(30, 1)
    p = tmp_path / "alias.json"; p.write_text('{"SYM0": "CANON"}')
    out = apply_alias_map(raw, p)
    assert set(out["symbol"]) == {"CANON"}
    missing = tmp_path / "none.json"
    assert apply_alias_map(raw, missing).equals(raw)
