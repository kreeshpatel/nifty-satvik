"""Reconcile the null t spread between the harness and the blind replica (owner decision 4, PR #218).

Feeds the replica's exact random draws into the harness, so the two can be compared seed by seed. The draws are
rng(s).standard_normal over (all weekly dates from 2016) x (sorted symbols), masked to NMS coverage.
Reports the per-seed difference, the t spread at NW lag 8 vs lag 0, a 200-seed spread on the same draw shape, and
how many weekly holds overlap the next one.
"""
import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from nq.research.layer_gate import Gate, nw_t, weekly_dates  # noqa: E402

m = pickle.load(open(ROOT / ".cache/phase0_market.pkl", "rb"))
nms = pd.read_pickle(ROOT / ".cache/phase0_nms.pkl")
rep = np.array(json.load(open(ROOT / "diagnostics/replica/phase0/null_replica.json"))["null"]["t_by_seed"], float)
g = Gate(m)
wd = weekly_dates(m.close.index)
cols = sorted(m.close.columns)
cov = nms.reindex(index=wd, columns=cols).notna()
t8, t0 = [], []
for s in range(200):
    z = pd.DataFrame(np.random.default_rng(s).standard_normal((len(wd), len(cols))), index=wd, columns=cols).where(cov)
    a = g.alpha(z)
    t8.append(a["t_nw"])
    t0.append(nw_t(a["_weekly"].to_numpy(), 0)[1])
t8, t0 = np.array(t8), np.array(t0)
pos = m.close.index.get_indexer(wd)
gaps = pd.Series(np.diff(pos)).value_counts().sort_index()
out = {"per_seed_max_abs_diff_vs_replica_0_49": float(np.abs(t8[:50] - rep).max()),
       "sd_t_lag8_seeds_0_49": float(np.std(t8[:50], ddof=1)), "sd_t_lag0_seeds_0_49": float(np.std(t0[:50], ddof=1)),
       "sd_t_lag8_seeds_0_199": float(np.std(t8, ddof=1)), "mean_t_lag8_seeds_0_199": float(t8.mean()),
       "false_pass_two_sided_0_199_pct": float(100 * np.mean(np.abs(t8) >= 2.6)),
       "harness_own_draws_sd_200": 0.968,
       "weekly_gap_sessions_counts": {int(k): int(v) for k, v in gaps.items()},
       "holds_overlapping_next_week_pct": float(100 * (np.diff(pos) < 5).mean())}
(ROOT / "diagnostics/replica/phase0/null_reconcile.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print(json.dumps(out, indent=1))
