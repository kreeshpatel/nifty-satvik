"""Step-2 AUDIT GATE for the 0118 delivery screen (pre-reg: the screen is INVALID unless this passes).

Checks, in order: (1) per-year coverage of the substrate's trades (delivery features joinable at the
signal-week Friday), incl. DELISTED-name presence; (2) the MTO <-> sec_bhavdata seam: same-day
cross-fetch on overlap dates, deliv_pct definition drift; (3) spot-checks of parsed values against the
raw published file text; (4) the invalidation clause: if coverage holes correlate with outcomes,
REPORT AND STOP.

    python scripts/diag_delivery_audit.py
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from nq.data.delivery import DELIVERY_RAW_PATH, apply_alias_map  # noqa: E402

CTX = ROOT / "research" / "substrate" / "context_windows.parquet"
HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Referer": "https://www.nseindia.com/"}


def main() -> int:
    raw = apply_alias_map(pd.read_parquet(DELIVERY_RAW_PATH))
    raw["date"] = pd.to_datetime(raw["date"]).astype("datetime64[ns]")
    t = pd.read_parquet(CTX)
    col = {c.lower(): c for c in t.columns}
    t["entry_date"] = pd.to_datetime(t[col["entry_date"]])
    t["sig_fri"] = t["entry_date"] - pd.to_timedelta(t["entry_date"].dt.weekday + 3, unit="D")
    t = t[t["entry_date"] >= "2019-01-01"]
    have = set(zip(raw["symbol"], raw["date"]))
    sym_days = raw.groupby("symbol")["date"].agg(["min", "max", "count"])

    # 1. coverage: a trade is covered if its symbol has >=10 delivery rows in the 30 cal-days before sig_fri
    def covered(r):
        s = r[col["ticker"]]
        if s not in sym_days.index:
            return False
        g = raw[raw["symbol"] == s]
        return int(((g["date"] <= r["sig_fri"]) & (g["date"] > r["sig_fri"] - pd.Timedelta(days=30))).sum()) >= 10
    # vectorized approximation: per-symbol sorted date arrays
    arr = {s: g["date"].to_numpy() for s, g in raw.groupby("symbol")}
    cov = []
    for _, r in t.iterrows():
        a = arr.get(r[col["ticker"]])
        if a is None:
            cov.append(False); continue
        lo = np.searchsorted(a, np.datetime64(r["sig_fri"] - pd.Timedelta(days=30)), "right")
        hi = np.searchsorted(a, np.datetime64(r["sig_fri"]), "right")
        cov.append((hi - lo) >= 10)
    t["cov"] = cov
    print("=== 1. per-year coverage (trades with joinable pre-entry delivery data) ===")
    tab = t.groupby(t["entry_date"].dt.year)["cov"].agg(["count", "mean"])
    tab["mean"] = (tab["mean"] * 100).round(1)
    print(tab.rename(columns={"count": "trades", "mean": "coverage_%"}).to_string())
    # delisted presence: names whose delivery data ENDS >60d before the raw max are delisted-in-window
    ended = sym_days[sym_days["max"] < raw["date"].max() - pd.Timedelta(days=60)]
    print(f"\ndelisted-in-window symbols present in raw: {len(ended)} (data continues to their last trading day)")
    # invalidation check: does coverage correlate with outcome?
    r_cov = t[t["cov"]][col["r"]].mean(); r_unc = t[~t["cov"]][col["r"]].mean() if (~t["cov"]).any() else np.nan
    print(f"meanR covered {r_cov:+.3f} vs uncovered {r_unc:+.3f} | uncovered n={int((~t['cov']).sum())}")

    # 2. seam cross-check: same-day MTO vs sec_bhavdata for 3 overlap dates
    print("\n=== 2. MTO <-> sec_bhavdata seam cross-check ===")
    from harvest_delivery import _url_mto, _url_sec, parse_mto, parse_sec  # noqa: E402
    sess = requests.Session()
    for ds in ("2020-09-15", "2021-03-10", "2022-01-12"):
        d = pd.Timestamp(ds)
        a = sess.get(_url_mto(d), headers=HDR, timeout=30); b = sess.get(_url_sec(d), headers=HDR, timeout=30)
        if a.status_code != 200 or b.status_code != 200:
            print(f"  {ds}: fetch miss (mto {a.status_code} / sec {b.status_code})"); continue
        m = parse_mto(a.text, d).set_index("symbol")["deliv_pct"]
        s2 = parse_sec(b.text, d).set_index("symbol")["deliv_pct"]
        j = m.to_frame("mto").join(s2.rename("sec"), how="inner").dropna()
        diff = (j["mto"] - j["sec"]).abs()
        print(f"  {ds}: {len(j)} common symbols | mean|diff| {diff.mean():.3f}pp | max {diff.max():.2f}pp "
              f"| identical(<0.05pp) {(diff<0.05).mean()*100:.0f}%")

    # 3. spot-checks: parsed vs raw text for 2 name-days
    print("\n=== 3. spot-checks (parsed vs raw file text) ===")
    d = pd.Timestamp("2019-06-14")
    a = sess.get(_url_mto(d), headers=HDR, timeout=30)
    m = parse_mto(a.text, d)
    for sym in ("RELIANCE", "TCS"):
        row = m[m["symbol"] == sym]
        rawline = [ln for ln in a.text.splitlines() if ln.startswith("20,") and f",{sym}," in ln][:1]
        print(f"  {sym} {d.date()}: parsed {row['deliv_pct'].iloc[0] if len(row) else 'NA'} | raw: {rawline}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
