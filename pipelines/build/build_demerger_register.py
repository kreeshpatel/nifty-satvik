"""Build ``data/corporate_actions_demerger_register.csv`` — every demerger, DESCRIBED not decided.

## Why a new file rather than extending the existing one

``data/corporate_actions_demergers.csv`` is **prescriptive**: ``nq.data.ohlcv`` reads it, and listing
a ``(ticker, date)`` there *instructs the cleaner* to leave the discontinuity alone. Adding all 37
events to it would therefore be **applying the listed-entity convention to all of them** — i.e.
deciding binder §10 by editing a data file. That decision is the owner's and is not taken here.

This register is the opposite: a complete, neutral description of what the vendor actually did to
each event, with the convention column left ``UNDECIDED``. It makes the October decision
**enforceable** — whichever convention is chosen, the events it governs are already enumerated —
without pre-empting it. The legacy four-row file is untouched and still drives the cleaner.

## What each column means

| column | meaning |
|---|---|
| ``ticker`` / ``ex_date`` | the exchange's own symbol and ex-date |
| ``subject`` | NSE's corporate-action subject line, verbatim |
| ``isin`` | identity independent of the ticker string |
| ``vendor_treatment`` | **measured**, not assumed: ``BACK_ADJUSTED`` / ``LEFT_AS_CLIFF`` / ``UNRESOLVED`` |
| ``implied_factor`` | ``adj(ex)/adj(ex-1)`` measured against NSE bhavcopy; 1.0 means the vendor left the cliff |
| ``series_return_at_ex`` | what the pinned series actually printed across the ex-date |
| ``in_pinned_universe`` | whether the name is in the pin at all |
| ``substrate_trades`` / ``substrate_sumR`` | how much of the record rests on this name |
| ``convention`` | **always ``UNDECIDED``** until binder §10 is decided |

Sources: the harvested NSE corporate-action record and the layer-2 measurements, both committed
under ``diagnostics/research/foundation_audit_2026Q3/``. Zero trials; nothing is recomputed.

    python scripts/build_demerger_register.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
AUDIT = ROOT / "diagnostics" / "research" / "foundation_audit_2026Q3"
OUT = ROOT / "data" / "corporate_actions_demerger_register.csv"

TREATMENT = {
    "CONVENTION_DEMERGER_BACKADJUSTED": "BACK_ADJUSTED",
    "LEFT_UNADJUSTED_AS_INTENDED": "LEFT_AS_CLIFF",
    "GENUINE_MOVE": "LEFT_AS_CLIFF",
    "NOT_IN_SERIES": "UNRESOLVED",
    "NO_EXCHANGE_DATA": "UNRESOLVED",
    "NO_EXPECTED_FACTOR": "UNRESOLVED",
}


def main() -> int:
    A = pd.read_parquet(AUDIT / "layer2_passA.parquet")
    dem = A[A["kind"].astype(str).str.contains("demerger")].copy()

    ca = pd.read_parquet(AUDIT / "corpactions_raw.parquet")
    ca["ex_date"] = pd.to_datetime(ca["exDate"]).dt.strftime("%Y-%m-%d")
    isin = (ca.dropna(subset=["isin"]).drop_duplicates(["symbol"])
              .set_index("symbol")["isin"].to_dict())

    tr = pd.read_parquet(ROOT / "research" / "substrate" / "trades.parquet")
    n_tr = tr.groupby("ticker").size().to_dict()
    sum_r = tr.groupby("ticker")["R"].sum().round(3).to_dict()

    import pickle
    pinned = set(pickle.load(open(ROOT / "data" / "ohlcv.pkl", "rb")))

    rows = []
    for _, e in dem.sort_values(["ex_date", "symbol"]).iterrows():
        sym = e["symbol"]
        rows.append({
            "ticker": sym,
            "ex_date": e["ex_date"],
            "subject": " ".join(str(e["subject"]).split())[:120],
            "isin": isin.get(sym, ""),
            "vendor_treatment": TREATMENT.get(str(e["resolution"]), "UNRESOLVED"),
            "implied_factor": ("" if pd.isna(e.get("implied_factor"))
                               else round(float(e["implied_factor"]), 6)),
            "series_return_at_ex": ("" if pd.isna(e.get("series_return"))
                                    else round(float(e["series_return"]), 6)),
            "in_pinned_universe": sym in pinned,
            "substrate_trades": int(n_tr.get(sym, 0)),
            "substrate_sumR": float(sum_r.get(sym, 0.0)),
            # NEVER auto-filled. Binder §10 is the only thing that may change this column, and it is
            # an owner decision. A build that populated it would be the decision taken by a script.
            "convention": "UNDECIDED",
            "source": "NSE corporate-action record + layer-2 measurement (2026Q3 foundation audit)",
        })

    df = pd.DataFrame(rows)
    header = (
        "# NiftyQuant — COMPLETE demerger register, 2019-01-01..2026-07-01.\n"
        "#\n"
        "# DESCRIPTIVE, NOT PRESCRIPTIVE. Nothing reads this file to decide how to clean a series.\n"
        "# The prescriptive file is data/corporate_actions_demergers.csv (4 rows, read by\n"
        "# nq.data.ohlcv) and it is deliberately UNCHANGED.\n"
        "#\n"
        "# `vendor_treatment` is MEASURED against NSE bhavcopy, not assumed: BACK_ADJUSTED means the\n"
        "# vendor rebased the pre-ex history (total-return convention); LEFT_AS_CLIFF means it left\n"
        "# the discontinuity (listed-entity convention, which is the one this repo's committed\n"
        "# reference asserts). The pin currently applies BOTH — see binder section 10.\n"
        "#\n"
        "# `convention` is UNDECIDED on every row and must stay that way until the 2026-10-01 review\n"
        "# nominates one. Populating it is the decision, not a data-entry step.\n"
        "#\n"
        "# Producer: scripts/build_demerger_register.py\n"
    )
    OUT.write_text(header + df.to_csv(index=False), encoding="utf-8")
    print(f"wrote {OUT}  events={len(df)}  names={df['ticker'].nunique()}")
    print(df["vendor_treatment"].value_counts().to_string())
    both = (df.groupby("ticker")["vendor_treatment"].nunique() > 1)
    if both.any():
        print(f"names carrying BOTH treatments: {sorted(both[both].index)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
