"""The prediction ledger must refuse anything that would let hindsight in.

Every assertion here is about a way the ledger could quietly stop being evidence:

  * a forecast stamped at or after its own outcome — the one rule that makes calibration measurable;
  * a rewritten row, a reordered row, a removed row — all caught by the chain;
  * a second resolution, or a resolution of something that was never predicted;
  * a Brier score pronounced on a handful of forecasts.

The chain shape deliberately mirrors `nq/paper/judge_log.py`, which already earned it.
"""

from __future__ import annotations

import json

import pytest

from nq.brain import predictions as P


@pytest.fixture
def log(tmp_path):
    return tmp_path / "prediction_ledger.jsonl"


def _pred(log, prob=0.33, stamped="2026-10-03T18:00:00Z", by="2026-11-03", subject="AAA:2026-10-03",
          basis="first_passage_null", claim="reaches +2R before its stop"):
    return P.append_prediction(subject=subject, claim=claim, probability=prob, stamped_at=stamped,
                               resolve_by=by, basis=basis, path=log)


# ---------------------------------------------------------------- the rule that makes it evidence
def test_a_forecast_stamped_after_its_outcome_is_refused(log):
    with pytest.raises(P.IntegrityError, match="strictly before"):
        _pred(log, stamped="2026-11-03T18:00:00Z", by="2026-11-03")


def test_a_forecast_stamped_exactly_at_its_outcome_is_refused(log):
    """Equality is not 'before'. A same-instant stamp is the cheapest way to launder hindsight."""
    with pytest.raises(P.IntegrityError, match="strictly before"):
        _pred(log, stamped="2026-11-03", by="2026-11-03")


def test_a_forecast_before_its_outcome_is_accepted(log):
    h = _pred(log)
    rows = P.read_verified(log)
    assert len(rows) == 1 and rows[0]["row_hash"] == h
    assert rows[0]["kind"] == "prediction" and rows[0]["seq"] == 0


@pytest.mark.parametrize("prob", [-0.01, 1.01, 2.0])
def test_a_probability_outside_zero_to_one_is_refused(log, prob):
    with pytest.raises(P.IntegrityError, match="not in"):
        _pred(log, prob=prob)


def test_a_claim_that_cannot_be_resolved_is_refused(log):
    with pytest.raises(P.IntegrityError, match="no claim"):
        _pred(log, claim="   ")


# ---------------------------------------------------------------- the chain
def test_a_rewritten_row_breaks_the_chain(log):
    _pred(log)
    _pred(log, subject="BBB:2026-10-03")
    rows = P.read_verified(log)
    rows[0]["probability"] = 0.99                    # the edit a forecaster would want to make
    ok, bad = P.verify_chain(rows)
    assert not ok and bad == 0


def test_a_reordered_row_breaks_the_chain(log):
    _pred(log)
    _pred(log, subject="BBB:2026-10-03")
    rows = P.read_verified(log)
    ok, bad = P.verify_chain([rows[1], rows[0]])
    assert not ok and bad == 0


def test_a_removed_row_breaks_the_chain(log):
    _pred(log)
    _pred(log, subject="BBB:2026-10-03")
    _pred(log, subject="CCC:2026-10-03")
    rows = P.read_verified(log)
    ok, bad = P.verify_chain([rows[0], rows[2]])
    assert not ok and bad == 1


def _corrupt(log, **changes) -> None:
    """Rewrite the first row through JSON, so the corruption cannot silently miss on formatting."""
    rows = [json.loads(ln) for ln in log.read_text(encoding="utf-8").splitlines() if ln.strip()]
    rows[0].update(changes)
    log.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows), encoding="utf-8")


def test_appending_onto_a_corrupt_chain_is_refused(log):
    _pred(log)
    _corrupt(log, probability=0.99)
    with pytest.raises(P.IntegrityError, match="fails to verify"):
        _pred(log, subject="BBB:2026-10-03")


def test_read_verified_raises_rather_than_returning_a_corrupt_ledger(log):
    _pred(log)
    _corrupt(log, subject="ZZZ:2026-10-03")
    with pytest.raises(P.IntegrityError):
        P.read_verified(log)


# ---------------------------------------------------------------- resolution is its own row
def test_resolution_never_rewrites_the_forecast(log):
    h = _pred(log, prob=0.33)
    before = log.read_text(encoding="utf-8")
    P.append_resolution(predicts=h, outcome=True, resolved_at="2026-10-20", path=log)
    after = log.read_text(encoding="utf-8")
    assert after.startswith(before), "the forecast's own line must survive verbatim"
    rows = P.read_verified(log)
    assert [r["kind"] for r in rows] == ["prediction", "resolution"]
    assert rows[0]["probability"] == 0.33           # untouched


def test_resolving_an_unknown_prediction_is_refused(log):
    _pred(log)
    with pytest.raises(P.IntegrityError, match="no prediction"):
        P.append_resolution(predicts="deadbeef", outcome=True, resolved_at="2026-10-20", path=log)


def test_double_resolution_is_refused(log):
    h = _pred(log)
    P.append_resolution(predicts=h, outcome=True, resolved_at="2026-10-20", path=log)
    with pytest.raises(P.IntegrityError, match="already resolved"):
        P.append_resolution(predicts=h, outcome=False, resolved_at="2026-10-21", path=log)


def test_a_resolution_cannot_precede_its_forecast(log):
    h = _pred(log, stamped="2026-10-03T18:00:00Z")
    with pytest.raises(P.IntegrityError, match="precedes"):
        P.append_resolution(predicts=h, outcome=True, resolved_at="2026-09-01", path=log)


# ---------------------------------------------------------------- scoring
def test_brier_is_the_squared_error():
    assert P.brier(1.0, True) == 0.0
    assert P.brier(0.0, True) == 1.0
    assert P.brier(0.5, True) == 0.25
    assert P.brier(0.5, False) == 0.25


def test_unresolved_forecasts_are_excluded_from_scoring(log):
    h = _pred(log)
    _pred(log, subject="BBB:2026-10-03")             # left unresolved
    P.append_resolution(predicts=h, outcome=True, resolved_at="2026-10-20", path=log)
    pairs = P.resolved_pairs(P.read_verified(log))
    assert len(pairs) == 1 and pairs[0]["subject"] == "AAA:2026-10-03"


def test_a_handful_of_forecasts_is_not_calibration(log):
    h = _pred(log)
    P.append_resolution(predicts=h, outcome=True, resolved_at="2026-10-20", path=log)
    s = P.summarise(P.read_verified(log))
    assert s["n_resolved"] == 1
    assert s["informative"] is False
    assert "BELOW THE FLOOR" in s["reading"]


def test_calibration_reports_the_references_that_make_a_brier_readable(log):
    """A Brier score alone is not interpretable — always-50% and always-the-base-rate must sit beside it."""
    for i in range(P.MIN_RESOLVED):
        h = _pred(log, prob=0.6, subject=f"T{i}:2026-10-03")
        P.append_resolution(predicts=h, outcome=bool(i % 2), resolved_at="2026-10-20", path=log)
    s = P.summarise(P.read_verified(log))
    assert s["n_resolved"] == P.MIN_RESOLVED and s["informative"] is True
    assert s["always_50pct_reference"] == 0.25
    assert s["base_rate"] == pytest.approx(0.5)
    assert s["always_base_rate_reference"] == pytest.approx(0.25)
    assert s["by_basis"]["first_passage_null"]["n"] == P.MIN_RESOLVED


def test_scores_are_split_by_basis_so_a_model_can_be_read_against_the_null(log):
    for i in range(4):
        h = _pred(log, prob=0.9, subject=f"N{i}:2026-10-03", basis="first_passage_null")
        P.append_resolution(predicts=h, outcome=True, resolved_at="2026-10-20", path=log)
    for i in range(4):
        h = _pred(log, prob=0.1, subject=f"O{i}:2026-10-03", basis="owner")
        P.append_resolution(predicts=h, outcome=True, resolved_at="2026-10-20", path=log)
    s = P.summarise(P.read_verified(log))
    assert s["by_basis"]["first_passage_null"]["mean_brier"] < s["by_basis"]["owner"]["mean_brier"]


def test_a_claim_about_the_system_itself_is_a_first_class_subject(log):
    """Layer 6: forecasts about markets AND about itself ("HEG carries after the scan")."""
    h = _pred(log, subject="self", claim="HEG carries after the scan", prob=0.8, basis="owner")
    P.append_resolution(predicts=h, outcome=True, resolved_at="2026-10-05", path=log)
    pairs = P.resolved_pairs(P.read_verified(log))
    assert pairs[0]["subject"] == "self" and pairs[0]["brier"] == pytest.approx(0.04)


def test_the_ledger_is_one_json_object_per_line(log):
    _pred(log)
    _pred(log, subject="BBB:2026-10-03")
    for line in log.read_text(encoding="utf-8").splitlines():
        assert json.loads(line)["row_hash"]
