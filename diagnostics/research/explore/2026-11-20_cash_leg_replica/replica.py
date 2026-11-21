"""Blind replica of SPEC.md (2026-11-20 cash-leg). Written from SPEC.md and the 2026-11-19 SPEC.md only.

Imports nothing from nq/ or pipelines/. Run: python replica.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
TRI_CSV = ROOT / "diagnostics/research/benchmarks/tri/nifty_midcap150_momentum_50_tri.csv"
NAV_DIR = ROOT / "diagnostics/replica/phase0/nav_20261120"

FEE_DAILY = 0.0030 / 252
BUY_COST = 0.00005
SELL_COST = 0.00001


def load_tri():
    t = pd.read_csv(TRI_CSV, parse_dates=["date"]).sort_values("date").set_index("date")["tri"].astype(float)
    return t


def load_nav(code):
    d = json.loads((NAV_DIR / f"{code}.json").read_text())["data"]
    s = pd.Series({pd.to_datetime(r["date"], format="%d-%m-%Y"): float(r["nav"]) for r in d}).sort_index()
    return s


# ---------------------------------------------------------------- Part A
def build_prices():
    tri = load_tri()
    sess = tri.loc["2017-01-01":"2026-06-30"].index
    tri_ret = tri.pct_change().reindex(sess)  # computed on full history; first session forced to 0 below
    r_idx = tri_ret.to_numpy(copy=True) - FEE_DAILY
    r_idx[0] = 0.0
    index_px = 100 * np.cumprod(1 + r_idx)

    nav = load_nav(119771)
    u = nav.index.union(sess)
    nav_s = nav.reindex(u).ffill().reindex(sess)
    r_arb = nav_s.pct_change().fillna(0.0).to_numpy(copy=True)
    r_arb[0] = 0.0
    arb_px = 100 * np.cumprod(1 + r_arb)
    return pd.DataFrame({"index_px": index_px, "arbitrage_px": arb_px}, index=sess)


def settle(ST, LT, cfST, cfLT):
    STloss = max(-ST, 0.0) + cfST
    STgain = max(ST, 0.0)
    LTloss = max(-LT, 0.0) + cfLT
    LTgain = max(LT, 0.0)
    m = min(LTloss, LTgain); LTloss -= m; LTgain -= m
    m = min(STloss, STgain); STloss -= m; STgain -= m
    m = min(STloss, LTgain); STloss -= m; LTgain -= m
    tax = 0.20 * STgain + 0.125 * max(LTgain - 125000.0, 0.0)
    return tax, STloss, LTloss


def run_book(px, w=(0.60, 0.40)):
    names = ["index_px", "arbitrage_px"]
    dates = px.index
    cash = 2_000_000.0
    lots = {n: [] for n in names}  # [units, cost_per_unit, date]
    st = {"ST": 0.0, "LT": 0.0, "cfST": 0.0, "cfLT": 0.0}
    total_tax = 0.0
    tax_days = set()
    for y in range(dates[0].year, dates[-1].year + 1):
        c = dates[dates <= pd.Timestamp(y, 3, 31)]
        if len(c) and c[-1] != dates[-1]:
            tax_days.add(c[-1])

    def units(n):
        return sum(l[0] for l in lots[n])

    def sell(n, q, price, d):
        nonlocal cash
        proceeds = q * price
        cash += proceeds * (1 - SELL_COST)
        while q > 1e-12 and lots[n]:
            lot = lots[n][0]
            take = min(lot[0], q)
            gain = take * (price - lot[1])  # gross gain; sell cost not deducted (ambiguity A3)
            if (d - lot[2]).days > 365:
                st["LT"] += gain
            else:
                st["ST"] += gain
            lot[0] -= take
            q -= take
            if lot[0] <= 1e-12:
                lots[n].pop(0)

    def buy(n, amt, price, d):
        nonlocal cash
        cash -= amt * (1 + BUY_COST)
        lots[n].append([amt / price, price, d])

    rec = []
    for i, d in enumerate(dates):
        p = {n: px.at[d, n] for n in names}
        is_tax = d in tax_days
        if is_tax:
            tax, st["cfST"], st["cfLT"] = settle(st["ST"], st["LT"], st["cfST"], st["cfLT"])
            st["ST"] = st["LT"] = 0.0
            cash -= tax
            total_tax += tax
        if i == 0 or is_tax:
            nav = cash + sum(units(n) * p[n] for n in names)
            tgt = {names[0]: nav * w[0], names[1]: nav * w[1]}
            diff = {n: tgt[n] - units(n) * p[n] for n in names}
            for n in names:
                if diff[n] < 0:
                    sell(n, -diff[n] / p[n], p[n], d)
            for n in names:
                if diff[n] > 0:
                    buy(n, diff[n], p[n], d)
        rec.append(cash + sum(units(n) * p[n] for n in names))
    d = dates[-1]
    for n in names:
        q = units(n)
        if q > 0:
            sell(n, q, px.at[d, n], d)
    tax, st["cfST"], st["cfLT"] = settle(st["ST"], st["LT"], st["cfST"], st["cfLT"])
    cash -= tax
    total_tax += tax
    return pd.Series(rec, index=dates), cash, total_tax, sorted(tax_days)


def p95_dd(nav):
    wk = nav.resample("W-FRI").last().dropna()
    w = wk.pct_change().dropna().values
    T, h, n = len(w), 156, 10_000
    rng = np.random.default_rng(20261118 + 1000 * 8 + 156)
    idx = np.empty((n, h), dtype=np.int64)
    idx[:, 0] = rng.integers(0, T, n)
    jump = rng.random((n, h)) < 1 / 8
    fresh = rng.integers(0, T, (n, h))
    for k in range(1, h):
        idx[:, k] = np.where(jump[:, k], fresh[:, k], (idx[:, k - 1] + 1) % T)
    path = np.concatenate([np.ones((n, 1)), np.cumprod(1 + w[idx], axis=1)], axis=1)
    depth = (1 - path / np.maximum.accumulate(path, axis=1)).max(axis=1) * 100
    return float(np.percentile(depth, 95)), T


# ---------------------------------------------------------------- Part B
def part_b():
    tri = load_tri()
    fund = load_nav(150738)
    # first TRI row = 1.0 (no return, no fee); ratios only, so the base row is irrelevant
    model_full = pd.Series(np.cumprod(np.r_[1.0, 1 + (tri.pct_change().values[1:] - FEE_DAILY)]), index=tri.index)
    common = tri.index.intersection(fund.index)
    common = common[common >= fund.index[0]]
    df = pd.DataFrame({"fund": fund.reindex(common), "tri": tri.reindex(common), "model": model_full.reindex(common)})
    rows = []
    for y in sorted(set(common.year)):
        before = common[common < pd.Timestamp(y, 1, 1)]
        start = before[-1] if len(before) else common[0]
        end = common[common.year == y][-1]
        r = {k: df.at[end, k] / df.at[start, k] - 1 for k in ["fund", "tri", "model"]}
        rows.append((y, start.date(), end.date(), r["fund"] * 100, r["tri"] * 100, r["model"] * 100,
                     (r["fund"] - r["tri"]) * 100, (r["fund"] - r["model"]) * 100))
    days = (common[-1] - common[0]).days
    ann = {k: (df[k].iloc[-1] / df[k].iloc[0]) ** (365.25 / days) - 1 for k in ["fund", "tri", "model"]}
    return rows, ann, common[0].date(), common[-1].date(), days, len(common)


def main():
    px = build_prices()
    nav, final_cash, total_tax, tax_days = run_book(px)
    days = (px.index[-1] - px.index[0]).days
    cagr = (final_cash / 2_000_000) ** (365.25 / days) - 1
    p95, T = p95_dd(nav)
    print("PART A")
    print(f"sessions {px.index[0].date()}..{px.index[-1].date()} n={len(px)} days={days}")
    print(f"index_px end {px['index_px'].iloc[-1]:.4f} arbitrage_px end {px['arbitrage_px'].iloc[-1]:.4f}")
    print(f"tax days: {[str(d.date()) for d in tax_days]}")
    print(f"final cash {final_cash:,.2f}  total tax {total_tax:,.2f}")
    print(f"after-tax CAGR {cagr*100:.4f}%")
    print(f"p95 156w drawdown {p95:.4f}%  (T={T} weekly returns)")
    rows, ann, f0, f1, d, nc = part_b()
    print("\nPART B")
    print(f"common {f0}..{f1} n={nc} days={d}")
    print("year | start | end | fund% | tri% | model% | fund-tri pp | fund-model pp")
    for r in rows:
        print(f"{r[0]} | {r[1]} | {r[2]} | {r[3]:.3f} | {r[4]:.3f} | {r[5]:.3f} | {r[6]:+.3f} | {r[7]:+.3f}")
    print(f"annualised fund {ann['fund']*100:.4f}% tri {ann['tri']*100:.4f}% model {ann['model']*100:.4f}%")
    print(f"fund-tri {(ann['fund']-ann['tri'])*100:+.4f}pp fund-model {(ann['fund']-ann['model'])*100:+.4f}pp")


if __name__ == "__main__":
    main()
