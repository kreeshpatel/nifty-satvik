"""FOUNDATION AUDIT — layer 2: is every corporate action adjusted, correctly scaled, on the right date?

Layer 1 asks whether a bar matches the exchange on the day. This layer asks the question layer 1
cannot answer by construction: **a series with an unadjusted split agrees with raw bhavcopy on both
sides of the split and is still broken**, because the return *across* the split is fabricated. The
defect lives in the join, not in either bar.

## The test

Write the pinned series as ``pickle(t) = raw(t) × adj(t)``, where ``raw`` is the exchange's own
unadjusted close and ``adj ≤ 1`` is whatever cumulative adjustment the vendor has applied to bars at
``t``. Both sides are observable — ``raw`` from bhavcopy, ``pickle`` from the pin — so ``adj(t)`` is
measurable on any date, for any name, with no modelling.

A corporate action of factor ``f`` (a 1:5 split is ``f = 5``) must divide every bar BEFORE its
ex-date by ``f`` and leave bars on and after it alone. So

    f_implied  =  adj(ex) / adj(ex−1)

and a correct series has ``f_implied == f`` exactly. This single quantity answers all three parts of
the question at once: **adjusted** (``f_implied ≠ 1`` when ``f ≠ 1``), **correctly scaled**
(``f_implied == f``), and **on the right date** (the step falls between ``ex−1`` and ``ex`` rather
than somewhere else). It needs two exchange sessions per event and assumes nothing.

## An assumption that was tested and FAILED, recorded because it would have produced a wrong audit

The first version of this script used ``PREVCLOSE(ex) / CLOSE(ex−1)`` as "the exchange's own
corporate-action receipt", on the belief that NSE republishes the previous close on the new scale.
**It does not.** ADANIPOWER's 5:1 split (ex 2025-09-22) prints ``prevclose = 709.40`` against a
close of ``170.25`` — the raw prior close, un-rebased. Every event therefore returned a factor of
exactly 1.0, which would have read as "the exchange never adjusts anything" and silently converted
the audit into a null instrument. The ratio-step test above replaces it and depends on no such
claim. The falsified assumption is kept here because an audit that hides its own wrong turns is
worth less than one that shows them.

## Two complementary passes

**Pass A — the census.** Every split, bonus and demerger NSE published for the pinned universe
between 2019-01-01 and 2026-07-01, each resolved individually. This asks: *is every real event
handled?*

**Pass B — the complement.** Every extreme single-day move in the pinned series, resolved against
the exchange. This asks the opposite and equally necessary question: *is every discontinuity in the
series a real event?* A series can pass A and fail B — an adjustment applied on the wrong day, or a
vintage seam where two differently-adjusted blocks were concatenated, produces a jump that no
corporate action explains. Pass A cannot see those, because it only ever looks at real ex-dates.

Outputs under ``diagnostics/research/foundation_audit_2026Q3/``: ``corpactions_raw.parquet`` (the
harvested exchange record), ``bhavcopy_events.parquet`` (the exchange sessions this layer pulled,
filtered to the pinned universe, so the audit re-runs without the network) and
``layer2_corpactions.json``.
"""
from __future__ import annotations

import json
import pickle
import re
import sys
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
OUTDIR = ROOT / "diagnostics" / "research" / "foundation_audit_2026Q3"
CA_RAW = OUTDIR / "corpactions_raw.parquet"
DAYCACHE = OUTDIR / "bhavcopy_events.parquet"
OUT = OUTDIR / "layer2_corpactions.json"

HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/120 Safari/537.36",
       "Referer": "https://www.nseindia.com/companies-listing/corporate-filings-actions",
       "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9"}
API = "https://www.nseindia.com/api/corporates-corporateActions"

# Corporate-action ratios are exact rationals, so the implied factor must match to 1%. Anything
# looser accepts a wrong ratio as a right one — which is the defect this layer exists to find.
FACTOR_TOL = 0.01
# Below this the series is treated as carrying no adjustment step at all.
NO_STEP = 0.01
# Pass B's threshold. -40%/+60% is the band that isolates corporate-action-scale discontinuities
# from ordinary crashes; it is the same order as the repo's existing _CORP_ACTION_MOVE = 0.50 guard.
EXTREME_DOWN, EXTREME_UP = -0.40, 0.60


def harvest(from_date: str, to_date: str) -> pd.DataFrame:
    """Every NSE equity corporate action between two dates, in quarterly slices (the API caps span)."""
    if CA_RAW.exists():
        return pd.read_parquet(CA_RAW)
    sess = requests.Session()
    sess.get("https://www.nseindia.com/", headers=HDR, timeout=25)
    rows: list[dict] = []
    edges = pd.date_range(from_date, to_date, freq="QS").tolist() + [pd.Timestamp(to_date)]
    for a, b in zip(edges, edges[1:]):
        q = {"index": "equities", "from_date": a.strftime("%d-%m-%Y"),
             "to_date": (b - pd.Timedelta(days=1)).strftime("%d-%m-%Y")}
        for attempt in range(3):
            try:
                r = sess.get(API, params=q, headers=HDR, timeout=40)
                if r.status_code == 200:
                    rows.extend(r.json())
                    break
            except Exception:
                pass
            time.sleep(2.0 * (attempt + 1))
            sess.get("https://www.nseindia.com/", headers=HDR, timeout=25)
        time.sleep(0.8)
    df = pd.DataFrame(rows)
    df["exDate"] = pd.to_datetime(df["exDate"], format="%d-%b-%Y", errors="coerce")
    OUTDIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(CA_RAW, index=False)
    return df


def expected_factor(subject: str) -> tuple[float | None, str]:
    """The price ratio the ex-date must produce, read out of the exchange's own subject line.

    The post-event price should be ``pre / factor``. A face-value split from Rs X to Rs Y multiplies
    the share count by X/Y. NSE writes bonuses as "Bonus a:b" — `a` new shares for every `b` held —
    so the count multiplies by (a+b)/b. Demergers carry no ratio in the text: the value that leaves
    is not a share-count operation, and the correct handling is to leave the discontinuity alone
    (this repo's own rule, `data/corporate_actions_demergers.csv`), so their expected factor is 1.
    """
    s = " ".join(str(subject).split()).lower()
    if "demerg" in s or "spin" in s or "arrangement" in s:
        return 1.0, "demerger"
    m = re.search(r"from\s*rs\.?\s*([\d.]+)\s*/?-?\s*per\s*share\s*to\s*(?:rs\.?|re\.?)\s*([\d.]+)", s)
    if m and ("split" in s or "sub-division" in s):
        a, b = float(m.group(1)), float(m.group(2))
        return (a / b, "split") if b > 0 else (None, "split")
    m = re.search(r"bonus\s*(\d+)\s*:\s*(\d+)", s)
    if m:
        a, b = float(m.group(1)), float(m.group(2))
        return ((a + b) / b, "bonus") if b > 0 else (None, "bonus")
    if "split" in s or "sub-division" in s:
        return None, "split"
    return None, "other"


class DayStore:
    """Exchange sessions, fetched once and cached to parquet so the audit re-runs offline."""

    def __init__(self, universe: set[str]):
        self.universe = universe
        self.df = pd.read_parquet(DAYCACHE) if DAYCACHE.exists() else pd.DataFrame()
        self.have = set(self.df["date"].dt.normalize()) if len(self.df) else set()
        self.miss: set[pd.Timestamp] = set()
        self.sess = requests.Session()
        self._isin_cache: dict[str, str | None] = {}
        self._full: dict[pd.Timestamp, pd.DataFrame | None] = {}
        self.renamed: dict[tuple[str, str], str] = {}

    def get(self, d: pd.Timestamp) -> pd.DataFrame | None:
        d = pd.Timestamp(d).normalize()
        if d in self.have:
            return self.df[self.df["date"].dt.normalize() == d]
        if d in self.miss:
            return None
        from audit_foundation_bhavcopy_2026Q3 import fetch_day
        got = fetch_day(self.sess, d)
        time.sleep(0.3)
        if got is None or not len(got):
            self.miss.add(d)
            return None
        keep = got[got["symbol"].isin(self.universe)].copy()
        self.df = pd.concat([self.df, keep], ignore_index=True) if len(self.df) else keep
        self.have.add(d)
        return keep

    def close(self, sym: str, d: pd.Timestamp) -> float | None:
        day = self.get(d)
        if day is None:
            return None
        r = day[day["symbol"] == sym]
        if len(r) and float(r["close"].iloc[0]) > 0:
            return float(r["close"].iloc[0])
        return self._close_by_isin(sym, d)

    def _isin(self, sym: str) -> str | None:
        """The symbol's ISIN, taken from the most recent session where the ticker appears."""
        if sym in self._isin_cache:
            return self._isin_cache[sym]
        got = None
        if len(self.df):
            r = self.df[(self.df["symbol"] == sym) & self.df["isin"].notna()]
            r = r[r["isin"].astype(str).str.startswith("INE")]
            if len(r):
                got = str(r.sort_values("date")["isin"].iloc[-1])
        self._isin_cache[sym] = got
        return got

    def _close_by_isin(self, sym: str, d: pd.Timestamp) -> float | None:
        """Renames break the ticker join, so fall back to identity.

        A company that changed its NSE symbol (RUCHISOYA -> PATANJALI, CENTURYTEX -> ABREL) is absent
        from the historical bhavcopy under today's ticker, and a ticker-only audit would silently
        report "no exchange data" for exactly the names most likely to carry a data defect. The ISIN
        is stable across a pure rename, so it recovers the row. It is NOT stable across a scheme of
        arrangement, so a miss here is reported rather than forced.
        """
        isin = self._isin(sym)
        if not isin:
            return None
        d = pd.Timestamp(d).normalize()
        full = self._full.get(d)
        if full is None:
            from audit_foundation_bhavcopy_2026Q3 import fetch_day
            full = fetch_day(self.sess, d)
            time.sleep(0.3)
            self._full[d] = full
        if full is None:
            return None
        r = full[full["isin"].astype(str) == isin]
        if not len(r):
            return None
        self.renamed[(sym, str(d.date()))] = str(r["symbol"].iloc[0])
        c = float(r["close"].iloc[0])
        return c if c > 0 else None

    def flush(self):
        if len(self.df):
            (self.df.drop_duplicates(["date", "symbol", "series"])
             .sort_values(["date", "symbol"]).to_parquet(DAYCACHE, index=False))


def adj_factor(store: DayStore, sym: str, d: pd.Timestamp, pk_close: float):
    """adj(t) = pickle(t) / raw(t) — the vendor's cumulative adjustment on that session."""
    raw = store.close(sym, d)
    return (pk_close / raw) if raw else None


def main() -> int:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    ohlcv = pickle.load(open(ROOT / "data" / "ohlcv.pkl", "rb"))
    store = DayStore(set(ohlcv))

    ca = harvest("2019-01-01", "2026-07-01")
    ca = ca[ca["symbol"].isin(ohlcv)].copy()
    ca["factor"], ca["kind"] = zip(*ca["subject"].map(expected_factor))
    events = (ca[ca["kind"].isin(("split", "bonus", "demerger"))]
              .drop_duplicates(["symbol", "exDate", "subject"])
              .sort_values(["exDate", "symbol"]))
    print(f"corporate actions in the pinned universe: {len(events)} "
          f"{events['kind'].value_counts().to_dict()}", flush=True)

    # ── PASS A — the census: is every real event handled? ──────────────────────────────────────
    #
    # Events are grouped by (symbol, ex-date) and their factors MULTIPLIED, because a company that
    # declares a 1:1 bonus and a 5:1 split on the same ex-date produces one price step of 10, not
    # two of 2 and 5. Judging such rows individually convicts a correctly-adjusted series twice —
    # BAJAJFINSV, BAJFINANCE, EASEMYTRIP, 360ONE, CGCL and NAZARA all pair this way, and an earlier
    # pass of this audit reported exactly that false positive before the grouping was added.
    groups = []
    for (sym, ex), g in events.groupby(["symbol", "exDate"], sort=True):
        fs = [f for f in g["factor"] if f is not None and f == f]
        combined = 1.0
        for f in fs:
            combined *= f
        groups.append({
            "symbol": sym, "exDate": ex, "n_events": int(len(g)),
            "kinds": "+".join(sorted(set(g["kind"]))),
            "factor": combined if len(fs) == len(g) else None,
            "subject": " | ".join(" ".join(str(s).split())[:70] for s in g["subject"]),
        })
    A = []
    for e in sorted(groups, key=lambda r: (r["exDate"], r["symbol"])):
        sym, ex, f_exp = e["symbol"], pd.Timestamp(e["exDate"]), e["factor"]
        rec = {"symbol": sym, "ex_date": str(ex.date()), "kind": e["kinds"],
               "n_same_day_events": e["n_events"], "subject": e["subject"][:180],
               "expected_factor": None if f_exp is None or f_exp != f_exp else round(float(f_exp), 6)}
        df = ohlcv.get(sym)
        idx = pd.DatetimeIndex(df.index) if df is not None else None
        if idx is None or ex not in idx or idx.get_loc(ex) == 0:
            rec["resolution"] = "NOT_IN_SERIES"
            A.append(rec)
            continue
        i = idx.get_loc(ex)
        prev = pd.Timestamp(idx[i - 1])
        a_ex = adj_factor(store, sym, ex, float(df["Close"].iloc[i]))
        a_pr = adj_factor(store, sym, prev, float(df["Close"].iloc[i - 1]))
        rec["prev_session"] = str(prev.date())
        rec["adj_prev"] = None if a_pr is None else round(a_pr, 6)
        rec["adj_ex"] = None if a_ex is None else round(a_ex, 6)
        if a_ex is None or a_pr is None or a_pr == 0:
            rec["resolution"] = "NO_EXCHANGE_DATA"
            A.append(rec)
            continue
        f_imp = a_ex / a_pr
        rec["implied_factor"] = round(f_imp, 6)
        rec["series_return"] = round(float(df["Close"].iloc[i]) / float(df["Close"].iloc[i - 1]) - 1,
                                     6)
        pure_demerger = "demerger" in rec["kind"] and "split" not in rec["kind"] \
            and "bonus" not in rec["kind"]
        if rec["expected_factor"] is None:
            rec["resolution"] = "NO_EXPECTED_FACTOR"
        elif abs(f_imp / rec["expected_factor"] - 1.0) <= FACTOR_TOL:
            rec["resolution"] = ("CORRECTLY_ADJUSTED" if rec["expected_factor"] > 1 + NO_STEP
                                 else "LEFT_UNADJUSTED_AS_INTENDED")
        elif pure_demerger and f_imp > 1 + NO_STEP:
            # The vendor back-adjusted a value-leaving event. This is NOT arithmetically wrong — it
            # is the total-return convention, in which the spun-off shares are treated as a
            # distribution. It contradicts THIS repo's committed convention
            # (data/corporate_actions_demergers.csv: "leave the honest discontinuity"), and the two
            # produce different trend slopes on the same name. Classified on its own so the owner
            # sees a convention conflict rather than an arithmetic error, and so it is never
            # silently folded into either the pass or the defect column.
            rec["resolution"] = "CONVENTION_DEMERGER_BACKADJUSTED"
        elif abs(f_imp - 1.0) <= NO_STEP:
            rec["resolution"] = "DEFECT_UNADJUSTED"
        else:
            rec["resolution"] = "DEFECT_MISSCALED"
        A.append(rec)
        if rec["resolution"].startswith(("DEFECT", "CONVENTION")):
            print(f"  A {sym:<12}{ex.date()} {rec['kind']:<16} exp={rec['expected_factor']} "
                  f"imp={rec['implied_factor']} -> {rec['resolution']}", flush=True)
    store.flush()

    # ── PASS B — the complement: is every discontinuity a real event? ──────────────────────────
    ex_index = {(r["symbol"], r["ex_date"]) for r in A}
    B = []
    for sym, df in ohlcv.items():
        c = df["Close"].astype(float)
        r = c.pct_change()
        for d, v in r[(r <= EXTREME_DOWN) | (r >= EXTREME_UP)].items():
            d = pd.Timestamp(d)
            i = pd.DatetimeIndex(df.index).get_loc(d)
            prev = pd.Timestamp(df.index[i - 1])
            rec = {"symbol": sym, "date": str(d.date()), "prev_session": str(prev.date()),
                   "series_return": round(float(v), 6),
                   "pk_prev": round(float(c.iloc[i - 1]), 4), "pk": round(float(c.iloc[i]), 4),
                   "is_ca_ex_date": (sym, str(d.date())) in ex_index}
            raw_now, raw_prev = store.close(sym, d), store.close(sym, prev)
            rec["ex_prev"] = raw_prev
            rec["ex"] = raw_now
            if raw_now is None or raw_prev is None:
                rec["resolution"] = "NO_EXCHANGE_DATA"
            else:
                rec["exchange_return"] = round(raw_now / raw_prev - 1.0, 6)
                a_now, a_pr = float(c.iloc[i]) / raw_now, float(c.iloc[i - 1]) / raw_prev
                rec["adj_prev"], rec["adj"] = round(a_pr, 6), round(a_now, 6)
                rec["implied_factor"] = round(a_now / a_pr, 6) if a_pr else None
                same = abs(rec["series_return"] - rec["exchange_return"]) <= 0.02
                if same and not rec["is_ca_ex_date"]:
                    # The exchange printed the same move and no corporate action is on the books.
                    rec["resolution"] = "GENUINE_MOVE"
                elif same and rec["is_ca_ex_date"]:
                    rec["resolution"] = "GENUINE_MOVE_ON_CA_DATE"
                else:
                    # The series moved and the exchange did not. Nothing on the exchange's record
                    # explains this jump: it is manufactured by the adjustment, not by the market.
                    rec["resolution"] = "DEFECT_UNEXPLAINED_JUMP"
            B.append(rec)
            print(f"  B {sym:<12}{d.date()} series={rec['series_return']:+.4f} "
                  f"exch={rec.get('exchange_return')} -> {rec['resolution']}", flush=True)
    store.flush()

    dfA, dfB = pd.DataFrame(A), pd.DataFrame(B)
    res = {
        "_class": "VERIFICATION — layer 2 corporate-action adjustment audit",
        "method": {
            "identity": "pickle(t) = raw(t) * adj(t); f_implied = adj(ex) / adj(ex-1)",
            "census": "NSE /api/corporates-corporateActions, equities, 2019-01-01..2026-07-01",
            "expected_factor": "parsed from the exchange's own subject line; demergers expect 1.0 "
                               "(no adjustment is the correct handling of a value-leaving event)",
            "falsified_assumption": "PREVCLOSE(ex) is NOT re-based by NSE (ADANIPOWER 2025-09-22: "
                                    "prevclose 709.40 vs close 170.25 across a 5:1 split), so it "
                                    "cannot serve as the exchange's adjustment receipt",
        },
        "tolerances": {"factor": FACTOR_TOL, "no_step": NO_STEP,
                       "extreme_band": [EXTREME_DOWN, EXTREME_UP]},
        "passA_census": {
            "events": int(len(events)),
            "by_kind": {k: int(v) for k, v in events["kind"].value_counts().items()},
            "resolutions": {k: int(v) for k, v in dfA["resolution"].value_counts().items()},
            "defects": dfA[dfA["resolution"].str.startswith("DEFECT")].to_dict("records"),
            "convention_conflicts": dfA[dfA["resolution"] == "CONVENTION_DEMERGER_BACKADJUSTED"]
                .to_dict("records"),
            "unresolved": dfA[dfA["resolution"].isin(
                ("NOT_IN_SERIES", "NO_EXCHANGE_DATA", "NO_EXPECTED_FACTOR"))].to_dict("records"),
        },
        "passB_complement": {
            "extreme_moves": int(len(dfB)),
            "resolutions": {k: int(v) for k, v in dfB["resolution"].value_counts().items()},
            "events": dfB.sort_values("series_return").to_dict("records"),
        },
        "renames_resolved_by_isin": {f"{k[0]}@{k[1]}": v for k, v in store.renamed.items()},
    }
    OUT.write_text(json.dumps(res, indent=2, default=str) + "\n", encoding="utf-8")
    dfA.to_parquet(OUTDIR / "layer2_passA.parquet", index=False)
    dfB.to_parquet(OUTDIR / "layer2_passB.parquet", index=False)
    print("\n" + json.dumps({"passA": res["passA_census"]["resolutions"],
                             "passB": res["passB_complement"]["resolutions"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
