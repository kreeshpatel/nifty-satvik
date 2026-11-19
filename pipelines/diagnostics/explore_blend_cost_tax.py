"""MEASUREMENT: decompose the 70/30 blend's gross-to-net gap into costs and tax, by source. Analysis only.

Owner request 2026-11-19, branch research/blend-cost-tax (cut from PR #214 head 5ce007c). No rule test, no trial, no
sealed read (swing prices cut 2024-06-30), no live change. Standing counts unchanged (24 / 4 / 3).

SIMULATOR  The lot-level engine of explore_after_tax_comparison.py (AT), imported, not re-implemented. A subclass adds
           logging only: every realised gain (pass-through of a book trade, or a sale of a unit lot) is written to an
           event log with its holding days and its settlement period; every trade is written to a trade log. Two
           switches are added, both defaulting to AT's behaviour: (1) expense ratios on/off (prices rebuilt with
           TER = 0); (2) gross sleeve NAVs (each book re-run with its own engine costs off). The exposure series e_t
           is ALWAYS the one AT computes from the NET books, so a gross run differs from the net run only in costs.
ANCHORS    (owner, 2026-11-19; committed JSON 2026-11-18_after_tax_comparison.json) blend after-tax 19.26 / p95 26.46;
           65/35 23.02 / 24.81; blend-level cost drag 1.58pp (25.38 -> 23.80); tax drag 4.54pp (23.80 -> 19.26).
           Re-derived here from the subclass with all switches at AT defaults; a miss over 0.1pp is logged, and the
           run stops only if a miss is unexplained or over 5% relative.

STEP 1  TAX BY SOURCE. Books: blend (AT run (a)); 0001 alone and swing alone, each held 100% as sleeve units with the
        same pass-through rule, re-targeted only on tax days (to fund the tax) and at the first close. The initial
        unit purchase of a standalone book is free (the engine already paid its own entry costs); the tax-funding
        sales and the terminal liquidation pay AT's stock sell rate.
        sources       book_trade (pass-through of a book's realised trade); unit_sale (the wrapper selling sleeve or
                      liquid units: exposure moves, the 70/30 rebalance, tax funding); unit_sale_terminal (the forced
                      liquidation at the last close - open positions taxed by UNIT-LOT age, a convention of the
                      pass-through model, not how the underlying stocks would be taxed).
        holding days  calendar days entry -> exit. Pass-through: the book trade's own entry/exit dates (a 0001
                      top-up keeps the first entry date). Unit-lot sale: lot purchase date -> sale date.
        class         > 365 days long-term (AT's rule); else short-term. Liquid-fund gains are slab (shown apart).
        buckets       0-30, 31-90, 91-180, 181-330, 331-364, 365+ days. Exits at exactly 365 days are short-term
                      under the rule and fall in "365+"; their count is reported.
        tax per bucket  per settlement period (the AT FY), the period's ST tax (20% of ST gains after set-off) is
                      allocated across ST events' buckets in proportion to each bucket's POSITIVE net gain in that
                      period; LT tax (12.5% above Rs 1.25L after set-off) likewise across LT buckets; slab tax to the
                      liquid row. A bucket that is net negative in a period gets zero. The per-period tax is recomputed
                      from the event log with AT's settle() logic and must equal AT's tax_paid schedule (checked).
        331-364 ceiling  every exit with 331-364 holding days re-labelled long-term, the same gains, the period tax
                      recomputed with carry-forwards; saving = actual tax - re-labelled tax. Arithmetic on existing
                      P&L, not an achievable saving: holding a further 1-34 days changes the P&L, and stops are
                      requests (a stopped trade cannot be held).
STEP 2  REBALANCE COST BY TRADE SIZE. Blend pre-tax run with costs (the run behind the 1.58pp). Every instrument-day
        trade from the second session to the last (the first-close purchase and the terminal liquidation excluded).
        size = |trade value| / pre-trade NAV of that close. Distribution p10/p50/p90/p99; share of cost and of
        turnover by size < 0.5%, 0.5-1%, 1-2%, > 2% of NAV. For bands 0.5/1/2%: cost of the trades below the band,
        and the distribution of the weight gap |target - held| each skipped trade would leave (= its size). Static:
        no re-simulation, so drift that would accumulate under a real band is NOT captured.
STEP 3  WATERFALL. gross -> minus engine costs (inside the books) -> minus expense ratios -> minus wrapper trading costs
        (blend unit trades / fund transaction costs) -> minus tax = after-tax CAGR. Sequential, in that fixed order;
        each step = CAGR before - CAGR after, in pp. CAGR = liquidation value ** (365.25 / days) - 1.
STEP 4  BY SLEEVE. Average holding days (trades exiting in the window); annual one-way turnover = sell notional in the
        window / mean daily NAV / years (0001: qty x exit price per trade row; swing: daily share decreases in the
        position log x mark price); after-tax / pre-tax CAGR ratio of the standalone runs (pre-tax = with all costs).

    python pipelines/diagnostics/explore_blend_cost_tax.py
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts"), str(ROOT / "pipelines" / "research"),
                str(ROOT / "pipelines" / "diagnostics"), str(ROOT / "pipelines" / "lifecycle")]
import core as C  # noqa: E402
import explore_after_tax_comparison as AT  # noqa: E402
import explore_blend_drawdown_sizing as B  # noqa: E402

CACHE = ROOT / ".cache" / "blend_cost_tax"
OUT_JSON = ROOT / "diagnostics" / "research" / "explore" / "2026-11-19_blend_cost_tax.json"
EXPORT = CACHE / "replica_inputs"
CAPITAL = AT.CAPITAL
BUCKETS = [(0, 30, "0-30"), (31, 90, "31-90"), (91, 180, "91-180"), (181, 330, "181-330"), (331, 364, "331-364"),
           (365, 10**6, "365+")]
SIZE_BINS = [(0, 0.005, "<0.5%"), (0.005, 0.01, "0.5-1%"), (0.01, 0.02, "1-2%"), (0.02, 10.0, ">2%")]
BANDS = (0.005, 0.01, 0.02)
ANCHORS = {"blend_cagr": 19.26, "blend_p95": 26.46, "s6535_cagr": 23.02, "s6535_p95": 24.81, "cost_pp": 1.58,
           "tax_pp": 4.54}


def bucket(days: int) -> str:
    for lo, hi, name in BUCKETS:
        if lo <= days <= hi:
            return name
    raise ValueError(days)


# ------------------------------------------------------------------------------------------ instrumented book
class LBook(AT.Book):
    """AT.Book plus an event log and a trade log. Tax and cost arithmetic are AT's, unchanged."""

    def __init__(self, tax_on=True, cost_on=True, free_first_buy=False):
        super().__init__(tax_on, cost_on)
        self.events: list[dict] = []
        self.trades: list[dict] = []
        self.period = 0
        self.free_first_buy = free_first_buy
        self.today_nav = None
        self.period_raw: list[dict] = []

    def buy(self, inst, value, px, d):
        if value <= 0:
            return
        if self.free_first_buy:
            on, self.cost_on = self.cost_on, False
            c0 = self.costs
            super().buy(inst, value, px, d)
            self.cost_on = on
            self.trades.append({"d": d, "inst": inst, "side": "B", "value": value, "cost": self.costs - c0,
                                "nav": self.today_nav})
            return
        c0 = self.costs
        super().buy(inst, value, px, d)
        self.trades.append({"d": d, "inst": inst, "side": "B", "value": value, "cost": self.costs - c0,
                            "nav": self.today_nav})

    def sell(self, inst, value, px, d):
        u = min(value / px, self.units[inst])
        if u <= 0:
            return
        # walk the lots exactly as AT.Book.sell will, to log each lot's gain and age, then let the parent book it
        rem, q = u, self.lots[inst]
        for lot in q:
            if rem <= 1e-12:
                break
            take = min(rem, lot[0])
            days = (d - lot[2]).days
            g = take * (px - lot[1])
            cls = "slab" if self.kind(inst) == "debt" else ("lt" if days > 365 else "st")
            self.events.append({"period": self.period, "d": d, "src": "unit_sale", "inst": inst, "gain": g,
                                "days": days, "cls": cls})
            rem -= take
        c0 = self.costs
        super().sell(inst, value, px, d)
        self.trades.append({"d": d, "inst": inst, "side": "S", "value": u * px, "cost": self.costs - c0,
                            "nav": self.today_nav})

    def passthrough_ev(self, inst, g, days):
        u = self.units[inst]
        if u <= 0 or g == 0:
            return
        lt = days > 365
        self.events.append({"period": self.period, "d": None, "src": "book_trade", "inst": inst, "gain": u * g,
                            "days": days, "cls": "lt" if lt else "st"})
        self.passthrough(inst, g, lt)

    def settle(self, d):
        self.period_raw.append({"period": self.period, "st": self.st, "lt": self.lt, "slab": self.slab})
        t = super().settle(d)
        self.period += 1
        return t


# ------------------------------------------------------------------------------------------ inputs
def gross_books(d: dict) -> dict:
    """Each book re-run with its own engine costs off. Cached. Measurement re-run, not a configuration change."""
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / "gross_navs.pkl"
    if f.exists():
        return pd.read_pickle(f)
    import run_0001_xsec_momentum as M
    from nq.data.membership import load_membership
    from nq.engine.rebalance_book import RebalanceConfig, simulate_rebalance_book
    from nq.lab import runs as L
    from nq.universe import build_universe
    from run_bhanushali_path1 import corrected_universe
    import diag_system_inventory_2026_11 as INV
    uni = corrected_universe()
    p = M.add_signals(build_universe(uni, load_membership(), start=M.START, end=M.END))
    b = p[p["ticker"].isin(p.loc[p["size_band"] == M.BAND, "ticker"].unique())].copy()
    b["rank"] = np.where(b["eligible"] & (b["size_band"] == M.BAND) & b["nms"].notna(), b["nms"], np.nan)
    bt = simulate_rebalance_book(b, cfg=RebalanceConfig(**M.BOOK, cost_mult=0.0), start=M.START, end=M.END,
                                 initial_capital=1_000_000.0)
    mom_gross = INV.to_nav(bt["equity_curve"])

    # swing: the body of nq.lab.runs.replay({}) with cost_off=True, WITHOUT its cache write or multiplicity record
    def swing(cost_off: bool) -> pd.Series:
        R94, live, load_demerger_rows, _cu = L._engine()
        cut = L.cut_universe(uni)
        L.assert_within_cut(cut)
        P = R94.prep_weekly_rank(cut, **live["LIVE_PREP"])
        as_of = max((pd.Timestamp(s["dates"][-1]) for s in P.values()), default=None)
        events = R94.build_demerger_events(cut, load_demerger_rows(), **{**live["LIVE_PREP"], "as_of": as_of})
        cfg = L.normalize_config({})
        out = R94.backtest(P, load_membership(), ledger=[], cost_off=cost_off,
                           a_grade=R94.grade_a_entries(P) if cfg["grade_gate"] else None,
                           **L.engine_kwargs(cfg), demerger_events=events, position_log=[], event_log=[])
        nav = pd.Series(out["curve"], dtype=float)
        nav.index = pd.DatetimeIndex(nav.index).normalize()
        nav = nav[~nav.index.duplicated(keep="last")].sort_index()
        return nav[nav.index >= pd.Timestamp(cfg["start"])]
    sw_net_check = swing(False)
    sw_gross = swing(True)
    out = {"momentum_gross": mom_gross, "swing_gross": sw_gross, "swing_net_inline": sw_net_check,
           "momentum_gross_metrics": {"cagr_pct": float(bt["metrics"]["cagr_pct"]), "sharpe": float(bt["metrics"]["sharpe"])}}
    pd.to_pickle(out, f)
    return out


def sleeves(d: dict, idx: pd.DatetimeIndex, mom_nav: pd.Series, sw_nav: pd.Series):
    """AT.sleeves, with holding days carried on each realised trade (AT carries only the long-term flag)."""
    def nav(s):
        s = s.copy()
        s.index = pd.DatetimeIndex(s.index).normalize()
        return s[~s.index.duplicated(keep="last")].reindex(idx).ffill()

    def snap(dates):
        pos = idx.searchsorted(pd.DatetimeIndex(dates).normalize())
        return [idx[i] if i < len(idx) else None for i in pos]
    mt = d["momentum_trades"].copy()
    mt["ed"], mt["xd"] = pd.to_datetime(mt["entry_date"]), pd.to_datetime(mt["exit_date"])
    mt = mt[(mt["xd"] >= idx[0]) & (mt["xd"] <= idx[-1])]
    mt["days"] = (mt["xd"] - mt["ed"]).dt.days
    mt["day"] = snap(mt["xd"])
    led = d["swing_ledger"].copy()
    led = led[led["reason"] != "eos"]
    led["ed"], led["xd"] = pd.to_datetime(led["entry_date"]), pd.to_datetime(led["exit_date"])
    led = led[(led["xd"] >= idx[0]) & (led["xd"] <= idx[-1])]
    led["days"] = (led["xd"] - led["ed"]).dt.days
    led["day"] = snap(led["xd"])
    gains = defaultdict(list)
    for r in mt.dropna(subset=["day"]).itertuples():
        gains[r.day].append((AT.MOM, float(r.pnl), int(r.days)))
    for r in led.dropna(subset=["day"]).itertuples():
        gains[r.day].append((AT.SW, float(r.net_pnl), int(r.days)))
    return nav(mom_nav), nav(sw_nav), gains, mt, led


def prices(idx, ter_on: bool):
    tri = pd.read_csv(AT.TRI, parse_dates=["date"]).set_index("date")["tri"].astype(float)
    r = tri.pct_change().reindex(idx).fillna(0.0)
    ti, tl = (AT.TER_INDEX, AT.TER_LIQUID) if ter_on else (0.0, 0.0)
    index_px = (1 + r - ti / 252).cumprod() * 100
    liq_px = pd.Series(((1 + AT.RF_D) * (1 - tl / 252)) ** np.arange(len(idx)), index=idx) * 100
    return index_px, liq_px, r


# ------------------------------------------------------------------------------------------ the run (AT.run + logs)
def run(kind, idx, px_index, px_liq, expo=None, px_m=None, px_s=None, gains=None, weight=None, tax_on=True,
        cost_on=True) -> dict:
    """Line-for-line AT.run, with: per-trade holding days on pass-through; kinds 'mom_only' / 'sw_only'."""
    b = LBook(tax_on, cost_on, free_first_buy=kind in ("mom_only", "sw_only"))
    b.cash = CAPITAL
    navs = []
    fy_last = {AT.fy_end(dd): dd for dd in idx}
    pay_days = {v for k, v in fy_last.items() if v != idx[-1]}

    def prices_at(k):
        pr = {AT.IDX: float(px_index.iloc[k]), AT.LIQ: float(px_liq.iloc[k])}
        if px_m is not None:
            pr[AT.MOM], pr[AT.SW] = float(px_m.iloc[k]), float(px_s.iloc[k])
        return pr
    for k, dd in enumerate(idx):
        pr = prices_at(k)
        if kind in ("blend", "mom_only", "sw_only") and gains:
            for inst, g, days in gains.get(dd, ()):
                b.passthrough_ev(inst, g, days)
        for e in b.events:
            if e["d"] is None:
                e["d"] = dd
        if dd in pay_days:
            b.settle(dd)
        nav = b.value(pr)
        b.today_nav = nav
        b.free_first_buy = b.free_first_buy and k == 0
        if k == 0 or dd in pay_days or kind in ("blend", "index_vt"):
            if kind == "blend":
                e = float(expo.iloc[k])
                tg = {AT.MOM: nav * e * 0.70, AT.SW: nav * e * 0.30, AT.LIQ: nav * (1 - e)}
            elif kind == "index_vt":
                e = float(expo.iloc[k])
                tg = {AT.IDX: nav * e, AT.LIQ: nav * (1 - e)}
            elif kind == "mom_only":
                tg = {AT.MOM: nav}
            elif kind == "sw_only":
                tg = {AT.SW: nav}
            else:
                tg = {AT.IDX: nav * weight, AT.LIQ: nav * (1 - weight)}
            b.retarget(tg, pr, dd)
        navs.append(b.value(pr))
    mtm = pd.Series(navs, index=idx)
    pr = prices_at(len(idx) - 1)
    b.today_nav = b.value(pr)
    n_before, n_ev = len(b.trades), len(b.events)
    for i in sorted(b.units):
        if b.units[i] > 0:
            b.sell(i, b.units[i] * pr[i], pr[i], idx[-1])
    for t in b.trades[n_before:]:
        t["terminal"] = True
    for e in b.events[n_ev:]:
        if e["src"] == "unit_sale":
            e["src"] = "unit_sale_terminal"
    b.settle(idx[-1])
    return {"mtm": mtm, "liquidation_value": b.cash, "tax_paid": b.tax_paid, "costs": b.costs, "book": b}


def cagr(res, idx) -> float:
    yrs = (idx[-1] - idx[0]).days / 365.25
    return ((res["liquidation_value"] / CAPITAL) ** (1 / yrs) - 1) * 100


# ------------------------------------------------------------------------------------------ tax arithmetic
def period_tax(st, lt, slab, cf_st, cf_lt):
    """AT.Book.settle, as a pure function. Returns (st_tax, lt_tax, slab_tax, cf_st, cf_lt)."""
    stl, stg = max(-st, 0) + cf_st, max(st, 0)
    ltl, ltg = max(-lt, 0) + cf_lt, max(lt, 0)
    x = min(ltl, ltg); ltg -= x; ltl -= x
    x = min(stl, stg); stg -= x; stl -= x
    x = min(stl, ltg); ltg -= x; stl -= x
    return AT.STCG * stg, AT.LTCG * max(ltg - AT.LTCG_EXEMPT, 0), AT.SLAB * max(slab, 0), stl, ltl


def tax_schedule(ev: pd.DataFrame, n_periods: int, relabel_331_364: bool = False) -> list[tuple]:
    cf_st = cf_lt = 0.0
    out = []
    for p in range(n_periods):
        e = ev[ev["period"] == p]
        cls = e["cls"].copy()
        if relabel_331_364:
            cls[(e["days"] >= 331) & (e["days"] <= 364) & (cls == "st")] = "lt"
        st = float(e.loc[cls == "st", "gain"].sum())
        lt = float(e.loc[cls == "lt", "gain"].sum())
        sl = float(e.loc[cls == "slab", "gain"].sum())
        a, b_, c, cf_st, cf_lt = period_tax(st, lt, sl, cf_st, cf_lt)
        out.append((a, b_, c))
    return out


def tax_by_bucket(res: dict) -> dict:
    b = res["book"]
    ev = pd.DataFrame(b.events)
    n = len(b.tax_paid)
    sched = tax_schedule(ev, n)
    # check: recomputed schedule equals the simulator's tax_paid (tax_on runs only)
    sim = [t for _, t in b.tax_paid]
    recon = [round(sum(x), 2) for x in sched]
    max_gap = max(abs(a - c) for a, c in zip(sim, recon)) if sim else 0.0
    ev["bucket"] = ev["days"].map(bucket)
    ev["tax"] = 0.0
    for p, (stt, ltt, slt) in enumerate(sched):
        for cls, tx in (("st", stt), ("lt", ltt), ("slab", slt)):
            m = (ev["period"] == p) & (ev["cls"] == cls)
            if tx <= 0 or not m.any():
                continue
            if cls == "slab":
                ev.loc[m, "tax"] = tx * ev.loc[m, "gain"].clip(lower=0) / ev.loc[m, "gain"].clip(lower=0).sum()
                continue
            net = ev[m].groupby("bucket")["gain"].sum().clip(lower=0)
            if net.sum() <= 0:
                continue
            for bk, g in net.items():
                mm = m & (ev["bucket"] == bk)
                pos = ev.loc[mm, "gain"].clip(lower=0)
                if g > 0 and pos.sum() > 0:
                    ev.loc[mm, "tax"] = tx * (g / net.sum()) * pos / pos.sum()
    rows = {}
    for src in ("book_trade", "unit_sale", "unit_sale_terminal"):
        for _, _, name in BUCKETS:
            for cls in ("st", "lt"):
                e = ev[(ev["src"] == src) & (ev["bucket"] == name) & (ev["cls"] == cls)]
                if len(e):
                    rows[f"{src}|{name}|{cls}"] = {"count": int(len(e)), "gain": round(float(e["gain"].sum()), 0),
                                                    "tax": round(float(e["tax"].sum()), 0)}
    sl = ev[ev["cls"] == "slab"]
    if len(sl):
        rows["liquid_fund|slab"] = {"count": int(len(sl)), "gain": round(float(sl["gain"].sum()), 0),
                                    "tax": round(float(sl["tax"].sum()), 0)}
    tot = {c: {"count": int((ev["cls"] == c).sum()), "gain": round(float(ev.loc[ev["cls"] == c, "gain"].sum()), 0),
               "tax": round(float(sum(s[i] for s in sched)), 0)} for i, c in enumerate(("st", "lt", "slab"))}
    relab = tax_schedule(ev, n, relabel_331_364=True)
    w = ev[(ev["days"] >= 331) & (ev["days"] <= 364)]
    return {"rows": rows, "totals_by_class": tot, "tax_total_recomputed": round(sum(map(sum, sched)), 0),
            "tax_total_simulator": round(sum(sim), 0), "max_period_gap_rupees": round(max_gap, 2),
            "exits_at_exactly_365_days_short_term": int((ev["days"] == 365).sum()),
            "ceiling_331_364_as_ltcg": {"exits": int(len(w)), "gain": round(float(w["gain"].sum()), 0),
                                        "tax_saved_rupees": round(sum(map(sum, sched)) - sum(map(sum, relab)), 0),
                                        "note": "arithmetic ceiling on existing P&L; not achievable - holding longer "
                                                "changes the P&L and stops are requests"}}


# ------------------------------------------------------------------------------------------ step 2
def rebalance_sizes(res: dict) -> dict:
    t = pd.DataFrame(res["book"].trades)
    t = t[(t["d"] != t["d"].min()) & (t.get("terminal", False) != True)]  # noqa: E712
    t["size"] = t["value"].abs() / t["nav"]
    tc, tv = t["cost"].sum(), t["value"].abs().sum()
    out = {"n_trades": int(len(t)), "total_cost": round(float(tc), 0), "total_turnover": round(float(tv), 0),
           "size_pct_of_nav": {f"p{p}": round(float(np.percentile(t["size"], p)) * 100, 4) for p in (10, 50, 90, 99)},
           "by_size": {}, "by_instrument_cost": {k: round(float(v), 0) for k, v in t.groupby("inst")["cost"].sum().items()},
           "bands": {}}
    for lo, hi, name in SIZE_BINS:
        m = (t["size"] >= lo) & (t["size"] < hi)
        out["by_size"][name] = {"n": int(m.sum()), "cost_share": round(float(t.loc[m, "cost"].sum() / tc), 4),
                                "turnover_share": round(float(t.loc[m, "value"].abs().sum() / tv), 4),
                                "cost": round(float(t.loc[m, "cost"].sum()), 0)}
    for bnd in BANDS:
        m = t["size"] < bnd
        g = t.loc[m, "size"] * 100
        out["bands"][f"{bnd*100:.1f}%"] = {
            "trades_below_band": int(m.sum()), "cost_of_those_trades": round(float(t.loc[m, "cost"].sum()), 0),
            "share_of_total_cost": round(float(t.loc[m, "cost"].sum() / tc), 4),
            "gap_left_pct_nav": {f"p{p}": round(float(np.percentile(g, p)), 4) for p in (50, 90, 99)} if len(g) else {},
            "gap_left_max_pct_nav": round(float(g.max()), 4) if len(g) else None,
            "caveat": "static: each skipped trade's gap taken alone; accumulation under a real band not simulated"}
    return out


# ------------------------------------------------------------------------------------------ step 4
def sleeve_stats(d, mt, led, idx) -> dict:
    yrs = (idx[-1] - idx[0]).days / 365.25
    mom_nav = B.window(d["momentum"])
    sw_nav = B.window(d["swing"])
    sell_m = float((mt["qty"] * mt["exit"]).sum())
    pl = d["swing_position_log"].copy()
    pl["date"] = pd.to_datetime(pl["date"]).dt.normalize()
    piv = pl.pivot_table(index="date", columns="tkr", values="shares", aggfunc="last").fillna(0.0)
    px = pl.pivot_table(index="date", columns="tkr", values="mark_px", aggfunc="last").ffill()
    dec = (-piv.diff()).clip(lower=0)
    dec.iloc[0] = 0
    sold = (dec * px.reindex_like(dec)).sum(axis=1)
    sold = sold[(sold.index >= idx[0]) & (sold.index <= idx[-1])]
    return {"0001": {"trades": int(len(mt)), "avg_holding_days": round(float(mt["days"].mean()), 1),
                     "median_holding_days": float(mt["days"].median()),
                     "annual_one_way_turnover_x": round(sell_m / float(mom_nav.mean()) / yrs, 2)},
            "swing": {"trades": int(len(led)), "avg_holding_days": round(float(led["days"].mean()), 1),
                      "median_holding_days": float(led["days"].median()),
                      "annual_one_way_turnover_x": round(float(sold.sum()) / float(sw_nav.mean()) / yrs, 2),
                      "turnover_method": "daily share decreases in the position log x mark price"}}


# ------------------------------------------------------------------------------------------ main
def main() -> int:
    d = B.navs()
    mo = d["momentum_metrics"]
    if (round(mo["cagr_pct"], 2), round(mo["sharpe"], 3)) != (21.73, 1.13):
        raise SystemExit("0001 anchor mismatch: stop")
    rm, rs = B.window(d["momentum"]).pct_change().dropna(), B.window(d["swing"]).pct_change().dropna()
    r_bl, expo_bl = C.vol_target_blend(rm, rs, target=0.11)
    idx = pd.DatetimeIndex(r_bl.index).normalize()
    expo_bl.index = idx
    pxi, pxl, r_tri = prices(idx, True)
    pxi0, pxl0, _ = prices(idx, False)
    vol = r_tri.rolling(20).std().shift(1) * np.sqrt(252)
    expo_ix = (0.11 / vol).clip(upper=1.0).fillna(1.0)
    gb = gross_books(d)
    px_m, px_s, gains, mt, led = sleeves(d, idx, d["momentum"], d["swing"])
    gpx_m, gpx_s, ggains, _, _ = sleeves(d, idx, gb["momentum_gross"], gb["swing_gross"])
    out = {"window": [str(idx[0].date()), str(idx[-1].date())], "capital": CAPITAL,
           "counts": "screens 24 / sealed opens 4 / n_trials 3 (unchanged; measurement)"}

    # -------- anchors
    bl = dict(expo=expo_bl, px_m=px_m, px_s=px_s, gains=gains)
    R = {}
    R["blend_after"] = run("blend", idx, pxi, pxl, **bl)
    R["blend_pre"] = run("blend", idx, pxi, pxl, **bl, tax_on=False)
    R["blend_pre_nowrap"] = run("blend", idx, pxi, pxl, **bl, tax_on=False, cost_on=False)
    R["s6535_after"] = run("static", idx, pxi, pxl, weight=0.65)
    got = {"blend_cagr": round(cagr(R["blend_after"], idx), 2),
           "blend_p95": AT.metrics({k: R["blend_after"][k] for k in ("mtm", "liquidation_value", "tax_paid", "costs")})["boot156_p95_b8"],
           "s6535_cagr": round(cagr(R["s6535_after"], idx), 2),
           "s6535_p95": AT.metrics({k: R["s6535_after"][k] for k in ("mtm", "liquidation_value", "tax_paid", "costs")})["boot156_p95_b8"],
           "cost_pp": round(cagr(R["blend_pre_nowrap"], idx) - cagr(R["blend_pre"], idx), 2),
           "tax_pp": round(cagr(R["blend_pre"], idx) - cagr(R["blend_after"], idx), 2)}
    misses = {k: (ANCHORS[k], got[k]) for k in ANCHORS if abs(ANCHORS[k] - got[k]) > 0.1 + 1e-9}
    out["anchors"] = {"expected": ANCHORS, "got": got, "misses_over_0.1pp": misses}
    print("ANCHORS", got, "misses", misses, flush=True)
    if any(abs(a - g) / abs(a) > 0.05 for a, g in misses.values()):
        raise SystemExit("anchor miss over 5% relative: stop")
    sw_chk = B.window(gb["swing_net_inline"]).iloc[-1] / B.window(d["swing"]).iloc[-1] - 1
    out["inline_swing_replay_vs_cached_terminal_nav_rel"] = float(sw_chk)

    # -------- standalone books
    so = dict(px_m=px_m, px_s=px_s, gains=gains)
    R["mom_after"] = run("mom_only", idx, pxi, pxl, **so)
    R["mom_pre"] = run("mom_only", idx, pxi, pxl, **so, tax_on=False)
    R["sw_after"] = run("sw_only", idx, pxi, pxl, **so)
    R["sw_pre"] = run("sw_only", idx, pxi, pxl, **so, tax_on=False)

    # -------- STEP 1
    out["step1_tax_by_source"] = {k: tax_by_bucket(R[k]) for k in ("blend_after", "mom_after", "sw_after")}

    # -------- STEP 2
    out["step2_rebalance_cost_by_size"] = {"run": "blend pre-tax with blend-level costs (the 1.58pp run)",
                                           **rebalance_sizes(R["blend_pre"])}
    out["step2_rebalance_cost_by_size"]["after_tax_run_total_cost"] = round(R["blend_after"]["costs"], 0)

    # -------- STEP 3 waterfall
    def chain(kind, gross_kw, net_kw, extra):
        g0 = run(kind, idx, pxi0, pxl0, **gross_kw, **extra, tax_on=False, cost_on=False)   # gross
        g1 = run(kind, idx, pxi0, pxl0, **net_kw, **extra, tax_on=False, cost_on=False)     # - engine costs
        g2 = run(kind, idx, pxi, pxl, **net_kw, **extra, tax_on=False, cost_on=False)       # - expense ratios
        g3 = run(kind, idx, pxi, pxl, **net_kw, **extra, tax_on=False)                      # - wrapper costs
        g4 = run(kind, idx, pxi, pxl, **net_kw, **extra)                                    # - tax
        c = [cagr(x, idx) for x in (g0, g1, g2, g3, g4)]
        return {"gross_cagr": round(c[0], 2), "engine_costs_pp": round(c[0] - c[1], 2),
                "expense_ratios_pp": round(c[1] - c[2], 2), "wrapper_trading_costs_pp": round(c[2] - c[3], 2),
                "tax_pp": round(c[3] - c[4], 2), "after_tax_cagr": round(c[4], 2), "pre_tax_cagr": round(c[3], 2),
                "rupees": {"wrapper_costs": round(g3["costs"], 0), "tax": round(sum(t for _, t in g4["tax_paid"]), 0)}}
    gk = dict(px_m=gpx_m, px_s=gpx_s, gains=ggains)
    nk = dict(px_m=px_m, px_s=px_s, gains=gains)
    wf = {"blend_vt11": chain("blend", gk, nk, {"expo": expo_bl}),
          "0001_alone": chain("mom_only", gk, nk, {}),
          "swing_alone": chain("sw_only", gk, nk, {}),
          "static_65_35": chain("static", {}, {}, {"weight": 0.65}),
          "index_vt11": chain("index_vt", {}, {}, {"expo": expo_ix})}
    out["step3_waterfall"] = {"order": "gross -> engine costs -> expense ratios -> wrapper trading costs -> tax",
                              "pass_through_note": "every step passes through the NET books' realised trades; "
                                                         "tax is off in every step but the last, so they only matter there", **wf}
    out["step3_waterfall"]["gross_book_check"] = {
        "momentum_gross_full_run_cagr_pct": gb["momentum_gross_metrics"]["cagr_pct"],
        "momentum_net_full_run_cagr_pct": mo["cagr_pct"]}

    # -------- STEP 4
    s4 = sleeve_stats(d, mt, led, idx)
    for k, w in (("0001", "0001_alone"), ("swing", "swing_alone")):
        s4[k]["pre_tax_cagr"] = wf[w]["pre_tax_cagr"]
        s4[k]["after_tax_cagr"] = wf[w]["after_tax_cagr"]
        s4[k]["after_to_pre_tax_ratio"] = round(wf[w]["after_tax_cagr"] / wf[w]["pre_tax_cagr"], 3)
    out["step4_by_sleeve"] = s4

    # -------- replica inputs (for Step 5)
    EXPORT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"mom_nav": px_m, "swing_nav": px_s, "exposure_e_t": expo_bl,
                  "liquid_px": pxl, "index_px": pxi}).to_csv(EXPORT / "daily.csv", index_label="date")
    mt[["ticker", "entry_date", "exit_date", "qty", "entry", "exit", "pnl", "reason"]].to_csv(EXPORT / "momentum_trades.csv", index=False)
    led[["tkr", "entry_date", "exit_date", "net_pnl", "reason"]].to_csv(EXPORT / "swing_ledger.csv", index=False)
    pd.DataFrame(R["blend_pre"]["book"].trades).to_csv(EXPORT / "_pipeline_blend_pre_trades.csv", index=False)
    pd.DataFrame(R["blend_after"]["book"].events).to_csv(EXPORT / "_pipeline_blend_after_events.csv", index=False)

    OUT_JSON.write_text(json.dumps(out, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
