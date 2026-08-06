"""The zoo shadow book must be COLD — it may observe the traded book and never influence it.

Pre-reg 0131 §5. The whole safety argument for an observational stream is that it cannot reach the
thing it observes, so that argument is tested rather than asserted. These are cheap structural tests;
the expensive end-to-end equivalence is the last one and is skipped when the pinned cache is absent.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

SRC = (ROOT / "scripts" / "run_zoo_shadow_book.py").read_text(encoding="utf-8")
TREE = ast.parse(SRC)


def _code_strings() -> set[str]:
    """Every string LITERAL that is actually code, with docstrings excluded.

    Scanning raw source text would flag this module's own documentation — it names the artifacts it
    must not touch precisely in order to say it does not touch them. A guard that fires on its own
    prose is a false-positive generator, so the scan reads the AST instead.
    """
    docstrings = set()
    for node in ast.walk(TREE):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            d = ast.get_docstring(node, clean=False)
            if d is not None:
                docstrings.add(d)
    return {n.value for n in ast.walk(TREE)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and n.value not in docstrings}


def _call_keywords() -> set[str]:
    return {kw.arg for n in ast.walk(TREE) if isinstance(n, ast.Call)
            for kw in n.keywords if kw.arg}


def test_it_writes_exactly_one_file_and_that_file_is_its_own():
    """A logger that can write anywhere is not a logger. The only artifact it may produce is its
    own JSON — never the paper book, the cards, the wall, the ledger or any config."""
    import run_zoo_shadow_book as Z
    assert Z.OUT.name == "zoo_shadow_book.json"
    assert Z.OUT.parent.name == "results"

    forbidden = (
        "paper_portfolio_weekly", "signals_today_weekly", "signals_history_weekly",
        "portfolio_history_weekly", "weekly_review_scorecard", "forward_wall", "wall_cron",
        "judge_log", "kill_state", "cards_archive", "config.json", "ohlcv.pkl",
    )
    code = " ".join(_code_strings())
    for name in forbidden:
        assert name not in code, f"shadow book references a traded-book artifact in CODE: {name}"

    writes = [n for n in ast.walk(TREE) if isinstance(n, ast.Attribute)
              and n.attr in {"write_text", "write_bytes", "to_csv", "to_parquet", "to_json"}]
    assert len(writes) == 1, f"expected exactly one write, found {len(writes)}"


def test_it_never_mutates_the_engine_or_shared_config():
    """It must not monkeypatch, reassign engine constants, or write into a shared module."""
    tree = ast.parse(SRC)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                # `R94.SOMETHING = ...` or `config.X = ...` would be a mutation of shared state
                assert not isinstance(tgt, ast.Attribute), (
                    f"shadow book assigns to an attribute of another module at line {node.lineno}")


def test_the_elected_pool_is_frozen_and_is_the_only_difference():
    """Pre-reg 0131 §1 elected exactly cup_handle + box + double_bottom. A quiet fourth setup, or a
    changed exit/priority/sizing kwarg, would make the shadow book a different experiment."""
    import run_zoo_shadow_book as Z
    assert Z.ELECTED_ZOO_ORIGINS == (6, 8)          # cup_handle, double_bottom
    assert Z.ELECTED_BOX is True
    kw = Z._pool_kwargs()
    assert set(kw) == {"box_breakout", "zoo_origins"}, (
        f"the pool is the ONLY permitted difference; found extra kwargs: {set(kw)}")
    # No call anywhere in the module may pass a kwarg that changes the exit ladder, the fill
    # priority or the sizing. Checked as CALL KEYWORDS, not as source text — the docstring names
    # P2_EXIT precisely to say this book does not use it.
    banned = {"no_time_cap", "wk20_trail_pct", "blowoff_arm_r", "scaled_exit", "fill_order",
              "risk_pct", "max_notional_pct", "max_positions", "ext_cap", "max_risk_pct",
              "uncapped", "eq0", "vol_target", "a_grade", "stop_atr_mult", "hard_stop"}
    used = _call_keywords() & banned
    assert not used, f"shadow book alters {sorted(used)} — the pool must be the only change"


def test_it_is_not_wired_into_any_traded_path():
    """Nothing the live book runs may import or call it."""
    for path in ("scripts/run_bhanushali_cron.py", "scripts/run_bhanushali_weekly_rank.py",
                 "scripts/run_bhanushali_path1.py", "scripts/build_substrate.py"):
        txt = (ROOT / path).read_text(encoding="utf-8")
        assert "run_zoo_shadow_book" not in txt, f"{path} references the shadow book"


def test_the_workflow_runs_it_beside_the_other_observational_logger_and_cannot_fail_the_scanner():
    wf = (ROOT / ".github" / "workflows" / "cron-bhanushali-scanner.yml").read_text(encoding="utf-8")
    assert "run_zoo_shadow_book.py" in wf, "shadow book not wired into the Saturday cron"
    step = wf[wf.index("run_zoo_shadow_book.py"):]
    assert "::warning::" in step[:400], (
        "the shadow book must warn, never fail the scanner — an observational stream may not take "
        "the traded book down with it")
    assert "opt results/zoo_shadow_book.json" in wf, "artifact must be staged as OPTIONAL, not need()"


@pytest.mark.skipif(not (ROOT / "data" / "ohlcv.pkl").exists(),
                    reason="pinned OHLCV cache absent (CI); structural tests above still bind")
def test_the_live_arm_reproduces_the_record_exactly():
    """The end-to-end guarantee: the shadow book's own live arm must BE the record. If widening the
    pool could perturb the record's selection or sizing, this is where it would show."""
    import run_bhanushali_weekly_rank as R94
    from nq.data.membership import load_membership
    from run_bhanushali_path1 import corrected_universe
    import run_zoo_shadow_book as Z

    ohlcv = corrected_universe()
    mem = load_membership()
    m_live = R94.backtest(R94.prep_weekly_rank(ohlcv), mem, start="2017-01-01")
    assert abs(m_live["sharpe"] - 1.132) < 0.01 and m_live["trades"] == 255

    # building the wider pool must leave the record's own numbers untouched
    m_after = R94.backtest(R94.prep_weekly_rank(ohlcv, **Z._pool_kwargs()), mem, start="2017-01-01")
    m_live2 = R94.backtest(R94.prep_weekly_rank(ohlcv), mem, start="2017-01-01")
    assert m_live2["sharpe"] == m_live["sharpe"] and m_live2["trades"] == m_live["trades"], (
        "computing the shadow pool changed the record — shared mutable state")
    assert m_after["trades"] != m_live["trades"], "the wider pool should change the SHADOW arm"
