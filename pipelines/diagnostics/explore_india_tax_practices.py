"""MEASUREMENT: after-tax value of standard Indian tax practices for the fallback books (analysis only, NOT tax advice).

Owner request 2026-11-18, branch research/india-tax-practices. Changes nothing live; no trial; no sealed read.

PARAMETERS  config/tax_india_fy2627.yaml (every value marked CONFIRM WITH CA). FY 2026-27 rules applied to the whole
            2019-03-05..2024-06-28 window. Rs 20,00,000 invested at the first close; everything sold at the last.

SIMULATOR   the lot-by-lot engine of explore_after_tax_comparison.py, generalised (same price series, same sleeve
            pass-through for the blend, same FIFO lots, same order on a tax day: [harvest] -> tax -> re-target, with the
            re-target's own gains falling into the next FY). New here:
  entity      individual (marginal slab m) or company. An individual's debt (liquid-fund) gains are taxed through the
              new-regime slab table on top of an assumed other income that puts the person at slab m: m = 0% -> other
              income 0; 5% -> Rs 6L; 30% -> Rs 30L (Kreesh). tax_debt = slabtax(other + gains) - slabtax(other).
              Equity: STCG 20%; LTCG 12.5% on the FY's LT gains above Rs 1.25L. A person at slab 0% also sets the unused
              basic exemption (Rs 4L - other income - debt gains) against STCG then LTCG (config flag). Surcharge
              (default 0) on all of it, capped at 15% on capital gains; cess 4% on the total.
              Company (s.115BAA): debt gains at 25.17%; STCG and LTCG at 20% / 12.5% x (1 + 10% surcharge) x (1 + 4% cess);
              no Rs 1.25L exemption by default; Rs 75,000 compliance a FY, pro-rated by the share of the FY inside the
              window, paid from cash each March (not deductible).
  losses      current-year LTCL vs LTCG; STCL vs STCG then LTCG; then brought-forward losses oldest first under the
              same rules; unused losses carry forward and lapse after 8 FYs. Debt losses are not carried (none arise).
  cash leg    S0 liquid fund (debt): 6.5% gross less 0.15% expense ratio. S1+ arbitrage fund (equity): the liquid fund's
              net return less 0.3% a year (PROXY: the Nifty 50 Arbitrage Index TRI could not be fetched on 2026-11-18),
              less a further 0.3% a year from 2026-04-01 (inert in this window).
  harvesting  S2+: in March, BEFORE tax. FIRST LOOK harvested on the 31-March tax day itself; a lot bought back there
              is sold by the next 31-March rebalance after exactly 365 days, i.e. SHORT-term, which made harvesting
              lose money (S1 -> S2 = -Rs 40.5k on 60/40). ADDED AFTER FIRST LOOK: harvest on the first session on or
              after 15 March (still that FY, still "each March"); the tax-day variant is reported beside it. Then: (1) every equity lot below cost is sold and bought back the same
              day (new lot, new date); (2) long-term lots in gain are sold oldest first, partially if needed, until the
              FY's taxable long-term gain after set-off reaches the exemption (Rs 1.25L; a company with no exemption does
              not gain-harvest), and bought back. Both legs pay the instrument's trading costs.
  family      S3: capital split equally across N adult PANs (Kreesh + N-1 others, all others at the same slab), each a
              separate taxpayer running the same book; values summed. The money is an IRREVOCABLE GIFT to each person.
              Gifts to a spouse (or son's wife) are clubbed back to the donor (s.64), so this models adult children or
              parents only.
  company     S4: S2 run by a company funded by retained profits. Reported without and with a final dividend of the
              whole liquidation value to Kreesh at 35.88%. ADDED SCOPE (stated before results, not in the request): a
              like-for-like row - pay the Rs 20L out as a dividend today, invest the after-dividend Rs 12.82L personally
              under S2 - because retained profits and personal money are not the same rupee.

BOOKS  static 60/40 and 65/35 (Midcap150 Momentum 50 index fund + cash leg, re-weighted each March after tax); the 70/30
       blend at 11% for reference (sleeve units + cash leg, re-targeted daily).

METRICS  after-tax CAGR = final value ** (365.25 / days) - 1; final value; total tax; trading costs; fund expenses
         (expense ratio accrued on holdings); compliance; 156-week p95 drawdown of the after-tax mark-to-market NAV
         (stationary bootstrap, mean block 8 weeks, 10,000 draws; S3 = the summed household NAV).
STEP VALUE  final value of each scenario minus the one before (S0 -> S1 -> S2 -> S3 -> S4).
SENSITIVITY  each rate default +/- 5 percentage points (floored at 0) and each cost +/- 50%, one at a time; reported is
         whether the ranking of the 60/40 scenarios and of the books at S2 changes.
ANCHOR   S0 with cess 0 reproduces explore_after_tax_comparison (60/40 21.76%, 65/35 23.02%, blend 19.26%).
BREAK-EVEN  the capital at which S4 (without / with the final dividend) equals S2's final value as a multiple of
         capital, by bisection on log capital between Rs 20L and Rs 500 crore; the individual's surcharge is held at the
         config value (it would rise above Rs 50L of income - stated, not modelled).

    python pipelines/diagnostics/explore_india_tax_practices.py
"""
from __future__ import annotations

import copy
import json
import sys
from collections import defaultdict, deque
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts"), str(ROOT / "pipelines" / "research"),
                str(ROOT / "pipelines" / "diagnostics"), str(ROOT / "pipelines" / "lifecycle")]
import core as C  # noqa: E402
import explore_after_tax_comparison as AT  # noqa: E402
import explore_blend_drawdown_sizing as B  # noqa: E402

CFG = ROOT / "config" / "tax_india_fy2627.yaml"
OUT_JSON = ROOT / "diagnostics" / "research" / "explore" / "2026-11-18_india_tax_practices.json"
CAPITAL = 2_000_000.0
LIQ, ARB, IDX, MOM, SW = "_LIQUID", "_ARBITRAGE", "_INDEXFUND", "_MOM", "_SW"
HARVEST_DAY = "mid_march"   # ADDED AFTER FIRST LOOK (see docstring); "tax_day" was the first-look schedule
EQUITY = {ARB, IDX, MOM, SW}
OTHER_INCOME = {0.0: 0.0, 0.05: 600_000.0, 0.30: 3_000_000.0}


def load_cfg() -> dict:
    return yaml.safe_load(CFG.read_text(encoding="utf-8"))


def slabtax(income: float, slabs) -> float:
    t, lo = 0.0, 0.0
    for hi, r in slabs:
        top = income if hi is None else min(income, hi)
        if top > lo:
            t += (top - lo) * r
        if hi is None or income <= hi:
            break
        lo = hi
    return t


def fy_of(d: pd.Timestamp) -> int:
    return d.year + 1 if d.month > 3 else d.year


class Taxpayer:
    def __init__(self, cfg: dict, kind: str = "individual", slab: float = 0.30, harvest: bool = False):
        self.c, self.kind, self.slab, self.harvest_on = cfg, kind, slab, harvest
        self.lots: dict[str, deque] = defaultdict(deque)
        self.units: dict[str, float] = defaultdict(float)
        self.cash = 0.0
        self.st = self.lt = self.debt = 0.0
        self.cf_st: list[list] = []          # [fy, amount] brought-forward short-term losses
        self.cf_lt: list[list] = []
        self.tax_paid: list = []
        self.costs = self.compliance = self.fund_exp = 0.0
        ins = cfg["instruments"]
        self.cost = {LIQ: (ins["mf_costs"]["buy"], ins["mf_costs"]["sell"]), ARB: (ins["mf_costs"]["buy"], ins["mf_costs"]["sell"]),
                     IDX: (ins["mf_costs"]["buy"], ins["mf_costs"]["sell"]),
                     MOM: (ins["stock_costs"]["buy"], ins["stock_costs"]["sell"]), SW: (ins["stock_costs"]["buy"], ins["stock_costs"]["sell"])}
        self.lt_days = cfg["equity"]["long_term_days"]

    # ---- trading
    def buy(self, inst, value, px, d):
        if value <= 0:
            return
        c = value * self.cost[inst][0]
        u = value / px
        self.lots[inst].append([u, px, d])
        self.units[inst] += u
        self.cash -= value + c
        self.costs += c

    def _book(self, inst, g, buy_d, d):
        if inst not in EQUITY:
            self.debt += g
        elif (d - buy_d).days > self.lt_days:
            self.lt += g
        else:
            self.st += g

    def sell(self, inst, value, px, d):
        u = min(value / px, self.units[inst])
        if u <= 0:
            return
        c = u * px * self.cost[inst][1]
        self.units[inst] -= u
        self.cash += u * px - c
        self.costs += c
        q = self.lots[inst]
        while u > 1e-12 and q:
            lot = q[0]
            take = min(u, lot[0])
            self._book(inst, take * (px - lot[1]), lot[2], d)
            lot[0] -= take
            u -= take
            if lot[0] <= 1e-12:
                q.popleft()

    def passthrough(self, inst, g, long_term):
        u = self.units[inst]
        if u <= 0 or g == 0:
            return
        if long_term:
            self.lt += u * g
        else:
            self.st += u * g
        for lot in self.lots[inst]:
            lot[1] += g

    def value(self, prices) -> float:
        return self.cash + sum(u * prices[i] for i, u in self.units.items() if u > 0)

    def retarget(self, targets, prices, d):
        cur = {i: self.units[i] * prices[i] for i in set(self.units) | set(targets)}
        for i, v in cur.items():
            t = targets.get(i, 0.0)
            if v > t + 1e-6:
                self.sell(i, v - t, prices[i], d)
        for i, v in cur.items():
            t = targets.get(i, 0.0)
            if t > v + 1e-6:
                self.buy(i, t - v, prices[i], d)

    # ---- tax
    def _exemption(self) -> float:
        if self.kind == "company":
            return self.c["equity"]["ltcg_exemption"] if self.c["company"]["ltcg_exemption_applies"] else 0.0
        return self.c["equity"]["ltcg_exemption"]

    def _setoff(self, fy, commit: bool):
        """Taxable (st, lt) after current-year and brought-forward set-off. commit=True updates the carry-forward."""
        st, lt = self.st, self.lt
        stl, stg = max(-st, 0.0), max(st, 0.0)
        ltl, ltg = max(-lt, 0.0), max(lt, 0.0)
        x = min(ltl, ltg); ltg -= x; ltl -= x
        x = min(stl, stg); stg -= x; stl -= x
        x = min(stl, ltg); ltg -= x; stl -= x
        keep = self.c["losses"]["carry_forward_years"]
        cf_st = [[f, a] for f, a in self.cf_st if fy - f <= keep and a > 0]
        cf_lt = [[f, a] for f, a in self.cf_lt if fy - f <= keep and a > 0]
        for e in cf_lt:                                     # brought-forward LTCL vs LTCG only
            x = min(e[1], ltg); ltg -= x; e[1] -= x
        for e in cf_st:                                     # brought-forward STCL vs STCG then LTCG
            x = min(e[1], stg); stg -= x; e[1] -= x
            x = min(e[1], ltg); ltg -= x; e[1] -= x
        if commit:
            self.cf_st = [e for e in cf_st if e[1] > 1e-9] + ([[fy, stl]] if stl > 0 else [])
            self.cf_lt = [e for e in cf_lt if e[1] > 1e-9] + ([[fy, ltl]] if ltl > 0 else [])
        return stg, ltg

    def taxable_lt_before_exemption(self, fy) -> float:
        saved = (copy.deepcopy(self.cf_st), copy.deepcopy(self.cf_lt))
        _, ltg = self._setoff(fy, commit=False)
        self.cf_st, self.cf_lt = saved
        return ltg

    def settle(self, d, fy_fraction: float = 1.0) -> float:
        fy = fy_of(d)
        stg, ltg = self._setoff(fy, commit=True)
        eq = self.c["equity"]
        if self.kind == "company":
            co = self.c["company"]
            mult = (1 + co["surcharge"]) * (1 + co["cess"])
            tax = co["rate_on_debt_income"] * max(self.debt, 0) + mult * (eq["stcg"] * stg + eq["ltcg"] * max(ltg - self._exemption(), 0))
            comp = co["annual_compliance"] * fy_fraction
            self.cash -= comp
            self.compliance += comp
        else:
            ind = self.c["individual"]
            debt = max(self.debt, 0)
            if round(self.slab, 2) in OTHER_INCOME:          # the three named slabs: through the slab table
                other = OTHER_INCOME[round(self.slab, 2)]
                t_debt = slabtax(other + debt, ind["slabs"]) - slabtax(other, ind["slabs"])
            else:                                            # a sensitivity value (e.g. 25%, 35%): flat marginal rate
                other = 3_000_000.0
                t_debt = self.slab * debt
            ltg_t = max(ltg - eq["ltcg_exemption"], 0)
            if ind["use_unexhausted_basic_exemption"] and self.slab == 0.0:
                head = max(ind["slabs"][0][0] - other - debt, 0)
                x = min(head, stg); stg -= x; head -= x
                x = min(head, ltg_t); ltg_t -= x
            t_cg = eq["stcg"] * stg + eq["ltcg"] * ltg_t
            sur = ind["surcharge_on_cg"]
            tax = (t_debt * (1 + sur) + t_cg * (1 + min(sur, ind["surcharge_cap_on_cg"]))) * (1 + ind["cess"])
        self.st = self.lt = self.debt = 0.0
        self.cash -= tax
        self.tax_paid.append((str(d.date()), round(tax, 2)))
        return tax

    def harvest(self, prices, d):
        fy = fy_of(d)
        for inst in [i for i in self.lots if i in EQUITY]:                  # losses: every equity lot below cost
            px = prices[inst]
            keep, rebought = deque(), []
            for lot in self.lots[inst]:
                if lot[0] > 0 and px < lot[1]:
                    u = lot[0]
                    self._book(inst, u * (px - lot[1]), lot[2], d)
                    c = u * px * (self.cost[inst][0] + self.cost[inst][1])
                    self.cash -= c
                    self.costs += c
                    rebought.append([u, px, d])
                else:
                    keep.append(lot)
            keep.extend(rebought)            # a buy-back is the NEWEST lot: last in FIFO order
            self.lots[inst] = keep
        room = self._exemption() - self.taxable_lt_before_exemption(fy)        # gains: up to the exemption
        if room <= 0:
            return
        for inst in [i for i in self.lots if i in EQUITY]:
            px = prices[inst]
            new, rebought = deque(), []
            for lot in self.lots[inst]:
                g_unit = px - lot[1]
                if room > 0 and g_unit > 0 and (d - lot[2]).days > self.lt_days:
                    u = min(lot[0], room / g_unit)
                    self.lt += u * g_unit
                    room -= u * g_unit
                    c = u * px * (self.cost[inst][0] + self.cost[inst][1])
                    self.cash -= c
                    self.costs += c
                    if lot[0] - u > 1e-12:
                        new.append([lot[0] - u, lot[1], lot[2]])
                    rebought.append([u, px, d])
                else:
                    new.append(lot)
            new.extend(rebought)             # a buy-back is the NEWEST lot: last in FIFO order
            self.lots[inst] = new


def cash_prices(idx, cfg):
    ins = cfg["instruments"]
    rf_d = (1 + ins["liquid"]["gross_return"]) ** (1 / 252) - 1
    liq_r = (1 + rf_d) * (1 - ins["liquid"]["ter"] / 252) - 1
    arb_r = pd.Series(liq_r - ins["arbitrage"]["liquid_minus"] / 252, index=idx)
    arb_r[idx >= pd.Timestamp(ins["arbitrage"]["stt_drag_from"])] -= ins["arbitrage"]["stt_drag"] / 252
    liq = pd.Series(100 * (1 + liq_r) ** np.arange(len(idx)), index=idx)
    arb = 100 * (1 + arb_r).cumprod() / (1 + arb_r.iloc[0])
    return liq, arb


def index_price(idx, cfg):
    tri = pd.read_csv(AT.TRI, parse_dates=["date"]).set_index("date")["tri"].astype(float)
    r = tri.pct_change().reindex(idx).fillna(0.0)
    return (1 + r - cfg["instruments"]["index_fund"]["ter"] / 252).cumprod() * 100


def simulate(book: str, cfg: dict, ctx: dict, *, kind="individual", slab=0.30, cash_leg=LIQ, harvest=False,
             capital=CAPITAL, harvest_day: str = "tax_day") -> dict:
    idx = ctx["idx"]
    tp = Taxpayer(cfg, kind, slab, harvest)
    tp.cash = capital
    px_idx, px_liq, px_arb = ctx["px_index"][id(cfg)], ctx["px_liq"][id(cfg)], ctx["px_arb"][id(cfg)]
    ter = {IDX: cfg["instruments"]["index_fund"]["ter"], LIQ: cfg["instruments"]["liquid"]["ter"],
           ARB: cfg["instruments"]["liquid"]["ter"] + cfg["instruments"]["arbitrage"]["liquid_minus"]}
    fy_last = {}
    for dd in idx:
        fy_last[fy_of(dd)] = dd
    pay = {v for v in fy_last.values() if v != idx[-1]}
    fy_days = {fy: ((min(pd.Timestamp(year=fy, month=3, day=31), idx[-1]) - max(pd.Timestamp(year=fy - 1, month=4, day=1), idx[0])).days + 1) / 365.0
               for fy in fy_last}
    if harvest_day == "mid_march":       # first session on/after 15 March, strictly before that FY's tax day
        hdays = {idx[idx >= pd.Timestamp(year=p.year, month=3, day=15)][0] for p in pay}
    else:
        hdays = set(pay)
    navs = []
    for k, dd in enumerate(idx):
        pr = {IDX: float(px_idx.iloc[k]), LIQ: float(px_liq.iloc[k]), ARB: float(px_arb.iloc[k]),
              MOM: float(ctx["px_m"].iloc[k]), SW: float(ctx["px_s"].iloc[k])}
        tp.fund_exp += sum(tp.units[i] * pr[i] * ter[i] / 252 for i in ter if tp.units[i] > 0)
        if book == "blend":
            for inst, g, lt in ctx["gains"].get(dd, ()):
                tp.passthrough(inst, g, lt)
        if harvest and dd in hdays:
            tp.harvest(pr, dd)
        if dd in pay:
            tp.settle(dd, fy_days[fy_of(dd)])
        nav = tp.value(pr)
        if book == "blend":
            e = float(ctx["expo"].iloc[k])
            tp.retarget({MOM: nav * e * 0.7, SW: nav * e * 0.3, cash_leg: nav * (1 - e)}, pr, dd)
        elif k == 0 or dd in pay:
            w = {"s60": 0.60, "s65": 0.65}[book]
            tp.retarget({IDX: nav * w, cash_leg: nav * (1 - w)}, pr, dd)
        navs.append(tp.value(pr))
    pr = {IDX: float(px_idx.iloc[-1]), LIQ: float(px_liq.iloc[-1]), ARB: float(px_arb.iloc[-1]),
          MOM: float(ctx["px_m"].iloc[-1]), SW: float(ctx["px_s"].iloc[-1])}
    for i in list(tp.units):
        if tp.units[i] > 0:
            tp.sell(i, tp.units[i] * pr[i], pr[i], idx[-1])
    tp.settle(idx[-1], fy_days[fy_of(idx[-1])])
    return {"mtm": pd.Series(navs, index=idx), "final": tp.cash, "tax": sum(t for _, t in tp.tax_paid),
            "costs": tp.costs, "fund_exp": tp.fund_exp, "compliance": tp.compliance, "capital": capital}


def household(parts: list[dict]) -> dict:
    return {"mtm": sum(p["mtm"] for p in parts), "final": sum(p["final"] for p in parts),
            "tax": sum(p["tax"] for p in parts), "costs": sum(p["costs"] for p in parts),
            "fund_exp": sum(p["fund_exp"] for p in parts), "compliance": sum(p["compliance"] for p in parts),
            "capital": sum(p["capital"] for p in parts)}


def summarise(r: dict, idx, *, dividend: float | None = None, boot=True) -> dict:
    yrs = (idx[-1] - idx[0]).days / 365.25
    final = r["final"] * (1 - dividend) if dividend else r["final"]
    out = {"final_value": round(final, 0), "after_tax_cagr_pct": round(((final / r["capital"]) ** (1 / yrs) - 1) * 100, 2),
           "tax": round(r["tax"] + (r["final"] * dividend if dividend else 0.0), 0), "trading_costs": round(r["costs"], 0),
           "fund_expenses": round(r["fund_exp"], 0), "compliance": round(r["compliance"], 0)}
    if boot:
        out["boot156_p95_b8"] = round(float(np.percentile(B.boot_dd(C.weekly_returns(r["mtm"]).to_numpy(), 156, 8), 95)), 2)
    return out


def context(cfgs: list[dict]) -> dict:
    d = B.navs()
    rm, rs = B.window(d["momentum"]).pct_change().dropna(), B.window(d["swing"]).pct_change().dropna()
    _, expo = C.vol_target_blend(rm, rs, target=0.11)
    idx = pd.DatetimeIndex(expo.index).normalize()
    expo.index = idx
    px_m, px_s, gains, _ = AT.sleeves(d, idx)
    ctx = {"idx": idx, "expo": expo, "px_m": px_m, "px_s": px_s, "gains": gains, "px_index": {}, "px_liq": {}, "px_arb": {}}
    for c in cfgs:
        add_prices(ctx, c)
    return ctx


def add_prices(ctx, c):
    ctx["px_index"][id(c)] = index_price(ctx["idx"], c)
    ctx["px_liq"][id(c)], ctx["px_arb"][id(c)] = cash_prices(ctx["idx"], c)


def scenarios(book, cfg, ctx, *, boot=True, family=True, capital=CAPITAL) -> dict:
    idx = ctx["idx"]
    owner = cfg["individual"]["owner_marginal_slab"]
    s = {}
    s["S0"] = simulate(book, cfg, ctx, slab=owner, cash_leg=LIQ, capital=capital)
    s["S1"] = simulate(book, cfg, ctx, slab=owner, cash_leg=ARB, capital=capital)
    s["S2"] = simulate(book, cfg, ctx, slab=owner, cash_leg=ARB, harvest=True, harvest_day=HARVEST_DAY, capital=capital)
    if family:
        for n in (2, 3):
            for sl in cfg["family"]["extra_person_slabs"]:
                parts = [simulate(book, cfg, ctx, slab=owner, cash_leg=ARB, harvest=True, harvest_day=HARVEST_DAY, capital=capital / n)]
                parts += [simulate(book, cfg, ctx, slab=sl, cash_leg=ARB, harvest=True, harvest_day=HARVEST_DAY, capital=capital / n) for _ in range(n - 1)]
                s[f"S3_N{n}_slab{int(sl * 100)}"] = household(parts)
    s["S4"] = simulate(book, cfg, ctx, kind="company", cash_leg=ARB, harvest=True, harvest_day=HARVEST_DAY, capital=capital)
    div = cfg["company"]["dividend_rate_to_owner"]
    out = {k: summarise(v, idx, boot=boot) for k, v in s.items()}
    out["S4_with_final_dividend"] = summarise(s["S4"], idx, dividend=div, boot=boot)
    # added scope: like-for-like retained-profits comparison (dividend now, then S2 personally)
    now = simulate(book, cfg, ctx, slab=owner, cash_leg=ARB, harvest=True, harvest_day=HARVEST_DAY, capital=capital * (1 - div))
    o = summarise(now, idx, boot=boot)
    o["after_tax_cagr_pct_on_pre_dividend_capital"] = round(((now["final"] / capital) ** (365.25 / (idx[-1] - idx[0]).days) - 1) * 100, 2)
    out["S2_after_dividend_today_like_for_like"] = o
    return out


def break_even(book, cfg, ctx, with_div: bool) -> float | None:
    div = cfg["company"]["dividend_rate_to_owner"]

    def gap(cap):
        s2 = simulate(book, cfg, ctx, slab=cfg["individual"]["owner_marginal_slab"], cash_leg=ARB, harvest=True, harvest_day=HARVEST_DAY, capital=cap)
        s4 = simulate(book, cfg, ctx, kind="company", cash_leg=ARB, harvest=True, harvest_day=HARVEST_DAY, capital=cap)
        return s4["final"] * ((1 - div) if with_div else 1.0) / cap - s2["final"] / cap
    lo, hi = np.log(2e6), np.log(5e9)
    glo, ghi = gap(np.exp(lo)), gap(np.exp(hi))
    if glo >= 0:
        return float(np.exp(lo))
    if ghi < 0:
        return None
    for _ in range(30):
        mid = (lo + hi) / 2
        if gap(np.exp(mid)) >= 0:
            hi = mid
        else:
            lo = mid
    return float(np.exp(hi))


def ranking(res: dict, keys) -> list[str]:
    return sorted(keys, key=lambda k: -res[k]["final_value"])


def main() -> int:
    base = load_cfg()
    anchor_cfg = copy.deepcopy(base)
    anchor_cfg["individual"]["cess"] = 0.0
    ctx = context([base, anchor_cfg])
    idx = ctx["idx"]
    # ---- anchor (rule 4): S0 with cess 0 = the earlier lot-level study
    anc = {b: summarise(simulate(b, anchor_cfg, ctx, slab=0.30, cash_leg=LIQ), idx, boot=False)["after_tax_cagr_pct"]
           for b in ("s60", "s65", "blend")}
    print("ANCHOR", anc, flush=True)
    if (anc["s60"], anc["s65"], anc["blend"]) != (21.76, 23.02, 19.26):
        raise SystemExit("anchor mismatch vs explore_after_tax_comparison: stop")
    res = {"window": [str(idx[0].date()), str(idx[-1].date())], "capital": CAPITAL, "config": str(CFG.relative_to(ROOT)),
           "status": base["status"], "anchor_S0_cess0": anc,
           "proxies": {"liquid": "6.5% gross less 0.15% TER (no liquid-fund index in repo)",
                       "arbitrage": "liquid net less 0.3%/yr (Nifty 50 Arbitrage TRI not retrievable 2026-11-18)"}}
    res["harvest_schedule"] = HARVEST_DAY
    res["first_look_same_day_harvest_S2"] = {}
    for b in ("s60", "s65", "blend"):
        r1 = summarise(simulate(b, base, ctx, slab=0.30, cash_leg=ARB, capital=CAPITAL), idx, boot=False)
        r2 = summarise(simulate(b, base, ctx, slab=0.30, cash_leg=ARB, harvest=True, harvest_day="tax_day", capital=CAPITAL), idx, boot=False)
        res["first_look_same_day_harvest_S2"][b] = {"S1": r1["final_value"], "S2_tax_day_harvest": r2["final_value"],
                                                   "step": round(r2["final_value"] - r1["final_value"], 0)}
    res["books"] = {}
    for b in ("s60", "s65", "blend"):
        r = scenarios(b, base, ctx)
        steps = {"S0->S1": r["S1"]["final_value"] - r["S0"]["final_value"],
                 "S1->S2": r["S2"]["final_value"] - r["S1"]["final_value"]}
        for k in r:
            if k.startswith("S3_"):
                steps[f"S2->{k}"] = r[k]["final_value"] - r["S2"]["final_value"]
        steps["S2->S4"] = r["S4"]["final_value"] - r["S2"]["final_value"]
        steps["S2->S4_with_final_dividend"] = r["S4_with_final_dividend"]["final_value"] - r["S2"]["final_value"]
        res["books"][b] = {"scenarios": r, "step_value_rupees": {k: round(v, 0) for k, v in steps.items()}}
        print(b, json.dumps({k: (v["after_tax_cagr_pct"], v["final_value"]) for k, v in r.items()}), flush=True)
    res["break_even_capital"] = {b: {"S4_vs_S2_no_dividend": break_even(b, base, ctx, False),
                                     "S4_vs_S2_with_final_dividend": break_even(b, base, ctx, True)} for b in ("s60", "s65")}
    # ADDED AFTER FIRST LOOK: with the config surcharge (0) S4 never breaks even, because every company rate is above
    # the individual's. The one route to a break-even is the individual's own surcharge at high income, so the search
    # is repeated with the individual at the 15% capital-gains surcharge cap (and 25% on slab income, new regime top).
    hi = copy.deepcopy(base)
    hi["individual"]["surcharge_on_cg"] = 0.25
    add_prices(ctx, hi)
    res["break_even_capital_individual_at_max_surcharge_added_after_first_look"] = {
        b: {"S4_vs_S2_no_dividend": break_even(b, hi, ctx, False),
            "S4_vs_S2_with_final_dividend": break_even(b, hi, ctx, True)} for b in ("s60", "s65")}
    print("BREAK-EVEN", res["break_even_capital"], flush=True)
    # ---- sensitivity: one at a time, static books, scenario ranking (60/40) and book ranking at S2
    rate_keys = [("equity", "stcg"), ("equity", "ltcg"), ("individual", "owner_marginal_slab"), ("individual", "cess"),
                 ("individual", "surcharge_on_cg"), ("company", "rate_on_debt_income"), ("company", "dividend_rate_to_owner"),
                 ("instruments", "liquid", "gross_return")]
    cost_keys = [("instruments", "index_fund", "ter"), ("instruments", "liquid", "ter"), ("instruments", "arbitrage", "liquid_minus"),
                 ("instruments", "mf_costs", "buy"), ("instruments", "mf_costs", "sell"), ("company", "annual_compliance")]
    scen_keys = ["S0", "S1", "S2", "S3_N3_slab0", "S4", "S4_with_final_dividend"]
    base_s60 = res["books"]["s60"]["scenarios"]
    base_rank = ranking(base_s60, scen_keys)
    base_books = ranking({"s60": base_s60["S2"], "s65": res["books"]["s65"]["scenarios"]["S2"]}, ["s60", "s65"])
    sens = []
    perturb = [(k, "rate", d) for k in rate_keys for d in (-0.05, 0.05)] + [(k, "cost", f) for k in cost_keys for f in (0.5, 1.5)]
    for key, typ, delta in perturb:
        c = copy.deepcopy(base)
        node = c
        for p in key[:-1]:
            node = node[p]
        old = node[key[-1]]
        node[key[-1]] = max(old + delta, 0.0) if typ == "rate" else old * delta
        add_prices(ctx, c)
        r60 = scenarios("s60", c, ctx, boot=False)
        r65 = scenarios("s65", c, ctx, boot=False)
        rk = ranking(r60, scen_keys)
        bk = ranking({"s60": r60["S2"], "s65": r65["S2"]}, ["s60", "s65"])
        sens.append({"param": ".".join(key), "from": old, "to": node[key[-1]],
                     "s60_scenario_ranking": rk, "scenario_ranking_changed": rk != base_rank, "top_changed": rk[0] != base_rank[0],
                     "book_ranking_at_S2": bk, "book_ranking_changed": bk != base_books,
                     "s60_S2_cagr": r60["S2"]["after_tax_cagr_pct"], "s60_S4_cagr": r60["S4"]["after_tax_cagr_pct"]})
        print("SENS", ".".join(key), node[key[-1]], rk[:3], bk, flush=True)
    res["sensitivity"] = {"base_s60_scenario_ranking": base_rank, "base_book_ranking_at_S2": base_books, "rows": sens}
    OUT_JSON.write_text(json.dumps(res, indent=1, default=str) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
