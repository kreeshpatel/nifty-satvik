"""MEASUREMENT: joint sensitivity + Monte Carlo on the India after-tax analysis (PR #212). Analysis, not tax advice.

Owner request 2026-11-19, branch research/tax-montecarlo (stacked on #212). No live change, no sealed read, no
trial-counter move. Distributions live in config/tax_montecarlo.yaml; base rates in config/tax_india_fy2627.yaml.

WHAT IS IMPORTED, NOT COPIED: explore_india_tax_practices.{simulate, scenarios, context, cash_prices, index_price,
break_even, load_cfg} - the lot-by-lot simulator of #212 runs unchanged. This file only builds its INPUTS:
  * cfg      a deep copy of the base config with one joint parameter draw written into it;
  * ctx      the simulator's price context with the index-fund price path replaced by a resampled one.
Two runtime mechanisms reach behaviour the simulator does not parameterise. Both are scoped to one draw and restored:
  * harvest-date offset: simulate() hard-codes 15 March; the module's `pd` is swapped for a proxy whose
    Timestamp(year=Y, month=3, day=15) returns 15 March + offset (every other call is plain pandas).
  * law C (arbitrage taxed at slab): ARB is removed from the module's EQUITY set, so its gains book to the debt bucket
    at slab and it is not harvested.
  Law D (family split fails): gifts are clubbed to the owner, so the household is taxed as one owner: S3 := S2.

PATHS  stationary bootstrap (Politis-Romano) of the DAILY index-TRI returns on the real 2019-03-05..2024-06-28
       session calendar, mean block 20 sessions. The SAME resampled indices are applied to the 70/30 blend's daily
       returns (cross-correlation check only - see below). The real dates are kept, so FY boundaries, the 365-day
       test and harvest timing are real; only the return attached to each date is resampled. The cash legs accrue a
       constant daily rate under the #212 proxy, so resampling them is the identity.
       Drift: the resampled index returns are re-centred on a drawn annual growth g ~ U(6%, 16%), keeping their
       standard deviation: r' = r - mean(r) + ln(1+g)/252 + var(r)/2.
       THIS MEASURES PATH UNCERTAINTY ON THE 2019-03..2024-06 HISTORY, NOT REGIME UNCERTAINTY: every path is built
       from days of that one window (plus a drift shift); a regime the window never saw is not in the draws.
       The blend is NOT tax-simulated in the Monte Carlo: its pass-through gains are the books' historical trade
       ledger, which has no meaning on a resampled path. Only the two static books are simulated.

DRAWS  Latin hypercube (seeded), one fresh path per draw, the same draws for every law scenario.
SCENARIOS per book (60/40, 65/35), as #212: S0 liquid; S1 arbitrage; S2 + harvesting (mid-March + offset);
       S3 = 3 PANs, two at slab 0% (owner's third + two zero-slab thirds; the two are identical, so simulated once x 2);
       S4 private company (and S4 with the final dividend at the config rate).
LAWS   E base; A LTCG exemption 0; B STCG 30%; C arbitrage at slab; D family split fails. C leaves S0 unchanged
       (liquid is debt either way); D changes only S3.
OUTPUTS
  1 terminal after-tax value (liquidation) p5/p25/p50/p75/p95 per law x book x scenario
  2 step gains S0->S1, S1->S2, S2->S3, S2->S4: distribution and P(gain > 0)
  3 rank order: share of draws with S3 > S2 > S1 > S0 > S4, and every pairwise P(Si > Sj), per law
  4 PRCC of each step gain (law E) on each parameter: rank-transform, regress out the other parameters from both,
    correlate the residuals; tornado table; top 3 per step
  5 company break-even capital (Rs crore), law E, 60/40, without / with dividend, via break_even(); "none" when no
    capital up to Rs 500 crore closes the gap
  6 parameters vs path: 500 draws at base parameters with paths varying; 500 draws on the historical path with
    parameters varying (incl. drift); std and IQR of each step gain in each mode vs the full run
  7 convergence: p50 relative change < 1% and P(gain>0) absolute change < 0.01 between the first half and all draws,
    per step (law E, both books); if not, a second independent LHS of the same size is added once
ANCHORS (step 0): the deterministic #212 pipeline reproduces +48,122 / +13,460 / +2,38,886 / -8,47,439 and 22.86%
    (tolerance Rs 1,000 / 0.02pp); and the identity path (no resample, no drift, base params) through THIS file's
    ctx builder reproduces the same S0..S4 values to the rupee.

    python pipelines/diagnostics/explore_tax_montecarlo.py
"""
from __future__ import annotations

import copy
import json
import multiprocessing as mp
import sys
import time
from pathlib import Path

import numpy as np
import pandas
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts"), str(ROOT / "pipelines" / "research"),
                str(ROOT / "pipelines" / "diagnostics"), str(ROOT / "pipelines" / "lifecycle")]
import explore_india_tax_practices as T  # noqa: E402

MC_CFG = ROOT / "config" / "tax_montecarlo.yaml"
CACHE = ROOT / ".cache" / "tax_mc"
OUT_JSON = ROOT / "diagnostics" / "research" / "explore" / "2026-11-19_tax_montecarlo.json"
BOOKS = ("s60", "s65")
LAWS = ("E", "A", "B", "C", "D")
SCEN = ("S0", "S1", "S2", "S3", "S4")
STEPS = (("S0", "S1"), ("S1", "S2"), ("S2", "S3"), ("S2", "S4"))
ANCHOR = {"S0->S1": 48122.0, "S1->S2": 13460.0, "S2->S3": 238886.0, "S2->S4": -847439.0, "best_cagr": 22.86}

G: dict = {}


# ------------------------------------------------------------------ runtime scoping helpers
class _PdProxy:
    """`pd` stand-in for the simulator module: shifts only Timestamp(year=Y, month=3, day=15)."""

    def __init__(self, offset_days: int):
        self._off = int(offset_days)

    def __getattr__(self, name):
        return getattr(pandas, name)

    def Timestamp(self, *a, **k):  # noqa: N802
        if not a and set(k) == {"year", "month", "day"} and k["month"] == 3 and k["day"] == 15:
            return pandas.Timestamp(**k) + pandas.Timedelta(days=self._off)
        return pandas.Timestamp(*a, **k)


class scoped:
    def __init__(self, offset_days: int = 0, arb_at_slab: bool = False):
        self.off, self.arb = offset_days, arb_at_slab

    def __enter__(self):
        self._pd = T.pd
        if self.off:
            T.pd = _PdProxy(self.off)
        if self.arb:
            T.EQUITY.discard(T.ARB)
        return self

    def __exit__(self, *exc):
        T.pd = self._pd
        T.EQUITY.add(T.ARB)
        return False


# ------------------------------------------------------------------ inputs
def set_path(cfg: dict, keys, value):
    node = cfg
    for k in keys[:-1]:
        node = node[k]
    node[keys[-1]] = value


def get_path(cfg: dict, keys):
    node = cfg
    for k in keys:
        node = node[k]
    return node


def draw_params(mc: dict, n: int, seed: int) -> list[dict]:
    from scipy.stats import qmc
    names = list(mc["params"]) + ["index_drift"]
    u = qmc.LatinHypercube(d=len(names), seed=seed).random(n)
    out = []
    for row in u:
        p = {}
        for j, name in enumerate(names):
            spec = mc["params"].get(name) or mc["paths"]["index_drift_annual"]
            if spec["dist"] == "choice":
                vals = spec["values"]
                p[name] = vals[min(int(row[j] * len(vals)), len(vals) - 1)]
            else:
                p[name] = spec["low"] + row[j] * (spec["high"] - spec["low"])
        p["harvest_offset_days"] = int(round(p["harvest_offset_days"]))
        out.append(p)
    return out


def apply_params(base: dict, mc: dict, p: dict | None) -> dict:
    cfg = copy.deepcopy(base)
    if p is None:
        return cfg
    for name, spec in mc["params"].items():
        if "cfg" not in spec:
            continue
        v = p[name]
        if spec["dist"] == "multiplier":
            v = get_path(base, spec["cfg"]) * v
        if spec.get("transform") == "negate":
            v = -v
        set_path(cfg, spec["cfg"], v)
        for extra in spec.get("also", []):
            set_path(cfg, extra, v)
    return cfg


def boot_indices(T_len: int, block: int, rng) -> np.ndarray:
    idx = np.empty(T_len, dtype=np.int64)
    idx[0] = rng.integers(0, T_len)
    jump = rng.random(T_len) < 1.0 / block
    fresh = rng.integers(0, T_len, T_len)
    for k in range(1, T_len):
        idx[k] = fresh[k] if jump[k] else (idx[k - 1] + 1) % T_len
    return idx


def path_returns(mode_path: str, i: int, drift: float | None):
    """(index daily returns on the real calendar, the bootstrap indices or None)."""
    r = G["r_tri"]
    ind = None
    if mode_path == "boot":
        ind = boot_indices(len(r), G["mc"]["paths"]["mean_block_days"], np.random.default_rng(G["mc"]["paths"]["path_seed"] + i))
        r = r[ind]
    if drift is not None:
        r = r - r.mean() + np.log1p(drift) / 252 + r.var() / 2
    return r, ind


def make_ctx(r_idx: np.ndarray, cfgs: list[dict]) -> dict:
    base = G["ctx0"]
    ctx = {"idx": base["idx"], "expo": base["expo"], "px_m": base["px_m"], "px_s": base["px_s"], "gains": {},
           "px_index": {}, "px_liq": {}, "px_arb": {}}
    idx = base["idx"]
    for c in cfgs:
        ter = c["instruments"]["index_fund"]["ter"]
        ctx["px_index"][id(c)] = pandas.Series(np.cumprod(1 + r_idx - ter / 252) * 100, index=idx)
        ctx["px_liq"][id(c)], ctx["px_arb"][id(c)] = T.cash_prices(idx, c)
    return ctx


# ------------------------------------------------------------------ one draw
def book_values(book: str, cfg: dict, ctx: dict, *, skip_s0=None) -> dict:
    owner = cfg["individual"]["owner_marginal_slab"]
    cap = T.CAPITAL
    hd = T.HARVEST_DAY
    v = {}
    v["S0"] = skip_s0 if skip_s0 is not None else T.simulate(book, cfg, ctx, slab=owner, cash_leg=T.LIQ)["final"]
    v["S1"] = T.simulate(book, cfg, ctx, slab=owner, cash_leg=T.ARB)["final"]
    v["S2"] = T.simulate(book, cfg, ctx, slab=owner, cash_leg=T.ARB, harvest=True, harvest_day=hd)["final"]
    own = T.simulate(book, cfg, ctx, slab=owner, cash_leg=T.ARB, harvest=True, harvest_day=hd, capital=cap / 3)["final"]
    zero = T.simulate(book, cfg, ctx, slab=0.0, cash_leg=T.ARB, harvest=True, harvest_day=hd, capital=cap / 3)["final"]
    v["S3"] = own + 2 * zero
    v["S4"] = T.simulate(book, cfg, ctx, kind="company", cash_leg=T.ARB, harvest=True, harvest_day=hd)["final"]
    v["S4div"] = v["S4"] * (1 - cfg["company"]["dividend_rate_to_owner"])
    return v


def run_one(task) -> dict:
    i, mode, p = task
    mc, base = G["mc"], G["base"]
    params = p if mode in ("main", "params_only") else None
    cfg = apply_params(base, mc, params)
    drift = params["index_drift"] if params else None
    r, ind = path_returns("hist" if mode == "params_only" else "boot", i if mode != "paths_only" else 100_000 + i, drift)
    laws = LAWS if mode == "main" else ("E",)
    cfgA, cfgB = copy.deepcopy(cfg), copy.deepcopy(cfg)
    cfgA["equity"]["ltcg_exemption"] = 0
    cfgB["equity"]["stcg"] = 0.30
    ctx = make_ctx(r, [cfg, cfgA, cfgB])
    off = params["harvest_offset_days"] if params else 0
    out = {"i": i, "mode": mode, "p": params, "v": {}}
    with scoped(off):
        for book in BOOKS:
            e = book_values(book, cfg, ctx)
            out["v"][f"E|{book}"] = e
            if "A" in laws:
                out["v"][f"A|{book}"] = book_values(book, cfgA, ctx)
                out["v"][f"B|{book}"] = book_values(book, cfgB, ctx)
                d = dict(e)
                d["S3"] = e["S2"]
                out["v"][f"D|{book}"] = d
        if mode == "main":
            out["be"] = {"no_div": T.break_even("s60", cfg, ctx, False), "with_div": T.break_even("s60", cfg, ctx, True)}
    if "C" in laws:
        with scoped(off, arb_at_slab=True):
            for book in BOOKS:
                out["v"][f"C|{book}"] = book_values(book, cfg, ctx, skip_s0=out["v"][f"E|{book}"]["S0"])
    if ind is not None and mode == "main":
        rb = G["r_blend"]
        out["corr"] = float(np.corrcoef(G["r_tri"][ind], rb[ind])[0, 1])
    return out


def init_worker():
    G["mc"] = yaml.safe_load(MC_CFG.read_text(encoding="utf-8"))
    G["base"] = T.load_cfg()
    G["ctx0"] = T.context([G["base"]])
    px = T.index_price(G["ctx0"]["idx"], G["base"]).to_numpy()
    ter = G["base"]["instruments"]["index_fund"]["ter"] / 252
    r = np.empty(len(px))
    r[0] = px[0] / 100 - 1 + ter
    r[1:] = px[1:] / px[:-1] - 1 + ter
    G["r_tri"] = r
    import explore_blend_drawdown_sizing as B
    import core as C
    d = B.navs()
    rm, rs = B.window(d["momentum"]).pct_change().dropna(), B.window(d["swing"]).pct_change().dropna()
    rb, _ = C.vol_target_blend(rm, rs, target=0.11)
    G["r_blend"] = rb.reindex(rb.index).to_numpy()[: len(r)]


# ------------------------------------------------------------------ statistics
def pct(x) -> dict:
    x = np.asarray(x, float)
    return {f"p{q}": round(float(np.percentile(x, q)), 0) for q in (5, 25, 50, 75, 95)}


def prcc(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    from scipy.stats import rankdata
    R = np.column_stack([rankdata(c) for c in X.T])
    ry = rankdata(y)
    out = np.zeros(R.shape[1])
    for j in range(R.shape[1]):
        others = np.column_stack([np.ones(len(ry)), np.delete(R, j, axis=1)])
        bx = np.linalg.lstsq(others, R[:, j], rcond=None)[0]
        by = np.linalg.lstsq(others, ry, rcond=None)[0]
        ex, ey = R[:, j] - others @ bx, ry - others @ by
        out[j] = float(np.corrcoef(ex, ey)[0, 1]) if ex.std() > 0 and ey.std() > 0 else 0.0
    return out


def step_stats(rows, law, book) -> dict:
    v = [r["v"][f"{law}|{book}"] for r in rows]
    out = {}
    for a, b in STEPS:
        g = np.array([x[b] - x[a] for x in v])
        out[f"{a}->{b}"] = {**pct(g), "p_gain_gt_0": round(float((g > 0).mean()), 4), "mean": round(float(g.mean()), 0)}
    g = np.array([x["S4div"] - x["S2"] for x in v])
    out["S2->S4div"] = {**pct(g), "p_gain_gt_0": round(float((g > 0).mean()), 4)}
    return out


def rank_stats(rows, law, book) -> dict:
    v = [r["v"][f"{law}|{book}"] for r in rows]
    full = np.mean([x["S3"] > x["S2"] > x["S1"] > x["S0"] > x["S4"] for x in v])
    pair = {}
    for a in SCEN:
        for b in SCEN:
            if a < b:
                pair[f"P({a}>{b})"] = round(float(np.mean([x[a] > x[b] for x in v])), 4)
    return {"P(S3>S2>S1>S0>S4)": round(float(full), 4), **pair}


def run_tasks(tasks, tag: str, workers: int, every: int) -> list[dict]:
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / f"{tag}.jsonl"
    done = {}
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                done[(r["mode"], r["i"])] = r
    todo = [t for t in tasks if (t[1], t[0]) not in done]
    t0 = time.time()
    buf = []
    with mp.Pool(workers, initializer=init_worker) as pool:
        for k, r in enumerate(pool.imap_unordered(run_one, todo, chunksize=4), 1):
            buf.append(r)
            if len(buf) >= every or k == len(todo):
                with f.open("a", encoding="utf-8") as fh:
                    for x in buf:
                        fh.write(json.dumps(x, default=float) + "\n")
                for x in buf:
                    done[(x["mode"], x["i"])] = x
                buf = []
                print(f"{tag}: {k}/{len(todo)} new, {time.time() - t0:.0f}s", flush=True)
    return [done[(t[1], t[0])] for t in tasks]


# ------------------------------------------------------------------ main
def anchors() -> dict:
    base = T.load_cfg()
    ctx = T.context([base])
    s = {b: T.scenarios(b, base, ctx, boot=False) for b in BOOKS}
    v = s["s60"]
    got = {"S0->S1": v["S1"]["final_value"] - v["S0"]["final_value"],
           "S1->S2": v["S2"]["final_value"] - v["S1"]["final_value"],
           "S2->S3": v["S3_N3_slab0"]["final_value"] - v["S2"]["final_value"],
           "S2->S4": v["S4"]["final_value"] - v["S2"]["final_value"],
           "best_cagr": v["S3_N3_slab0"]["after_tax_cagr_pct"]}
    ok = all(abs(got[k] - ANCHOR[k]) <= (0.02 if k == "best_cagr" else 1000) for k in ANCHOR)
    # identity path through this file's ctx builder
    init_worker()
    cfg = copy.deepcopy(G["base"])
    ctx2 = make_ctx(G["r_tri"], [cfg])
    with scoped(0):
        mine = book_values("s60", cfg, ctx2)
    ident = {"S0": (mine["S0"], v["S0"]["final_value"]), "S1": (mine["S1"], v["S1"]["final_value"]),
             "S2": (mine["S2"], v["S2"]["final_value"]), "S3": (mine["S3"], v["S3_N3_slab0"]["final_value"]),
             "S4": (mine["S4"], v["S4"]["final_value"])}
    ident_ok = all(abs(a - b) <= 1.0 for a, b in ident.values())
    return {"pipeline": {k: round(x, 2) for k, x in got.items()}, "target": ANCHOR, "pipeline_ok": bool(ok),
            "identity_path_vs_pipeline": {k: [round(a, 0), round(b, 0)] for k, (a, b) in ident.items()},
            "identity_ok": bool(ident_ok)}


def summarise_all(rows: list[dict]) -> dict:
    res = {"n": len(rows), "terminal": {}, "steps": {}, "rank": {}}
    for law in LAWS:
        for book in BOOKS:
            key = f"{law}|{book}"
            res["terminal"][key] = {s: pct([r["v"][key][s] for r in rows]) for s in (*SCEN, "S4div")}
            res["steps"][key] = step_stats(rows, law, book)
            res["rank"][key] = rank_stats(rows, law, book)
    return res


def main() -> int:
    mc = yaml.safe_load(MC_CFG.read_text(encoding="utf-8"))
    out = {"status": mc["status"], "config": "config/tax_montecarlo.yaml"}
    a = anchors()
    out["anchors"] = a
    print("ANCHORS", json.dumps(a), flush=True)
    if not (a["pipeline_ok"] and a["identity_ok"]):
        OUT_JSON.write_text(json.dumps(out, indent=1, default=float) + "\n", encoding="utf-8")
        raise SystemExit("anchor mismatch: stop")
    # timing
    t = time.time()
    run_one((0, "main", draw_params(mc, 1, 1)[0]))
    out["seconds_per_draw_single_core"] = round(time.time() - t, 2)
    print("seconds per draw", out["seconds_per_draw_single_core"], flush=True)

    S = mc["sampling"]
    P = draw_params(mc, S["n_draws"], S["seed"])
    rows = run_tasks([(i, "main", P[i]) for i in range(S["n_draws"])], "main", S["workers"], S["checkpoint_every"])
    names = list(P[0].keys())

    def converged(rs):
        half = rs[: len(rs) // 2]
        rep = {}
        for book in BOOKS:
            fa, fh = step_stats(rs, "E", book), step_stats(half, "E", book)
            for st in ("S0->S1", "S1->S2", "S2->S3", "S2->S4"):
                p50a, p50h = fa[st]["p50"], fh[st]["p50"]
                rel = abs(p50h / p50a - 1) if p50a else 0.0
                dp = abs(fa[st]["p_gain_gt_0"] - fh[st]["p_gain_gt_0"])
                rep[f"{book}|{st}"] = {"p50_rel_change": round(rel, 4), "p_abs_change": round(dp, 4),
                                       "ok": bool(rel < mc["convergence"]["p50_rel_tol"] and dp < mc["convergence"]["prob_abs_tol"])}
        return rep
    conv = converged(rows)
    doubled = False
    if not all(x["ok"] for x in conv.values()):
        P2 = draw_params(mc, S["n_draws"], S["n_double_seed"])
        rows += run_tasks([(S["n_draws"] + i, "main", P2[i]) for i in range(S["n_draws"])], "main_double", S["workers"], S["checkpoint_every"])
        P = P + P2
        doubled = True
        conv = {"first_pass": conv, "after_doubling": converged(rows)}
    out["convergence"] = {"doubled": doubled, "report": conv}
    out["n_draws"] = len(rows)
    out.update(summarise_all(rows))
    # PRCC (law E)
    X = np.array([[float(r["p"][k]) for k in names] for r in rows])
    tor = {}
    for book in BOOKS:
        for a_, b_ in STEPS:
            y = np.array([r["v"][f"E|{book}"][b_] - r["v"][f"E|{book}"][a_] for r in rows])
            c = prcc(X, y)
            order = np.argsort(-np.abs(c))
            tor[f"{book}|{a_}->{b_}"] = {"prcc": {names[j]: round(float(c[j]), 3) for j in order},
                                         "top3": [names[j] for j in order[:3]]}
    out["prcc"] = tor
    # break-even
    be = [r.get("be", {}) for r in rows if r["mode"] == "main"]
    for k in ("no_div", "with_div"):
        vals = [x.get(k) for x in be]
        fin = np.array([v_ / 1e7 for v_ in vals if v_ is not None])
        out.setdefault("break_even_crore_s60_lawE", {})[k] = {
            "share_with_break_even": round(float(len(fin) / len(vals)), 4),
            **({f"p{q}": round(float(np.percentile(fin, q)), 2) for q in (5, 50, 95)} if len(fin) else {})}
    # correlation preservation
    cs = [r["corr"] for r in rows if "corr" in r]
    G.clear()
    init_worker()
    out["cross_correlation"] = {"original_index_vs_blend": round(float(np.corrcoef(G["r_tri"], G["r_blend"])[0, 1]), 4),
                                "resampled_mean": round(float(np.mean(cs)), 4), "resampled_p5": round(float(np.percentile(cs, 5)), 4),
                                "resampled_p95": round(float(np.percentile(cs, 95)), 4), "n_paths": len(cs),
                                "mean_block_days": mc["paths"]["mean_block_days"]}
    # parameters vs path
    n = mc["decomposition"]["n_each"]
    po = run_tasks([(i, "paths_only", None) for i in range(n)], "paths_only", S["workers"], S["checkpoint_every"])
    pa = run_tasks([(i, "params_only", P[i]) for i in range(n)], "params_only", S["workers"], S["checkpoint_every"])
    dec = {}
    for book in BOOKS:
        for a_, b_ in STEPS:
            k = f"{book}|{a_}->{b_}"
            row = {}
            for tag, rs in (("full", rows), ("paths_only", po), ("params_only", pa)):
                g = np.array([r["v"][f"E|{book}"][b_] - r["v"][f"E|{book}"][a_] for r in rs])
                row[tag] = {"std": round(float(g.std()), 0), "iqr": round(float(np.percentile(g, 75) - np.percentile(g, 25)), 0)}
            dec[k] = row
    out["decomposition"] = dec
    OUT_JSON.write_text(json.dumps(out, indent=1, default=float) + "\n", encoding="utf-8")
    print("wrote", OUT_JSON, flush=True)
    return 0


if __name__ == "__main__":
    mp.freeze_support()
    raise SystemExit(main())
