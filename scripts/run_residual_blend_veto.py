"""Pre-reg 0078 — residual momentum as a COMPLEMENT: blend vs veto, graded on localized DD.

Four fixed-param arms vs the sma200_slope_63 base:
  BLEND l=0.25 / l=0.50  -> rank = pctile(trend_rank + l*resid_rank)
  VETO q=0.20 / q=0.10   -> rank by trend, but make bottom-quintile/decile resid_rank names ineligible.
Verdict per the pre-committed 0078 rule: (1) LIVE 2022-26 DD >= 8pp shallower than base (vol-guarded if
book vol < 24%), (2) full-period GROSS CAGR >= 13.5%, (3) skew & Sortino not worse -> SHADOW, else KILL.
DSR reported, not gated. No engine change. Writes research/exports/blendveto_0078_results.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from config import DATA_DIR, load_frozen_cfg  # noqa: E402
from nq.data.features import compute_all_features  # noqa: E402
from nq.data.fundamentals import load_fund_store  # noqa: E402
from nq.data.membership import load_membership  # noqa: E402
from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache  # noqa: E402
from nq.engine.panel import compose_ranked_panel  # noqa: E402
from nq.runner.research import (_after_tax_cagr, _daily_returns,  # noqa: E402
                                _dsr_from_bootstrap, _fold_pass, run_backtest)
from nq.validation.bootstrap import DEFAULT_BLOCK, block_bootstrap_metric, bootstrap_delta  # noqa: E402
from nq.validation.metrics import sharpe  # noqa: E402
from run_residual_momentum import residual_ranks  # noqa: E402

START, END, NT = "2017-01-01", "2026-06-30", 91
DD_MIN_SHALLOWER, GROSS_FLOOR, VOL_GUARD = 8.0, 13.5, 0.24


def skew(x) -> float:
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    return float((((x - x.mean()) / x.std()) ** 3).mean()) if x.size > 8 and x.std() else float("nan")


def live_dd(r: pd.Series, scale: float = 1.0) -> float:
    r = r[r.index >= pd.Timestamp("2022-01-01")] * scale
    eq = (1.0 + r).cumprod()
    return float((eq / eq.cummax() - 1.0).min() * 100)


def make_arm(panel: pd.DataFrame, rr: pd.DataFrame, kind: str, p: float) -> pd.DataFrame:
    c = panel.merge(rr, on=["date", "ticker"], how="left")
    if kind == "blend":
        score = c["trend_rank"] + p * c["resid_rank"].fillna(0.0)
        c["trend_rank"] = score.groupby(c["date"]).rank(pct=True)
    else:  # veto: resid_rank is already a per-day percentile, so resid_rank < q == bottom-q
        c.loc[c["resid_rank"].notna() & (c["resid_rank"] < p), "trend_rank"] = np.nan
    return c


def main() -> int:
    cfg = load_frozen_cfg()
    ohlcv = load_ohlcv_cache(OHLCV_CACHE)
    print(f"panel build ({len(ohlcv)} names) ...", flush=True)
    panel = compose_ranked_panel(compute_all_features(ohlcv), ohlcv,
                                 fund_store=load_fund_store(), membership=load_membership())
    panel["date"] = pd.to_datetime(panel["date"])
    factors = pd.read_parquet(DATA_DIR / "ff_india_factors.parquet").set_index("date").sort_index()
    print("residualizing ...", flush=True)
    rr = residual_ranks(panel, factors)

    base_bt = run_backtest(panel, cfg, start=START, end=END)
    b = _daily_returns(base_bt["equity_curve"])
    bm = base_bt["metrics"]
    base_vol = float(b.std() * np.sqrt(252))
    base_live = live_dd(b)
    base_skew, base_atx = skew(b.to_numpy()), _after_tax_cagr(base_bt, 1e6)
    print(f"\nBASE  gross CAGR {bm['cagr_pct']:.1f}  after-tax {base_atx:.2f}  Sharpe {bm['sharpe']:.3f}  "
          f"Sortino {bm['sortino']:.3f}  skew {base_skew:+.3f}  vol {base_vol*100:.1f}%  LIVE DD {base_live:.1f}")

    arms = [("blend", 0.25), ("blend", 0.50), ("veto", 0.20), ("veto", 0.10)]
    out = []
    hdr = f"{'arm':<12}{'grossCAGR':>10}{'aftertax':>9}{'Sortino':>8}{'skew':>8}{'vol%':>6}{'LIVE_DD':>9}{'guarded':>9}{'dSharpe':>9}{'DSR':>6}  verdict"
    print("\n" + hdr)
    print("-" * len(hdr))
    for kind, p in arms:
        cand = make_arm(panel, rr, kind, p)
        cb = run_backtest(cand, cfg, start=START, end=END)
        c = _daily_returns(cb["equity_curve"])
        cm = cb["metrics"]
        common = b.index.intersection(c.index)
        av, bv = c.loc[common].to_numpy(float), b.loc[common].to_numpy(float)
        avol = float(c.std() * np.sqrt(252))
        ld = live_dd(c)
        guard_k = (base_vol / avol) if avol < VOL_GUARD else 1.0
        ld_g = live_dd(c, guard_k)
        dsh = bootstrap_delta(av, bv, sharpe, block_size=DEFAULT_BLOCK, n_samples=5000, seed=12345)
        ci = block_bootstrap_metric(av, sharpe, block_size=DEFAULT_BLOCK, n_samples=5000, seed=12345)
        dsr = _dsr_from_bootstrap(av, NT, (ci.lower, ci.upper))
        atx, sk = _after_tax_cagr(cb, 1e6), skew(av)
        c1 = ld_g >= base_live + DD_MIN_SHALLOWER   # >=8pp shallower = LESS negative than -38.3, vol-guarded
        c2 = cm["cagr_pct"] >= GROSS_FLOOR
        c3 = sk >= base_skew and cm["sortino"] >= bm["sortino"]
        verdict = "SHADOW" if (c1 and c2 and c3) else "KILL"
        tag = f"{kind}-{p}"
        print(f"{tag:<12}{cm['cagr_pct']:>10.1f}{atx:>9.2f}{cm['sortino']:>8.3f}{sk:>+8.3f}{avol*100:>6.1f}"
              f"{ld:>9.1f}{ld_g:>9.1f}{dsh.point:>+9.3f}{dsr:>6.2f}  {verdict}"
              f"{'' if guard_k == 1.0 else f'  [vol-guarded k={guard_k:.2f}]'}", flush=True)
        out.append({"arm": tag, "gross_cagr": cm["cagr_pct"], "after_tax_cagr": atx,
                    "sortino": cm["sortino"], "skew": round(sk, 3), "sharpe": cm["sharpe"],
                    "ann_vol": round(avol, 3), "live_dd": round(ld, 1), "live_dd_guarded": round(ld_g, 1),
                    "full_dd": cm["max_drawdown_pct"], "n_trades": cm["n_trades"],
                    "dSharpe": round(dsh.point, 3), "dSharpe_ci": [round(dsh.lower, 3), round(dsh.upper, 3)],
                    "dsr": round(float(dsr), 3), "fold": round(_fold_pass(common, av, bv, 2019)[0], 3),
                    "crit1_dd": bool(c1), "crit2_cagr": bool(c2), "crit3_shape": bool(c3), "verdict": verdict})

    payload = {"prereg": "0078", "n_trials": NT,
               "base": {"gross_cagr": bm["cagr_pct"], "after_tax_cagr": base_atx, "sharpe": bm["sharpe"],
                        "sortino": bm["sortino"], "skew": round(base_skew, 3), "ann_vol": round(base_vol, 3),
                        "live_dd": round(base_live, 1)},
               "criteria": {"live_dd_shallower_pp": DD_MIN_SHALLOWER, "gross_cagr_floor": GROSS_FLOOR,
                            "vol_guard_below": VOL_GUARD}, "arms": out}
    pth = ROOT / "research" / "exports" / "blendveto_0078_results.json"
    pth.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"\nwrote {pth}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
