"""MEASUREMENT: after-tax comparison on 2019-03-01..2024-06-28. (a) the 70/30 blend at 11%; (b) the index fund
vol-targeted at 11%; (c) 60/40 index/liquid fund rebalanced yearly; (d) 65/35 rebalanced yearly.

Owner request 2026-11-18. Analysis only: no rule, trial or sealed read (swing prices cut 2024-06-30).

ONE LOT-LEVEL SIMULATOR FOR ALL FOUR (so the books differ only in what they hold, never in how tax is computed)
  capital        Rs 20,00,000 on 2019-03-01 (the FULL stage).
  instruments    each priced daily; every buy opens a FIFO lot (units, cost per unit, date); every sell consumes
                 lots first-in-first-out and books the gain to its bucket.
  index fund     price = Nifty Midcap150 Momentum 50 TRI less a 0.30%/yr expense ratio accrued per session.
                 Buy: stamp duty 0.005%. Redeem: STT 0.001% (equity mutual fund).
  liquid fund    price grows at 6.5%/yr gross compounded per session, less a 0.15%/yr expense ratio.
  stocks (blend) adjusted daily closes from run_bhanushali_path1.corrected_universe() (the panel both books trade).
                 Every buy pays STT 0.1% + stamp 0.015% + exchange 0.004% + slippage 0.10%. Every sell pays STT 0.1% +
                 exchange 0.004% + slippage 0.10%. Brokerage is zero (delivery).
  book cash      the share of each book's own NAV that the book holds uninvested earns nothing, as in the engines.

  TAX (owner's rules, applied to the whole window)
    equity lots (stocks, index fund): held > 365 days -> long-term (12.5% on the FY's net long-term gain above
      Rs 1,25,000); otherwise short-term (20%).
    liquid fund: gains at slab. ASSUMED 30% (the owner did not state a slab).
    set-off:     long-term losses only against long-term gains; short-term losses against short-term then long-term
                 gains; unused losses carry forward. The 8-year expiry is never reached in a 5-year window.
    no surcharge or cess (the owner's rates as given).
    payment:     on the last trading session on or before 31 March, the FY's tax is debited from the book's cash and
                 the book is re-targeted that same close, so the sale that funds it is itself a taxable event in the
                 next FY.
    terminal:    every lot is sold at the 2024-06-28 close and that partial FY's tax is paid. PRIMARY after-tax CAGR
                 = liquidation value. Also reported: the mark-to-market NAV after taxes paid to date (no liquidation).

  TARGETS (re-traded at every close to the targets; no no-trade band)
    (a) blend    held as two SLEEVE UNITS priced at each book's own pre-tax NAV (0001 momentum; live swing), plus the
                 liquid fund. Daily targets: momentum units = NAV * e_t * 0.70, swing units = NAV * e_t * 0.30, liquid
                 = NAV * (1 - e_t), with e_t = core.vol_target_blend(r_mom, r_swing, target=0.11)[1] (frozen rule).
                 PASS-THROUGH TAX of the books' own trades: each realised trade of a book (0001 trade list pnl at its
                 exit_date; swing ledger net_pnl at its exit_date) is taxable to the blend in proportion to the units
                 held that day (units / book units). It is short-term or long-term by that trade's own entry-to-exit
                 calendar days (> 365 = long-term). The same amount per unit is added to the cost basis of every lot
                 of that sleeve, so a later sale of units is taxed only on gains not yet realised inside the book. The
                 blend's own unit trades (exposure moves, the daily 70/30 rebalance, tax-funding sales) pay the stock
                 cost rates above and are taxed on (price - stepped-up basis) by the unit lot's own holding period.
                 WHY NOT STOCK-LEVEL: the 0001 trade list records sells only (a top-up keeps the first entry date),
                 so per-stock holdings cannot be rebuilt; a first stock-level attempt summed to 1.23x the momentum
                 NAV and failed the reconciliation below (added after first look).
    (b) index vt e_t from the same rule on the TRI's own daily returns, lagged one session, cap 1.0. Index fund =
                 NAV * e_t, liquid fund = rest.
    (c)/(d)      60/40 or 65/35. Bought 2019-03-01, re-weighted once a year at the 31-March close (after the tax
                 payment), and otherwise left to drift.

METRICS (after tax)
  CAGR           liquidation value ** (365.25 / days) - 1. A second reading is mark-to-market after taxes paid.
  Sharpe excess  (mean(r) - rf_d) / std(r, ddof 1) * sqrt(252), rf_d = 1.065 ** (1/252) - 1. Computed on the
                 mark-to-market after-tax daily NAV (tax payments appear as debits; the terminal liquidation is not
                 in the return series).
  156w p95 DD    stationary bootstrap of W-FRI weekly returns of that same NAV, mean block 8, 10,000 draws.
RECONCILIATION   (a) is also run with tax switched off, and its pre-tax CAGR is compared with the return-series blend
                 (vol_target_blend at 11% with 6.5% cash). A gap means the stock-level replication of the two books
                 is off; the gap is reported, never patched.
WINNER (fixed before results): the highest after-tax liquidation CAGR among the books whose after-tax 156-week p95
  drawdown is at or under 25%. Excess Sharpe is reported beside it.

    python pipelines/diagnostics/explore_after_tax_comparison.py
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict, deque
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts"), str(ROOT / "pipelines" / "research"),
                str(ROOT / "pipelines" / "diagnostics"), str(ROOT / "pipelines" / "lifecycle")]
import core as C  # noqa: E402
import explore_blend_drawdown_sizing as B  # noqa: E402

OUT_JSON = ROOT / "diagnostics" / "research" / "explore" / "2026-11-18_after_tax_comparison.json"
TRI = ROOT / "diagnostics" / "research" / "benchmarks" / "tri" / "nifty_midcap150_momentum_50_tri.csv"
WIN = B.COMMON
CAPITAL = 2_000_000.0
RF = 0.065
RF_D = (1 + RF) ** (1 / 252) - 1
TER_INDEX, TER_LIQUID = 0.0030, 0.0015
STCG, LTCG, LTCG_EXEMPT, SLAB = 0.20, 0.125, 125_000.0, 0.30
COST_STOCK_BUY = 0.001 + 0.00015 + 0.00004 + 0.001
COST_STOCK_SELL = 0.001 + 0.00004 + 0.001
COST_MF_BUY, COST_MF_SELL = 0.00005, 0.00001
CASH, LIQ, IDX, MOM, SW = "_BOOKCASH", "_LIQUID", "_INDEXFUND", "_MOM", "_SW"


def fy_end(d: pd.Timestamp) -> pd.Timestamp:
    return pd.Timestamp(year=d.year if d.month <= 3 else d.year + 1, month=3, day=31)


class Book:
    def __init__(self, tax_on: bool = True, cost_on: bool = True):
        self.cost_on = cost_on
        self.lots: dict[str, deque] = defaultdict(deque)
        self.units: dict[str, float] = defaultdict(float)
        self.cash = 0.0
        self.tax_on = tax_on
        self.st = self.lt = self.slab = 0.0
        self.cf_st = self.cf_lt = 0.0
        self.tax_paid: list[tuple[str, float]] = []
        self.costs = 0.0

    @staticmethod
    def kind(inst: str) -> str:
        return "debt" if inst == LIQ else "equity"

    def buy(self, inst, value, px, d):
        if value <= 0:
            return
        c = value * (COST_MF_BUY if inst in (IDX, LIQ) else COST_STOCK_BUY) * self.cost_on
        u = value / px
        self.lots[inst].append([u, px, d])
        self.units[inst] += u
        self.cash -= value + c
        self.costs += c

    def sell(self, inst, value, px, d):
        u = min(value / px, self.units[inst])
        if u <= 0:
            return
        c = u * px * (COST_MF_SELL if inst in (IDX, LIQ) else COST_STOCK_SELL) * self.cost_on
        self.units[inst] -= u
        self.cash += u * px - c
        self.costs += c
        q = self.lots[inst]
        while u > 1e-12 and q:
            lot = q[0]
            take = min(u, lot[0])
            g = take * (px - lot[1])
            if self.kind(inst) == "debt":
                self.slab += g
            elif (d - lot[2]).days > 365:
                self.lt += g
            else:
                self.st += g
            lot[0] -= take
            u -= take
            if lot[0] <= 1e-12:
                q.popleft()

    def passthrough(self, inst, gain_per_unit: float, long_term: bool):
        """A realised gain inside a sleeve: taxable now in proportion to units held; basis steps up by the same."""
        u = self.units[inst]
        if u <= 0 or gain_per_unit == 0:
            return
        if long_term:
            self.lt += u * gain_per_unit
        else:
            self.st += u * gain_per_unit
        for lot in self.lots[inst]:
            lot[1] += gain_per_unit

    def settle(self, d) -> float:
        stl, stg = max(-self.st, 0) + self.cf_st, max(self.st, 0)
        ltl, ltg = max(-self.lt, 0) + self.cf_lt, max(self.lt, 0)
        x = min(ltl, ltg); ltg -= x; ltl -= x
        x = min(stl, stg); stg -= x; stl -= x
        x = min(stl, ltg); ltg -= x; stl -= x
        tax = STCG * stg + LTCG * max(ltg - LTCG_EXEMPT, 0) + SLAB * max(self.slab, 0)
        self.cf_st, self.cf_lt = stl, ltl
        self.st = self.lt = self.slab = 0.0
        if not self.tax_on:
            tax = 0.0
        self.cash -= tax
        self.tax_paid.append((str(d.date()), round(tax, 2)))
        return tax

    def value(self, prices: dict) -> float:
        return self.cash + sum(u * prices[i] for i, u in self.units.items() if u > 0)

    def retarget(self, targets: dict, prices: dict, d):
        """Trade every instrument to its target value: sells first, then buys; book cash is the residual."""
        cur = {i: self.units[i] * prices[i] for i in set(self.units) | set(targets) if i != CASH}
        for i, v in cur.items():
            t = targets.get(i, 0.0)
            if v > t + 1e-6:
                self.sell(i, v - t, prices[i], d)
        for i, v in cur.items():
            t = targets.get(i, 0.0)
            if t > v + 1e-6:
                self.buy(i, t - v, prices[i], d)


def price_series(idx: pd.DatetimeIndex):
    tri = pd.read_csv(TRI, parse_dates=["date"]).set_index("date")["tri"].astype(float)
    r = tri.pct_change().reindex(idx).fillna(0.0)
    index_px = (1 + r - TER_INDEX / 252).cumprod() * 100
    liq_px = pd.Series(((1 + RF_D) * (1 - TER_LIQUID / 252)) ** np.arange(len(idx)), index=idx) * 100
    return index_px, liq_px, r


def sleeves(d: dict, idx: pd.DatetimeIndex):
    """Sleeve unit prices (each book's pre-tax NAV) and the books' realised gains by session and character."""
    def nav(s):
        s = s.copy()
        s.index = pd.DatetimeIndex(s.index).normalize()
        return s[~s.index.duplicated(keep="last")].reindex(idx).ffill()
    px_m, px_s = nav(d["momentum"]), nav(d["swing"])

    def snap(dates):                                    # an exit off the session calendar books on the next session
        pos = idx.searchsorted(pd.DatetimeIndex(dates).normalize())
        return [idx[i] if i < len(idx) else None for i in pos]
    mt = d["momentum_trades"].copy()
    mt["ed"], mt["xd"] = pd.to_datetime(mt["entry_date"]), pd.to_datetime(mt["exit_date"])
    mt = mt[(mt["xd"] >= idx[0]) & (mt["xd"] <= idx[-1])]
    mt["lt"] = (mt["xd"] - mt["ed"]).dt.days > 365
    mt["day"] = snap(mt["xd"])
    led = d["swing_ledger"].copy()
    led = led[led["reason"] != "eos"]
    led["ed"], led["xd"] = pd.to_datetime(led["entry_date"]), pd.to_datetime(led["exit_date"])
    led = led[(led["xd"] >= idx[0]) & (led["xd"] <= idx[-1])]
    led["lt"] = (led["xd"] - led["ed"]).dt.days > 365
    led["day"] = snap(led["xd"])
    gains = defaultdict(list)
    for r in mt.dropna(subset=["day"]).itertuples():
        gains[r.day].append((MOM, float(r.pnl), bool(r.lt)))
    for r in led.dropna(subset=["day"]).itertuples():
        gains[r.day].append((SW, float(r.net_pnl), bool(r.lt)))
    info = {"momentum_trades_in_window": int(len(mt)), "momentum_lt_share_of_trades": round(float(mt["lt"].mean()), 3),
            "momentum_realised_pnl": round(float(mt["pnl"].sum()), 0),
            "swing_trades_in_window": int(len(led)), "swing_lt_trades": int(led["lt"].sum()),
            "swing_realised_pnl": round(float(led["net_pnl"].sum()), 0)}
    return px_m, px_s, gains, info


def run(kind: str, idx, px_index, px_liq, expo=None, px_m=None, px_s=None, gains=None, weight=None,
        tax_on=True, cost_on=True) -> dict:
    b = Book(tax_on, cost_on)
    b.cash = CAPITAL
    navs = []
    fy_last = {fy_end(dd): dd for dd in idx}            # last session of each FY in the window
    pay_days = {v for k, v in fy_last.items() if v != idx[-1]}

    def prices_at(k):
        pr = {IDX: float(px_index.iloc[k]), LIQ: float(px_liq.iloc[k])}
        if px_m is not None:
            pr[MOM], pr[SW] = float(px_m.iloc[k]), float(px_s.iloc[k])
        return pr
    for k, dd in enumerate(idx):
        prices = prices_at(k)
        if kind == "blend" and gains:
            for inst, g, lt in gains.get(dd, ()):
                b.passthrough(inst, g, lt)
        if dd in pay_days:
            b.settle(dd)
        nav = b.value(prices)
        if k == 0 or dd in pay_days or kind in ("blend", "index_vt"):
            if kind == "blend":
                e = float(expo.iloc[k])
                tg = {MOM: nav * e * 0.70, SW: nav * e * 0.30, LIQ: nav * (1 - e)}
            elif kind == "index_vt":
                e = float(expo.iloc[k])
                tg = {IDX: nav * e, LIQ: nav * (1 - e)}
            else:
                tg = {IDX: nav * weight, LIQ: nav * (1 - weight)}
            b.retarget(tg, prices, dd)
        navs.append(b.value(prices))
    mtm = pd.Series(navs, index=idx)
    prices = prices_at(len(idx) - 1)
    for i in list(b.units):
        if b.units[i] > 0:
            b.sell(i, b.units[i] * prices[i], prices[i], idx[-1])
    b.settle(idx[-1])
    return {"mtm": mtm, "liquidation_value": b.cash, "tax_paid": b.tax_paid, "costs": b.costs}


def metrics(res: dict) -> dict:
    n = res["mtm"]
    yrs = (n.index[-1] - n.index[0]).days / 365.25
    r = n.pct_change().dropna()
    w = C.weekly_returns(n).to_numpy()
    dd = B.boot_dd(w, 156, 8)
    return {"after_tax_cagr_liquidation_pct": round(((res["liquidation_value"] / CAPITAL) ** (1 / yrs) - 1) * 100, 2),
            "after_tax_cagr_mtm_taxes_to_date_pct": round(((n.iloc[-1] / CAPITAL) ** (1 / yrs) - 1) * 100, 2),
            "sharpe_excess": round(float((r.mean() - RF_D) / r.std() * np.sqrt(252)), 3),
            "boot156_p95_b8": round(float(np.percentile(dd, 95)), 2),
            "worst_daily_dd_pct": round(float((n / n.cummax() - 1).min() * 100), 2),
            "tax_total": round(sum(t for _, t in res["tax_paid"]), 0), "tax_by_fy": res["tax_paid"],
            "trading_costs": round(res["costs"], 0), "liquidation_value": round(res["liquidation_value"], 0)}


def main() -> int:
    d = B.navs()
    mo = d["momentum_metrics"]
    if (round(mo["cagr_pct"], 2), round(mo["sharpe"], 3)) != (21.73, 1.13):
        raise SystemExit("0001 anchor mismatch: stop")
    rm, rs = B.window(d["momentum"]).pct_change().dropna(), B.window(d["swing"]).pct_change().dropna()
    r_bl, expo_bl = C.vol_target_blend(rm, rs, target=0.11)
    idx = pd.DatetimeIndex(r_bl.index).normalize()
    expo_bl.index = idx
    px_index, px_liq, r_tri = price_series(idx)
    vol = r_tri.rolling(20).std().shift(1) * np.sqrt(252)
    expo_ix = (0.11 / vol).clip(upper=1.0).fillna(1.0)
    px_m, px_s, gains, ginfo = sleeves(d, idx)
    out = {"window": [str(idx[0].date()), str(idx[-1].date())], "capital": CAPITAL,
           "assumptions": {"slab_liquid": SLAB, "ter_index": TER_INDEX, "ter_liquid": TER_LIQUID,
                           "stock_cost_buy": COST_STOCK_BUY, "stock_cost_sell": COST_STOCK_SELL},
           "blend_realised_inside_books": ginfo}
    books = {}
    books["a_blend_vt11"] = run("blend", idx, px_index, px_liq, expo=expo_bl, px_m=px_m, px_s=px_s, gains=gains)
    books["b_index_vt11"] = run("index_vt", idx, px_index, px_liq, expo=expo_ix)
    books["c_static_60_40"] = run("static", idx, px_index, px_liq, weight=0.60)
    books["d_static_65_35"] = run("static", idx, px_index, px_liq, weight=0.65)
    out["after_tax"] = {k: metrics(v) for k, v in books.items()}
    # pre-tax runs (reconciliation and tax drag)
    pre = {"a_blend_vt11": run("blend", idx, px_index, px_liq, expo=expo_bl, px_m=px_m, px_s=px_s, gains=gains, tax_on=False),
           "b_index_vt11": run("index_vt", idx, px_index, px_liq, expo=expo_ix, tax_on=False),
           "c_static_60_40": run("static", idx, px_index, px_liq, weight=0.60, tax_on=False),
           "d_static_65_35": run("static", idx, px_index, px_liq, weight=0.65, tax_on=False)}
    out["pre_tax_sim"] = {k: {kk: v for kk, v in metrics(x).items() if kk in ("after_tax_cagr_liquidation_pct", "sharpe_excess", "boot156_p95_b8", "trading_costs")}
                          for k, x in pre.items()}
    # reconciliation target: return-series blend at 11% with the 6.5% liquid cash
    idx2 = rm.index.intersection(rs.index)
    raw = 0.7 * rm.reindex(idx2).fillna(0) + 0.3 * rs.reindex(idx2).fillna(0)
    v = raw.rolling(20).std().shift(1) * np.sqrt(252)
    e = (0.11 / v).clip(upper=1.0).fillna(1.0)
    rr = e * raw + (1 - e) * (((1 + RF_D) * (1 - TER_LIQUID / 252)) - 1)
    yrs = (rr.index[-1] - rr.index[0]).days / 365.25
    nocost = run("blend", idx, px_index, px_liq, expo=expo_bl, px_m=px_m, px_s=px_s, gains=gains, tax_on=False, cost_on=False)
    out["reconciliation"] = {"lot_sim_pre_tax_no_blend_costs_cagr_pct": metrics(nocost)["after_tax_cagr_liquidation_pct"],"return_series_blend_vt11_cagr_pct": round(((1 + rr).prod() ** (1 / yrs) - 1) * 100, 2),
                             "lot_sim_pre_tax_cagr_pct": out["pre_tax_sim"]["a_blend_vt11"]["after_tax_cagr_liquidation_pct"]}
    # ADDED AFTER FIRST LOOK (2026-11-18): the blend-level trading costs (daily 70/30 + exposure moves at stock rates,
    # Rs 2.4L pre-tax) were the largest single drag and rest on an assumed 0.10% slippage. The same blend with those
    # costs off (each book's own engine costs only) is reported as the bound; it is not eligible for "winner".
    out["added_after_first_look"] = {"a_blend_vt11_no_blend_level_costs": metrics(run(
        "blend", idx, px_index, px_liq, expo=expo_bl, px_m=px_m, px_s=px_s, gains=gains, cost_on=False))}
    ok = {k: v for k, v in out["after_tax"].items() if v["boot156_p95_b8"] <= 25.0}
    out["winner_rule"] = "highest after-tax liquidation CAGR among books with after-tax 156w p95 (block 8) <= 25%"
    out["winner"] = max(ok, key=lambda k: ok[k]["after_tax_cagr_liquidation_pct"]) if ok else None
    OUT_JSON.write_text(json.dumps(out, indent=1, default=str) + "\n", encoding="utf-8")
    slim = {k: v for k, v in out.items() if k != "after_tax"}
    slim["after_tax"] = {k: {kk: vv for kk, vv in v.items() if kk != "tax_by_fy"} for k, v in out["after_tax"].items()}
    print(json.dumps(slim, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
