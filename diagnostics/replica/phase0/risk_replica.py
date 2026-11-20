"""Blind replica of the L5 risk-feature panel (spec: diagnostics/replica/phase0/risk_features_spec.md, part C).

Written from the spec only; does not import or read nq/data/risk_features.py or the build pipeline.
Uses only the loaders the spec names (membership, ohlcv cache/clean, fundamentals_q.company_key).
Computes the 20 sample keys in risk_sample_keys.csv. Ambiguity choices: replica_notes.md.

Run:  python diagnostics/replica/phase0/risk_replica.py [--asm-cache PATH]
"""
from __future__ import annotations

import argparse
import glob
import gzip
import json
import os
import pickle
import re
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from nq.data.membership import load_membership  # noqa: E402
from nq.data.ohlcv import clean_ohlcv_dict, load_ohlcv_cache  # noqa: E402
from nq.data.fundamentals_q import company_key  # noqa: E402

HERE = Path(__file__).resolve().parent
KEYS = HERE / "risk_sample_keys.csv"
OUT = HERE / "risk_replica.csv"
LABEL_CUTOFF = pd.Timestamp("2024-06-30")
COLS = ["rv63", "rv126", "dvol126", "beta126", "dbeta126", "mdd252", "n_down5_252", "adv20_cr", "adv60_cr",
        "lo_hits63", "lo_hits252", "up_hits63", "up_hits252", "band_pct", "gsm_stage", "asm_stage",
        "asm_days_in_stage", "pledge_pct", "pledge_chg_1q", "pledge_declared_none", "de_ratio", "int_cover",
        "ttm_core_pat_pos", "ttm_core_pat_chg4", "last_lag_days", "late_filer", "label_crash"]


# ----------------------------------------------------------------------------------------------- prices
def load_panels():
    with open(ROOT / "data" / "ohlcv_backfill.pkl", "rb") as f:
        d = dict(pickle.load(f))
    d.update(load_ohlcv_cache())          # cache wins
    d = clean_ohlcv_dict(d)
    close, vol = {}, {}
    for s, df in d.items():
        df = df[df.index >= pd.Timestamp("2016-01-01")]
        close[s] = df["Close"].astype(float)
        vol[s] = df["Volume"].astype(float)
    close = pd.DataFrame(close).sort_index()
    vol = pd.DataFrame(vol).reindex(close.index)
    close.index = pd.DatetimeIndex(close.index).as_unit("ns")
    vol.index = close.index
    return close, vol


def member_mask(index, columns, mem):
    m = pd.DataFrame(False, index=index, columns=columns)
    for s in columns:
        for a, b in mem.get(s, []):
            m.loc[(index >= pd.Timestamp(a)) & (index <= pd.Timestamp(b)), s] = True
    return m


def fridays(sessions: pd.DatetimeIndex) -> pd.DatetimeIndex:
    s = pd.Series(sessions, index=sessions)
    out = s.groupby(sessions.to_period("W-FRI")).max()
    # drop a final week whose last session is not a Friday (data ends mid-week)
    if out.iloc[-1].dayofweek != 4:
        out = out.iloc[:-1]
    return pd.DatetimeIndex(out.values)


# ----------------------------------------------------------------------------------------------- price family
def price_features(sym, fri, close, vol, mk, sessions):
    p = sessions.get_loc(fri)
    c = close[sym]
    r = np.log(c / c.shift(1))
    rs = c / c.shift(1) - 1
    o = {}

    def win(x, n):
        return x.iloc[p - n + 1: p + 1] if p - n + 1 >= 0 else None

    for n, mn in ((63, 50), (126, 100)):
        w = win(r, n)
        o[f"rv{n}"] = (w.std(ddof=1) * np.sqrt(252)) if w is not None and w.notna().sum() >= mn else np.nan
    w = win(r, 126)
    if w is not None and w.notna().sum() >= 100:
        o["dvol126"] = np.sqrt((np.minimum(w.dropna(), 0) ** 2).mean()) * np.sqrt(252)
    else:
        o["dvol126"] = np.nan

    wr, wm = win(rs, 126), win(mk, 126)
    o["beta126"] = np.nan
    o["dbeta126"] = np.nan
    if wr is not None:
        pair = wr.notna() & wm.notna()
        if pair.sum() >= 100 and wm.notna().sum() >= 100:
            o["beta126"] = wr[pair].cov(wm[pair]) / wm.dropna().var(ddof=1)
        dn = wm < 0
        pd_ = pair & dn
        if pd_.sum() >= 40 and (dn & wm.notna()).sum() >= 40:
            o["dbeta126"] = wr[pd_].cov(wm[pd_]) / wm[dn].var(ddof=1)

    peak = c.rolling(252, min_periods=200).max()
    dd = c / peak - 1
    mdd = dd.rolling(252, min_periods=200).min()
    o["mdd252"] = mdd.iloc[p]
    w = win(rs, 252)
    o["n_down5_252"] = float((w <= -0.05).sum()) if w is not None and w.notna().sum() >= 200 else np.nan

    tv = c * vol[sym]
    for n, mn in ((20, 15), (60, 45)):
        w = win(tv, n)
        o[f"adv{n}_cr"] = w.mean() / 1e7 if w is not None and w.notna().sum() >= mn else np.nan

    # label
    o["label_crash"] = np.nan
    b = o["beta126"]
    if p + 63 < len(sessions) and sessions[p + 63] <= LABEL_CUTOFF and np.isfinite(b):
        fr = rs.iloc[p + 1: p + 64]
        fm = mk.iloc[p + 1: p + 64]
        if fr.notna().sum() >= 51:
            seg = fr.fillna(0.0) - b * fm
            path = (1 + seg).cumprod() - 1
            o["label_crash"] = 1.0 if path.min() <= -0.25 else 0.0
    return o


# ----------------------------------------------------------------------------------------------- bands
def band_setup():
    h = pd.read_parquet(ROOT / "data" / "nse_bands" / "band_hitters.parquet")
    first = pd.Timestamp(h["date"].min())
    h = h[h["series"].astype(str).str.strip() == "EQ"].copy()
    h["symbol"] = h["symbol"].astype(str).str.strip()
    h["side"] = h["side"].astype(str).str.strip()
    h["date"] = pd.DatetimeIndex(h["date"]).as_unit("ns")
    files = {}
    for f in glob.glob(str(ROOT / ".cache" / "nse_bands" / "raw" / "sec_list_*.csv")):
        files[pd.Timestamp(re.search(r"sec_list_(\d{8})", f).group(1))] = f
    return h, first, pd.Series(files).sort_index()


ROMAN = {"0": 0, "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6}


def band_features(sym, fri, sessions, hits, first, files):
    p = sessions.get_loc(fri)
    o = {}
    for side, nm in (("L", "lo"), ("H", "up")):
        hs = hits[(hits["symbol"] == sym) & (hits["side"] == side)]
        for n in (63, 252):
            if p - n + 1 < 0 or sessions[p - n + 1] < first:
                o[f"{nm}_hits{n}"] = np.nan
                continue
            w = sessions[p - n + 1: p + 1]
            o[f"{nm}_hits{n}"] = float(hs["date"].isin(w).sum())
    asof = files[files.index <= fri]
    if len(asof) == 0:
        o["band_pct"] = np.nan
        o["gsm_stage"] = np.nan
        return o
    d = pd.read_csv(asof.iloc[-1], dtype=str)
    d.columns = [c.strip() for c in d.columns]
    for c in d.columns:
        d[c] = d[c].astype(str).str.strip()
    d = d[d["Series"] == "EQ"]
    row = d[d["Symbol"] == sym]
    if len(row) == 0:
        o["band_pct"] = np.nan
        o["gsm_stage"] = 0.0
        return o
    row = row.iloc[0]
    o["band_pct"] = pd.to_numeric(row["Band"], errors="coerce")
    rem = row["Remarks"]
    if "GSM" not in rem.upper():
        o["gsm_stage"] = 0.0
    else:
        m = re.search(r"GSM\s*STAGE\s*-\s*(VI|IV|V|III|II|I|0)\b", rem.upper())
        o["gsm_stage"] = float(ROMAN[m.group(1)] + 1) if m else 1.0
    return o


# ----------------------------------------------------------------------------------------------- ASM
MONTHS = {m: i for i, m in enumerate(["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT",
                                       "NOV", "DEC"], 1)}
WEF = re.compile(r"w\.e\.f\.?\s*([A-Za-z]+)\s*(\d{1,2})\s*,?\s*(\d{4})", re.I)
STAGE_RE = re.compile(r"\b(VI|IV|V|III|II|I)\b|(\d+)")


def parse_stage(v):
    if v is None:
        return None
    s = str(v).strip().upper()
    if not s:
        return None
    m = STAGE_RE.search(s)
    if not m:
        return None
    return ROMAN[m.group(1)] if m.group(1) else int(m.group(2))


def parse_asm_file(path):
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    eff = None
    consol = None
    for ws in wb.worksheets:
        rows = list(ws.iter_rows(values_only=True))
        if eff is None:
            for r in rows:
                for c in r:
                    if isinstance(c, str):
                        m = WEF.search(c)
                        if m and m.group(1)[:3].upper() in MONTHS:
                            try:
                                eff = pd.Timestamp(int(m.group(3)), MONTHS[m.group(1)[:3].upper()], int(m.group(2)))
                            except ValueError:
                                continue
                            break
                if eff is not None:
                    break
        t = ws.title.upper()
        if consol is None and "CONSOL" in t and "IBC" not in t and "ICA" not in t:
            consol = rows
    wb.close()
    if consol is None:
        return None, eff
    hdr = None
    for i, r in enumerate(consol):
        if any(isinstance(c, str) and c.strip() == "Symbol" for c in r):
            hdr = i
            break
    if hdr is None:
        return None, eff
    h = consol[hdr]
    si = [j for j, c in enumerate(h) if isinstance(c, str) and c.strip() == "Symbol"][0]
    st = [j for j, c in enumerate(h) if isinstance(c, str) and "Stage" in c]
    lst = {}
    for r in consol[hdr + 1:]:
        if si >= len(r) or r[si] is None or not str(r[si]).strip():
            continue
        sym = str(r[si]).strip()
        k = 1
        if st:
            v = parse_stage(r[st[0]] if st[0] < len(r) else None)
            k = v if v is not None else 1
        lst[sym] = max(lst.get(sym, 0), k)
    return lst, eff


def asm_snapshots(max_date, cache_path):
    cache = {}
    if cache_path and os.path.exists(cache_path):
        with open(cache_path, "rb") as f:
            cache = pickle.load(f)
    snaps = []
    for d in glob.glob(str(ROOT / "data" / "surv_raw" / "asm" / "*")):
        mp = os.path.join(d, "meta.json")
        if not os.path.exists(mp):
            continue
        meta = json.load(open(mp, encoding="utf-8"))
        if meta.get("status") != 200:
            continue
        pub = pd.Timestamp(meta["cirDate"])
        if pub > max_date:
            continue
        sub = meta.get("sub") or ""
        if " IBC" in sub or " ICA" in sub:
            continue
        for f in sorted(glob.glob(os.path.join(d, "*.xlsx"))):
            name = os.path.basename(f)
            if "IBC" in name or "ICA" in name:
                continue
            fw = "ST" if ("_ST" in name or "SHORT" in sub.upper().replace(" ", "")
                          or "ST-ASM" in sub.upper().replace(" ", "")) else "LT"
            if f not in cache:
                try:
                    cache[f] = parse_asm_file(f)
                except Exception as e:  # unreadable workbook -> no snapshot
                    cache[f] = (None, None)
                    print("ASM parse fail", f, e)
            lst, eff = cache[f]
            if lst is None:
                continue
            snaps.append((pub, int(meta["circNumber"]), fw, lst, eff if eff is not None else pub))
    if cache_path:
        with open(cache_path, "wb") as fh:
            pickle.dump(cache, fh)
    snaps.sort(key=lambda x: (x[0], x[1]))
    cur = {"ST": {}, "LT": {}}
    comb = {}
    events = []
    for pub, cn, fw, lst, eff in snaps:
        cur[fw] = lst
        syms = set(comb) | set(cur["ST"]) | set(cur["LT"])
        for s in syms:
            v = 0
            if s in cur["ST"]:
                v = max(v, 10 + cur["ST"][s])
            if s in cur["LT"]:
                v = max(v, 20 + cur["LT"][s])
            if v != comb.get(s, 0):
                events.append((s, pub, eff, v, cn))
                comb[s] = v
    return pd.DataFrame(events, columns=["symbol", "pub_date", "eff_date", "stage", "circ"])


def asm_features(sym, fri, ev):
    if len(ev) == 0 or fri <= ev["pub_date"].min():
        return {"asm_stage": np.nan, "asm_days_in_stage": np.nan}
    e = ev[(ev["symbol"] == sym) & (ev["pub_date"] < fri)]
    if len(e) == 0:
        return {"asm_stage": 0.0, "asm_days_in_stage": np.nan}
    last = e.iloc[-1]
    st = float(last["stage"])
    return {"asm_stage": st, "asm_days_in_stage": float((fri - last["eff_date"]).days) if st > 0 else np.nan}


# ----------------------------------------------------------------------------------------------- pledge
LIST_RECS = None


def all_list_recs():
    global LIST_RECS
    if LIST_RECS is None:
        recs = []
        for f in sorted(glob.glob(str(ROOT / "data" / "shp_raw" / "lists" / "*.json"))):
            recs += json.load(open(f, encoding="utf-8"))
        LIST_RECS = recs
    return LIST_RECS


def _num(x):
    if x is None:
        return np.nan
    x = x.strip()
    if x == "":
        return np.nan
    try:
        return float(x)
    except ValueError:
        return np.nan


FLAG_PREFIX = ("WhetherAnySharesHeldByPromotersArePledgeOrOtherwiseEncumbered",
               "WhetherAnySharesHeldByPromotersAreEncumbered")
FLAG_EXCL = ("ForNonPromoterNonPublic", "ForPublicShareHolder", "ForPublicShareholder")


def parse_shp(rid):
    p = ROOT / "data" / "shp_raw" / "xml" / f"{rid}.xml.gz"
    if not p.exists():
        return np.nan, False
    root = ET.fromstring(gzip.open(p).read())
    pctx = set()
    for c in root.iter():
        if c.tag.endswith("}context"):
            mems = [m.text.strip().split(":")[-1] for m in c.iter() if m.tag.endswith("}explicitMember") and m.text]
            if len(mems) == 1 and mems[0].startswith("ShareholdingOfPromoterAndPromoterGroup"):
                pctx.add(c.get("id"))
    facts = {}
    flags = []
    for e in root:
        loc = e.tag.split("}")[-1]
        if loc.startswith(FLAG_PREFIX) and not loc.endswith(FLAG_EXCL):
            flags.append((e.text or "").strip().lower())
        if e.get("contextRef") in pctx and loc not in facts:
            facts[loc] = e.text
    held = _num(facts.get("NumberOfShares"))
    val = np.nan
    # old format
    pl = _num(facts.get("PledgedOrEncumberedNumberOfShares"))
    if np.isfinite(pl) and np.isfinite(held) and held != 0:
        val = 100 * pl / held
    else:
        val = _num(facts.get("PledgedOrEncumberedSharesHeldAsPercentageOfTotalNumberOfShares"))
    if not np.isfinite(val):
        en = _num(facts.get("NumberOfSharesEncumbered"))
        if np.isfinite(en) and np.isfinite(held) and held != 0:
            val = 100 * en / held
        else:
            val = 100 * _num(facts.get("EncumberedSharesHeldAsPercentageOfTotalNumberOfShares"))
    # owner decision 2026-11-20: no number filed + every promoter pledge/encumbrance flag false -> 0 (declared)
    declared = bool((not np.isfinite(val)) and flags and all(f == "false" for f in flags))
    if declared:
        val = 0.0
    return val, declared


def pledge_features(sym, fri):
    recs = [r for r in all_list_recs() if r.get("symbol") == sym]
    rows = []
    for r in recs:
        sub = pd.to_datetime(r["submissionDate"], format="%d-%b-%Y")
        bc = pd.to_datetime(r["broadcastDate"], format="%d-%b-%Y %H:%M:%S")
        if r.get("revisedStatus") == "Revised":
            kt = bc
        else:
            kt = min(sub + pd.Timedelta(days=1), bc)
        rows.append((kt, int(r["recordId"]), r["recordId"]))
    rows.sort()
    cut = fri + pd.Timedelta(hours=15, minutes=30)
    known = [x for x in rows if x[0] <= cut]
    o = {"pledge_pct": np.nan, "pledge_chg_1q": np.nan, "pledge_declared_none": np.nan}
    if not known:
        return o
    v, declared = parse_shp(known[-1][2])
    o["pledge_pct"] = v
    if len(known) >= 2:
        v0, _ = parse_shp(known[-2][2])
        o["pledge_chg_1q"] = v - v0
    if fri >= pd.Timestamp("2021-01-01"):
        o["pledge_declared_none"] = 1.0 if declared else 0.0
    return o


# ----------------------------------------------------------------------------------------------- fundamentals
def fund_setup():
    view = pd.read_parquet(ROOT / "data" / "fundamentals_q_features.parquet")
    x = pd.read_parquet(ROOT / "data" / "results_xbrl.parquet")
    x = x.reset_index(drop=True)
    x["company"] = company_key(x["isin"], x["symbol"])
    return view, x


def fund_features(sym, fri, view, x):
    o = {k: np.nan for k in ("de_ratio", "int_cover", "ttm_core_pat_pos", "ttm_core_pat_chg4",
                             "last_lag_days", "late_filer")}
    comp = x.loc[x["symbol"] == sym, "company"]
    if len(comp) == 0:
        return o, None
    comp = comp.iloc[0]
    cut = fri + pd.Timedelta(hours=15, minutes=30)
    v = view[view["company"] == comp]
    vv = v[v["broadcast_ts"] <= cut].sort_values("broadcast_ts", kind="stable")
    if len(vv):
        r = vv.iloc[-1]
        fc, pbt = r["ttm_finance_costs"], r["ttm_pbt"]
        o["int_cover"] = (pbt + fc) / fc if pd.notna(fc) and fc > 0 else np.nan
        o["ttm_core_pat_pos"] = np.nan if pd.isna(r["ttm_core_pat"]) else float(r["ttm_core_pat"] > 0)
        o["ttm_core_pat_chg4"] = r["ttm_core_pat_chg4"]
        o["last_lag_days"] = r["lag_days"]
        o["late_filer"] = np.nan if pd.isna(r["lag_days"]) else float(r["lag_days"] > 120)
    pbs = v["primary_basis"].dropna()
    if len(pbs) == 0:
        return o, comp
    pb = pbs.mode().iloc[0]
    want_consol = pb == "consolidated"
    b = x[(x["company"] == comp) & (x["context_role"] == "current") & x["bs_total_equity"].notna()]
    b = b[b["consolidated"].astype(bool) == want_consol]
    b = b[b["broadcast_ts"] <= cut].sort_values(["broadcast_ts", "period_end"], kind="stable")
    if len(b):
        r = b.iloc[-1]
        bc, bn = r["bs_borrowings_current"], r["bs_borrowings_noncurrent"]
        debt = np.nan if (pd.isna(bc) and pd.isna(bn)) else (0 if pd.isna(bc) else bc) + (0 if pd.isna(bn) else bn)
        eq = r["bs_total_equity"]
        de = debt / eq if eq > 0 else np.nan
        shifted = pd.Timestamp(r["period_end"]) + pd.offsets.MonthEnd(6)
        lim = shifted + pd.Timedelta(days=60 if shifted.month == 3 else 45) + pd.Timedelta(days=60)
        o["de_ratio"] = de if fri <= lim else np.nan
    return o, comp


# ----------------------------------------------------------------------------------------------- main
PLEDGE_COLS = ["pledge_pct", "pledge_chg_1q", "pledge_declared_none"]


def pledge_only(keys_path, out_path, update_in_place):
    """Pledge family only (spec change 2026-11-20). Writes symbol,date + 3 pledge columns to out_path, or, when
    update_in_place, overwrites those 3 columns of an existing replica CSV keyed on (symbol, date)."""
    keys = pd.read_csv(keys_path, parse_dates=["date"])
    rows = []
    for _, k in keys.iterrows():
        r = {"symbol": k["symbol"], "date": k["date"].date().isoformat()}
        r.update(pledge_features(k["symbol"], pd.Timestamp(k["date"])))
        rows.append(r)
    new = pd.DataFrame(rows)
    if update_in_place:
        old = pd.read_csv(out_path, dtype={"symbol": str, "date": str}, keep_default_na=False, na_values=[""])
        m = old.merge(new, on=["symbol", "date"], how="left", suffixes=("_old", ""))
        assert m[PLEDGE_COLS].notna().any(axis=1).sum() + 0 >= 0 and len(m) == len(old)
        for c in PLEDGE_COLS:
            old[c] = m[c].values
        old.to_csv(out_path, index=False, na_rep="")
    else:
        new.reindex(columns=["symbol", "date"] + PLEDGE_COLS).to_csv(out_path, index=False, na_rep="")
    print(new.to_string())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--asm-cache", default=None)
    ap.add_argument("--pledge-only", nargs=2, metavar=("KEYS", "OUT"), default=None)
    ap.add_argument("--update-in-place", action="store_true")
    a = ap.parse_args()
    if a.pledge_only:
        pledge_only(a.pledge_only[0], a.pledge_only[1], a.update_in_place)
        return
    t0 = time.time()
    keys = pd.read_csv(KEYS, parse_dates=["date"])
    close, vol = load_panels()
    sessions = close.index
    mem = load_membership()
    mm = member_mask(sessions, close.columns, mem)
    rs_all = close / close.shift(1) - 1
    mk = rs_all.where(mm).mean(axis=1, skipna=True)
    fr = set(fridays(sessions))
    print(f"panel {close.shape} sessions {sessions[0].date()}..{sessions[-1].date()}  t={time.time()-t0:.0f}s")

    hits, first, files = band_setup()
    print(f"hitters dup rows (EQ, symbol/date/side): {hits.duplicated(['symbol','date','side']).sum()}")
    ev = asm_snapshots(keys["date"].max(), a.asm_cache)
    print(f"ASM events {len(ev)} first pub {ev['pub_date'].min().date()}  t={time.time()-t0:.0f}s")
    view, x = fund_setup()

    out = []
    for _, k in keys.iterrows():
        sym, fri = k["symbol"], pd.Timestamp(k["date"])
        row = {"symbol": sym, "date": fri.date().isoformat()}
        is_fri = fri in fr
        is_mem = any(pd.Timestamp(s) <= fri <= pd.Timestamp(e) for s, e in mem.get(sym, []))
        if not is_fri or not is_mem or sym not in close.columns:
            print(f"WARN {sym} {fri.date()} friday={is_fri} member={is_mem} in_prices={sym in close.columns}")
        if sym in close.columns and fri in sessions:
            row.update(price_features(sym, fri, close, vol, mk, sessions))
            row.update(band_features(sym, fri, sessions, hits, first, files))
        row.update(asm_features(sym, fri, ev))
        row.update(pledge_features(sym, fri))
        f, comp = fund_features(sym, fri, view, x)
        row.update(f)
        out.append(row)
        print(sym, fri.date(), "company", comp)
    df = pd.DataFrame(out).reindex(columns=["symbol", "date"] + COLS)
    df.to_csv(OUT, index=False, na_rep="")
    print(df.to_string())
    print(f"runtime {time.time()-t0:.0f}s -> {OUT}")


if __name__ == "__main__":
    main()
