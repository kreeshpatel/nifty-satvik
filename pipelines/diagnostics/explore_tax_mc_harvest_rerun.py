"""MEASUREMENT (owner task 2026-11-19, item 5): the S1->S2 harvest step re-run on the EXISTING 4,000 Monte Carlo draws
with the hash-seed-fixed #212 simulator. Analysis, not tax advice. No live change; counts unchanged.

Same parameters and paths as the #214 run: explore_tax_montecarlo.draw_params(mc, 2000, seed) for i < 2000 and
(mc, 2000, n_double_seed) for i >= 2000; path for draw i = default_rng(path_seed + i); same drift and harvest offset.
Only S1 (no harvest) and S2 (harvest) are simulated, law E, books 60/40 and 65/35. Results are keyed by the draw index
`i` (the cache files are in completion order, not index order). Old values come from .cache/tax_mc/main*.jsonl.
The draw parameters are re-derived from the seeds and checked equal to the cached `p` of every draw.

    python pipelines/diagnostics/explore_tax_mc_harvest_rerun.py
"""
from __future__ import annotations

import json
import multiprocessing as mp
import sys
import time
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts"), str(ROOT / "pipelines" / "research"),
                str(ROOT / "pipelines" / "diagnostics"), str(ROOT / "pipelines" / "lifecycle")]
import explore_india_tax_practices as T  # noqa: E402
import explore_tax_montecarlo as M  # noqa: E402

OUT_JSON = ROOT / "diagnostics" / "research" / "explore" / "2026-11-19_tax_mc_harvest_rerun.json"


def one(task):
    i, p = task
    G = M.G
    cfg = M.apply_params(G["base"], G["mc"], p)
    r, _ = M.path_returns("boot", i, p["index_drift"])
    ctx = M.make_ctx(r, [cfg])
    o = cfg["individual"]["owner_marginal_slab"]
    out = {"i": i}
    with M.scoped(p["harvest_offset_days"]):
        for b in M.BOOKS:
            out[b] = {"S1": T.simulate(b, cfg, ctx, slab=o, cash_leg=T.ARB)["final"],
                      "S2": T.simulate(b, cfg, ctx, slab=o, cash_leg=T.ARB, harvest=True, harvest_day=T.HARVEST_DAY)["final"]}
    return out


def q(x):
    x = np.asarray(x, float)
    return {"p5": round(float(np.percentile(x, 5)), 0), "p50": round(float(np.percentile(x, 50)), 0),
            "p95": round(float(np.percentile(x, 95)), 0), "P(gain>0)": round(float((x > 0).mean()), 4), "n": int(len(x))}


def main() -> int:
    mc = yaml.safe_load(M.MC_CFG.read_text(encoding="utf-8"))
    S = mc["sampling"]
    P = M.draw_params(mc, S["n_draws"], S["seed"]) + M.draw_params(mc, S["n_draws"], S["n_double_seed"])
    old = {}
    for tag in ("main", "main_double"):
        for line in (M.CACHE / f"{tag}.jsonl").read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                old[r["i"]] = r
    assert len(old) == len(P) == 4000
    bad = [i for i in range(4000) if any(abs(float(old[i]["p"][k]) - float(P[i][k])) > 1e-12 for k in P[i])]
    if bad:
        raise SystemExit(f"re-derived parameters differ from the cache on {len(bad)} draws: stop")
    t0 = time.time()
    with mp.Pool(S["workers"], initializer=M.init_worker) as pool:
        new = {r["i"]: r for r in pool.imap_unordered(one, list(enumerate(P)), chunksize=8)}
    print(f"re-run {len(new)} draws in {time.time() - t0:.0f}s", flush=True)
    res = {"n": 4000, "seconds": round(time.time() - t0)}
    for b in M.BOOKS:
        idx = range(4000)
        off = np.array([P[i]["harvest_offset_days"] for i in idx])
        s1_old = np.array([old[i]["v"][f"E|{b}"]["S1"] for i in idx])
        s1_new = np.array([new[i][b]["S1"] for i in idx])
        g_old = np.array([old[i]["v"][f"E|{b}"]["S2"] for i in idx]) - s1_old
        g_new = np.array([new[i][b]["S2"] for i in idx]) - s1_new
        pre = off <= 15
        half = np.arange(4000) < 2000
        res[b] = {"S1_max_abs_change_rupees": round(float(np.abs(s1_new - s1_old).max()), 4),
                  "draws_where_harvest_gain_changed_gt_1rupee": int((np.abs(g_new - g_old) > 1).sum()),
                  "max_abs_gain_change": round(float(np.abs(g_new - g_old).max()), 0),
                  "all": {"old": q(g_old), "new": q(g_new)},
                  "pre_31_march_le_15": {"old": q(g_old[pre]), "new": q(g_new[pre])},
                  "on_or_after_31_march_gt_15": {"old": q(g_old[~pre]), "new": q(g_new[~pre])},
                  "convergence_new_all": {"p50_first_half": round(float(np.median(g_new[half])), 0),
                                          "p50_all": round(float(np.median(g_new)), 0),
                                          "p50_rel_change": round(abs(float(np.median(g_new[half])) / float(np.median(g_new)) - 1), 4),
                                          "P_abs_change": round(abs(float((g_new[half] > 0).mean()) - float((g_new > 0).mean())), 4)},
                  "bins_new": [{"offset": f"{lo:+d}..{(lo + 4 if lo < 25 else 30):+d}",
                                **q(g_new[(off >= lo) & (off <= (lo + 4 if lo < 25 else 30))])} for lo in range(-30, 26, 5)]}
    OUT_JSON.write_text(json.dumps(res, indent=1, default=float) + "\n", encoding="utf-8")
    print(json.dumps({b: {k: v for k, v in res[b].items() if k != "bins_new"} for b in M.BOOKS}, indent=1))
    return 0


if __name__ == "__main__":
    mp.freeze_support()
    raise SystemExit(main())
