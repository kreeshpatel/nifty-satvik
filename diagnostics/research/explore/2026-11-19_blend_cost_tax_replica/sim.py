"""Independent replica of the after-tax 70/30 blend lot simulator, from SPEC.md only."""
import sys, json
from collections import deque
import numpy as np
import pandas as pd

HERE = "/tmp/claude-0/-home-user-nifty-satvik/26ce7f30-6a8b-5683-bd62-539ae0908694/scratchpad/replica"
CAP = 2_000_000.0
COSTS = {"MOM": (0.002190, 0.002040), "SW": (0.002190, 0.002040), "LIQ": (0.00005, 0.00001)}
WEIGHTS = {"MOM": 0.70, "SW": 0.30}

daily = pd.read_csv(f"{HERE}/inputs/daily.csv", parse_dates=["date"])
mt = pd.read_csv(f"{HERE}/inputs/momentum_trades.csv", parse_dates=["entry_date", "exit_date"])
sw = pd.read_csv(f"{HERE}/inputs/swing_ledger.csv", parse_dates=["entry_date", "exit_date"])
dates = list(daily["date"])
N = len(dates)
PX = {"MOM": daily["mom_nav"].values, "SW": daily["swing_nav"].values, "LIQ": daily["liquid_px"].values}
E = daily["exposure_e_t"].values


def bucket(d):
    if d <= 30: return "0-30"
    if d <= 90: return "31-90"
    if d <= 180: return "91-180"
    if d <= 330: return "181-330"
    if d <= 364: return "331-364"
    return "365+"


def map_trades(df, pnlcol, sleeve, shift_next=False):
    """Map each trade exit to session index. Non-session -> next session; after last -> dropped."""
    out = {}
    darr = np.array(dates, dtype="datetime64[ns]")
    for r in df.itertuples(index=False):
        ex = np.datetime64(r.exit_date)
        i = int(np.searchsorted(darr, ex, side="left"))
        if shift_next:
            if i < N and darr[i] == ex:
                i += 1
        if i >= N:
            continue
        hd = (r.exit_date - r.entry_date).days
        out.setdefault(i, []).append((sleeve, float(getattr(r, pnlcol)), hd))
    return out


def tax_days():
    s = set()
    years = sorted({d.year for d in dates})
    for y in years:
        cutoff = pd.Timestamp(y, 3, 31)
        cands = [i for i, d in enumerate(dates) if d <= cutoff]
        if cands and dates[cands[-1]].year == y:
            s.add(cands[-1])
    s.discard(N - 1)
    return s


def tax_days_april():
    s = set()
    years = sorted({d.year for d in dates})
    for y in years:
        cands = [i for i, d in enumerate(dates) if d >= pd.Timestamp(y, 4, 1)]
        if cands and dates[cands[0]].year == y:
            s.add(cands[0])
    s.discard(N - 1)
    return s


def settle(ST, LT, SL, cfST, cfLT, taxon=True):
    STloss = max(-ST, 0) + cfST; STgain = max(ST, 0)
    LTloss = max(-LT, 0) + cfLT; LTgain = max(LT, 0)
    m = min(LTloss, LTgain); LTloss -= m; LTgain -= m
    m = min(STloss, STgain); STloss -= m; STgain -= m
    m = min(STloss, LTgain); STloss -= m; LTgain -= m
    st_tax = 0.20 * STgain
    lt_tax = 0.125 * max(LTgain - 125_000, 0)
    sl_tax = 0.30 * max(SL, 0)
    if not taxon:
        st_tax = lt_tax = sl_tax = 0.0
    return st_tax, lt_tax, sl_tax, STloss, LTloss


def run(tax=True, costs=True, pt_next=False, april=False, sameday_current=False,
        notax_day_cost=False, lifo=False, no_stepup=False, lt_ge=False,
        basis_incl_cost=False, net_sell_cost=False, skip_first_taxday=False, record=False):
    cost = COSTS if costs else {k: (0.0, 0.0) for k in COSTS}
    passthru = {}
    for k, v in map_trades(mt, "pnl", "MOM", pt_next).items():
        passthru.setdefault(k, []).extend(v)
    for k, v in map_trades(sw, "net_pnl", "SW", pt_next).items():
        passthru.setdefault(k, []).extend(v)
    tdays = tax_days_april() if april else tax_days()
    if skip_first_taxday:
        tdays = set(tdays) - {min(tdays)}

    cash = CAP
    lots = {k: deque() for k in COSTS}  # each lot: [units, basis_per_unit, date_idx]
    period = 0
    # running per-period accumulators
    acc = {"ST": 0.0, "LT": 0.0, "SL": 0.0}
    cfST = cfLT = 0.0
    events = []   # (period, source, cls, hd, gain)
    trades = []   # (i, inst, value, cost, nav_before)
    periods = []  # (period, settle_date, st_tax, lt_tax, sl_tax)

    def is_lt(hd):
        return hd >= 365 if lt_ge else hd > 365

    def units(inst):
        return sum(l[0] for l in lots[inst])

    def book(per_, source, cls, hd, gain):
        events.append((per_, source, cls, hd, gain))

    def sell(inst, u, i, source, per_):
        nonlocal cash
        px = PX[inst][i]
        val = u * px
        c = val * cost[inst][1]
        cash += val - c
        rem = u
        q = lots[inst]
        while rem > 1e-12 and q:
            lot = q[-1] if lifo else q[0]
            take = min(rem, lot[0])
            gain = take * (px * (1 - cost[inst][1] if net_sell_cost else 1) - lot[1]) if net_sell_cost else take * (px - lot[1])
            hd = (dates[i] - dates[lot[2]]).days
            if inst == "LIQ":
                cls = "SL"
            else:
                cls = "LT" if is_lt(hd) else "ST"
            book(per_, source if inst != "LIQ" else "liquid", cls, hd, gain)
            lot[0] -= take
            rem -= take
            if lot[0] <= 1e-12:
                (q.pop() if lifo else q.popleft())
        return val, c

    def buy(inst, u, i):
        nonlocal cash
        px = PX[inst][i]
        val = u * px
        c = val * cost[inst][0]
        cash -= val + c
        basis = px * (1 + cost[inst][0]) if basis_incl_cost else px
        lots[inst].append([u, basis, i])
        return val, c

    for i in range(N):
        # 1. pass-through
        for (sl, pnl, hd) in passthru.get(i, []):
            u = units(sl)
            if u > 0:
                cls = "LT" if is_lt(hd) else "ST"
                book(period, "passthrough", cls, hd, u * pnl)
            if not no_stepup:
                for lot in lots[sl]:
                    lot[1] += pnl
        # 2. tax day
        taxday = i in tdays
        if taxday:
            # sum period gains
            settle_period = period
            if sameday_current:
                pass  # settle after retarget instead
            else:
                cash, cfST, cfLT = do_settle(events, period, cash, cfST, cfLT, tax, periods, dates[i])
                period += 1
        # 3. retarget
        nav = cash + sum(units(k) * PX[k][i] for k in COSTS)
        e = E[i]
        tgt = {"MOM": nav * e * 0.70, "SW": nav * e * 0.30, "LIQ": nav * (1 - e)}
        diffs = {k: tgt[k] - units(k) * PX[k][i] for k in COSTS}
        src = "wrapper"
        saved_cost = cost
        if notax_day_cost and taxday:
            cost = {k: (0.0, 0.0) for k in COSTS}
        for k in COSTS:
            if diffs[k] < -1e-9:
                u = -diffs[k] / PX[k][i]
                u = min(u, units(k))
                v, c = sell(k, u, i, src, period)
                trades.append((i, k, -v, c, nav))
        for k in COSTS:
            if diffs[k] > 1e-9:
                u = diffs[k] / PX[k][i]
                v, c = buy(k, u, i)
                trades.append((i, k, v, c, nav))
        cost = saved_cost
        if taxday and sameday_current:
            cash, cfST, cfLT = do_settle(events, period, cash, cfST, cfLT, tax, periods, dates[i])
            period += 1
    # 4. terminal liquidation
    i = N - 1
    for k in COSTS:
        u = units(k)
        if u > 0:
            sell(k, u, i, "terminal", period)
    cash, cfST, cfLT = do_settle(events, period, cash, cfST, cfLT, tax, periods, dates[i])
    days = (dates[-1] - dates[0]).days
    cagr = (cash / CAP) ** (365.25 / days) - 1
    return {"cagr": cagr, "final_cash": cash, "events": events, "trades": trades, "periods": periods,
            "first_idx": 0}


def do_settle(events, period, cash, cfST, cfLT, taxon, periods, d):
    ST = sum(g for p, s, c, h, g in events if p == period and c == "ST")
    LT = sum(g for p, s, c, h, g in events if p == period and c == "LT")
    SL = sum(g for p, s, c, h, g in events if p == period and c == "SL")
    st, lt, slt, cfST, cfLT = settle(ST, LT, SL, cfST, cfLT, taxon)
    periods.append((period, d.date().isoformat(), st, lt, slt, ST, LT, SL))
    return cash - (st + lt + slt), cfST, cfLT


def recompute_tax(events, relabel_ceiling=False):
    nper = max(p for p, *_ in events) + 1
    cfST = cfLT = 0.0
    tot = 0.0
    for p in range(nper):
        ST = LT = SL = 0.0
        for pp, s, c, h, g in events:
            if pp != p: continue
            if c == "SL": SL += g
            else:
                if relabel_ceiling and 331 <= h <= 364: c = "LT"
                if c == "ST": ST += g
                else: LT += g
        st, lt, slt, cfST, cfLT = settle(ST, LT, SL, cfST, cfLT, True)
        tot += st + lt + slt
    return tot
