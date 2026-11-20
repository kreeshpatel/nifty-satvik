"""Blind replica of SPEC.md. Plain, slow, explicit. Reads only inputs/."""
import os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
INP = os.path.join(HERE, "inputs")

COST = {"MOM": (0.002190, 0.002040), "SW": (0.002190, 0.002040),
        "IDX": (0.00005, 0.00001), "ARB": (0.00005, 0.00001)}
PXCOL = {"MOM": "mom_nav", "SW": "swing_nav", "IDX": "index_px", "ARB": "arbitrage_real_px"}
START = 2_000_000.0

d = pd.read_csv(os.path.join(INP, "daily.csv"), parse_dates=["date"])
mt = pd.read_csv(os.path.join(INP, "momentum_trades.csv"), parse_dates=["entry_date", "exit_date"])
sl = pd.read_csv(os.path.join(INP, "swing_ledger.csv"), parse_dates=["entry_date", "exit_date"])
op = pd.read_csv(os.path.join(INP, "open_positions_at_cut.csv"))
dates = list(d["date"])
N = len(dates)


def map_exit(ts):
    """exit date -> session index (next session if not a session); None if after last."""
    i = int(np.searchsorted(np.array(dates, dtype="datetime64[ns]"), np.datetime64(ts), side="left"))
    return i if i < N else None


# pass-through events per session: list of (sleeve, pnl, is_lt)
events = {i: [] for i in range(N)}
dropped = {"after_last": 0}
for sleeve, df, col in (("MOM", mt, "pnl"), ("SW", sl, "net_pnl")):
    for _, r in df.iterrows():
        i = map_exit(r["exit_date"])
        if i is None:
            dropped["after_last"] += 1
            continue
        events[i].append((sleeve, float(r[col]), (r["exit_date"] - r["entry_date"]).days > 365))
n_before_first = sum(1 for df in (mt, sl) for x in df["exit_date"] if x < dates[0])

# tax days: last session on/before 31 Mar of a year, not the final session
tax_days = set()
for i in range(N - 1):
    dt, nx = dates[i], dates[i + 1]
    mar31 = pd.Timestamp(dt.year, 3, 31)
    if dt <= mar31 and nx > mar31:
        tax_days.add(i)


class Book:
    def __init__(self):
        self.cash = START
        self.lots = {k: [] for k in COST}  # list of [units, basis_per_unit, date]
        self.ST = 0.0
        self.LT = 0.0
        self.cfST = 0.0
        self.cfLT = 0.0
        self.tax_total = 0.0
        self.tax_log = []

    def units(self, k):
        return sum(l[0] for l in self.lots[k])

    def nav(self, i):
        return self.cash + sum(self.units(k) * d[PXCOL[k]].iat[i] for k in COST)

    def book_gain(self, g, lt):
        if lt:
            self.LT += g
        else:
            self.ST += g

    def passthrough(self, sleeve, pnl, lt):
        u = self.units(sleeve)
        if u > 0:
            self.book_gain(u * pnl, lt)
            for l in self.lots[sleeve]:
                l[1] += pnl

    def sell(self, k, units, i):
        px = d[PXCOL[k]].iat[i]
        dt = dates[i]
        self.cash += units * px * (1 - COST[k][1])
        rem = units
        while rem > 1e-12 and self.lots[k]:
            lot = self.lots[k][0]
            take = min(lot[0], rem)
            gain = take * (px - lot[1])  # sell cost NOT deducted from gain (literal spec)
            self.book_gain(gain, (dt - lot[2]).days > 365)
            lot[0] -= take
            rem -= take
            if lot[0] <= 1e-12:
                self.lots[k].pop(0)

    def buy(self, k, units, i):
        px = d[PXCOL[k]].iat[i]
        self.cash -= units * px * (1 + COST[k][0])
        self.lots[k].append([units, px, dates[i]])  # basis = price, buy cost excluded

    def retarget(self, i, w):
        nav = self.nav(i)
        delta = {}
        for k in COST:
            px = d[PXCOL[k]].iat[i]
            delta[k] = nav * w.get(k, 0.0) / px - self.units(k)
        for k in COST:
            if delta[k] < 0:
                self.sell(k, -delta[k], i)
        for k in COST:
            if delta[k] > 0:
                self.buy(k, delta[k], i)

    def settle(self, label):
        ST, LT = self.ST, self.LT
        STl = max(-ST, 0) + self.cfST
        STg = max(ST, 0)
        LTl = max(-LT, 0) + self.cfLT
        LTg = max(LT, 0)
        x = min(LTl, LTg); LTl -= x; LTg -= x
        x = min(STl, STg); STl -= x; STg -= x
        x = min(STl, LTg); STl -= x; LTg -= x
        tax = 0.20 * STg + 0.125 * max(LTg - 125_000, 0)
        self.cash -= tax
        self.tax_total += tax
        self.tax_log.append((label, ST, LT, tax, STl, LTl))
        self.cfST, self.cfLT = STl, LTl
        self.ST = self.LT = 0.0


def run(point):
    b = Book()
    rec = []
    r = 0.70 * d["mom_ret"].values + 0.30 * d["swing_ret"].values
    for i in range(N):
        if point == "A":
            for ev in events[i]:
                b.passthrough(*ev)
        if i in tax_days:
            b.settle(str(dates[i].date()))
        if point == "A":
            if i < 20:
                e = 1.0
            else:
                vol = np.std(r[i - 20:i], ddof=1) * np.sqrt(252)
                e = min(1.0, 0.10 / vol)
            b.retarget(i, {"MOM": e * 0.70, "SW": e * 0.30, "ARB": 1 - e})
        else:
            if i == 0 or i in tax_days:
                b.retarget(i, {"IDX": 0.65, "ARB": 0.35})
        rec.append(b.nav(i))
    last = N - 1
    if point == "A":
        for _, row in op.iterrows():
            b.passthrough(row["sleeve"], float(row["gain"]), int(row["days"]) > 365)
    for k in COST:
        u = b.units(k)
        if u > 0:
            b.sell(k, u, last)
    b.settle("final " + str(dates[last].date()))
    return b, pd.Series(rec, index=pd.DatetimeIndex(dates))


def p95_dd(nav):
    wk = nav.resample("W-FRI").last().dropna()
    w = wk.pct_change().dropna().values
    T, h, bsz, n = len(w), 156, 8, 10_000
    rng = np.random.default_rng(20261118 + 1000 * 8 + 156)
    idx = np.empty((n, h), dtype=np.int64)
    idx[:, 0] = rng.integers(0, T, n)
    jump = rng.random((n, h)) < 1 / bsz
    fresh = rng.integers(0, T, (n, h))
    for k in range(1, h):
        idx[:, k] = np.where(jump[:, k], fresh[:, k], (idx[:, k - 1] + 1) % T)
    paths = np.concatenate([np.ones((n, 1)), np.cumprod(1 + w[idx], axis=1)], axis=1)
    peak = np.maximum.accumulate(paths, axis=1)
    depth = ((1 - paths / peak) * 100).max(axis=1)
    return float(np.percentile(depth, 95)), T


def sharpe(nav):
    r = nav.pct_change().dropna().values
    rf = 1.065 ** (1 / 252) - 1
    return (r.mean() - rf) / r.std(ddof=1) * np.sqrt(252)


if __name__ == "__main__":
    days = (dates[-1] - dates[0]).days
    print(f"sessions={N} days={days} tax_days={[str(dates[i].date()) for i in sorted(tax_days)]}")
    print(f"exits dropped after last={dropped['after_last']} exits before first session={n_before_first}")
    out = []
    for p in ("A", "B"):
        b, nav = run(p)
        cagr = ((b.cash / START) ** (365.25 / days) - 1) * 100
        dd, T = p95_dd(nav)
        sh = sharpe(nav)
        print(f"\nPoint {p}: final_cash={b.cash:,.2f} CAGR={cagr:.4f}% p95DD={dd:.4f}% (T={T}) "
              f"exSharpe={sh:.4f} tax={b.tax_total:,.2f} last_recorded_nav={nav.iloc[-1]:,.2f} "
              f"min_cash_left={b.cash:.2f}")
        for t in b.tax_log:
            print("  settle %s ST=%.0f LT=%.0f tax=%.0f cfST=%.0f cfLT=%.0f" % t)
