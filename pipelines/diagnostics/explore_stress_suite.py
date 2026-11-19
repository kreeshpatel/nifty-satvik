"""MEASUREMENT: stress suite (S1-S7) with negative controls (N1-N3) for the live swing book, 0001 momentum and the 70/30
blend at an 11% vol target.

Owner request 2026-11-19 ("prompt 2", research/stress-suite). Analysis only: no live rule, no trial counter, no sealed
read. Pass criteria and the full method are fixed in diagnostics/research/2026-11-19_stress_suite.md (Step 0, committed
before any run). This file implements that method; nothing here can be adopted.

REUSED, NOT EDITED: nq/lab/ensemble.py (draw_perturbations, cost_jitter, prepare_context), explore_param_sensitivity
(TRI Sharpe), explore_stops_are_requests (apply_cash_scaled idea - re-expressed in return space here), and
explore_blend_drawdown_sizing (navs, window, blend, boot_dd). Shocks that must act inside an engine run on a SOURCE-
PATCHED COPY of that engine (the sma_len technique of explore_param_sensitivity): each patched literal is asserted to
occur exactly once, and with every hook off the copy reproduces prompt 1's path-0 Sharpe 1.348913.

    python pipelines/diagnostics/explore_stress_suite.py swing    <scen> [<scen> ...]   # base S1 S2 S3 S4 S5 N1 N2 N3
    python pipelines/diagnostics/explore_stress_suite.py momentum <scen> [<scen> ...]   # base S1 S2 S3 S4 S5 N1 N2 N3
    python pipelines/diagnostics/explore_stress_suite.py controls      # N1-N3 verdict (run first)
    python pipelines/diagnostics/explore_stress_suite.py report        # shocks table + everything
"""
from __future__ import annotations

import json
import os
import sys
import time
import types
import zlib
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts"), str(ROOT / "pipelines" / "research"),
                str(ROOT / "pipelines" / "diagnostics"), str(ROOT / "pipelines" / "lifecycle")]

CACHE = Path(os.environ.get("STRESS_CACHE", str(ROOT / ".cache" / "stress_suite")))   # Step 0b runs use a separate dir
OUT_JSON = ROOT / "diagnostics" / "research" / "explore" / "2026-11-19_stress_suite.json"
N_PATHS, N_SEEDS = 20, 100
TARGET = 0.11
P_DROP, P_GAP = 0.10, 0.01
SEED_LABEL, SEED_S6, SEED_S7 = 20261119, 20261120, 20261121
LEG_COST_REF = 0.0035
SW_WIN = ("2019-03-01", "2024-06-28")
MOM_END = "2026-06-30"
PATH0_ANCHOR = 1.348913                    # prompt 1: path 0 of the 20-path base, unpatched engine
NEUTRAL = {"lat": False, "stop_low": False, "drop": None, "n4": None}


def _drop_fn(seed: int):
    """Deterministic p=0.10 drop, independent of evaluation order: hash(seed, ticker, key) -> U[0,1)."""
    def f(tkr, key) -> bool:
        return zlib.crc32(f"{seed}|{tkr}|{key}".encode()) / 2 ** 32 < P_DROP
    return f


# ======================================================================================== swing: patched engine
def install_swing_engine():
    """Register a source-patched copy of the swing engine as `run_bhanushali_weekly_rank` (before nq.lab imports it)."""
    src_path = ROOT / "scripts" / "run_bhanushali_weekly_rank.py"
    src = src_path.read_text(encoding="utf-8")
    reps = [
        ('orders[t] = {"days": set(days), "lo": lo,',
         'orders[t] = {"days": ({k + 1 for k in days} if _STRESS["lat"] else set(days)), "lo": lo,'),
        ('            if p["pending"] is not None:\n                act, rs = p["pending"]\n                px = s["o"][i]\n',
         '            if _STRESS.get("n4") is not None:\n'
         '                if "_n4_exit" not in p:\n'
         '                    _ed = pd.Timestamp(p["rec"]["entry_date"]) if "rec" in p else pd.Timestamp(d)\n'
         '                    p["_n4_exit"] = _ed + pd.Timedelta(days=int(_STRESS["n4"](t, str(_ed.date()))))\n'
         '                if p["pending"] is None and pd.Timestamp(d) >= p["_n4_exit"]:\n'
         '                    p["pending"] = ("full", "n4_time")\n'
         '            if p["pending"] is not None and _STRESS["lat"] and p.get("_lag_d") is None:\n'
         '                p["_lag_d"] = d\n'
         '            if p["pending"] is not None and not (_STRESS["lat"] and p.get("_lag_d") == d):\n'
         '                p.pop("_lag_d", None)\n'
         '                act, rs = p["pending"]\n'
         '                px = s["o"][i]\n'
         '                if _STRESS["stop_low"] and act == "full" and str(rs).startswith("stop"):\n'
         '                    px = s["l"][i]\n'),
        ('            # forensic lever 2b: book the +2R half at a RESTING LIMIT',
         '            if _STRESS.get("n4") is not None:\n                continue\n'
         '            # forensic lever 2b: book the +2R half at a RESTING LIMIT'),
        ('        for rk, t, i, opn in sorted(cands, key=_key):\n            o_ = orders.get(t)\n'
         '            if o_ is None or t in op:\n                continue\n',
         '        for rk, t, i, opn in sorted(cands, key=_key):\n            o_ = orders.get(t)\n'
         '            if o_ is None or t in op:\n                continue\n'
         '            if _STRESS["drop"] is not None and _STRESS["drop"](t, str(pd.Timestamp(d).date())):\n'
         '                del orders[t]\n                continue\n')]
    for a, b in reps:
        assert src.count(a) == 1, f"patch anchor moved: {a[:60]!r}"
        src = src.replace(a, b)
    mod = types.ModuleType("run_bhanushali_weekly_rank")
    mod.__file__ = str(src_path)
    mod._STRESS = dict(NEUTRAL)
    sys.modules["run_bhanushali_weekly_rank"] = mod
    exec(compile(src, str(src_path), "exec"), mod.__dict__)
    return mod


def _week_index(s: dict) -> tuple[np.ndarray, dict]:
    dts = pd.DatetimeIndex(s["dates"])
    iso = dts.isocalendar()
    yw = (iso["year"].to_numpy() * 100 + iso["week"].to_numpy()).astype(int)
    first = {}
    for j, k in enumerate(yw):
        first.setdefault(int(k), [j, j])[1] = j
    return yw, first


def _yw(ts) -> int:
    c = pd.Timestamp(ts).isocalendar()
    return int(c[0]) * 100 + int(c[1])


class SwingControls:
    """Builds relabelled / random / reversed entry windows on a copy of the prepared panel (P is never mutated)."""

    def __init__(self, ctx):
        self.P, self.mem = ctx.P, ctx.mem
        self.didx = {t: {pd.Timestamp(d).normalize(): i for i, d in enumerate(s["dates"])} for t, s in ctx.P.items()}
        self.wk = {t: _week_index(s) for t, s in ctx.P.items()}
        self.sigs = []                                  # (t, e0, entry_date, entry_week_dates, lo, hi, rk, sma, org)
        for t, s in ctx.P.items():
            dts = pd.DatetimeIndex(s["dates"]).normalize()
            for e0, (days, lo, hi, rk, sma, org) in s["entry_win"].items():
                self.sigs.append((t, e0, dts[e0], [dts[k] for k in days], lo, hi, rk, sma, org))
        self._pool = {}
        cal = sorted(set().union(*[set(pd.DatetimeIndex(s["dates"]).normalize()) for s in ctx.P.values()]))
        self.cal = pd.DatetimeIndex(cal)

    def member(self, t, d) -> bool:
        if self.mem is None:
            return True
        per = self.mem.get(t.upper())
        dd = pd.Timestamp(d).date()
        return bool(per) and any(a <= dd <= b for a, b in per)

    def pool(self, d) -> list:
        d = pd.Timestamp(d).normalize()
        if d not in self._pool:
            self._pool[d] = sorted(u for u in self.P if d in self.didx[u] and self.member(u, d))
        return self._pool[d]

    def geometry(self, u, entry_dates, rk, org):
        """Entry window for ticker u: its own signal-week low/high/44w SMA, the given rank/origin."""
        dix = self.didx[u]
        eidx = [dix[d] for d in entry_dates if d in dix]
        if not eidx:
            return None
        yw, first = self.wk[u]
        sig = first.get(_yw(pd.Timestamp(entry_dates[0]) - pd.Timedelta(days=7)))
        if sig is None:
            return None
        s = self.P[u]
        lo = float(np.min(s["l"][sig[0]:sig[1] + 1]))
        hi = float(np.max(s["h"][sig[0]:sig[1] + 1]))
        sma = s["wsma_at"].get(sig[1], float("nan"))
        sma = float(sma) if sma == sma else lo
        return eidx[0], (eidx, lo, hi, float(rk), sma, int(org))

    def build(self, mode: str, seed: int):
        rng = np.random.default_rng(SEED_LABEL + seed)
        new = {t: {} for t in self.P}
        if mode == "N3":
            for t, e0, _d, _ed, lo, hi, rk, sma, org in self.sigs:
                new[t][e0] = (self.P[t]["entry_win"][e0][0], lo, hi, -rk, sma, org)
        elif mode == "N1":
            by_week = {}
            for sg in self.sigs:
                by_week.setdefault(_yw(sg[2]), []).append(sg)
            for wk in sorted(by_week):
                used = set()
                for t, e0, d, ed, lo, hi, rk, sma, org in sorted(by_week[wk], key=lambda x: (x[0], x[1])):
                    pool = [u for u in self.pool(d) if u != t and u not in used]
                    for _try in range(8):
                        if not pool:
                            break
                        u = pool[int(rng.integers(len(pool)))]
                        g = self.geometry(u, ed, rk, org)
                        if g is not None and g[0] not in new[u]:
                            new[u][g[0]] = g[1]
                            used.add(u)
                            break
                        pool.remove(u)
        elif mode == "N2":
            per_year = pd.Series([sg[2].year for sg in self.sigs]).value_counts().to_dict()
            weeks = pd.Series(self.cal).groupby([self.cal.isocalendar()["year"].to_numpy(),
                                                 self.cal.isocalendar()["week"].to_numpy()]).apply(list)
            wk_by_year = {}
            for (y, w), dates in weeks.items():
                wk_by_year.setdefault(pd.Timestamp(dates[0]).year, []).append(list(dates))
            for y in sorted(per_year):
                wl = wk_by_year.get(y, [])
                for _ in range(int(per_year[y])):
                    if not wl:
                        break
                    ed = wl[int(rng.integers(len(wl)))]
                    pool = self.pool(ed[0])
                    for _try in range(8):
                        if not pool:
                            break
                        u = pool[int(rng.integers(len(pool)))]
                        g = self.geometry(u, ed, float(rng.random()), 0)
                        if g is not None and g[0] not in new[u]:
                            new[u][g[0]] = g[1]
                            break
        else:
            raise ValueError(mode)
        return {t: {**s, "entry_win": new[t], "atr_at": {}} for t, s in self.P.items()}, int(sum(map(len, new.values())))

    def ew_universe(self) -> pd.Series:
        """Equal-weight close-to-close daily return of PIT members with a bar (the swing controls' sampling universe)."""
        cols = {}
        for t, s in self.P.items():
            c = pd.Series(np.asarray(s["c"], float), index=pd.DatetimeIndex(s["dates"]).normalize())
            c = c[~c.index.duplicated(keep="last")]
            r = c.pct_change()
            per = (self.mem or {}).get(t.upper()) if self.mem is not None else None
            if self.mem is not None:
                if not per:
                    continue
                m = np.zeros(len(r), bool)
                dd = r.index.date
                for a, b in per:
                    m |= (dd >= a) & (dd <= b)
                r = r[m]
            cols[t] = r
        return pd.DataFrame(cols).mean(axis=1, skipna=True).dropna()


def run_swing(scens: list[str]) -> None:
    R94 = install_swing_engine()
    from nq.lab import ensemble as E
    from nq.lab import runs as L
    import nq.engine.portfolio as PF
    assert L._engine()[0] is R94, "the patched engine did not take"
    CACHE.mkdir(parents=True, exist_ok=True)
    ctx = E.prepare_context()
    ctl = None

    def one(d, stress, P=None, a_grade=None, keep_w=False, cost_off=False):
        R94._STRESS.clear(); R94._STRESS.update(stress)
        cfg = {**L.normalize_config({}), "start": str(pd.Timestamp(d["start"]).date())}
        kw = L.engine_kwargs(cfg)
        led, plog = [], ([] if keep_w else None)
        ag = a_grade if a_grade is not None else ctx.a_grade("default")
        with E.cost_jitter(0.0 if cost_off else float(d["cost_delta"])):
            out = R94.backtest(P if P is not None else ctx.P, ctx.mem, ledger=led, a_grade=ag, **kw,
                               demerger_events=ctx.events, position_log=plog, cost_off=cost_off)
        R94._STRESS.clear(); R94._STRESS.update(NEUTRAL)
        nav = pd.Series(out["curve"], dtype=float)
        nav.index = pd.DatetimeIndex(nav.index).normalize()
        nav = nav[~nav.index.duplicated(keep="last")].sort_index()
        led = pd.DataFrame(led)
        n_tr = int(((pd.to_datetime(led["entry_date"]) >= pd.Timestamp(SW_WIN[0])).sum()) if len(led) else 0)
        row = {"path": int(d["path"]), "nav": nav, "trades": n_tr,
               "stop_exits": int(led["reason"].isin(["stop", "stop_part"]).sum()) if len(led) else 0}
        if keep_w:
            pl = pd.DataFrame(plog)
            pl["w"] = pl["notional"] / pl["equity"]
            row["weights"] = {pd.Timestamp(k).normalize(): g["w"].to_numpy(float) for k, g in pl.groupby("date")}
            ex = pl.groupby(pd.to_datetime(pl["date"]).dt.normalize())["w"].sum()
            row["expo"] = ex.reindex(nav.index).fillna(0.0)          # invested fraction at each close
        return row

    for scen in scens:
        f = CACHE / f"swing__{scen}.pkl"
        if f.exists():
            print("skip", f.name, flush=True)
            continue
        t0 = time.time()
        n = N_SEEDS if scen.startswith("N") else N_PATHS
        draws = E.draw_perturbations(n, E.DEFAULT_SEED)
        rows, extra = [], {}
        orig_cost, orig_slip = R94._cost_leg, PF._slip
        for _, d in draws.iterrows():
            k = int(d["path"])
            try:
                if scen == "base":
                    rows.append(one(d, NEUTRAL, keep_w=True))
                    if k == 0:
                        s0 = rows[0]["nav"]
                        s0 = s0[(s0.index >= pd.Timestamp(SW_WIN[0])) & (s0.index <= pd.Timestamp(SW_WIN[1]))]
                        r0 = s0.pct_change().dropna()
                        sh0 = round(float(r0.mean() / r0.std() * np.sqrt(252)), 6)
                        print("path-0 anchor (patched engine, hooks off):", sh0, flush=True)
                        if sh0 != PATH0_ANCHOR:
                            raise SystemExit(f"path-0 anchor mismatch {sh0} != {PATH0_ANCHOR}: the patch moved the engine; stop")
                elif scen == "S1":
                    rows.append(one(d, {**NEUTRAL, "lat": True}))
                elif scen == "S2":
                    rows.append(one(d, {**NEUTRAL, "drop": _drop_fn(SEED_LABEL + k)}))
                elif scen == "S3":
                    rows.append(one(d, {**NEUTRAL, "stop_low": True}))
                elif scen == "S4":
                    def tripled(adv, notional, cost_off=False, _o=orig_cost):
                        return 0.0 if cost_off else 3.0 * _o(adv, notional, cost_off)
                    R94._cost_leg = tripled
                    rows.append(one(d, NEUTRAL))
                elif scen == "S5":
                    def slip_half(adv_rupees, notional, _o=orig_slip):
                        base = _o(adv_rupees, 0.0)
                        return base + (0.001 if adv_rupees > 0 and notional > 0.0025 * adv_rupees else 0.0)
                    PF._slip = slip_half
                    rows.append(one(d, NEUTRAL))
                elif scen in ("N1", "N2", "N3", "N1off", "N2off"):
                    if ctl is None:
                        ctl = SwingControls(ctx)
                    P2, n_sig = ctl.build(scen[:2], k)
                    r_ = one(d, NEUTRAL, P=P2, a_grade=R94.grade_a_entries(P2), keep_w=True,
                             cost_off=scen.endswith("off"))
                    r_.pop("weights", None)
                    rows.append({**r_, "n_signals": n_sig})
                else:
                    raise ValueError(scen)
            finally:
                R94._cost_leg, PF._slip = orig_cost, orig_slip
            if k % 10 == 0:
                print("swing", scen, k, round(time.time() - t0), flush=True)
        if scen.startswith("N") or scen == "base":
            if ctl is None:
                ctl = SwingControls(ctx)
            extra["ew_universe"] = ctl.ew_universe()
            extra["n_real_signals"] = len(ctl.sigs)
        pd.to_pickle({"rows": rows, **extra, "seconds": round(time.time() - t0, 1)}, f)
        print("done swing", scen, round(time.time() - t0), flush=True)


# ======================================================================================== momentum
def install_rebalance_copy():
    import nq.engine.rebalance_book as RB0
    src = Path(RB0.__file__).read_text(encoding="utf-8")
    reps = [("                delta = tgt_qty - held_qty\n",
             "                delta = tgt_qty - held_qty\n"
             "                if _STRESS_DROP[0] is not None and held_qty == 0 and delta > 0 and _STRESS_DROP[0](tkr, _REB[0]):\n"
             "                    continue\n"),
            ("            armed = True\n", "            armed = True\n            _REB[0] += 1\n")]
    for a, b in reps:
        assert src.count(a) == 1, f"patch anchor moved: {a!r}"
        src = src.replace(a, b)
    name = "nq.engine._rebalance_book_stress"
    mod = types.ModuleType(name)
    mod.__file__, mod.__package__ = RB0.__file__, "nq.engine"
    mod._STRESS_DROP, mod._REB = [None], [0]
    sys.modules[name] = mod
    exec(compile(src, RB0.__file__, "exec"), mod.__dict__)
    return mod


def momentum_panel():
    import run_0001_xsec_momentum as M
    from nq.data.membership import load_membership
    from nq.universe import build_universe
    from run_bhanushali_path1 import corrected_universe
    p = M.add_signals(build_universe(corrected_universe(), load_membership(), start=M.START, end=M.END))
    b = p[p["ticker"].isin(p.loc[p["size_band"] == M.BAND, "ticker"].unique())].copy()
    b["rank"] = np.where(b["eligible"] & (b["size_band"] == M.BAND) & b["nms"].notna(), b["nms"], np.nan)
    return M, b.sort_values(["ticker", "date"]).reset_index(drop=True)


def momentum_ew(M, b) -> pd.Series:
    b = b.copy()
    b["r"] = b.groupby("ticker")["close"].pct_change()
    m = b["eligible"] & (b["size_band"] == M.BAND)
    return b.loc[m].groupby("date")["r"].mean().dropna().sort_index()


def run_momentum(scens: list[str]) -> None:
    import diag_system_inventory_2026_11 as INV
    import nq.engine.rebalance_book as RB
    from nq.lab import ensemble as E
    M, b0 = momentum_panel()
    RBX = install_rebalance_copy()
    CACHE.mkdir(parents=True, exist_ok=True)

    def one(b, start, mult, book, mod=RB):
        bt = mod.simulate_rebalance_book(b, cfg=RB.RebalanceConfig(**{**book, "cost_mult": float(mult)}), start=str(start),
                                         end=M.END, initial_capital=1_000_000.0)
        return bt

    bt0 = one(b0, M.START, 1.0, M.BOOK)
    anchor = (round(float(bt0["metrics"]["cagr_pct"]), 2), round(float(bt0["metrics"]["sharpe"]), 3))
    print("ANCHOR 0001:", anchor, flush=True)
    if anchor != (21.73, 1.13):
        raise SystemExit(f"anchor mismatch {anchor}: stop")
    nav0 = INV.to_nav(bt0["equity_curve"])
    RBX._STRESS_DROP[0], RBX._REB[0] = None, 0
    chk = INV.to_nav(one(b0, M.START, 1.0, M.BOOK, RBX)["equity_curve"])
    if not np.allclose(chk.to_numpy(), nav0.to_numpy(), rtol=0, atol=1e-9):
        raise SystemExit("patched rebalance copy with hooks off does not reproduce the run of record: stop")
    tr0 = pd.DataFrame(bt0["trades"])
    n_reb = len(RB.rebalance_dates(sorted(b0["date"].unique()), M.BOOK["cadence"]))
    ec0 = pd.DataFrame(bt0["equity_curve"])
    base_turn = {"exits_per_rebalance": float((tr0["reason"] == "rebalance_exit").sum() / n_reb),
                 "mean_positions": float(ec0["n_positions"].mean()), "trade_rows_per_year":
                 float(len(tr0) / ((pd.Timestamp(M.END) - pd.Timestamp(M.START)).days / 365.25))}

    def shifted_rebal(orig):
        def f(dates, cadence="M"):
            ds = sorted(pd.to_datetime(list(dates)))
            pos = {d: i for i, d in enumerate(ds)}
            return [ds[pos[pd.Timestamp(r)] + 1] for r in orig(dates, cadence) if pos[pd.Timestamp(r)] + 1 < len(ds)]
        return f

    def n2_panel(q, seed):
        rng = np.random.default_rng(SEED_LABEL + seed)
        b = b0.copy()
        mon = b["date"].dt.to_period("M")
        months = np.sort(mon.unique())
        tick = np.sort(b["ticker"].unique())
        S = rng.random((len(months), len(tick)))
        red = rng.random((len(months), len(tick))) < q
        for m in range(1, len(months)):
            S[m] = np.where(red[m], S[m], S[m - 1])
        mi = np.searchsorted(months, mon.to_numpy())
        ti = np.searchsorted(tick, b["ticker"].to_numpy())
        b["rank"] = np.where(b["rank"].notna(), S[mi, ti], np.nan)
        return b

    def n1_panel(seed):
        rng = np.random.default_rng(SEED_LABEL + seed)
        b = b0.copy()
        m = b["rank"].notna().to_numpy()
        sub_d = b.loc[m, "date"].to_numpy()
        vals = b.loc[m, "rank"].to_numpy()
        order = np.lexsort((rng.random(len(vals)), sub_d))
        stable = np.argsort(sub_d, kind="stable")
        new = np.empty(len(vals))
        new[stable] = vals[order]
        b.loc[m, "rank"] = new
        return b

    draws20 = E.draw_perturbations(N_PATHS, E.DEFAULT_SEED, start_base=str(nav0.index[0].date()))
    draws100 = E.draw_perturbations(N_SEEDS, E.DEFAULT_SEED, start_base=str(nav0.index[0].date()))
    q_cal = None
    for scen in scens:
        f = CACHE / f"momentum__{scen}.pkl"
        if f.exists():
            print("skip", f.name, flush=True)
            continue
        t0 = time.time()
        draws = draws100 if scen.startswith("N") else draws20
        extra = {"base_turnover": base_turn}
        if scen in ("N2", "N2off"):
            # one mechanical calibration step, fixed before the 100 seeds (Step 0: turnover matched)
            q0 = base_turn["exits_per_rebalance"] / base_turn["mean_positions"]
            bt = one(n2_panel(q0, -1), M.START, 1.0, M.BOOK)
            t_q0 = (pd.DataFrame(bt["trades"])["reason"] == "rebalance_exit").sum() / n_reb
            q_cal = float(min(1.0, q0 * base_turn["exits_per_rebalance"] / max(t_q0, 1e-9)))
            extra["n2_calibration"] = {"q0": q0, "exits_per_rebalance_at_q0": float(t_q0), "q": q_cal}
            print("N2 calibration", extra["n2_calibration"], flush=True)
        rows = []
        orig_rd = RB.rebalance_dates
        for _, d in draws.iterrows():
            k = int(d["path"])
            mult = 1.0 + float(d["cost_delta"]) / LEG_COST_REF
            book, b, mod = dict(M.BOOK), b0, RB
            try:
                if scen == "S1":
                    b = b0.copy()
                    b["rank"] = b.groupby("ticker")["rank"].shift(1)
                    RB.rebalance_dates = shifted_rebal(orig_rd)
                elif scen == "S2":
                    mod = RBX
                    RBX._STRESS_DROP[0], RBX._REB[0] = _drop_fn(SEED_LABEL + k), 0
                elif scen == "S4":
                    mult *= 3.0
                elif scen == "S5":
                    book["max_adv_participation"] = RB.RebalanceConfig().max_adv_participation * 0.5
                elif scen in ("N1", "N1off"):
                    b = n1_panel(k)
                    mult = 0.0 if scen == "N1off" else mult
                elif scen in ("N2", "N2off"):
                    b = n2_panel(q_cal, k)
                    mult = 0.0 if scen == "N2off" else mult
                elif scen == "N3":
                    b = b0.copy()
                    b["rank"] = -b["rank"]
                elif scen not in ("base", "S3"):
                    raise ValueError(scen)
                bt = one(b, d["start"], mult, book, mod)
            finally:
                RB.rebalance_dates = orig_rd
                RBX._STRESS_DROP[0], RBX._REB[0] = None, 0
            ec = pd.DataFrame(bt["equity_curve"])
            ec["date"] = pd.to_datetime(ec["date"])
            trd = pd.DataFrame(bt["trades"])
            row = {"path": k, "nav": INV.to_nav(bt["equity_curve"]),
                   "exits_per_rebalance": float((trd["reason"] == "rebalance_exit").sum() / n_reb) if len(trd) else 0.0}
            ec = ec.set_index("date")
            inv = ((ec["equity"] - ec["cash"]) / ec["equity"]).clip(lower=0)
            row["expo"] = inv
            if scen == "base":
                row["weights"] = {dd: np.full(int(n), inv[dd] / n) for dd, n in ec["n_positions"].items() if n > 0}
            rows.append(row)
            if k % 10 == 0:
                print("momentum", scen, k, round(time.time() - t0), flush=True)
        if scen.startswith("N") or scen == "base":
            extra["ew_universe"] = momentum_ew(M, b0)
        pd.to_pickle({"rows": rows, **extra, "seconds": round(time.time() - t0, 1)}, f)
        print("done momentum", scen, round(time.time() - t0), flush=True)


# ======================================================================================== metrics
def _load(book, scen):
    return pd.read_pickle(CACHE / f"{book}__{scen}.pkl")


def win(nav: pd.Series, lo, hi) -> pd.Series:
    return nav[(nav.index >= pd.Timestamp(lo)) & (nav.index <= pd.Timestamp(hi))]


def sharpe_r(r: pd.Series) -> float:
    r = pd.Series(r).dropna()
    return float(r.mean() / r.std() * np.sqrt(252)) if len(r) > 2 and r.std() > 0 else float("nan")


def appraisal(r: pd.Series, x: pd.Series) -> float:
    """alpha / sd(residual) * sqrt(252) from OLS of daily r on the EW-universe return x (aligned dates)."""
    j = pd.concat([pd.Series(r), pd.Series(x)], axis=1, join="inner").dropna()
    if len(j) < 30:
        return float("nan")
    y, z = j.iloc[:, 0].to_numpy(), j.iloc[:, 1].to_numpy()
    beta = np.cov(y, z, ddof=1)[0, 1] / np.var(z, ddof=1)
    a = y.mean() - beta * z.mean()
    e = y - a - beta * z
    return float(a / e.std(ddof=2) * np.sqrt(252)) if e.std() > 0 else float("nan")


def tri_series() -> pd.Series:
    import explore_param_sensitivity as PS
    d = pd.read_csv(PS.TRI, parse_dates=["date"]).set_index("date").iloc[:, 0].sort_index()
    return d.pct_change().dropna()


def book_returns(book: str, nav: pd.Series) -> pd.Series:
    if book == "swing":
        return win(nav, *SW_WIN).pct_change().dropna()
    return nav[nav.index <= pd.Timestamp(MOM_END)].pct_change().dropna()


def blend_returns(mom_nav, sw_nav) -> pd.Series:
    import explore_blend_drawdown_sizing as B
    return B.blend_daily(mom_nav, sw_nav, TARGET)


def blend_p95(r: pd.Series) -> float:
    import core as C
    import explore_blend_drawdown_sizing as B
    return float(np.percentile(B.boot_dd(C.weekly_returns(B.to_nav(r)).to_numpy(), 156, 8), 95))


def gap_G() -> float:
    f = CACHE / "gap_G.json"
    if f.exists():
        return json.loads(f.read_text())["G"]
    from run_bhanushali_path1 import corrected_universe
    gs = []
    for _t, df in corrected_universe().items():
        o = df["open"] if "open" in df else df["Open"]
        c = df["close"] if "close" in df else df["Close"]
        g = (o / c.shift(1) - 1)
        idx = pd.DatetimeIndex(df.index)
        g = g[(idx >= pd.Timestamp(SW_WIN[0])) & (idx <= pd.Timestamp(SW_WIN[1]))]
        gs.append(g.replace([np.inf, -np.inf], np.nan).dropna().to_numpy(float))
    allg = np.concatenate(gs)
    p1 = float(np.percentile(allg, 1))
    out = {"p1_gap": p1, "G": 2 * p1, "n_pairs": int(len(allg))}
    f.write_text(json.dumps(out))
    return out["G"]


def s6_returns(r: pd.Series, weights: dict, seed: int, G: float) -> tuple[pd.Series, int]:
    """Gap shock in return space: each prior-close holding is hit with p=0.01, subtracting w*|G| from that day's return."""
    rng = np.random.default_rng(seed)
    wd = sorted(weights)
    wdi = pd.DatetimeIndex(wd)
    out = r.copy()
    hits = 0
    for j, d in enumerate(r.index):
        k = wdi.searchsorted(d) - 1                      # last session strictly before d
        if k < 0:
            continue
        w = weights[wd[k]]
        h = rng.random(len(w)) < P_GAP
        if h.any():
            out.iloc[j] += float(w[h].sum()) * G
            hits += int(h.sum())
    return out, hits


def s7_years(index: pd.DatetimeIndex, seed: int) -> list[int]:
    yrs = sorted(set(index.year))
    rng = np.random.default_rng(seed)
    return [yrs[int(i)] for i in rng.integers(0, len(yrs), len(yrs))]


def s7_apply(r: pd.Series, years: list[int]) -> pd.Series:
    parts = [r[r.index.year == y].to_numpy() for y in years]
    v = np.concatenate(parts) if parts else np.array([])
    return pd.Series(v, index=pd.RangeIndex(len(v)))


# ======================================================================================== controls verdict
def _baseline(r_on: pd.Series, r_off: pd.Series, expo: pd.Series, ew: pd.Series) -> pd.Series:
    """Amendment 1 beta baseline: x_{t-1} * EW_t - c_t, c_t = r_on - r_off (the placebo's own cost drag)."""
    x = expo.reindex(expo.index.union(r_on.index)).ffill().shift(1).reindex(r_on.index).fillna(0.0)
    c = (r_on - r_off.reindex(r_on.index).fillna(0.0))
    return x * ew.reindex(r_on.index).fillna(0.0) - c


def controls() -> dict:
    """Amendment 1 (2026-11-19, before first look): beta-baseline test for N1/N2, cost drag, permutation p, N3."""
    import core as C
    out = {"amendment": "Amendment 1, 2026-11-19, amended before first look"}
    base = {}
    for book in ("swing", "momentum"):
        bb = _load(book, "base")
        base[book] = np.array([sharpe_r(book_returns(book, r["nav"])) for r in bb["rows"]])
    bnav = {b: [r["nav"] for r in _load(b, "base")["rows"]] for b in ("swing", "momentum")}
    base["blend"] = np.array([sharpe_r(blend_returns(m, s)) for m, s in zip(bnav["momentum"], bnav["swing"])])
    ew = {b: _load(b, "base")["ew_universe"] for b in ("swing", "momentum")}
    for scen in ("N1", "N2", "N3"):
        on = {b: _load(b, scen)["rows"] for b in ("swing", "momentum")}
        off = {b: _load(b, scen + "off")["rows"] for b in ("swing", "momentum")} if scen != "N3" else None
        res = {}
        ser_on = {b: [book_returns(b, r["nav"]) for r in on[b]] for b in on}
        ser_on["blend"] = [blend_returns(m["nav"], s["nav"]) for m, s in zip(on["momentum"], on["swing"])]
        sh_on = {b: np.array([sharpe_r(r) for r in v]) for b, v in ser_on.items()}
        if off is not None:
            ser_off = {b: [book_returns(b, r["nav"]) for r in off[b]] for b in off}
            sh_off = {b: np.array([sharpe_r(r) for r in v]) for b, v in ser_off.items()}
            bl = {b: [_baseline(ser_on[b][k], ser_off[b][k], on[b][k]["expo"], ew[b]) for k in range(len(on[b]))]
                  for b in ("swing", "momentum")}
            win_ = lambda r: r[(r.index >= pd.Timestamp(SW_WIN[0])) & (r.index <= pd.Timestamp(SW_WIN[1]))]
            bl["blend"] = [C.vol_target_blend(win_(m), win_(s), target=TARGET)[0]
                           for m, s in zip(bl["momentum"], bl["swing"])]
            ser_off["blend"] = [blend_returns(m["nav"], s["nav"]) for m, s in zip(off["momentum"], off["swing"])]
            sh_off["blend"] = np.array([sharpe_r(r) for r in ser_off["blend"]])
        for b in ("swing", "momentum", "blend"):
            v = sh_on[b]
            strat = float(np.median(base[b]))
            r_ = {"n": int(np.isfinite(v).sum()), "placebo_sharpe_mean": round(float(np.nanmean(v)), 4),
                  "placebo_sharpe_median": round(float(np.nanmedian(v)), 4),
                  "placebo_sharpe_p5": round(float(np.nanpercentile(v, 5)), 4),
                  "placebo_sharpe_p95": round(float(np.nanpercentile(v, 95)), 4),
                  "strategy_sharpe_base_median": round(strat, 4),
                  "base_p5": round(float(np.percentile(base[b], 5)), 4)}
            if off is not None:
                bs = np.array([sharpe_r(x) for x in bl[b]])
                dd = v - bs
                dd = dd[np.isfinite(dd)]
                se = float(dd.std(ddof=1) / np.sqrt(len(dd)))
                r_.update({"baseline_sharpe_mean": round(float(np.nanmean(bs)), 4),
                           "paired_diff_mean": round(float(dd.mean()), 4), "paired_diff_se": round(se, 4),
                           "z": round(float(dd.mean() / se), 2) if se > 0 else None,
                           "pass_beta_baseline": bool(abs(dd.mean()) <= 2 * se),
                           "cost_off_sharpe_median": round(float(np.nanmedian(sh_off[b])), 4),
                           "cost_drag_median_sharpe": round(float(np.nanmedian(sh_off[b]) - np.nanmedian(v)), 4),
                           "permutation_p_strategy": round(float(np.mean(v >= strat)), 3)})
            else:
                r_["pass_clearly_below_base"] = bool(np.nanmedian(v) < np.percentile(base[b], 5))
            if b == "swing":
                r_["realised_trades_mean"] = float(np.mean([x["trades"] for x in on["swing"]]))
                r_["n_signals_mean"] = float(np.mean([x.get("n_signals", np.nan) for x in on["swing"]]))
            if b == "momentum":
                r_["exits_per_rebalance_mean"] = float(np.mean([x["exits_per_rebalance"] for x in on["momentum"]]))
            res[b] = r_
        out[scen] = res
    sw_b, mo_b = _load("swing", "base"), _load("momentum", "base")
    out["base_reference"] = {"swing_trades_mean": float(np.mean([r["trades"] for r in sw_b["rows"]])),
                             "swing_real_signals": sw_b.get("n_real_signals"),
                             "momentum_exits_per_rebalance": mo_b["base_turnover"]["exits_per_rebalance"],
                             "n2_calibration": _load("momentum", "N2").get("n2_calibration"),
                             "sharpe_base_median": {b: round(float(np.median(base[b])), 4) for b in base}}
    fails = [(s, b) for s in ("N1", "N2") for b in ("swing", "momentum", "blend") if not out[s][b]["pass_beta_baseline"]]
    n3 = [b for b in ("swing", "momentum", "blend") if not out["N3"][b]["pass_clearly_below_base"]]
    out["verdict"] = {"suite_failed": bool(fails), "failing_beta_baseline": fails, "n3_not_clearly_below_base": n3,
                      "rule": "suite FAILS only if N1 or N2 breaks the beta-baseline test (Amendment 1)"}
    return out


# ======================================================================================== Amendment 2
def controls_a2(export_dir: Path | None = None) -> dict:
    """Amendment 2 (post-hoc spec correction): mean daily return of the cost-OFF placebo vs the exposure-scaled EW
    universe over the same invested days; z across seeds; vol ratio; Sharpe gap predicted by the vol ratio alone."""
    import core as C
    ew = {b: _load(b, "base")["ew_universe"] for b in ("swing", "momentum")}
    out = {"amendment": "Amendment 2, 2026-11-19, post-hoc spec correction; cost-OFF twins only; pass |z| < 3 on all 6",
           "multiplicity": "2 harness specifications x 6 tests = 12 on the same cached placebos; Amendment 2's 6 binding"}
    win_ = lambda r: r[(r.index >= pd.Timestamp(SW_WIN[0])) & (r.index <= pd.Timestamp(SW_WIN[1]))]
    for scen in ("N1off", "N2off"):
        rows = {b: _load(b, scen)["rows"] for b in ("swing", "momentum")}
        per = {b: [] for b in ("swing", "momentum", "blend")}
        legs = {"swing": [], "momentum": []}
        for b in ("swing", "momentum"):
            for k, row in enumerate(rows[b]):
                r = book_returns(b, row["nav"])
                x = row["expo"].reindex(row["expo"].index.union(r.index)).ffill().shift(1).reindex(r.index).fillna(0.0)
                base = x * ew[b].reindex(r.index).fillna(0.0)
                legs[b].append((r, base))
                m = x > 0
                per[b].append((r[m], base[m]))
                if export_dir is not None and b == "swing" and scen == "N2off":
                    export_dir.mkdir(parents=True, exist_ok=True)
                    pd.DataFrame({"placebo_ret": r, "expo_prior_close": x}).to_csv(export_dir / f"seed_{k:03d}.csv",
                                                                                 index_label="date", float_format="%.12g")
        if export_dir is not None and scen == "N2off":
            ew["swing"].rename("ew_universe_ret").to_csv(export_dir / "ew_universe.csv", index_label="date", float_format="%.12g")
        for (rm_, bm_), (rs_, bs_) in zip(legs["momentum"], legs["swing"]):
            pr = C.vol_target_blend(win_(rm_), win_(rs_), target=TARGET)[0]
            br = C.vol_target_blend(win_(bm_), win_(bs_), target=TARGET)[0]
            per["blend"].append((pr, br))
        res = {}
        for b, pairs in per.items():
            d = np.array([(r.mean() - bb.mean()) * 252 for r, bb in pairs])
            vr = np.array([r.std() / bb.std() for r, bb in pairs])
            sh_r = np.array([sharpe_r(r) for r, _ in pairs])
            sh_b = np.array([sharpe_r(bb) for _, bb in pairs])
            se = d.std(ddof=1) / np.sqrt(len(d))
            res[b] = {"n": int(len(d)), "diff_ann_pct_mean": round(float(d.mean()) * 100, 3),
                      "diff_ann_pct_se": round(float(se) * 100, 3), "z": round(float(d.mean() / se), 2),
                      "pass_abs_z_lt_3": bool(abs(d.mean() / se) < 3),
                      "placebo_mean_ann_pct": round(float(np.mean([r.mean() for r, _ in pairs])) * 252 * 100, 2),
                      "baseline_mean_ann_pct": round(float(np.mean([bb.mean() for _, bb in pairs])) * 252 * 100, 2),
                      "vol_ratio_mean": round(float(vr.mean()), 3),
                      "sharpe_placebo_mean": round(float(sh_r.mean()), 3), "sharpe_baseline_mean": round(float(sh_b.mean()), 3),
                      "sharpe_gap_observed": round(float((sh_r - sh_b).mean()), 3),
                      "sharpe_gap_predicted_by_vol_ratio": round(float((sh_b * (1 / vr - 1)).mean()), 3),
                      "invested_days_mean": int(np.mean([len(r) for r, _ in pairs]))}
        out[scen[:2]] = res
    tests = [(s, b, out[s][b]["pass_abs_z_lt_3"]) for s in ("N1", "N2") for b in ("swing", "momentum", "blend")]
    out["verdict"] = {"passed": all(t[2] for t in tests), "failing": [(s, b) for s, b, ok in tests if not ok],
                      "tests": 6}
    return out


def held_gap_p1() -> dict:
    """S6 add-on: 1st-percentile open/prev-close gap over (held name, day) pairs of the unperturbed books."""
    import explore_blend_drawdown_sizing as B
    from run_bhanushali_path1 import corrected_universe
    d = B.navs()
    u = corrected_universe()
    gaps = {}
    for t, df in u.items():
        o = df["open"] if "open" in df else df["Open"]
        c = df["close"] if "close" in df else df["Close"]
        g = (o / c.shift(1) - 1).replace([np.inf, -np.inf], np.nan)
        g.index = pd.DatetimeIndex(df.index).normalize()
        gaps[t] = g[~g.index.duplicated(keep="last")]
    out = {}
    pl = d["swing_position_log"]
    pairs = pd.DataFrame({"t": pl["tkr"], "d": pd.to_datetime(pl["date"]).dt.normalize()})
    pairs = pairs[(pairs.d >= pd.Timestamp(SW_WIN[0])) & (pairs.d <= pd.Timestamp(SW_WIN[1]))]
    v = np.array([gaps[t].get(dd, np.nan) for t, dd in zip(pairs.t, pairs.d)], float)
    v = v[np.isfinite(v)]
    out["swing_held_pairs"] = {"n": int(len(v)), "p1_gap_pct": round(float(np.percentile(v, 1)) * 100, 2)}
    mt = d["momentum_trades"]
    vals = []
    for r in mt.itertuples():
        g = gaps.get(r.ticker)
        if g is None:
            continue
        lo, hi = pd.Timestamp(r.entry_date), pd.Timestamp(r.exit_date)
        vals.append(g[(g.index > lo) & (g.index <= hi) & (g.index <= pd.Timestamp(MOM_END))].to_numpy(float))
    v = np.concatenate(vals) if vals else np.array([])
    v = v[np.isfinite(v)]
    out["momentum_held_pairs_approx"] = {"n": int(len(v)), "p1_gap_pct": round(float(np.percentile(v, 1)) * 100, 2),
                                         "note": "entry..exit spans of every trade row; overlapping rows double-count a few days"}
    out["all_pairs_p1_gap_pct"] = round(json.loads((CACHE / "gap_G.json").read_text())["p1_gap"] * 100, 2)
    return out


# ======================================================================================== Harness Step A (spec 3)
OPEN_REASONS = {"stop", "stop_part", "sma_break", "time", "stale"}


def ew_components(ctl) -> pd.DataFrame:
    """Equal-weight member returns: close-to-close (cc), overnight (on: open/prev close), intraday (id: close/open)."""
    cc, on, idr = {}, {}, {}
    for t, s in ctl.P.items():
        per = (ctl.mem or {}).get(t.upper()) if ctl.mem is not None else None
        if ctl.mem is not None and not per:
            continue
        ix = pd.DatetimeIndex(s["dates"]).normalize()
        o, c = np.asarray(s["o"], float), np.asarray(s["c"], float)
        pc = np.concatenate([[np.nan], c[:-1]])
        m = np.ones(len(ix), bool)
        if ctl.mem is not None:
            m[:] = False
            dd = ix.date
            for a, b in per:
                m |= (dd >= a) & (dd <= b)
        keep = m & ~ix.duplicated(keep="last")
        cc[t] = pd.Series((c / pc - 1)[keep], index=ix[keep])
        on[t] = pd.Series((o / pc - 1)[keep], index=ix[keep])
        idr[t] = pd.Series((c / o - 1)[keep], index=ix[keep])
    f = lambda dct: pd.DataFrame(dct).replace([np.inf, -np.inf], np.nan).mean(axis=1, skipna=True)
    return pd.DataFrame({"cc": f(cc), "on": f(on), "id": f(idr)})


def matched_baseline(nav: pd.Series, plog: pd.DataFrame, led: pd.DataFrame, ev: pd.DataFrame, ewc: pd.DataFrame,
                     dates: pd.DatetimeIndex) -> pd.Series:
    """Spec 3 baseline on `dates` (the placebo's return dates)."""
    plog = plog.copy()
    plog["date"] = pd.to_datetime(plog["date"]).dt.normalize()
    hold = {d: g.set_index("tkr") for d, g in plog.groupby("date")}
    navd = nav.copy()
    exit_reason = {}
    if len(led):
        for r in led.itertuples():
            exit_reason[(r.tkr, pd.Timestamp(r.exit_date).normalize())] = r.reason
    part = {}
    if len(ev):
        for r in ev[ev["event_type"] == "partial_book"].itertuples():
            part.setdefault((r.ticker, pd.Timestamp(r.event_date).normalize()), []).append(r.reason_code)
    allx = navd.index
    out = []
    for d in dates:
        k = allx.get_loc(d)
        if k == 0:
            out.append(0.0)
            continue
        dp = allx[k - 1]
        eq0 = float(navd.iloc[k - 1])
        hp, hc = hold.get(dp), hold.get(d)
        e = ewc.loc[d] if d in ewc.index else pd.Series({"cc": 0.0, "on": 0.0, "id": 0.0})
        e = e.fillna(0.0)
        b = 0.0
        if hp is not None:
            for t, r in hp.iterrows():
                w0 = float(r["shares"]) * float(r["mark_px"]) / eq0
                sh_now = float(hc.loc[t, "shares"]) if (hc is not None and t in hc.index) else 0.0
                sold = max(0.0, float(r["shares"]) - sh_now) / float(r["shares"]) if r["shares"] > 0 else 0.0
                if sh_now == 0.0:
                    rs = exit_reason.get((t, d), "stop")
                    b += w0 * (e["cc"] if rs == "targets" else e["on"])
                    continue
                if sold > 1e-9:
                    rc = part.get((t, d), [])
                    leg = e["on"] if ("pattern_frac" in rc and "t1_done" not in rc) else e["cc"]
                    b += w0 * sold * leg + w0 * (1 - sold) * e["cc"]
                else:
                    b += w0 * e["cc"]
        if hc is not None:
            for t, r in hc.iterrows():
                if hp is None or t not in hp.index:
                    b += float(r["shares"]) * float(r["entry"]) / eq0 * e["id"]
        out.append(b)
    return pd.Series(out, index=dates)


def n4_hold_fn(seed: int):
    """Holding period (calendar days) drawn by hash(seed, ticker, entry date) from the unperturbed swing ledger."""
    import explore_blend_drawdown_sizing as B
    led = B.navs()["swing_ledger"]
    led = led[led["reason"] != "eos"]
    hp = sorted(int(x) for x in (pd.to_datetime(led["exit_date"]) - pd.to_datetime(led["entry_date"])).dt.days)
    def f(tkr, entry_date) -> int:
        return hp[zlib.crc32(f"{seed}|{tkr}|{entry_date}".encode()) % len(hp)]
    f.pool = hp
    return f


def run_a3(scen: str) -> None:
    """Regenerate the cached cost-OFF swing twin `scen` with fill logs; verify NAV identity; both baselines per seed."""
    R94 = install_swing_engine()
    from nq.lab import ensemble as E
    from nq.lab import runs as L
    ctx = E.prepare_context()
    ctl = SwingControls(ctx)
    ewc = ew_components(ctl)
    cached = [] if scen == "N4off" else _load("swing", scen)["rows"]
    draws = E.draw_perturbations(N_SEEDS, E.DEFAULT_SEED)
    res = []
    t0 = time.time()
    for _, d in draws.iterrows():
        k = int(d["path"])
        P2, _n = ctl.build("N2" if scen == "N4off" else scen[:2], k)
        cfg = {**L.normalize_config({}), "start": str(pd.Timestamp(d["start"]).date())}
        led, plog, ev = [], [], []
        R94._STRESS.clear(); R94._STRESS.update({**NEUTRAL, "n4": n4_hold_fn(k) if scen == "N4off" else None})
        with E.cost_jitter(0.0):
            out = R94.backtest(P2, ctx.mem, ledger=led, a_grade=R94.grade_a_entries(P2), **L.engine_kwargs(cfg),
                               demerger_events=ctx.events, position_log=plog, event_log=ev, cost_off=True)
        nav = pd.Series(out["curve"], dtype=float)
        nav.index = pd.DatetimeIndex(nav.index).normalize()
        nav = nav[~nav.index.duplicated(keep="last")].sort_index()
        R94._STRESS.clear(); R94._STRESS.update(NEUTRAL)
        if scen == "N4off":
            pl = pd.DataFrame(plog)
            pl["w"] = pl["notional"] / pl["equity"]
            expo_k = pl.groupby(pd.to_datetime(pl["date"]).dt.normalize())["w"].sum().reindex(nav.index).fillna(0.0)
            cached.append({"nav": nav, "expo": expo_k})
            hold = pd.DataFrame(led)
            hold = hold[hold["reason"] != "eos"] if len(hold) else hold
        c = cached[k]["nav"]
        if not (len(c) == len(nav) and np.array_equal(c.to_numpy(), nav.to_numpy()) and c.index.equals(nav.index)):
            raise SystemExit(f"{scen} seed {k}: regenerated NAV differs from the cache: stop")
        r = book_returns("swing", nav)
        bm = matched_baseline(nav, pd.DataFrame(plog), pd.DataFrame(led), pd.DataFrame(ev), ewc, r.index)
        x = cached[k]["expo"].reindex(cached[k]["expo"].index.union(r.index)).ffill().shift(1).reindex(r.index).fillna(0.0)
        ba2 = x * ewc["cc"].reindex(r.index).fillna(0.0)
        res.append({"seed": k, "d_matched": float((r.mean() - bm.mean()) * 252), "d_a2": float((r.mean() - ba2.mean()) * 252),
                    "placebo_ann": float(r.mean() * 252), "baseline_matched_ann": float(bm.mean() * 252),
                    "baseline_a2_ann": float(ba2.mean() * 252)})
        if k % 10 == 0:
            print("a3", scen, k, round(time.time() - t0), flush=True)
    pd.to_pickle(res, CACHE / f"a3_swing__{scen}.pkl")
    print("done a3", scen, round(time.time() - t0), flush=True)


def a3_report(names=("N1off", "N2off")) -> dict:
    out = {"spec": "post-hoc spec 3 (Harness Step A): matched-fill baseline; pass |z| < 3 on swing N1 and N2"}
    for scen in names:
        rows = pd.DataFrame(pd.read_pickle(CACHE / f"a3_swing__{scen}.pkl"))
        o = {}
        for col in ("d_matched", "d_a2"):
            v = rows[col].to_numpy()
            se = v.std(ddof=1) / np.sqrt(len(v))
            o[col] = {"mean_ann_pct": round(float(v.mean()) * 100, 3), "se_pct": round(float(se) * 100, 3),
                      "z": round(float(v.mean() / se), 2), "pass_abs_z_lt_3": bool(abs(v.mean() / se) < 3)}
        o["placebo_ann_pct"] = round(float(rows["placebo_ann"].mean()) * 100, 2)
        o["baseline_matched_ann_pct"] = round(float(rows["baseline_matched_ann"].mean()) * 100, 2)
        o["baseline_a2_ann_pct"] = round(float(rows["baseline_a2_ann"].mean()) * 100, 2)
        o["n_seeds"] = int(len(rows))
        out[scen] = o
    out["passed"] = all(out[s]["d_matched"]["pass_abs_z_lt_3"] for s in names)
    return out


# ======================================================================================== report
def report() -> None:
    tri = tri_series()
    G = gap_G()
    res = {"G_gap": json.loads((CACHE / "gap_G.json").read_text()), "target": TARGET, "n_paths": N_PATHS}
    res["controls"] = controls()
    bases = {b: _load(b, "base") for b in ("swing", "momentum")}

    def legs(scen):
        if scen in ("S6", "S7", "S3m"):
            return None
        return {b: _load(b, scen) for b in ("swing", "momentum")}

    table = {}
    for scen in ("base", "S1", "S2", "S3", "S4", "S5", "S6", "S7"):
        cells = {"swing": [], "momentum": [], "blend": []}
        hits = {"swing": 0, "momentum": 0}
        for k in range(N_PATHS):
            navs = {}
            rr = {}
            for b in ("swing", "momentum"):
                src = bases[b] if scen in ("base", "S6", "S7") or (scen == "S3" and b == "momentum") else _load(b, scen)
                navs[b] = src["rows"][k]["nav"]
                rr[b] = book_returns(b, navs[b])
            if scen == "S6":
                for j, b in enumerate(("swing", "momentum")):
                    full = navs[b].pct_change().dropna()
                    sh, h = s6_returns(full, bases[b]["rows"][k]["weights"], SEED_S6 + 1000 * j + k, G)
                    hits[b] += h
                    navs[b] = (1 + sh).cumprod() * navs[b].iloc[0]
                    navs[b] = pd.concat([pd.Series([bases[b]["rows"][k]["nav"].iloc[0]], index=[bases[b]["rows"][k]["nav"].index[0]]), navs[b]])
                    rr[b] = book_returns(b, navs[b])
            rb = blend_returns(navs["momentum"], navs["swing"])
            tri_b = {"swing": tri[(tri.index >= rr["swing"].index[0]) & (tri.index <= rr["swing"].index[-1])],
                     "momentum": tri[(tri.index >= rr["momentum"].index[0]) & (tri.index <= rr["momentum"].index[-1])],
                     "blend": tri[(tri.index >= rb.index[0]) & (tri.index <= rb.index[-1])]}
            ser = {"swing": rr["swing"], "momentum": rr["momentum"], "blend": rb}
            if scen == "S7":
                for j, b in enumerate(("swing", "momentum", "blend")):
                    yrs = s7_years(ser[b].index, SEED_S7 + 1000 * j + k)
                    tri_b[b] = s7_apply(tri_b[b], yrs)
                    ser[b] = s7_apply(ser[b], yrs)
            for b in ("swing", "momentum", "blend"):
                sh = sharpe_r(ser[b])
                c = {"sharpe": sh, "vs_tri": sh - sharpe_r(tri_b[b])}
                if b == "blend":
                    s_ = ser[b]
                    if scen == "S7":
                        s_ = pd.Series(s_.to_numpy(), index=pd.bdate_range("2001-01-01", periods=len(s_)))
                    c["p95_dd156"] = blend_p95(s_)
                cells[b].append(c)
        table[scen] = {b: pd.DataFrame(v) for b, v in cells.items()}
        table[scen]["_hits"] = hits
        print("scenario", scen, {b: round(float(table[scen][b]["sharpe"].median()), 3) for b in cells}, flush=True)

    out = {}
    for scen, t in table.items():
        out[scen] = {}
        for b in ("swing", "momentum", "blend"):
            df = t[b]
            base_med = float(table["base"][b]["sharpe"].median())
            m = float(df["sharpe"].median())
            o = {"median_sharpe": round(m, 3), "p5": round(float(df["sharpe"].quantile(0.05)), 3),
                 "p95": round(float(df["sharpe"].quantile(0.95)), 3),
                 "median_vs_tri": round(float(df["vs_tri"].median()), 3),
                 "ratio_to_base": round(m / base_med, 3), "sharpe_pass": bool(m >= 0.5 * base_med)}
            if b == "blend":
                o["p95_dd156_median"] = round(float(df["p95_dd156"].median()), 2)
                o["p95_dd156_max_path"] = round(float(df["p95_dd156"].max()), 2)
                o["dd_pass"] = bool(df["p95_dd156"].median() <= 25.0)
                o["pass"] = o["sharpe_pass"] and o["dd_pass"]
            else:
                o["pass"] = o["sharpe_pass"]
            out[scen][b] = o
        if scen == "S6":
            out[scen]["gap_hits_total"] = t["_hits"]
    worst = {b: min((s for s in out if s != "base"), key=lambda s: out[s][b]["ratio_to_base"]) for b in ("swing", "momentum", "blend")}
    res["shocks"] = out
    res["worst_shock"] = worst
    sw = _load("swing", "S3")
    res["s3_stop_exits_swing_mean"] = float(np.mean([r["stop_exits"] for r in sw["rows"]]))
    OUT_JSON.write_text(json.dumps(res, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    mode, *args = sys.argv[1:]
    if mode == "swing":
        run_swing(args)
    elif mode == "momentum":
        run_momentum(args)
    elif mode == "controls":
        print(json.dumps(controls(), indent=1, default=str))
    elif mode == "a3":
        run_a3(args[0])
    elif mode == "a3_report":
        print(json.dumps(a3_report(tuple(args) if args else ("N1off", "N2off")), indent=1, default=str))
    elif mode == "a2":
        print(json.dumps(controls_a2(ROOT / ".cache" / "stress_suite_a2_replica"), indent=1, default=str))
    elif mode == "held_gap":
        print(json.dumps(held_gap_p1(), indent=1, default=str))
    elif mode == "gap":
        print(gap_G())
    else:
        report()
