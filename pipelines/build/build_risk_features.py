"""Build data/risk_features.parquet: the L5 crash-risk feature and label panel (nq/data/risk_features.py).

Data engineering and measurement only. No model, no AUC, no feature-label statistic. The only label statistics
reported are base rates and sample sizes, so the L5 study can be planned honestly.

  python pipelines/build/build_risk_features.py

Writes data/risk_features.parquet (gitignored) and diagnostics/research/explore/2026-11-21_risk_features.json.
"""
from __future__ import annotations

import glob
import gzip
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "pipelines" / "build")]
from nq.data import risk_features as RF  # noqa: E402

OUT = ROOT / "data" / "risk_features.parquet"
SUMMARY = ROOT / "diagnostics" / "research" / "explore" / "2026-11-21_risk_features.json"
BANDS_RAW = ROOT / ".cache" / "nse_bands" / "raw"
SURV = ROOT / "data" / "surv_raw"
SHP = ROOT / "data" / "shp_raw"
START = "2017-01-01"


# ---------------------------------------------------------------------------------------------- inputs
def market():
    from nq.data.membership import load_membership
    from nq.data.ohlcv import clean_ohlcv_dict, load_ohlcv_cache
    d = dict(pd.read_pickle(ROOT / "data" / "ohlcv_backfill.pkl"))
    d.update(load_ohlcv_cache())
    d = clean_ohlcv_dict(d)
    close = pd.DataFrame({k: v["Close"] for k, v in d.items()}).sort_index().loc["2016-01-01":]
    vol = pd.DataFrame({k: v["Volume"] for k, v in d.items()}).reindex_like(close)
    mem = load_membership() or {}
    member = pd.DataFrame(False, index=close.index, columns=close.columns)
    for s in close.columns:
        for a, b in mem.get(s.upper(), []):
            member.loc[pd.Timestamp(a):pd.Timestamp(b), s] = True
    return close, vol, member


def bands_inputs():
    hit = pd.read_parquet(ROOT / "data" / "nse_bands" / "band_hitters.parquet")
    rows = []
    for f in sorted(glob.glob(str(BANDS_RAW / "sec_list_*.csv"))):
        d = pd.Timestamp(Path(f).stem.split("_")[-1])
        x = pd.read_csv(f, dtype=str, encoding="latin-1")
        x.columns = [c.strip() for c in x.columns]
        rows.append(pd.DataFrame({"date": d, "symbol": x["Symbol"].str.strip(), "series": x["Series"].str.strip(),
                                  "band_pct": pd.to_numeric(x["Band"], errors="coerce"),
                                  "remarks": x.get("Remarks", pd.Series(dtype=str)).astype(str).str.strip()}))
    return hit, pd.concat(rows, ignore_index=True)


ASM_CACHE = ROOT / ".cache" / "asm_snapshots.pkl"


def asm_events() -> pd.DataFrame:
    """ASM stage events from the circulars' CONSOLIDATED sheets (the full list in force after each circular).

    - Framework per circular: ST-ASM if the file or subject says short-term; LT-ASM otherwise. The IBC and ICA
      frameworks are out of scope and skipped.
    - Each consolidated sheet is a complete snapshot of its framework. A symbol absent from the latest snapshot is
      out of that framework.
    - Two dates per circular:
      - pub_date: the circular date (NSE gives a date only, no time);
      - eff_date: the "w.e.f." date in the sheet titles (the circular date if none is stated).
      Snapshots are applied in publication order. `date` (the known-at date used for the Friday close) is pub_date;
      days-in-stage counts from eff_date.
    - Combined stage = max over frameworks, coded 10+k for ST stage k and 20+k for LT stage k (LT outranks ST); 0
      means in neither.
    - Events are emitted only when a symbol's combined stage changes.
    """
    import pickle
    cache = pickle.loads(ASM_CACHE.read_bytes()) if ASM_CACHE.exists() else {}
    snaps, skipped, circ = [], [], []
    for d in sorted((SURV / "asm").glob("*")):
        meta = json.loads((d / "meta.json").read_text(encoding="utf-8")) if (d / "meta.json").exists() else {}
        if meta.get("status") != 200:
            continue
        pub = pd.Timestamp(str(meta["cirDate"]))
        sub = str(meta.get("sub", "")).upper()
        for f in d.iterdir():
            if f.suffix.lower() not in (".xlsx", ".xls"):
                continue
            nm = f.name.upper().replace(" ", "")
            if "IBC" in nm or "ICA" in nm or " IBC" in sub or " ICA" in sub:
                continue
            fw = "ST" if ("_ST" in nm or "SHORT" in sub or "ST-ASM" in sub.replace(" ", "")) else "LT"
            key = (str(f), f.stat().st_mtime)
            if key not in cache or cache[key][0] == "ERR" or cache[key][1] is None:
                try:
                    cache[key] = parse_asm_consolidated(f)
                except Exception as e:  # noqa: BLE001 - counted in the summary, never silently dropped
                    cache[key] = ("ERR", type(e).__name__)
            snap, wef = cache[key]
            if snap == "ERR":
                skipped.append(f"{d.name}/{f.name}:{wef}")
                continue
            circ.append((d.name, fw, pub, wef))
            if snap is None:
                skipped.append(f"{d.name}/{f.name}:no-consolidated-sheet")
                continue
            snaps.append((pub, int(d.name), fw, snap, wef if wef is not None else pub))
    ASM_CACHE.parent.mkdir(exist_ok=True)
    ASM_CACHE.write_bytes(pickle.dumps(cache))
    snaps.sort(key=lambda x: (x[0], x[1]))
    state = {"ST": {}, "LT": {}}
    cur, ev = {}, []
    for pub, cno, fw, snap, eff in snaps:
        state[fw] = snap
        comb = {}
        for k, off in (("ST", 10), ("LT", 20)):
            for s, n in state[k].items():
                comb[s] = max(comb.get(s, 0), off + n)
        for s in set(cur) | set(comb):
            if comb.get(s, 0) != cur.get(s, 0):
                ev.append((s, pub, eff, float(comb.get(s, 0)), cno))
        cur = comb
    out = pd.DataFrame(ev, columns=["symbol", "date", "eff_date", "stage", "circular"])
    out.attrs["skipped"] = skipped
    out.attrs["snapshots"] = len(snaps)
    out.attrs["circulars"] = pd.DataFrame(circ, columns=["circular", "framework", "pub_date", "eff_date"])
    return out


WEF_RE = re.compile(r"W\.?\s*E\.?\s*F\.?\s*([A-Z]{3,9}\.?\s*\d{1,2}\s*,?\s*\d{4})", re.I)


def parse_asm_consolidated(f: Path):
    """Return ({symbol: stage}, wef) from the consolidated sheet (name contains CONSOL; IBC/ICA consolidated sheets
    excluded), or (None, wef) if there is none."""
    sheets = pd.read_excel(f, sheet_name=None, header=None)
    wef = None
    for raw in sheets.values():
        for v in raw.astype(str).to_numpy().ravel():
            m = WEF_RE.search(str(v))
            if m:
                t = pd.to_datetime(re.sub(r"[.,\s]+", " ", m.group(1)).strip(), errors="coerce")
                if pd.notna(t):
                    wef = t
                    break
        if wef is not None:
            break
    name = next((n for n in sheets if "CONSOL" in str(n).upper() and not any(k in str(n).upper() for k in ("IBC", "ICA"))),
                None)
    if name is None:
        return None, wef
    raw = sheets[name].astype(str)
    hdr = next(i for i in range(min(len(raw), 15)) if raw.iloc[i].str.upper().str.strip().eq("SYMBOL").any())
    cols = [str(c).strip().upper() for c in raw.iloc[hdr]]
    symc = cols.index("SYMBOL")
    stc = next((i for i, c in enumerate(cols) if "STAGE" in c), None)
    snap = {}
    for r in raw.iloc[hdr + 1:].itertuples(index=False):
        s = str(r[symc]).strip().upper()
        if not s or s in ("NAN", "NONE") or len(s) > 20 or " " in s:
            continue
        st = str(r[stc]).strip().upper() if stc is not None else "I"
        st = re.sub(r"[^IV0-9]", "", st.replace("STAGE", ""))
        n = RF.ROMAN.get(st, int(st) if st.isdigit() else 1)
        snap[s] = max(snap.get(s, 0), n)
    return snap, wef


def pledge_rows() -> pd.DataFrame:
    """One row per shareholding filing: symbol, known_ts, pledge_pct, reason, as_on.

    NSE lists only the latest version of each filing. Its broadcastDate is the latest (re-)broadcast: revisions, and a
    bulk re-broadcast that stamped most 2021 filings with 2022 dates. So the known time is:
    - unrevised filing: the XML is the original content, public on submission (date only, no time). Known from
      submissionDate + 1 day 00:00, i.e. counted at the close of the next calendar day at the earliest; capped by
      broadcastDate if that is earlier;
    - revised filing: this XML's values became public only at the revision broadcast, so known from broadcastDate."""
    meta = {}
    for f in sorted((SHP / "lists").glob("*.json")):
        for r in json.loads(f.read_text(encoding="utf-8")):
            meta[str(r.get("recordId"))] = r
    out = []
    for f in sorted((SHP / "xml").glob("*.xml.gz")):
        rid = f.name.split(".")[0]
        m = meta.get(rid)
        if not m:
            continue
        pct, why = parse_pledge(gzip.decompress(f.read_bytes()).decode("utf-8", "ignore"))
        bt = pd.to_datetime(m.get("broadcastDate"), format="%d-%b-%Y %H:%M:%S", errors="coerce")
        sd = pd.to_datetime(m.get("submissionDate"), format="%d-%b-%Y", errors="coerce")
        revised = str(m.get("revisedStatus") or "").strip().lower() == "revised"
        known = bt if (revised or pd.isna(sd)) else min(sd + pd.Timedelta(days=1), bt) if pd.notna(bt) else sd + pd.Timedelta(days=1)
        out.append((str(m.get("symbol")).upper(), known, pct, why, m.get("date"), revised, rid))
    return pd.DataFrame(out, columns=["symbol", "broadcast_ts", "pledge_pct", "reason", "as_on", "revised", "record_id"])


def parse_pledge(xml: str) -> tuple[float, str]:
    """Return (promoter pledged-or-encumbered %, source code).

    Promoter context = the XBRL context whose only dimension member is ShareholdingOfPromoterAndPromoterGroup*
    (Table I, the promoter-group total). Two filing formats:
    - to mid-2025: PledgedOrEncumberedNumberOfShares, and PledgedOrEncumberedSharesHeldAsPercentageOfTotalNumberOfShares
      in percent (BCG Dec-2020: 59,544,862 / 186,627,685 = 31.91%, equal to the filed 31.91);
    - from mid-2025: NumberOfSharesEncumbered (pledge + NDU + other encumbrance, the same scope as the old field), and
      EncumberedSharesHeldAsPercentageOfTotalNumberOfShares as a FRACTION (RAYMONDLSL 2026: 5,508,676 / 35,470,444 =
      15.53%, filed 0.1553). The new format omits the numbers entirely when its yes/no flags are all "false".
    pct = 100 x encumbered / promoter NumberOfShares; else the filed percentage tag (fraction x 100 for the new tag).

    Codes. Filed values: "filed_number" and "filed_pct" (a filed 0 is a real 0), and "declared_none" (0.0: every
    promoter pledge/encumbrance yes/no flag says false and no number was filed - an explicit declaration, set to 0 by
    owner decision 2026-11-20). Genuinely missing, NaN never 0: "flag_true_no_field", "blank_field",
    "no_promoter_context", "missing_field"."""
    prom = set()
    for cid, body in re.findall(r'<xbrli:context id="([^"]+)">(.*?)</xbrli:context>', xml, re.S):
        mem = re.findall(r"<xbrldi:explicitMember[^>]*>([^<]+)<", body)
        if len(mem) == 1 and mem[0].split(":")[-1].startswith("ShareholdingOfPromoterAndPromoterGroup"):
            prom.add(cid)
    if not prom:
        return np.nan, "no_promoter_context"

    def raw(tag):  # every value of tag in a promoter context; None = self-closing/nil, "" = blank
        out = []
        for m in re.finditer(rf'<[\w-]+:{tag}\s([^>]*?)(/>|>([^<]*)</)', xml):
            c = re.search(r'contextRef="([^"]+)"', m.group(1))
            if c and c.group(1) in prom:
                out.append(None if m.group(2) == "/>" else m.group(3).strip())
        return out

    def num(vals):
        v = [x for x in vals if x not in (None, "")]
        return float(v[0].replace(",", "")) if v else None

    held = num(raw("NumberOfShares"))
    seen_blank = False
    for n_tag, p_tag, scale in (("PledgedOrEncumberedNumberOfShares",
                                 "PledgedOrEncumberedSharesHeldAsPercentageOfTotalNumberOfShares", 1.0),
                                ("NumberOfSharesEncumbered", "EncumberedSharesHeldAsPercentageOfTotalNumberOfShares",
                                 100.0)):
        n_raw, p_raw = raw(n_tag), raw(p_tag)
        n, p = num(n_raw), num(p_raw)
        if n is not None and held:
            return 100.0 * n / held, "filed_number"
        if p is not None:
            return p * scale, "filed_pct"
        seen_blank |= bool(n_raw or p_raw)
    if seen_blank:
        return np.nan, "blank_field"
    flags = re.findall(r"<[\w-]+:WhetherAnySharesHeldByPromoters(?:ArePledgeOrOtherwiseEncumbered|AreEncumbered)"
                       r"(\w*)[^>]*>\s*(true|false)\s*<", xml)
    prom_flags = [v for name, v in flags if name in ("", "ForPromoterAndPromoterGroup")
                  or name.endswith("ForPromoterAndPromoterGroup")]
    if prom_flags and all(v == "false" for v in prom_flags):
        return 0.0, "declared_none"      # explicit filed declaration: 0 (owner decision 2026-11-20)
    if any(v == "true" for v in prom_flags):
        return np.nan, "flag_true_no_field"
    return np.nan, "missing_field"


def fundamentals_inputs():
    from nq.data.fundamentals_q import company_key
    view = pd.read_parquet(ROOT / "data" / "fundamentals_q_features.parquet")
    d = pd.read_parquet(ROOT / "data" / "results_xbrl.parquet",
                        columns=["symbol", "isin", "period_end", "consolidated", "context_role", "broadcast_ts",
                                 "bs_borrowings_current", "bs_borrowings_noncurrent", "bs_total_equity"])
    d["company"] = company_key(d["isin"], d["symbol"])
    prim = view.drop_duplicates("company").set_index("company")["primary_basis"]
    d = d[d["bs_total_equity"].notna() & (d["context_role"] == "current")]
    d = d[(d["consolidated"].astype(bool)) == (d["company"].map(prim) == "consolidated")]
    bs = d.rename(columns={"bs_borrowings_current": "borrowings_current",
                           "bs_borrowings_noncurrent": "borrowings_noncurrent", "bs_total_equity": "total_equity"})
    sym2co = view.sort_values("broadcast_ts").drop_duplicates("symbol", keep="last").set_index("symbol")["company"].to_dict()
    return view[view["version"] >= 0], bs, sym2co


# ---------------------------------------------------------------------------------------------- build
def build() -> dict:
    close, vol, member = market()
    sessions = close.index
    dates = RF.fridays(sessions[sessions >= START])
    if dates[-1] == sessions[-1] and dates[-1].weekday() != 4:   # the data ends mid-week: drop the partial week
        dates = dates[:-1]
    syms = list(close.columns)
    parts = {"price": RF.price_features(close, vol, member, dates)}
    hit, bands = bands_inputs()
    parts["bands"] = RF.band_features(hit, bands, sessions, dates, syms)
    ev = asm_events()
    asm_err = len(ev.attrs.get("skipped", []))
    asm_circ = ev.attrs["circulars"]
    ev = ev.dropna(subset=["symbol"]).copy()
    ev.attrs.clear()                      # attrs hold a DataFrame; parquet would try to serialise it
    ev[["symbol", "date", "eff_date", "stage", "circular"]].to_parquet(ROOT / "data" / "asm_events.parquet")
    parts["asm"] = RF.asm_features(ev[["symbol", "date", "eff_date", "stage"]], dates, syms)
    pl = pledge_rows()
    parts["pledge"] = RF.pledge_features(pl.dropna(subset=["broadcast_ts"]), dates, syms)
    view, bs, sym2co = fundamentals_inputs()
    parts["fundamentals"] = RF.fundamental_features(view, bs, dates, {s: c for s, c in sym2co.items() if s in set(syms)})
    beta = parts["price"]["beta126"].unstack("symbol").reindex(index=dates, columns=syms)
    parts["label"] = RF.crash_label(close, member, beta, dates)
    base = parts["price"].index
    df = pd.concat([p.reindex(base) for p in parts.values()], axis=1)
    is_mem = member.reindex(dates).stack(future_stack=True).reindex(df.index).fillna(False).astype(bool)
    df = df[is_mem.to_numpy()].reset_index()                 # one row per PIT member on its Friday
    df.to_parquet(OUT, index=False)
    extra = {"asm_timing": asm_timing(asm_circ, sessions),
             "pledge_filing_sources": pl["reason"].value_counts().to_dict(),
             "pledge_filings_zero_filed": int((pl["pledge_pct"] == 0).sum())}
    return summarise(df, close, member, dates, asm_err, len(ev), len(pl), extra)


def asm_timing(circ: pd.DataFrame, sessions: pd.DatetimeIndex) -> dict:
    """Effective date vs publication date + 1 session, per circular attachment (IBC/ICA excluded)."""
    c = circ.drop_duplicates(["circular", "framework"]).copy()
    nxt = sessions[np.minimum(sessions.searchsorted(c["pub_date"], side="right"), len(sessions) - 1)]
    c["next_session"] = nxt
    c["eff"] = c["eff_date"].fillna(pd.NaT)
    no_wef = c["eff"].isna()
    lag = pd.Series([int(sessions.searchsorted(e, side="left") - sessions.searchsorted(p, side="left"))
                     if pd.notna(e) else None for e, p in zip(c["eff"], c["pub_date"])], index=c.index)
    differ = ~no_wef & (c["eff"] != c["next_session"])
    return {"circulars": int(len(c)), "no_wef_stated": int(no_wef.sum()),
            "eff_eq_pub_plus_1_session": int((~no_wef & ~differ).sum()),
            "eff_ne_pub_plus_1_session": int(differ.sum()),
            "lag_sessions_distribution": lag[differ].value_counts().sort_index().to_dict(),
            "published_on_friday": int((c["pub_date"].dt.weekday == 4).sum())}


FAMILY_COL = {"price": "rv63", "bands": "band_pct", "band_hits": "lo_hits252", "gsm": "gsm_stage",
              "asm": "asm_stage", "pledge": "pledge_pct", "de_ratio": "de_ratio", "int_cover": "int_cover",
              "ttm_core_pat": "ttm_core_pat_pos", "lateness": "last_lag_days", "adv": "adv20_cr"}


def summarise(df, close, member, dates, asm_err, n_asm_ev, n_pledge, extra=None) -> dict:
    y = df["date"].dt.year
    cov = {f: (100 * df[c].notna().groupby(y).mean()).round(1).to_dict() for f, c in FAMILY_COL.items()}
    lab = df.dropna(subset=["label_crash"])
    ly = lab["date"].dt.year
    rs = close.pct_change(fill_method=None)
    mk = rs.where(member).mean(axis=1)
    mm = (1 + mk).groupby(mk.index.to_period("M")).prod() - 1
    # the label window only (first label Friday's month .. 2024-06): months before it cannot hold a positive
    mm = mm[(mm.index >= lab["date"].min().to_period("M")) & (mm.index <= pd.Period("2024-06", "M"))]
    worst = mm.nsmallest(5)
    # a label "falls in" a worst month if its 63-session forward window overlaps that month
    pos = lab[lab["label_crash"] == 1]
    idx = close.index
    p0 = idx.get_indexer(pos["date"])
    win_end = idx[np.minimum(p0 + RF.H_LABEL, len(idx) - 1)]
    hit_worst = np.zeros(len(pos), bool)
    for m in worst.index:
        hit_worst |= (pos["date"].to_numpy() <= m.end_time.to_datetime64()) & (win_end.to_numpy() >= m.start_time.to_datetime64())
    by_date = lab.groupby("date")["label_crash"].agg(["mean", "size"])
    n, m_bar = len(lab), by_date["size"].mean()
    p = lab["label_crash"].mean()
    # one-way ANOVA ICC of the label within date clusters
    msb = (by_date["size"] * (by_date["mean"] - p) ** 2).sum() / max(len(by_date) - 1, 1)
    msw = (lab["label_crash"] - lab["date"].map(by_date["mean"])).pow(2).sum() / max(n - len(by_date), 1)
    icc = (msb - msw) / (msb + (m_bar - 1) * msw) if (msb + (m_bar - 1) * msw) > 0 else np.nan
    res = {
        "rows": int(len(df)), "symbols": int(df["symbol"].nunique()), "fridays": int(df["date"].nunique()),
        "first_friday": str(df["date"].min().date()), "last_friday": str(df["date"].max().date()),
        "coverage_pct_by_family_year": cov, "asm_events": n_asm_ev, "asm_parse_errors": asm_err, "pledge_filings_parsed": n_pledge,
        "label": {"rows": int(n), "label_dates": int(len(by_date)), "first": str(lab["date"].min().date()),
                  "last": str(lab["date"].max().date()), "base_rate_pct": round(100 * p, 2),
                  "base_rate_pct_by_year": (100 * lab.groupby(ly)["label_crash"].mean()).round(2).to_dict(),
                  "positives": int(len(pos)),
                  "worst5_market_months": {str(k): round(100 * v, 1) for k, v in worst.items()},
                  "positives_overlapping_worst5_months_pct": round(100 * float(hit_worst.mean()), 1) if len(pos) else None,
                  "non_overlapping_63s_windows": int(len(by_date) / 13),
                  "icc_within_date": round(float(icc), 4),
                  "design_effect": round(float(1 + (m_bar - 1) * icc), 1),
                  "n_eff_observations": int(n / (1 + (m_bar - 1) * icc)) if icc and icc > 0 else int(n)}}
    res.update(extra or {})
    SUMMARY.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    return res


if __name__ == "__main__":
    print(json.dumps(build(), indent=1, default=str))
