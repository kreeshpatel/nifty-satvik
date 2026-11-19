"""Blind replica (S1 / N1) -- shared plumbing. Written from replica_spec.md only.

Engine copies are loaded into this process; no repo file is edited.
"""
from __future__ import annotations

import sys
import types
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("/home/user/nifty-satvik")
HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
CACHE.mkdir(exist_ok=True)
for p in (ROOT, ROOT / "scripts", ROOT / "pipelines" / "research"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

SW_WIN = ("2019-03-01", "2024-06-28")


# ----------------------------------------------------------------------------- swing engine copy
_OLD = '''            if p["pending"] is not None:
                act, rs = p["pending"]
                px = s["o"][i]
'''
_NEW = '''            if p["pending"] is not None and S1_EXIT_DELAY and not p.get("_s1_waited"):
                p["_s1_waited"] = True                      # S1: skip this open, fill at the next one
                if i in s["weekend"]:
                    S1_STATS["wait_on_weekend"] += 1
            elif p["pending"] is not None:
                p.pop("_s1_waited", None)
                act, rs = p["pending"]
                px = s["o"][i]
'''


def load_engine_copy():
    """exec a source-modified copy of run_bhanushali_weekly_rank under its own name, before nq.lab imports it."""
    name = "run_bhanushali_weekly_rank"
    if name in sys.modules and getattr(sys.modules[name], "_REPLICA_COPY", False):
        return sys.modules[name]
    assert name not in sys.modules, "original engine already imported"
    path = ROOT / "scripts" / f"{name}.py"
    src = path.read_text(encoding="utf-8")
    assert src.count(_OLD) == 1, "pending-exit block not found exactly once"
    src = src.replace(_OLD, _NEW)
    mod = types.ModuleType(name)
    mod.__file__ = str(path)
    mod.S1_EXIT_DELAY = False
    mod.S1_STATS = {"wait_on_weekend": 0}
    mod._REPLICA_COPY = True
    sys.modules[name] = mod
    exec(compile(src, str(path), "exec"), mod.__dict__)
    return mod


def swing_context():
    R94 = load_engine_copy()
    from nq.lab import ensemble as E
    f = CACHE / "swing_ctx.pkl"
    if f.exists():
        with open(f, "rb") as fh:
            P, mem, events, last_bar = pickle.load(fh)
        ctx = E.EnsembleContext(P=P, mem=mem, events=events, last_bar=last_bar)
    else:
        ctx = E.prepare_context()
        with open(f, "wb") as fh:
            pickle.dump((ctx.P, ctx.mem, ctx.events, ctx.last_bar), fh)
    return R94, ctx


def run_swing(R94, ctx, P, a_grade, d) -> pd.Series:
    from nq.lab import ensemble as E, runs as L
    cfg = {**L.normalize_config({}), "start": str(d["start"])}
    kw = L.engine_kwargs(cfg)
    with E.cost_jitter(float(d["cost_delta"])):
        out = R94.backtest(P, ctx.mem, ledger=[], a_grade=a_grade, **kw, demerger_events=ctx.events)
    nav = pd.Series(out["curve"], dtype=float)
    nav.index = pd.DatetimeIndex(nav.index).normalize()
    nav = nav[~nav.index.duplicated(keep="last")].sort_index()
    return nav


def swing_returns(nav: pd.Series) -> pd.Series:
    s = nav[(nav.index >= pd.Timestamp(SW_WIN[0])) & (nav.index <= pd.Timestamp(SW_WIN[1]))]
    return s.pct_change().dropna()


def sharpe(r: pd.Series) -> float:
    r = r.dropna()
    return float(r.mean() / r.std() * np.sqrt(252))


def appraisal(r: pd.Series, bench: pd.Series) -> dict:
    """OLS r = a + b*bench + e ; appraisal = a / sd(e) * sqrt(252), sd with n-2 dof."""
    df = pd.concat([r.rename("y"), bench.rename("x")], axis=1, join="inner").dropna()
    y, x = df["y"].to_numpy(float), df["x"].to_numpy(float)
    X = np.column_stack([np.ones_like(x), x])
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ coef
    sd = np.sqrt((e @ e) / (len(y) - 2))
    return {"appraisal": float(coef[0] / sd * np.sqrt(252)), "alpha_d": float(coef[0]), "beta": float(coef[1]),
            "n": int(len(y))}


def swing_member_frames(ctx):
    """dates x tickers: close-to-close return on each ticker's own bars, and PIT-member-with-bar mask."""
    f = CACHE / "swing_frames.pkl"
    if f.exists():
        return pd.read_pickle(f)
    closes = {}
    for t, s in ctx.P.items():
        idx = pd.DatetimeIndex(pd.to_datetime(list(s["dates"]))).normalize()
        c = pd.Series(np.asarray(s["c"], float), index=idx)
        closes[t] = c[~c.index.duplicated(keep="last")]
    C = pd.DataFrame(closes).sort_index()
    bar = C.notna()
    R = pd.DataFrame({t: closes[t].pct_change() for t in closes}).reindex(C.index)
    mem = ctx.mem
    M = pd.DataFrame(False, index=C.index, columns=C.columns)
    for t in C.columns:
        per = mem.get(t.upper()) if mem else None
        if not per:
            continue
        m = np.zeros(len(C.index), bool)
        dd = C.index.date
        for a, b in per:
            m |= (dd >= a) & (dd <= b)
        M[t] = m
    M = M & bar
    out = {"R": R, "M": M}
    pd.to_pickle(out, f)
    return out


# ----------------------------------------------------------------------------- 0001 momentum
def mom_panel() -> pd.DataFrame:
    f = CACHE / "mom_panel.pkl"
    if f.exists():
        return pd.read_pickle(f)
    import run_0001_xsec_momentum as M
    from nq.data.membership import load_membership
    from nq.universe import build_universe
    from run_bhanushali_path1 import corrected_universe
    p = M.add_signals(build_universe(corrected_universe(), load_membership(), start=M.START, end=M.END))
    b = p[p["ticker"].isin(p.loc[p["size_band"] == M.BAND, "ticker"].unique())].copy()
    b["rank"] = np.where(b["eligible"] & (b["size_band"] == M.BAND) & b["nms"].notna(), b["nms"], np.nan)
    b["date"] = pd.to_datetime(b["date"])
    b = b.sort_values(["date", "ticker"]).reset_index(drop=True)
    b.to_pickle(f)
    return b


def mom_nav(bt) -> pd.Series:
    ec = bt["equity_curve"]
    s = pd.Series([float(e["equity"]) for e in ec], index=pd.to_datetime([e["date"] for e in ec]), dtype=float)
    return s[~s.index.duplicated(keep="last")].sort_index()


def mom_ew_bench(b: pd.DataFrame) -> pd.Series:
    """EW daily close-to-close return over rows eligible & size_band == BAND on that date."""
    import run_0001_xsec_momentum as M
    q = b.sort_values(["ticker", "date"]).copy()
    q["r"] = q.groupby("ticker")["close"].pct_change()
    q = q[q["eligible"].astype(bool) & (q["size_band"] == M.BAND)]
    return q.groupby("date")["r"].mean()
