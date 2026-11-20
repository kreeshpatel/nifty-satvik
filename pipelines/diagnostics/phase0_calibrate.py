"""Calibrate the layer-gate harness (company-engine Phase 0, Step 7). No candidate signal is run.

- **Anchor.** 0001's own ranker (NMS). It must correlate 1.0 with itself and show a positive momentum
  spread on the training window.
- **Null.** 200 seeds of i.i.d. normal scores with exactly the NMS coverage. Reports the false-pass rate at
  |t| ≥ 2.6 on gross alpha, and also the one-sided rate.
- **Placebo.** NMS shuffled across stocks within each date, 100 seeds. It must fail.

  python pipelines/diagnostics/phase0_calibrate.py [--null 200 --placebo 100 --out path]
"""
from __future__ import annotations

import argparse
import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from nq.research.layer_gate import T_PASS, Gate, load_market, nms_panel  # noqa: E402


def _load():
    mp, npth = ROOT / ".cache/phase0_market.pkl", ROOT / ".cache/phase0_nms.pkl"
    m = pickle.load(open(mp, "rb")) if mp.exists() else load_market()
    n = pd.read_pickle(npth) if npth.exists() else nms_panel(m)
    return m, n


def _clean(d):
    if isinstance(d, dict):
        return {str(k): _clean(v) for k, v in d.items() if k != "_weekly"}
    if isinstance(d, (np.floating, float)):
        return None if not np.isfinite(d) else round(float(d), 5)
    if isinstance(d, (np.bool_,)):
        return bool(d)
    return d


def main(n_null=200, n_placebo=100, out=None, seed0=0):
    m, nms = _load()
    g = Gate(m)
    anchor = g.evaluate(nms, ref_0001=nms)
    cov = nms.notna()
    null_t = []
    for s in range(seed0, seed0 + n_null):
        rnd = pd.DataFrame(np.random.default_rng(s).standard_normal(nms.shape), index=nms.index,
                           columns=nms.columns).where(cov)
        null_t.append(g.alpha(rnd)["t_nw"])
    null_t = np.array(null_t)
    plc_t = []
    for s in range(n_placebo):
        rng = np.random.default_rng(10_000 + s)
        v = nms.to_numpy().copy()
        for i in range(v.shape[0]):
            j = np.flatnonzero(np.isfinite(v[i]))
            v[i, j] = v[i, rng.permutation(j)]
        plc_t.append(g.alpha(pd.DataFrame(v, index=nms.index, columns=nms.columns))["t_nw"])
    plc_t = np.array(plc_t)
    res = {
        "window": {"first_signal": str(g.excess(5, 0).index.min().date()),
                   "last_signal": str(g.excess(5, 0).index.max().date()), "train_end": "2024-06-30"},
        "anchor_0001_nms": _clean(anchor),
        "null": {"seeds": n_null, "seed0": seed0, "false_pass_two_sided_pct": float(100 * np.mean(np.abs(null_t) >= T_PASS)),
                 "false_pass_one_sided_pct": float(100 * np.mean(null_t >= T_PASS)),
                 "t_mean": float(np.mean(null_t)), "t_sd": float(np.std(null_t, ddof=1)),
                 "t_p99_abs": float(np.quantile(np.abs(null_t), 0.99))},
        "placebo": {"seeds": n_placebo, "pass_pct": float(100 * np.mean(np.abs(plc_t) >= T_PASS)),
                    "t_mean": float(np.mean(plc_t)), "t_max_abs": float(np.max(np.abs(plc_t)))},
    }
    if out:
        Path(out).write_text(json.dumps(res, indent=1), encoding="utf-8")
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--null", type=int, default=200)
    ap.add_argument("--placebo", type=int, default=100)
    ap.add_argument("--out", default=str(ROOT / "diagnostics/research/explore/2026-11-20_phase0_calibration.json"))
    a = ap.parse_args()
    r = main(a.null, a.placebo, a.out)
    print(json.dumps({k: r[k] for k in ("window", "null", "placebo")}, indent=1))
    an = r["anchor_0001_nms"]
    print(json.dumps({k: an[k] for k in ("corr_0001", "decile_21", "decile_63", "ic_63", "alpha", "turnover_ann")}, indent=1))
