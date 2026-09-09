"""A corporate action after the audit's harvest window must survive a register rebuild.

`pipelines/build/build_demerger_register.py` regenerates the register in full from the 2026Q3
foundation audit, whose NSE harvest ends 2026-06-24. HEG's demerger (ex-date 2026-09-07) is past
that, so a row hand-added to the generated CSV would be wiped by the next build — silently, since
the build prints success either way. `data/corporate_actions_post_harvest.csv` is the supported
carrier; these tests hold it to the properties that make it trustworthy.

The line these tests will not let anyone cross: the addendum is DESCRIPTIVE. Adding HEG here records
what the exchange did. It does not decide how the series is cleaned — that is
`data/corporate_actions_demergers.csv`, the binder §10 convention, and the 2026-10-01 review's call.
For a live held position the two readings differ by roughly 6R, so the separation is load-bearing.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

ADDENDUM = ROOT / "data" / "corporate_actions_post_harvest.csv"
PRESCRIPTIVE = ROOT / "data" / "corporate_actions_demergers.csv"
REGISTER = ROOT / "data" / "corporate_actions_demerger_register.csv"

_spec = importlib.util.spec_from_file_location(
    "build_demerger_register", ROOT / "pipelines" / "build" / "build_demerger_register.py")
_B = importlib.util.module_from_spec(_spec)
sys.modules["build_demerger_register"] = _B
_spec.loader.exec_module(_B)


# The producer reads artifacts that are deliberately NOT committed: the 64 MB OHLCV pin and the
# research substrate. So `main()` cannot run on a clean clone or on CI, and the two tests that
# invoke it are skipped there rather than failing. Stated out loud because a skip that nobody
# notices is how a guard quietly stops guarding — the hermetic properties (a post-harvest row is
# appended, sourced, de-duplicated against the audit) are covered by the `_with_post_harvest` tests
# below, which run everywhere.
PRODUCER_INPUTS = (
    ROOT / "diagnostics" / "research" / "foundation_audit_2026Q3" / "layer2_passA.parquet",
    ROOT / "diagnostics" / "research" / "foundation_audit_2026Q3" / "corpactions_raw.parquet",
    ROOT / "research" / "substrate" / "trades.parquet",
    ROOT / "data" / "ohlcv.pkl",
)
needs_producer = pytest.mark.skipif(
    not all(p.exists() for p in PRODUCER_INPUTS),
    reason="register producer needs uncommitted artifacts (OHLCV pin, research substrate); "
           "the append/source/de-dup properties are covered hermetically below")


def _addendum() -> pd.DataFrame:
    return pd.read_csv(ADDENDUM, comment="#")


def _register() -> pd.DataFrame:
    return pd.read_csv(REGISTER, comment="#")


# --------------------------------------------------------------------------- the event
def test_hegs_demerger_is_registered():
    """The event this file was created for: HEG, ex-date 2026-09-07, confirmed by NSE."""
    r = _register()
    heg = r[(r.ticker == "HEG") & (r.ex_date == "2026-09-07")]
    assert len(heg) == 1, "HEG's 2026-09-07 demerger is missing from the register"
    assert heg.iloc[0]["vendor_treatment"] == "LEFT_AS_CLIFF"
    assert heg.iloc[0]["convention"] == "UNDECIDED"


@needs_producer
def test_the_addendum_survives_a_rebuild():
    """The whole point. A hand-added row in the generated CSV would not."""
    before = _register()
    assert _B.main() == 0
    after = _register()
    assert len(after) == len(before), "the rebuild changed the row count"
    assert "HEG" in set(after.ticker), "HEG did not survive the rebuild"


@needs_producer
def test_the_rebuild_is_deterministic():
    """Re-running must produce byte-identical output, or the register is not a reproducible artifact."""
    _B.main()
    first = REGISTER.read_bytes()
    _B.main()
    assert REGISTER.read_bytes() == first


# --------------------------------------------------------------------------- provenance
def test_every_addendum_row_names_its_source():
    """An unsourced corporate action is a guess with a date on it. The producer raises on this;
    assert the committed file actually satisfies it."""
    add = _addendum()
    assert len(add) > 0
    for _, r in add.iterrows():
        src = str(r["source"]).strip()
        assert src and src.lower() != "nan", f"{r['symbol']} {r['ex_date']} has no source"
        assert len(src) > 60, f"{r['symbol']}: source is too thin to verify later"


def test_an_addendum_row_keeps_its_own_source_in_the_register():
    """It must NOT inherit the audit's blanket string — that would attribute a 2026-09 API lookup
    to a frozen harvest that never saw the event, which is a false citation in a governance file."""
    r = _register()
    heg = r[r.ticker == "HEG"].iloc[0]
    assert "2026Q3 foundation audit" not in heg["source"], "HEG inherited the audit's source"
    assert "NSE corporate-actions API" in heg["source"]
    assert "2026-09-09" in heg["source"], "the retrieval date is what makes it checkable"


def test_audit_rows_keep_the_audit_source():
    """The paired negative: adding the addendum must not blank out the 37 audit rows' provenance.
    An earlier revision of the producer set them all to the string 'nan'."""
    r = _register()
    audit = r[r.ticker != "HEG"]
    assert len(audit) >= 37
    assert audit["source"].astype(str).str.contains("2026Q3 foundation audit").all()
    assert not audit["source"].astype(str).str.strip().isin({"nan", ""}).any()


def test_an_unsourced_row_is_refused(tmp_path, monkeypatch):
    p = tmp_path / "post.csv"
    p.write_text("symbol,ex_date,kind,subject,implied_factor,series_return,resolution,source\n"
                 "FOO,2026-09-07,demerger,Demerger,1.0,-0.5,LEFT_UNADJUSTED_AS_INTENDED,\n",
                 encoding="utf-8")
    monkeypatch.setattr(_B, "POST_HARVEST", p)
    with pytest.raises(ValueError, match="must name the exchange record"):
        _B._with_post_harvest(pd.DataFrame(columns=["symbol", "ex_date", "kind"]))


def test_the_audit_wins_when_the_harvest_catches_up(tmp_path, monkeypatch):
    """Once the harvest extends past an ex_date the audit measured it directly, so the addendum row
    is redundant and must not double-count. It should then be deleted from the CSV."""
    p = tmp_path / "post.csv"
    p.write_text("symbol,ex_date,kind,subject,implied_factor,series_return,resolution,source\n"
                 "VEDL,2026-04-30,demerger,Demerger,1.0,-0.649,LEFT_UNADJUSTED_AS_INTENDED,"
                 "a source long enough to pass the producer's own check on provenance strings\n",
                 encoding="utf-8")
    monkeypatch.setattr(_B, "POST_HARVEST", p)
    audit = pd.DataFrame([{"symbol": "VEDL", "ex_date": "2026-04-30", "kind": "demerger",
                           "resolution": "CONVENTION_DEMERGER_BACKADJUSTED"}])
    out = _B._with_post_harvest(audit)
    assert len(out) == 1, "the addendum double-counted an event the audit already carries"
    assert out.iloc[0]["resolution"] == "CONVENTION_DEMERGER_BACKADJUSTED", "the audit must win"


# --------------------------------------------------------------------------- the separation
def test_the_prescriptive_file_is_untouched():
    """Registering an event DESCRIBES it. Listing a (ticker,date) in the prescriptive file INSTRUCTS
    the cleaner to keep the discontinuity — for HEG, a live held position, that is the difference
    between the book carrying the position and booking roughly -6R. That is binder §10, an owner
    decision reserved for the 2026-10-01 review, and no build or test may take it by editing data."""
    body = PRESCRIPTIVE.read_text(encoding="utf-8")
    rows = [ln for ln in body.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    tickers = {ln.split(",")[0].strip() for ln in rows if "," in ln}
    assert "HEG" not in tickers, (
        "HEG was added to the PRESCRIPTIVE cleaner file. That decides the demerger convention for a "
        "live held position by editing a data file. It belongs to binder §10 / the 2026-10-01 review.")
    assert tickers <= {"ticker", "VEDL", "ABFRL", "RAYMOND", "SKFINDIA"}


def test_convention_is_undecided_everywhere():
    """Populating this column IS the decision, per the register's own header."""
    assert set(_register()["convention"]) == {"UNDECIDED"}


# --------------------------------------------------------------------------- the ignore trap
def test_the_addendum_is_committable():
    """SEVENTH instance of the `data/*` + `results/*` ignore trap (judge_log, output_contracts,
    base_swing_forward, intraday_scan, weekly_monitor, the D2 archive were the first six).

    `/data/*` ignores everything by default. Ignored-and-untracked, this file would be absent on a
    fresh clone; `_with_post_harvest` would find nothing, return the audit rows unchanged, and the
    rebuild would drop HEG while printing success. Caught 2026-09-09 before the first commit rather
    than after a month of silent loss.
    """
    import subprocess
    r = subprocess.run(["git", "check-ignore", str(ADDENDUM)],
                       capture_output=True, text=True, cwd=ROOT)
    # `git check-ignore` prints the path only when it is genuinely EXCLUDED; a whitelisted path
    # matches a negation and prints nothing.
    assert not r.stdout.strip(), (
        f"{ADDENDUM.name} is gitignored — add `!data/{ADDENDUM.name}` to .gitignore. "
        f"Without it the register loses every post-harvest event on a clean clone.")


def test_the_producer_survives_a_missing_addendum():
    """It must degrade to the audit rows, not crash — a clean clone that predates the file, or a
    future state where every event has been folded back into the harvest and the file is deleted."""
    base = pd.DataFrame([{"symbol": "VEDL", "ex_date": "2026-04-30", "kind": "demerger"}])
    saved = _B.POST_HARVEST
    try:
        _B.POST_HARVEST = ROOT / "data" / "__definitely_absent__.csv"
        out = _B._with_post_harvest(base)
    finally:
        _B.POST_HARVEST = saved
    assert len(out) == 1 and out.iloc[0]["symbol"] == "VEDL"
