"""After-tax lot engine, copied VERBATIM from PR #212's simulator (pipelines/diagnostics/explore_india_tax_practices.py,
branch research/india-tax-practices, commit 259546d, which includes the 2026-11-19 hash-seed fix). Only `slabtax`,
`fy_of` and `Taxpayer` are copied, with the constants they use. The rest of that file depends on two other unmerged
modules. When #212 merges, replace this file with an import. Analysis only, not tax advice.
"""
from __future__ import annotations

import copy
from collections import defaultdict, deque
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
CFG = ROOT / "config" / "tax_india_fy2627.yaml"
LIQ, ARB, IDX, MOM, SW = "_LIQUID", "_ARBITRAGE", "_INDEXFUND", "_MOM", "_SW"
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
        # sorted: a float sum in dict-insertion order is not reproducible across hash seeds (2026-11-19 fix)
        return self.cash + sum(self.units[i] * prices[i] for i in sorted(self.units) if self.units[i] > 0)

    def retarget(self, targets, prices, d):
        # sorted, not set order: set iteration of strings depends on PYTHONHASHSEED, and the trade order fed the
        # lot-insertion order the harvest walked (#214 Correction 3; fixed 2026-11-19)
        cur = {i: self.units[i] * prices[i] for i in sorted(set(self.units) | set(targets))}
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
        for inst in sorted(i for i in self.lots if i in EQUITY):            # losses: every equity lot below cost
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
        # ORDER (fixed 2026-11-19; previously dict-insertion order, i.e. hash-seed dependent):
        #  * within a scheme: FIFO, oldest lot first - Indian mutual-fund redemptions are computed first-in-first-out,
        #    so the lot is not a free choice [assumed, CONFIRM WITH CA];
        #  * across schemes: highest unrealised gain per rupee redeemed on the scheme's oldest long-term lot first,
        #    then instrument name - it uses the exemption with the least money churned and the fewest units restarted
        #    on a new 12-month clock.
        def _key(i):
            px = prices[i]
            lt = [lot for lot in self.lots[i] if lot[0] > 0 and (d - lot[2]).days > self.lt_days]
            ratio = (px - lt[0][1]) / px if lt else float("-inf")
            return (-ratio, i)
        for inst in sorted((i for i in self.lots if i in EQUITY), key=_key):
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
