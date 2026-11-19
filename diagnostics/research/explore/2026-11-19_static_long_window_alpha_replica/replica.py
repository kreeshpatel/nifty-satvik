"""Blind replica of SPEC.md. Plain, slow, explicit. Not engine code."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
INP = HERE / "inputs"

BUY_C = 0.00005
SELL_C = 0.00001
# Ambiguity switch: realised gain computed on gross price (spec: "cost per unit = price")
GAIN_NET_OF_COSTS = "--net-gain" in sys.argv


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


def part1():
    df = pd.read_csv(INP / "step1_daily.csv", parse_dates=["date"]).set_index("date").sort_index()
    df = df.loc["2017-01-02":"2026-06-30"]
    dates = list(df.index)
    names = ["index_px", "arbitrage_px"]
    wts = {"index_px": 0.60, "arbitrage_px": 0.40}

    # tax days: for each year Y, last session with date <= Y-03-31; exclude final session
    tax_days = set()
    for y in range(dates[0].year, dates[-1].year + 1):
        cand = [d for d in dates if d <= pd.Timestamp(y, 3, 31)]
        if cand:
            tax_days.add(cand[-1])
    tax_days.discard(dates[-1])

    cash = 2_000_000.0
    lots = {n: [] for n in names}  # list of [units, px, date]
    ST = LT = cfST = cfLT = 0.0
    total_tax = 0.0
    nav_rec = []

    def units(n):
        return sum(l[0] for l in lots[n])

    def sell(n, u, px, d):
        nonlocal cash, ST, LT
        val = u * px
        cash += val * (1 - SELL_C)
        rem = u
        while rem > 1e-12:
            lot = lots[n][0]
            take = min(rem, lot[0])
            if GAIN_NET_OF_COSTS:
                g = take * (px * (1 - SELL_C) - lot[1] * (1 + BUY_C))
            else:
                g = take * (px - lot[1])
            if (d - lot[2]).days > 365:
                LT += g
            else:
                ST += g
            lot[0] -= take
            rem -= take
            if lot[0] <= 1e-12:
                lots[n].pop(0)

    def buy(n, val, px, d):
        nonlocal cash
        cash -= val * (1 + BUY_C)
        lots[n].append([val / px, px, d])

    for i, d in enumerate(dates):
        px = {n: float(df.at[d, n]) for n in names}
        is_tax = d in tax_days
        if is_tax:
            tax, cfST, cfLT = settle(ST, LT, cfST, cfLT)
            ST = LT = 0.0
            cash -= tax
            total_tax += tax
        if i == 0 or is_tax:
            nav = cash + sum(units(n) * px[n] for n in names)
            delta = {n: nav * wts[n] - units(n) * px[n] for n in names}
            for n in names:
                if delta[n] < 0:
                    sell(n, -delta[n] / px[n], px[n], d)
            for n in names:
                if delta[n] > 0:
                    buy(n, delta[n], px[n], d)
        nav_rec.append(cash + sum(units(n) * px[n] for n in names))

    d = dates[-1]
    px = {n: float(df.at[d, n]) for n in names}
    for n in names:
        u = units(n)
        if u > 0:
            sell(n, u, px[n], d)
    tax, cfST, cfLT = settle(ST, LT, cfST, cfLT)
    cash -= tax
    total_tax += tax

    days = (dates[-1] - dates[0]).days
    cagr = ((cash / 2_000_000.0) ** (365.25 / days) - 1) * 100

    nav = pd.Series(nav_rec, index=df.index)
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
    paths = np.concatenate([np.ones((n, 1)), np.cumprod(1 + w[idx], axis=1)], axis=1)
    dd = (1 - paths / np.maximum.accumulate(paths, axis=1)).max(axis=1) * 100
    p95 = np.percentile(dd, 95)
    return dict(final_cash=cash, cagr=cagr, p95_dd=p95, total_tax=total_tax, T=T, days=days,
                n_tax_days=len(tax_days), cf=(cfST, cfLT))


def part2():
    df = pd.read_csv(INP / "step2_daily.csv", parse_dates=["date"]).set_index("date").sort_index()
    df = df.loc["2019-03-01":"2024-06-30"]
    rb = df["blend_net_nav"].resample("W-FRI").last().dropna().pct_change().dropna()
    ri = df["index_fund_px"].resample("W-FRI").last().dropna().pct_change().dropna()
    j = pd.concat([rb, ri], axis=1, join="inner").dropna()
    j.columns = ["b", "i"]
    rf = 1.065 ** (1 / 52) - 1
    y = (j["b"] - rf).values
    x1 = (j["i"] - rf).values
    X = np.column_stack([np.ones_like(x1), x1])
    XtX_inv = np.linalg.inv(X.T @ X)
    beta_vec = XtX_inv @ X.T @ y
    e = y - X @ beta_vec
    nobs = len(y)
    S = np.zeros((2, 2))
    for t in range(nobs):
        S += np.outer(X[t], X[t]) * e[t] ** 2
    L = 8
    for l in range(1, L + 1):
        wl = 1 - l / (L + 1)
        G = np.zeros((2, 2))
        for t in range(l, nobs):
            G += np.outer(X[t], X[t - l]) * e[t] * e[t - l]
        S += wl * (G + G.T)
    V = XtX_inv @ S @ XtX_inv
    a, b = beta_vec
    tstat = a / np.sqrt(V[0, 0])
    r2 = 1 - (e @ e) / ((y - y.mean()) @ (y - y.mean()))
    mix = b * j["i"].values + (1 - b) * rf
    growth = np.prod(1 + mix)
    years = ((j.index[-1] - j.index[0]).days + 7) / 365.25
    mix_cagr = (growth ** (1 / years) - 1) * 100
    return dict(alpha_ann=52 * a * 100, beta=b, t=tstat, r2=r2, n=nobs, mix_cagr=mix_cagr,
                first=j.index[0].date(), last=j.index[-1].date())


if __name__ == "__main__":
    print("PART1", part1())
    print("PART2", part2())
