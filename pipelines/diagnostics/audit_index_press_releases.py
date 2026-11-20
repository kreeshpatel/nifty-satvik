"""MEASUREMENT (data-readiness audit v2, item 3): NSE Indices press releases 2017-2024 - which equity "Replacements in
indices" releases name Nifty 500, Nifty Midcap 150 and Nifty Midcap150 Momentum 50, with announcement and effective
dates. Computes no signal and no return.

SOURCE   https://www.niftyindices.com/press-release (listing page) -> Press_Release/ind_prs*.pdf
SELECTED releases dated 2017-2024 whose listing title contains "replacement", excluding SME / IPO / G-Sec / SDL /
         bond / debt / FPI titles.
DATES    announcement = the date printed at the end of the listing title; effective = the first "effective from" /
         "w.e.f." date in the PDF text. lead = effective - announcement (calendar days).
INDEX    Nifty 500: /NIFTY ?500/ not followed by a strategy suffix; Midcap 150: /NIFTY ?Midcap ?150/ not followed by
         Momentum/Quality; Momentum 50: /Midcap ?150 ?Momentum ?50/.
Downloads go to .cache/index_press_releases/ (untrusted, parsed as text only).
Writes diagnostics/research/explore/2026-11-18_index_press_releases.csv and prints a per-index summary.

    python pipelines/diagnostics/audit_index_press_releases.py
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / ".cache" / "index_press_releases"
OUT = ROOT / "diagnostics" / "research" / "explore" / "2026-11-18_index_press_releases.csv"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}
BASE = "https://www.niftyindices.com/"


def listing() -> dict[str, str]:
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / "press-release.html"
    if not f.exists():
        f.write_bytes(requests.get(BASE + "press-release", headers=UA, timeout=60).content)
    h = f.read_text(encoding="utf-8", errors="ignore")
    ms = list(re.finditer(r"Press_Release/(ind_prs\d{8}[^\"' >]*\.pdf)", h))
    out = {}
    for a, b in zip(ms, ms[1:] + [None]):
        seg = h[a.end(): b.start() if b else a.end() + 800]
        out.setdefault(a.group(1), re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", seg)).strip()[:200])
    return out


def main() -> int:
    import pypdf
    items = listing()
    rows = []
    for f, title in items.items():
        dates = re.findall(r"([A-Z][a-z]{2} \d{2}, \d{4})", title)
        ann = pd.to_datetime(dates[-1], errors="coerce") if dates else pd.NaT
        if pd.isna(ann) or not 2017 <= ann.year <= 2024:
            continue
        if not re.search(r"replacement", title, re.I) or re.search(r"SME|IPO|G-?Sec|SDL|bond|debt|FPI", title, re.I):
            continue
        p = CACHE / f
        if not p.exists():
            p.write_bytes(requests.get(BASE + "Press_Release/" + f, headers=UA, timeout=60).content)
            time.sleep(0.5)
        try:
            txt = re.sub(r"\s+", " ", " ".join(pg.extract_text() or "" for pg in pypdf.PdfReader(str(p)).pages))
        except Exception:
            txt = ""
        eff = re.search(r"(?:effective|w\.e\.f\.?)\D{0,60}?(\w+ \d{1,2},? ?\d{4})", txt, re.I) or re.search(r"w\.e\.f\.? ?(\w+ \d{1,2},? ?\d{4})", title)
        eff_dt = pd.to_datetime(re.sub(r"(\d),(\d)", r"\1, \2", eff.group(1)), errors="coerce") if eff else pd.NaT
        rows.append({"file": f, "announced": ann.date(), "effective": eff_dt.date() if pd.notna(eff_dt) else None,
                     "lead_days": (eff_dt - ann).days if pd.notna(eff_dt) else None, "text_chars": len(txt),
                     "nifty500": bool(re.search(r"NIFTY ?500(?! ?(Multicap|Value|Momentum|Quality|Equal|Shariah|LargeMidSmall|Low|Multifactor))", txt, re.I)),
                     "midcap150": bool(re.search(r"NIFTY ?Midcap ?150(?! ?(Momentum|Quality))", txt, re.I)),
                     "midcap150_momentum50": bool(re.search(r"Midcap ?150 ?Momentum ?50", txt, re.I))})
    d = pd.DataFrame(rows).sort_values("announced")
    d.to_csv(OUT, index=False)
    summ = {"releases": int(len(d)), "image_only_pdfs": d.loc[d.text_chars < 200, "file"].tolist()}
    for k in ("nifty500", "midcap150", "midcap150_momentum50"):
        s = d[d[k]]
        summ[k] = {"n": int(len(s)), "first": str(s.announced.min()), "last": str(s.announced.max()),
                   "lead_median": float(s.lead_days.median()), "lead_p95": float(s.lead_days.quantile(0.95))}
    print(json.dumps(summ, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
