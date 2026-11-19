"""MEASUREMENT (amendment to PR #214, item 2): owner surcharge as a dimension of the company (S4) vs individual (S2)
comparison. Analysis, not tax advice. No live change; counts unchanged.

WHAT CHANGES vs the #214 run: the owner's surcharge s in {0, 10%, 15%, 25%} (CONFIRM WITH CA). In the #212 simulator
`individual.surcharge_on_cg = s` applies s to slab (interest / debt) income and min(s, 15%) to capital gains
(`individual.surcharge_cap_on_cg`, unchanged). The final dividend from the company to the owner is taxed at
owner_slab x (1 + s) x (1 + cess) [ASSUMED; at the base 30% / 15% / 4% this is the config's 35.88%. The statutory
surcharge on dividends may itself be capped at 15% - CONFIRM WITH CA].
EVERY draw is evaluated at ALL FOUR surcharge levels (a full conditional design, so each level has 2,000 draws on
identical paths and parameters); "discrete parameter" results are the per-level conditionals.

SAME DRAWS as #214's first pass: explore_tax_montecarlo.draw_params(mc, 2000, sampling.seed), path for draw i =
default_rng(paths.path_seed + i), identical drift re-centring and harvest offset. Only S2 and S4 are re-simulated:
laws E, A, B, C (D does not touch S2 or S4), books 60/40 and 65/35; break-even (s60, law E) without / with dividend via
explore_india_tax_practices.break_even (bisection on log capital, Rs 20L..Rs 500 crore).
ANCHOR: #212's break-even at maximum surcharge (s = 25%, historical path, base parameters, no dividend) =
Rs 5.52 crore (55,176,677); reproduce within 2% or stop.

    python pipelines/diagnostics/explore_tax_mc_surcharge.py
"""
from __future__ import annotations

import copy
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

LEVELS = (0.0, 0.10, 0.15, 0.25)
OUT_JSON = ROOT / "diagnostics" / "research" / "explore" / "2026-11-19_tax_mc_surcharge.json"
TAG = "surcharge"
ANCHOR_BE = 55_176_677.0


def with_surcharge(cfg: dict, s: float) -> dict:
    c = copy.deepcopy(cfg)
    c["individual"]["surcharge_on_cg"] = s
    c["company"]["dividend_rate_to_owner"] = c["individual"]["owner_marginal_slab"] * (1 + s) * (1 + c["individual"]["cess"])
    return c


def s2(book, cfg, ctx):
    return T.simulate(book, cfg, ctx, slab=cfg["individual"]["owner_marginal_slab"], cash_leg=T.ARB, harvest=True,
                      harvest_day=T.HARVEST_DAY)["final"]


def s4(book, cfg, ctx):
    return T.simulate(book, cfg, ctx, kind="company", cash_leg=T.ARB, harvest=True, harvest_day=T.HARVEST_DAY)["final"]


def run_one(task) -> dict:
    i, p = task
    G = M.G
    cfg0 = M.apply_params(G["base"], G["mc"], p)
    r, _ = M.path_returns("boot", i, p["index_drift"])
    law_cfgs = {"E": cfg0}
    law_cfgs["A"] = copy.deepcopy(cfg0); law_cfgs["A"]["equity"]["ltcg_exemption"] = 0
    law_cfgs["B"] = copy.deepcopy(cfg0); law_cfgs["B"]["equity"]["stcg"] = 0.30
    law_cfgs["C"] = cfg0
    per = {s: {law: with_surcharge(c, s) for law, c in law_cfgs.items()} for s in LEVELS}
    all_cfgs = [c for d in per.values() for c in d.values()]
    ctx = M.make_ctx(r, all_cfgs)
    out = {"i": i, "p": p, "v": {}, "be": {}}
    for law in ("E", "A", "B", "C"):
        with M.scoped(p["harvest_offset_days"], arb_at_slab=(law == "C")):
            for book in M.BOOKS:
                v4 = s4(book, per[0.0][law], ctx)          # the company does not see the owner's surcharge
                for s in LEVELS:
                    c = per[s][law]
                    out["v"][f"{law}|{book}|{s}"] = {"S2": s2(book, c, ctx), "S4": v4,
                                                    "S4div": v4 * (1 - c["company"]["dividend_rate_to_owner"])}
            if law == "E":
                for s in LEVELS:
                    c = per[s]["E"]
                    out["be"][str(s)] = {"no_div": T.break_even("s60", c, ctx, False), "with_div": T.break_even("s60", c, ctx, True)}
    return out


def anchor() -> dict:
    M.init_worker()
    c = with_surcharge(M.G["base"], 0.25)
    c["company"]["dividend_rate_to_owner"] = M.G["base"]["company"]["dividend_rate_to_owner"]   # #212 kept 35.88%
    ctx = M.make_ctx(M.G["r_tri"], [c])
    with M.scoped(0):
        be = T.break_even("s60", c, ctx, False)
    return {"break_even_rupees": be, "target": ANCHOR_BE,
            "rel_diff": None if be is None else round(abs(be / ANCHOR_BE - 1), 5),
            "ok": be is not None and abs(be / ANCHOR_BE - 1) <= 0.02}


def main() -> int:
    mc = yaml.safe_load(M.MC_CFG.read_text(encoding="utf-8"))
    a = anchor()
    print("ANCHOR", a, flush=True)
    out = {"anchor_212_max_surcharge": a, "levels": LEVELS}
    if not a["ok"]:
        OUT_JSON.write_text(json.dumps(out, indent=1, default=float) + "\n", encoding="utf-8")
        raise SystemExit("anchor mismatch: stop")
    S = mc["sampling"]
    P = M.draw_params(mc, S["n_draws"], S["seed"])
    tasks = [(i, P[i]) for i in range(S["n_draws"])]
    M.CACHE.mkdir(parents=True, exist_ok=True)
    f = M.CACHE / f"{TAG}.jsonl"
    done = {}
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                done[r["i"]] = r
    todo = [t for t in tasks if t[0] not in done]
    t0, buf = time.time(), []
    with mp.Pool(S["workers"], initializer=M.init_worker) as pool:
        for k, r in enumerate(pool.imap_unordered(run_one, todo, chunksize=2), 1):
            buf.append(r)
            if len(buf) >= S["checkpoint_every"] or k == len(todo):
                with f.open("a", encoding="utf-8") as fh:
                    for x in buf:
                        fh.write(json.dumps(x, default=float) + "\n")
                for x in buf:
                    done[x["i"]] = x
                buf = []
                print(f"{TAG}: {k}/{len(todo)} {time.time() - t0:.0f}s", flush=True)
    rows = [done[t[0]] for t in tasks]
    res = {}
    for law in ("E", "A", "B", "C"):
        for book in M.BOOKS:
            for s in LEVELS:
                v = [r["v"][f"{law}|{book}|{s}"] for r in rows]
                g = np.array([x["S4"] - x["S2"] for x in v])
                gd = np.array([x["S4div"] - x["S2"] for x in v])
                res[f"{law}|{book}|{s}"] = {"P(S4>S2)": round(float((g > 0).mean()), 4),
                                            "P(S4div>S2)": round(float((gd > 0).mean()), 4),
                                            "S4-S2": M.pct(g), "S4div-S2": M.pct(gd)}
    be = {}
    for s in LEVELS:
        for k in ("no_div", "with_div"):
            vals = [r["be"][str(s)][k] for r in rows]
            fin = np.array([x / 1e7 for x in vals if x is not None])
            be[f"{s}|{k}"] = {"share_with_break_even": round(float(len(fin) / len(vals)), 4),
                              **({f"p{q}": round(float(np.percentile(fin, q)), 2) for q in (5, 25, 50, 75, 95)} if len(fin) else {})}
    out.update({"n_draws": len(rows), "s4_vs_s2": res, "break_even_crore_s60_lawE": be})
    OUT_JSON.write_text(json.dumps(out, indent=1, default=float) + "\n", encoding="utf-8")
    print(json.dumps(be, indent=1), flush=True)
    return 0


if __name__ == "__main__":
    mp.freeze_support()
    raise SystemExit(main())
