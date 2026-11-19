"""MEASUREMENT: data-readiness audit v2 for a multi-signal cross-sectional model (2019 to mid-2024).

Owner request 2026-11-18, an owner-approved exception to the research freeze limited to this audit. It computes NO
signal, NO IC and NO return: only whether each data need exists, how much of the point-in-time Nifty 500 it covers,
and WHEN each item became public. Branch research/data-audit-v2.

DEFINITIONS (fixed before any number)
  PIT universe       nq.data.membership.load_membership(): names whose membership interval contains 30 June of the year
  coverage           names in the PIT universe of year y with >= 1 record dated in year y, over the universe size
  public timestamp   the date the item became public:
                       results    NSE corporates-financial-results broadCastDate (the exchange dissemination time)
                       meetings   board-meeting date (results are approved at the meeting; event_date in the calendar)
                       insider    NSE corporates-pit 'date' (the exchange broadcast) vs the trade's acqtoDt
                       SAST       NSE corporate-sast-reg29 'timestamp' vs acquirerDate
                       fundamentals pkl  available_date (a synthetic period_end + 90 days, not a filing timestamp)
  lag                public timestamp minus the period end the item describes, in calendar days: median and p95
  match (prices)     50 random (seeded) PIT-N500 names x 20 random sessions in 2019-2024: the daily close-to-close return
                     from the repo's prices (run_bhanushali_path1.corrected_universe, Yahoo-sourced, adjusted) vs NSE's
                     sec_bhavdata_full CLOSE_PRICE / PREV_CLOSE - 1 (NSE adjusts PREV_CLOSE for corporate actions).
                     A pair matches when the two returns differ by <= 0.10 percentage points. Pairs where either side
                     is missing are reported separately, not counted as mismatches.

Every NSE listing pull is cached under .cache/data_audit_v2/ (gitignored) and is month by month, 2019-01..2024-06.
Writes diagnostics/research/explore/2026-11-18_data_readiness_v2.json.

    python pipelines/diagnostics/audit_data_readiness_v2.py
"""
from __future__ import annotations

import io
import json
import random
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts"), str(ROOT / "pipelines" / "research")]
CACHE = ROOT / ".cache" / "data_audit_v2"
OUT = ROOT / "diagnostics" / "research" / "explore" / "2026-11-18_data_readiness_v2.json"
MONTHS = pd.period_range("2019-01", "2024-06", freq="M")
YEARS = range(2019, 2025)
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
      "Accept": "application/json,text/plain,*/*", "Referer": "https://www.nseindia.com/"}


def session() -> requests.Session:
    s = requests.Session()
    s.headers.update(UA)
    try:
        s.get("https://www.nseindia.com/", timeout=20)
    except requests.RequestException:
        pass
    return s


def pull(s, name: str, url_fmt: str) -> pd.DataFrame:
    """Month-by-month NSE API listing, cached per month."""
    d = CACHE / name
    d.mkdir(parents=True, exist_ok=True)
    frames = []
    for m in MONTHS:
        f = d / f"{m}.json"
        if not f.exists():
            a, b = m.start_time, m.end_time
            for attempt in range(3):
                try:
                    r = s.get(url_fmt.format(f=a.strftime("%d-%m-%Y"), t=b.strftime("%d-%m-%Y")), timeout=60)
                    j = r.json()
                    f.write_text(json.dumps(j), encoding="utf-8")
                    break
                except Exception:
                    time.sleep(3 * (attempt + 1))
                    s = session()
            time.sleep(1.2)
        if f.exists():
            j = json.loads(f.read_text(encoding="utf-8"))
            rows = j.get("data", []) if isinstance(j, dict) else j
            if rows:
                frames.append(pd.DataFrame(rows).assign(_month=str(m)))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def universe() -> dict[int, set]:
    from nq.data.membership import load_membership
    mem = load_membership()
    out = {}
    for y in YEARS:
        d = pd.Timestamp(f"{y}-06-30").date()
        out[y] = {t for t, iv in mem.items() if any(a <= d <= b for a, b in iv)}
    return out


def all_members() -> set:
    from nq.data.membership import load_membership
    mem = load_membership()
    lo, hi = pd.Timestamp("2019-01-01").date(), pd.Timestamp("2024-06-30").date()
    return {t for t, iv in mem.items() if any(a <= hi and b >= lo for a, b in iv)}


def coverage(sym_by_year: dict[int, set], U: dict[int, set]) -> dict:
    return {str(y): {"universe": len(U[y]), "covered": len(U[y] & sym_by_year.get(y, set())),
                     "pct": round(100 * len(U[y] & sym_by_year.get(y, set())) / len(U[y]), 1)} for y in YEARS}


def lag_stats(days: pd.Series) -> dict:
    x = pd.to_numeric(days, errors="coerce").dropna()
    return {"n": int(len(x)), "median_days": float(np.median(x)) if len(x) else None,
            "p95_days": float(np.percentile(x, 95)) if len(x) else None}


def by_year(df: pd.DataFrame, sym: str, date: str) -> dict[int, set]:
    d = df.dropna(subset=[date])
    return {y: set(d.loc[d[date].dt.year == y, sym]) for y in YEARS}


# ------------------------------------------------------------------ 1 sector
def audit_sector(U) -> dict:
    import config
    sm = config.SECTOR_MAP
    ever = all_members()
    return {"source": "config.py SECTOR_MAP (one label per ticker, no dates)", "labels": len(set(sm.values())),
            "tickers": len(sm), "coverage": {str(y): {"universe": len(U[y]), "covered": len(U[y] & set(sm)),
                                                      "pct": round(100 * len(U[y] & set(sm)) / len(U[y]), 1)} for y in YEARS},
            "delisted_or_dropped_members_covered": f"{len((ever - set().union(*[U[2024]])) & set(sm))} of {len(ever - U[2024])}",
            "point_in_time": "NO - a single current label applied to every date",
            "problem_sector_map": "themes -> sectors knowledge base; no ticker classification",
            "sector_intelligence": "sector-level monthly/daily return aggregates keyed by SECTOR_MAP labels; no ticker classification"}


# ------------------------------------------------------------------ 2 results
def audit_results(s, U) -> dict:
    out = {}
    # (a) fundamentals pkls
    for f in ("fundamentals_pit_screener.pkl", "fundamentals_pit_depth.pkl", "fundamentals_pit_backfill_20260729.pkl"):
        o = pd.read_pickle(ROOT / "data" / f)
        rows = []
        for t, df in o.items():
            for ad, r in df.iterrows():
                rows.append((t, pd.Timestamp(ad), pd.Timestamp(r["period_end"])))
        d = pd.DataFrame(rows, columns=["sym", "avail", "pe"])
        freq = d.groupby("sym")["pe"].apply(lambda x: x.sort_values().diff().dt.days.median()).median()
        out[f] = {"tickers": len(o), "columns": list(next(iter(o.values())).columns),
                  "period_ends": f"{d.pe.min().date()}..{d.pe.max().date()}",
                  "median_days_between_periods": float(freq), "lag": lag_stats((d.avail - d.pe).dt.days),
                  "coverage": coverage({y: set(d.loc[d.avail.dt.year == y, "sym"]) for y in YEARS}, U)}
    # (b) board-meeting calendar used by the loss diagnosis
    e = pd.read_parquet(ROOT / "data" / "_earnings_raw.parquet")
    e["ev"] = pd.to_datetime(e["event_date"], errors="coerce", format="%d-%b-%Y")
    e["ann"] = pd.to_datetime(e["ann_ts"], errors="coerce", format="%d-%b-%Y %H:%M:%S")
    res = e[e["purpose"].str.contains("Result", case=False, na=False)].copy()
    res["qend"] = (res["ev"] - pd.offsets.QuarterEnd(1)).dt.normalize()
    out["_earnings_raw.parquet"] = {"rows": int(len(e)), "results_rows": int(len(res)),
                                    "event_dates": f"{e.ev.min().date()}..{e.ev.max().date()}",
                                    "lag_meeting_minus_prior_quarter_end": lag_stats((res.ev - res.qend).dt.days),
                                    "intimation_lead_days": lag_stats((res.ev - res.ann).dt.days),
                                    "coverage": coverage(by_year(res, "symbol", "ev"), U),
                                    "line_items": "none - the calendar has dates and purposes only"}
    # (c) NSE financial-results filings with broadcast timestamps (2019-01..2024-06)
    fr = pull(s, "fin_results", "https://www.nseindia.com/api/corporates-financial-results?index=equities&from_date={f}&to_date={t}&period=Quarterly")
    if len(fr):
        fr["bc"] = pd.to_datetime(fr["broadCastDate"], errors="coerce", format="%d-%b-%Y %H:%M:%S")
        fr["pe"] = pd.to_datetime(fr["toDate"], errors="coerce", format="%d-%b-%Y")
        q = fr[(fr.pe.notna()) & ((fr.pe - pd.to_datetime(fr["fromDate"], errors="coerce", format="%d-%b-%Y")).dt.days < 100)]
        out["nse_financial_results_api"] = {
            "rows": int(len(fr)), "quarterly_rows": int(len(q)),
            "broadcast": f"{fr.bc.min()}..{fr.bc.max()}",
            "lag_broadcast_minus_period_end": lag_stats((q.bc - q.pe).dt.days),
            "with_xbrl_link": int((fr["xbrl"].astype(str).str.startswith("http")).sum()),
            "consolidated_share": round(float((fr["consolidated"] == "Consolidated").mean()), 3),
            "coverage": coverage(by_year(q, "symbol", "bc"), U)}
        out["broadcast_vs_board_meeting"] = broadcast_vs_meeting(q, res)
    return out


def broadcast_vs_meeting(q: pd.DataFrame, res: pd.DataFrame) -> dict:
    """ADDED 2026-11-18 (owner follow-up): gap between the NSE results broadcast and the board-meeting date in
    _earnings_raw, and the broadcast time of day - does it resolve 0128's 'no release time' blocker?

    Match: same symbol; the meeting whose event_date is the latest on or before the broadcast date and no more than
    10 days before it (a results broadcast follows its approving meeting). One broadcast per (symbol, period end):
    the earliest (standalone and consolidated files of one meeting usually broadcast minutes apart).
    Time of day buckets (IST): pre-open < 09:15, market 09:15-15:30, post-close > 15:30."""
    b = q.dropna(subset=["bc"]).sort_values("bc").groupby(["symbol", "pe"], as_index=False).first()
    m = res.dropna(subset=["ev"])[["symbol", "ev"]].drop_duplicates().sort_values("ev")
    j = pd.merge_asof(b.sort_values("bc").assign(bcd=lambda x: x.bc.dt.normalize()), m.rename(columns={"ev": "meet"}),
                      left_on="bcd", right_on="meet", by="symbol", direction="backward", tolerance=pd.Timedelta(days=10))
    jm = j.dropna(subset=["meet"])
    gap = (jm.bcd - jm.meet).dt.days
    tod = j.bc.dt.hour * 60 + j.bc.dt.minute
    win = (j.bc >= "2019-01-01") & (j.bc <= "2024-06-30")
    return {"broadcasts_one_per_symbol_period": int(len(b)), "matched_to_meeting": int(len(jm)),
            "match_rate_pct": round(100 * len(jm) / len(b), 1) if len(b) else None,
            "gap_days_broadcast_minus_meeting": {"same_day_pct": round(100 * float((gap == 0).mean()), 1),
                                                 "next_day_pct": round(100 * float((gap == 1).mean()), 1),
                                                 "2plus_days_pct": round(100 * float((gap >= 2).mean()), 1),
                                                 "median": float(gap.median()), "p95": float(gap.quantile(0.95))},
            "time_of_day_ist_pct": {"pre_open_lt_0915": round(100 * float((tod[win] < 555).mean()), 1),
                                    "market_0915_1530": round(100 * float(((tod[win] >= 555) & (tod[win] <= 930)).mean()), 1),
                                    "post_close_gt_1530": round(100 * float((tod[win] > 930).mean()), 1)},
            "seconds_resolution": "broadCastDate carries HH:MM:SS (exchange dissemination time)"}


# ------------------------------------------------------------------ 3 index
def audit_index(U) -> dict:
    tw = pd.read_csv(ROOT / "data" / "nse_circulars" / "transitions_wayback.csv", parse_dates=["effective_date"])
    return {"repo_nifty500_transitions": {"file": "data/nse_circulars/transitions_wayback.csv", "rows": int(len(tw)),
                                          "effective": f"{tw.effective_date.min().date()}..{tw.effective_date.max().date()}",
                                          "announcement_date": "absent (effective date only)"}}


# ------------------------------------------------------------------ 4 surveillance
def audit_surveillance(s) -> dict:
    c = pull(s, "circulars_surv", "https://www.nseindia.com/api/circulars?fromDate={f}&toDate={t}&dept=SURV")
    out = {}
    if len(c):
        c["dt"] = pd.to_datetime(c["cirDate"], format="%Y%m%d", errors="coerce")
        for k, pat in (("ASM", "Additional Surveillance"), ("GSM", "Graded Surveillance")):
            g = c[c["sub"].str.contains(pat, case=False, na=False)]
            out[f"{k}_circulars"] = {"n": int(len(g)), "by_year": g.dt.dt.year.value_counts().sort_index().to_dict(),
                                     "attachments": g["fileExt"].value_counts().to_dict()}
    raw = sorted((ROOT / ".cache" / "nse_bands" / "raw").glob("sec_list_*.csv"))
    gsm = 0
    for f in raw:
        d = pd.read_csv(f, dtype=str, encoding="latin-1")
        d.columns = [x.strip() for x in d.columns]
        gsm += int(d["Remarks"].fillna("").str.contains("GSM", case=False).sum())
    out["gsm_in_daily_band_files"] = {"files": len(raw), "first": raw[0].stem[-8:] if raw else None,
                                      "last": raw[-1].stem[-8:] if raw else None, "gsm_rows": gsm}
    return out


# ------------------------------------------------------------------ 5 insider / SAST / pledge
def audit_insider(s, U) -> dict:
    out = {}
    pit = pull(s, "pit", "https://www.nseindia.com/api/corporates-pit?index=equities&from_date={f}&to_date={t}")
    if len(pit):
        pit["bc"] = pd.to_datetime(pit["date"], errors="coerce", format="%d-%b-%Y %H:%M")
        pit["trade"] = pd.to_datetime(pit["acqtoDt"], errors="coerce", format="%d-%b-%Y")
        prom = pit[pit["personCategory"].astype(str).str.contains("Promoter", case=False)]
        out["pit_reg7"] = {"rows": int(len(pit)), "promoter_rows": int(len(prom)), "broadcast": f"{pit.bc.min()}..{pit.bc.max()}",
                           "lag_broadcast_minus_trade": lag_stats((pit.bc.dt.normalize() - pit.trade).dt.days),
                           "modes": pit["acqMode"].value_counts().head(6).to_dict(),
                           "coverage_any_disclosure": coverage(by_year(pit, "symbol", "bc"), U)}
    sast = pull(s, "sast29", "https://www.nseindia.com/api/corporate-sast-reg29?index=equities&from_date={f}&to_date={t}")
    if len(sast):
        sast["bc"] = pd.to_datetime(sast["timestamp"], errors="coerce", format="%d-%b-%Y %H:%M")
        # acquirerDate is 'DD-MON-YYYY' or 'DD-MON-YYYY to DD-MON-YYYY': the last date is the end of the acquisition
        sast["trade"] = pd.to_datetime(sast["acquirerDate"].astype(str).str.split(" to ").str[-1].str.strip(),
                                       errors="coerce", format="%d-%b-%Y")
        out["sast_reg29"] = {"rows": int(len(sast)), "broadcast": f"{sast.bc.min()}..{sast.bc.max()}",
                             "lag_broadcast_minus_acquisition": lag_stats((sast.bc.dt.normalize() - sast.trade).dt.days),
                             "coverage_any_disclosure": coverage(by_year(sast, "symbol", "bc"), U)}
    return out


# ------------------------------------------------------------------ 6 prices
def audit_prices(U) -> dict:
    from run_bhanushali_path1 import corrected_universe
    px = corrected_universe()
    ever = all_members()
    dropped = ever - U[2024]
    out = {"price_tickers": len(px), "pit_members_2019_2024": len(ever),
           "members_with_prices": len(ever & set(px)), "members_dropped_by_2024": len(dropped),
           "dropped_with_prices": len(dropped & set(px)),
           "adjustment": "yfinance auto_adjust=True (splits, bonuses and dividends back-adjusted) plus carried corrections "
                         "(corporate_actions_*.csv, delisted_alias_map.json)"}
    for y in YEARS:
        out[f"coverage_{y}"] = f"{len(U[y] & set(px))}/{len(U[y])}"
    rng = random.Random(20261118)
    names = sorted(ever & set(px))
    days = pd.bdate_range("2019-01-02", "2024-06-28")
    sample_names = rng.sample(names, 50)
    sample_days = sorted(rng.sample(list(days), 20))
    s = requests.Session()
    s.headers.update({"User-Agent": UA["User-Agent"], "Referer": "https://www.nseindia.com/"})
    rows = []
    bdir = CACHE / "bhav"
    bdir.mkdir(parents=True, exist_ok=True)
    for d in sample_days:
        f = bdir / f"{d:%Y%m%d}.csv"
        if not f.exists():
            r = s.get(f"https://archives.nseindia.com/products/content/sec_bhavdata_full_{d:%d%m%Y}.csv", timeout=60)
            if r.status_code == 200 and not r.content.lstrip().startswith(b"<"):
                f.write_bytes(r.content)
            time.sleep(1)
        bh = None
        if f.exists():
            bh = pd.read_csv(f, dtype=str)
            bh.columns = [c.strip() for c in bh.columns]
            bh = bh[bh["SERIES"].str.strip().isin(["EQ", "BE", "BZ"])]
            bh = bh.set_index(bh["SYMBOL"].str.strip())
        for t in sample_names:
            df = px[t]
            idx = pd.DatetimeIndex(df.index).normalize()
            cl = pd.Series((df["Close"] if "Close" in df else df["close"]).to_numpy(), index=idx)
            y_ret = None
            if d in cl.index:
                k = cl.index.get_loc(d)
                if isinstance(k, (int, np.integer)) and k > 0:
                    y_ret = float(cl.iloc[k] / cl.iloc[k - 1] - 1)
            b_ret = None
            if bh is not None and t in bh.index:
                rr = bh.loc[t]
                if isinstance(rr, pd.DataFrame):
                    rr = rr.iloc[0]
                try:
                    b_ret = float(rr["CLOSE_PRICE"]) / float(rr["PREV_CLOSE"]) - 1
                except (ValueError, ZeroDivisionError):
                    b_ret = None
            rows.append({"tkr": t, "date": str(d.date()), "yahoo": y_ret, "bhav": b_ret})
    m = pd.DataFrame(rows)
    both = m.dropna(subset=["yahoo", "bhav"])
    diff = (both.yahoo - both.bhav).abs() * 100
    # 2024-01-22 was an unscheduled NSE holiday; a session missing on either side shifts the previous close
    ex = both[both.date != "2024-01-23"]
    dx = (ex.yahoo - ex.bhav).abs() * 100
    out["match_test_excl_2024_01_23"] = {"pairs": int(len(ex)), "match_rate_pct": round(100 * float((dx <= 0.10).mean()), 1),
                                         "mismatches": ex.assign(diff_pp=dx)[dx > 0.10].to_dict("records")}
    out["match_test"] = {"pairs": int(len(m)), "both_present": int(len(both)),
                         "missing_yahoo": int(m.yahoo.isna().sum()), "missing_bhav": int(m.bhav.isna().sum()),
                         "match_le_0p10pp": int((diff <= 0.10).sum()),
                         "match_rate_pct": round(100 * float((diff <= 0.10).mean()), 1) if len(both) else None,
                         "match_le_0p50pp": int((diff <= 0.50).sum()),
                         "worst": both.assign(diff_pp=diff).sort_values("diff_pp", ascending=False).head(5).to_dict("records"),
                         "bhav_days_fetched": int(sum(1 for d in sample_days if (bdir / f"{d:%Y%m%d}.csv").exists()))}
    return out


def main() -> int:
    CACHE.mkdir(parents=True, exist_ok=True)
    U = universe()
    s = session()
    res = {"universe_sizes": {str(y): len(U[y]) for y in YEARS}}
    res["1_sector"] = audit_sector(U)
    print("sector done", flush=True)
    res["2_results"] = audit_results(s, U)
    print("results done", flush=True)
    res["3_index"] = audit_index(U)
    res["4_surveillance"] = audit_surveillance(s)
    print("surveillance done", flush=True)
    res["5_insider"] = audit_insider(s, U)
    print("insider done", flush=True)
    res["6_prices"] = audit_prices(U)
    OUT.write_text(json.dumps(res, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps(res, indent=1, default=str)[:12000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
