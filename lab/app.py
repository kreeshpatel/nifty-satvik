"""Strategy Lab — a train-window playground for the weekly-swing engine.

    streamlit run lab/app.py

Streamlit is imported ONLY here (it is not a project dependency and CI does not have it). All numbers come
from `nq.lab.stats` / `nq.lab.runs`; this file only lays them out. Nothing here touches the live engine.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import altair as alt            # noqa: E402  (bundled with streamlit)
import numpy as np              # noqa: E402
import pandas as pd             # noqa: E402
import streamlit as st          # noqa: E402

from nq.brain import portfolio as PF                       # noqa: E402
from nq.lab import runs as L                               # noqa: E402
from nq.lab import stats as S                              # noqa: E402

BANNER = ("Train window only (to 2024-06-30). Nothing here changes the live engine. "
          "A promising result leaves the lab as a pre-registered screen.")

st.set_page_config(page_title="Strategy Lab", layout="wide")


# --------------------------------------------------------------------------- cached loaders
@st.cache_data(show_spinner="Loading Nifty (cut at 2024-06-30)...")
def _nifty() -> pd.Series:
    return L.load_nifty()


@st.cache_resource(show_spinner="Loading corrected universe (cut at 2024-06-30)...")
def _universe() -> dict:
    return L.load_cut_universe()


@st.cache_resource(show_spinner="Running the engine (cached by config hash)...")
def _replay(cfg_key: str, cfg_json: str) -> dict:
    import json
    return L.replay(json.loads(cfg_json))


@st.cache_data(show_spinner="Building the returns panel...")
def _returns_panel(_ohlcv: dict, key: str) -> pd.DataFrame:
    cols = {t: df["Close"].astype(float) for t, df in _ohlcv.items() if "Close" in df}
    px = pd.DataFrame(cols).sort_index()
    return px.pct_change(fill_method=None)


@st.cache_data(show_spinner="Correlation through time...")
def _corr_series(key: str, _plog: pd.DataFrame, _rets: pd.DataFrame) -> pd.DataFrame:
    dates = sorted(pd.to_datetime(_plog["date"]).unique())
    wk = pd.Series(dates, index=pd.DatetimeIndex(dates)).groupby(pd.Grouper(freq="W-FRI")).last().dropna()
    return S.correlation_timeseries(_plog, _rets, list(pd.DatetimeIndex(wk.to_numpy())), window=63)


def _pct(x: float, d: int = 1) -> str:
    return "n/a" if x is None or not np.isfinite(x) else f"{x * 100:.{d}f}%"


def _num(x: float, d: int = 2) -> str:
    return "n/a" if x is None or not np.isfinite(x) else f"{x:.{d}f}"


def _flag(cell: dict) -> None:
    if cell.get("uninformative"):
        st.caption(f":orange[uninformative: n = {cell.get('n')} is below the minimum "
                   f"({S.MIN_TRADES} trades / {S.MIN_SESSIONS} sessions) - read as a story, not a measurement]")


def _line(df: pd.DataFrame, title: str, fmt: str = ".2f", height: int = 220) -> alt.Chart:
    d = df.reset_index()
    d.columns = ["date"] + list(df.columns)
    d = d.melt("date", var_name="series", value_name="value")
    return (alt.Chart(d).mark_line().encode(x="date:T", y=alt.Y("value:Q", title=title),
                                            color="series:N",
                                            tooltip=["date:T", "series:N", alt.Tooltip("value:Q", format=fmt)])
            .properties(height=height))


# --------------------------------------------------------------------------- header + sidebar
st.title("Strategy Lab")
st.warning(BANNER)

with st.sidebar:
    st.header("Config")
    st.caption("Defaults = the live book. Change a control, press Run.")
    no_cap = st.checkbox("No ext cap", value=False)
    ext_cap = None if no_cap else st.slider("ext_cap (skip fills above SMA x (1+cap))", 0.05, 0.60, 0.20, 0.01)
    grade_gate = st.checkbox("Grade-A only (a_grade gate)", value=True)
    uncapped = st.checkbox("Uncapped (every signal, NAV ignored)", value=False)
    max_notional = st.slider("max_notional_pct", 0.05, 1.00, 0.20, 0.05)
    max_risk = st.slider("max_risk_pct (stop floor)", 0.03, 0.30, 0.10, 0.01)
    exit_mode = st.selectbox("exit", ["live", "base"], help="live = config P scaled exit; base = engine default exit")
    start = st.date_input("start", value=pd.Timestamp(L.MIN_START).date(),
                          min_value=pd.Timestamp(L.MIN_START).date(), max_value=pd.Timestamp("2023-12-31").date())
    pit = st.checkbox("Point-in-time membership filter (live)", value=True,
                      help="Off reproduces the committed diagnostics' anchor; on is what the live cron applies.")
    run = st.button("Run", type="primary", use_container_width=True)

cfg = {"ext_cap": ext_cap, "grade_gate": grade_gate, "uncapped": uncapped, "max_notional_pct": max_notional,
       "max_risk_pct": max_risk, "exit": exit_mode, "start": str(start), "pit_membership": pit}

if run:
    import json
    norm = L.normalize_config(cfg)
    with st.spinner("Replaying the engine (a few minutes the first time for a new config)..."):
        st.session_state["res"] = _replay(L.config_hash(norm), json.dumps(norm))

res = st.session_state.get("res")
tried = L.n_configs_tried()
c0, c1, c2, c3, c4 = st.columns(5)
c0.metric("configs tried", tried)
if res is None:
    st.info("Pick a config in the sidebar and press Run. The first run of a new config takes a few minutes.")
    st.stop()

nav: pd.Series = res["nav"]
ledger: pd.DataFrame = res["ledger"]
nifty = _nifty()
assert nav.index.max() <= pd.Timestamp(L.CUT) and nifty.index.max() <= pd.Timestamp(L.CUT)

tail = S.return_tail(nav)
dsr = L.deflated_sharpe(res["sharpe"], tail["n"], max(tried, 1))
c1.metric("Sharpe (raw)", _num(res["sharpe"]))
c2.metric("Sharpe (DEFLATED)", _num(dsr["deflated_sharpe"]),
          help=f"raw minus the expected best Sharpe of {tried} configs ({_num(dsr['sr0_annual'])}); DSR prob = {_num(dsr['dsr'])}")
c3.metric("DSR probability", _num(dsr["dsr"]), help="P(Sharpe beats the max expected from n configs); >= 0.95 to clear")
c4.metric("MaxDD", _pct(res["maxdd"]))
ran_note = "cached" if res["cached"] else "ran in %ss" % res["seconds"]
st.caption(f"hash {res['config_hash'][:12]} | {ran_note} | "
           f"{res['n_trades']} trades | last bar {res['last_bar']} | "
           f"{'uncapped: NAV is meaningless, read the ledger' if res['config']['uncapped'] else 'capital book'}")

tabs = st.tabs(["Overview", "Correlation & variance", "Market exposure", "Trade quality", "Return & tail"])

# --------------------------------------------------------------------------- Overview
with tabs[0]:
    both = pd.concat([nav.rename("Book"), nifty.rename("Nifty 50")], axis=1, join="inner").dropna()
    rebased = both / both.iloc[0] * 100
    st.subheader("NAV vs Nifty (rebased to 100)")
    st.altair_chart(_line(rebased, "rebased NAV", height=300), use_container_width=True)
    dd = (both / both.cummax() - 1).rename(columns={"Book": "Book DD", "Nifty 50": "Nifty DD"})
    st.subheader("Drawdown")
    st.altair_chart(_line(dd, "drawdown", fmt=".1%", height=220), use_container_width=True)
    st.caption("Book NAV is a fresh-capital run from the chosen start; it is a description, not a gate number "
               "(sub-period gates are continuous slices of one full run).")

# --------------------------------------------------------------------------- Correlation & variance
with tabs[1]:
    plog = res["position_log"]
    if plog.empty:
        st.info("No position log for this config.")
    else:
        rets = _returns_panel(_universe(), "universe")
        mkt_r = PF.daily_returns(nifty)
        wk = sorted(pd.to_datetime(plog["date"]).unique())
        weeks = pd.Series(wk, index=pd.DatetimeIndex(wk)).groupby(pd.Grouper(freq="W-FRI")).last().dropna()
        weeks = [pd.Timestamp(x) for x in weeks]
        i = st.slider("Week (Friday close)", 0, len(weeks) - 1, len(weeks) - 1,
                      format="%d", help="drag to choose the week; shows the held names' trailing 63-session correlation")
        d = weeks[i]
        st.write(f"**{d.date()}** - holdings and their trailing 63-session correlation")
        c = S.correlation_at(plog, rets, d, window=63, market=mkt_r)
        if c["n_names"] < 2:
            st.info(f"{c['n_names']} name(s) held - no correlation to show.")
        else:
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("names", c["n_names"])
            m2.metric("avg pairwise corr", _num(c["avg_pairwise_corr"]))
            m3.metric("effective bets", _num(c["effective_bets"]))
            m4.metric("diversification ratio", _num(c["diversification_ratio"]))
            m5.metric("top eigenvalue share", _pct(c["top_eigenvalue_share"], 0))
            _flag(c)
            cm = c["corr_matrix"].round(2)
            long = cm.reset_index().melt(cm.index.name or "index", var_name="b", value_name="corr")
            long.columns = ["a", "b", "corr"]
            heat = alt.Chart(long).mark_rect().encode(
                x=alt.X("a:N", title=None), y=alt.Y("b:N", title=None),
                color=alt.Color("corr:Q", scale=alt.Scale(domain=[-1, 1], scheme="redblue", reverse=True)),
                tooltip=["a", "b", "corr"])
            txt = alt.Chart(long).mark_text(fontSize=11).encode(x="a:N", y="b:N", text=alt.Text("corr:Q", format=".2f"))
            lc, rc = st.columns([3, 2])
            lc.altair_chart(heat + txt, use_container_width=True)
            vs = c["variance_shares"].copy()
            vs["weight"] = S.holdings_weights(plog, d).reindex(vs.index)
            rc.write("Variance share by position")
            rc.dataframe(vs[["weight", "share", "own", "cov"]].style.format("{:.1%}"), use_container_width=True)
            if np.isfinite(c["systematic_var_share"]):
                rc.write(f"Systematic (market) variance **{c['systematic_var_share']:.0%}** | "
                         f"idiosyncratic **{c['idiosyncratic_var_share']:.0%}** | beta to Nifty {_num(c['beta_to_market'])}")
        st.subheader("Through time (weekly)")
        ts = _corr_series(res["config_hash"], plog, rets)
        st.altair_chart(_line(ts[["avg_corr"]], "average pairwise correlation"), use_container_width=True)
        st.altair_chart(_line(ts[["effective_bets", "n_held"]], "effective bets vs names held"),
                        use_container_width=True)
        st.caption("Effective bets fall with fewer seats by construction (N / (1 + (N-1) rho)); compare against names held.")

# --------------------------------------------------------------------------- Market exposure
with tabs[2]:
    book_r = PF.daily_returns(nav)
    mx = S.market_exposure(book_r, PF.daily_returns(nifty), window=63)
    a, b, c_, d_ = st.columns(4)
    a.metric("beta", _num(mx["beta"]))
    b.metric("alpha (annual)", _pct(mx["alpha_annual"]))
    c_.metric("R squared", _num(mx["r2"]))
    d_.metric("sessions", mx["n"])
    _flag(mx)
    st.subheader("Rolling 63-session beta")
    st.altair_chart(_line(mx["rolling_beta"].to_frame(), "beta"), use_container_width=True)
    st.subheader("Correlation with the index: drawdown days vs normal days")
    cmp_ = pd.DataFrame({"days": ["index >=10% under 252d high", "all other days"],
                         "n": [mx["drawdown_days"]["n"], mx["normal_days"]["n"]],
                         "corr": [mx["dd_corr"], mx["calm_corr"]]})
    st.dataframe(cmp_.style.format({"corr": "{:.2f}"}), hide_index=True)
    if mx["drawdown_days"]["uninformative"] or mx["normal_days"]["uninformative"]:
        st.caption(":orange[a regime cell has fewer than 30 sessions - not a measurement]")

# --------------------------------------------------------------------------- Trade quality
with tabs[3]:
    closed = ledger[ledger["reason"] != "eos"] if len(ledger) else ledger
    tq = S.trade_quality(closed, _universe())
    _flag(tq)
    if tq["n"]:
        r = tq["R"]
        a, b, c_, d_, e_ = st.columns(5)
        a.metric("closed trades", tq["n"])
        b.metric("mean R", _num(r["mean"], 3))
        c_.metric("median R", _num(r["median"], 3))
        d_.metric("win rate", _pct(r["win_rate"]))
        e_.metric("R skew", _num(r["skew"]))
        st.write(f"R quantiles: 5% {_num(r['q05'])} | 25% {_num(r['q25'])} | 75% {_num(r['q75'])} | 95% {_num(r['q95'])}")
        st.altair_chart(alt.Chart(closed[["R"]]).mark_bar().encode(
            x=alt.X("R:Q", bin=alt.Bin(maxbins=40)), y="count()").properties(height=200), use_container_width=True)
        ex, ht, sk = tq.get("excursion") or {}, tq.get("hit_target") or {}, tq["streaks"]
        if ex:
            st.write(f"**Excursions (R of initial risk)** - MFE mean {_num(ex['mfe_r_mean'])} / median "
                     f"{_num(ex['mfe_r_median'])} | MAE mean {_num(ex['mae_r_mean'])} / median {_num(ex['mae_r_median'])} | "
                     f"capture (sum R / sum MFE) {_num(ex['capture_agg'])}, median per trade {_num(ex['capture_median'])}")
        if ht:
            st.write(f"**{ht['target_r']:.0f}R hit rate** {_pct(ht['hit_rate'])} vs driftless first-passage null "
                     f"{_pct(ht['null_rate'])} (excess {ht['excess'] * 100:+.1f}pp, n = {ht['n']}). "
                     "Only the excess is the entry's doing.")
        st.write(f"**Streaks** - longest win {sk['longest_win']} (expected under independence "
                 f"{_num(sk['expected_longest_win'], 1)}) | longest loss {sk['longest_loss']} "
                 f"(expected {_num(sk['expected_longest_loss'], 1)})")
        st.caption(sk["formula"])
        if "by_exit_reason" in tq:
            st.write("By exit reason")
            st.dataframe(tq["by_exit_reason"])
        if n_open := int((ledger["reason"] == "eos").sum()) if len(ledger) else 0:
            st.caption(f"{n_open} trade(s) still open at the cut are excluded here (marked at the cut).")

# --------------------------------------------------------------------------- Return & tail
with tabs[4]:
    _flag(tail)
    a, b, c_, d_ = st.columns(4)
    a.metric("Sharpe", _num(tail["sharpe"]))
    b.metric("Sortino", _num(tail["sortino"]))
    c_.metric("CAGR", _pct(tail["cagr"]))
    d_.metric("Calmar", _num(tail["calmar"]))
    e, f, g, h = st.columns(4)
    e.metric("MaxDD", _pct(tail["maxdd"]))
    f.metric("longest drawdown", f"{tail['longest_dd_sessions']} sessions")
    g.metric("VaR 95 (1d)", _pct(tail["var95"], 2))
    h.metric("CVaR 95 (1d)", _pct(tail["cvar95"], 2))
    lo, hi = tail["sharpe_ci"]
    st.write(f"Sharpe 95% block-bootstrap CI (63-session blocks): **[{_num(lo)}, {_num(hi)}]**")
    st.altair_chart(_line(tail["drawdown"].to_frame(), "drawdown", fmt=".1%"), use_container_width=True)
