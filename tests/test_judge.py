"""Contract tests for the informed judge (pre-reg 0125). No network: a fake client stands in.

These pin the properties the pre-registration froze, so a later edit that changes the instrument
fails a test instead of silently starting a new cohort inside the old one.
"""
from __future__ import annotations

import json

import pytest

from nq.paper import judge as J


class _Usage:
    input_tokens, output_tokens = 1000, 200
    cache_read_input_tokens = cache_creation_input_tokens = 0


class _Block:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class _Resp:
    def __init__(self, content, stop_reason="end_turn", stop_details=None):
        self.content, self.stop_reason, self.stop_details = content, stop_reason, stop_details
        self.usage = _Usage()


class _FakeClient:
    """Records the request so the frozen call shape can be asserted."""

    def __init__(self, resp=None, raise_exc=None, model_id=J.MODEL):
        self._resp, self._raise, self._model_id = resp, raise_exc, model_id
        self.calls: list[dict] = []
        self.models = self                                   # models.retrieve lives on the same object

    def retrieve(self, model):                               # client.models.retrieve
        if self._model_id is None:
            raise RuntimeError("not found")
        return _Block(id=self._model_id)

    @property
    def messages(self):
        return self

    def create(self, **kw):                                  # client.messages.create
        self.calls.append(kw)
        if self._raise:
            raise self._raise
        return self._resp


def _ok_resp(verdict="take"):
    payload = {"verdict": verdict, "conviction": 4, "primary_reason": "no material news found",
               "risk_flag": "none"}
    return _Resp([
        _Block(type="server_tool_use", name="web_search", input={"query": "ACME news"}),
        _Block(type="web_search_tool_result",
               content=[_Block(url="https://x.test/a", title="ACME Q1", page_age="2 days")]),
        _Block(type="text", text=json.dumps(payload)),
    ])


CARD = {"ticker": "ACME", "signal_date": "2026-08-01", "entry": 100.0, "entry_low": 95.0,
        "entry_high": 105.0, "stop": 90.0, "target": 130.0, "crs_rank": 0.12, "grade": "A",
        "pattern": "44-week SMA pullback"}


# ── the frozen call shape (pre-reg §3) ────────────────────────────────────────────────────────────

def test_model_and_effort_are_pinned_and_temperature_is_never_sent():
    """`temperature` returns HTTP 400 on the pinned model; effort is the determinism control."""
    c = _FakeClient(_ok_resp())
    J.judge_card(c, card=CARD, chart_png=b"png", context_json="{}", as_of="2026-08-01",
                 fetched_at="t")
    kw = c.calls[0]
    assert kw["model"] == "claude-opus-5"
    assert kw["output_config"]["effort"] == "high"
    assert "temperature" not in kw and "top_p" not in kw and "top_k" not in kw


def test_structured_output_schema_is_frozen():
    c = _FakeClient(_ok_resp())
    J.judge_card(c, card=CARD, chart_png=b"png", context_json="{}", as_of="d", fetched_at="t")
    fmt = c.calls[0]["output_config"]["format"]
    assert fmt["type"] == "json_schema"
    schema = fmt["schema"]
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {"verdict", "conviction", "primary_reason", "risk_flag"}
    assert schema["properties"]["verdict"]["enum"] == ["take", "skip", "wait"]
    assert schema["properties"]["conviction"]["enum"] == [1, 2, 3, 4, 5]


def test_exactly_one_call_per_card_and_news_tool_is_attached():
    c = _FakeClient(_ok_resp())
    J.judge_card(c, card=CARD, chart_png=b"png", context_json="{}", as_of="d", fetched_at="t")
    assert len(c.calls) == 1
    assert c.calls[0]["tools"] == [J.WEB_SEARCH_TOOL]


def test_prompt_hash_is_logged_so_an_edit_is_visible():
    row = J.judge_card(_FakeClient(_ok_resp()), card=CARD, chart_png=b"png", context_json="{}",
                       as_of="d", fetched_at="t")
    assert row["prompt_sha256"] == J.PROMPT_SHA
    assert row["chart_sha256"] == __import__("hashlib").sha256(b"png").hexdigest()


# ── failure tolerance (pre-reg §6): never raise, always log ────────────────────────────────────────

def test_api_exception_is_logged_not_raised():
    row = J.judge_card(_FakeClient(raise_exc=RuntimeError("boom")), card=CARD, chart_png=b"p",
                       context_json="{}", as_of="d", fetched_at="t")
    assert row["ok"] is False and "boom" in row["error"]


def test_refusal_is_checked_before_content_is_read():
    """A refusal is HTTP 200 with empty content — indexing content[0] would crash."""
    resp = _Resp([], stop_reason="refusal", stop_details=_Block(category="cyber"))
    row = J.judge_card(_FakeClient(resp), card=CARD, chart_png=b"p", context_json="{}",
                       as_of="d", fetched_at="t")
    assert row["ok"] is False and row["error"] == "refusal" and row["refusal_category"] == "cyber"


def test_unparseable_verdict_is_logged():
    row = J.judge_card(_FakeClient(_Resp([_Block(type="text", text="not json")])), card=CARD,
                       chart_png=b"p", context_json="{}", as_of="d", fetched_at="t")
    assert row["ok"] is False and "unparseable" in row["error"]


# ── provenance + cost ─────────────────────────────────────────────────────────────────────────────

def test_search_provenance_and_cost_are_logged():
    row = J.judge_card(_FakeClient(_ok_resp()), card=CARD, chart_png=b"p", context_json="{}",
                       as_of="d", fetched_at="2026-08-01T12:00:00Z")
    kinds = [s["kind"] for s in row["search"]]
    assert kinds == ["query", "results"]
    assert row["search"][1]["results"][0]["url"] == "https://x.test/a"
    assert row["news_fetched_at"] == "2026-08-01T12:00:00Z"
    assert row["news_source"] == "anthropic.web_search_20260209"
    assert row["cost_usd"] == pytest.approx(1000 / 1e6 * 5.0 + 200 / 1e6 * 25.0)


def test_web_search_error_object_does_not_crash_provenance():
    """Search errors arrive as HTTP 200 with an error OBJECT where results would be a LIST."""
    resp = _Resp([_Block(type="web_search_tool_result", content=_Block(error_code="max_uses_exceeded")),
                  _Block(type="text", text=json.dumps(
                      {"verdict": "wait", "conviction": 2, "primary_reason": "x", "risk_flag": "y"}))])
    row = J.judge_card(_FakeClient(resp), card=CARD, chart_png=b"p", context_json="{}",
                       as_of="d", fetched_at="t")
    assert row["ok"] is True
    assert row["search"][0] == {"kind": "error", "error_code": "max_uses_exceeded"}


# ── drift alarm (pre-reg §6): alarm, never substitute ─────────────────────────────────────────────

def test_drift_alarm_fires_when_pinned_model_is_gone():
    with pytest.raises(J.ModelDriftError):
        J.assert_model_available(_FakeClient(model_id=None))


def test_drift_alarm_fires_on_a_silent_substitution():
    with pytest.raises(J.ModelDriftError, match="resolved to"):
        J.assert_model_available(_FakeClient(model_id="claude-sonnet-5"))


def test_drift_alarm_passes_on_the_pinned_model():
    J.assert_model_available(_FakeClient(model_id=J.MODEL))


# ── card context is echoed, never re-derived (D5 parity) ─────────────────────────────────────────

def test_context_echoes_printed_numbers_and_computes_rr_from_them():
    ctx = json.loads(J.build_card_context(
        CARD, sma44=88.0, ext_vs_sma_pct=13.6, ext_band="10-15%",
        event_status={"days_to_known_event": 5.0, "known_event_within_14cd": True}))
    assert ctx["printed_entry"] == 100.0 and ctx["printed_stop"] == 90.0
    assert ctx["reward_to_risk"] == 3.0                      # (130-100)/(100-90)
    assert ctx["ext_band"] == "10-15%" and ctx["crs_rank"] == 0.12
    assert ctx["earnings_calendar_pit"]["known_event_within_14cd"] is True


def test_context_tolerates_a_degenerate_stop():
    ctx = json.loads(J.build_card_context({**CARD, "stop": 100.0}, sma44=None,
                                          ext_vs_sma_pct=None, ext_band=None, event_status=None))
    assert ctx["reward_to_risk"] is None


# ── the prohibition (pre-reg §1) is structural, not documentary ───────────────────────────────────

def test_no_historical_entry_point_exists():
    """A backfill/as-of path would void the pre-registration — assert none is exposed."""
    import inspect

    # `as_of` is the LABEL of today's run, and the news fetch is always live — there is no parameter
    # anywhere on the public surface that would let a caller aim the judge at a past week.
    sig = inspect.signature(J.judge_card)
    assert "as_of" in sig.parameters and "fetched_at" in sig.parameters
    banned_params = {"start", "end", "backfill", "asof_override", "history", "replay", "since"}
    for name, fn in vars(J).items():
        if (name.startswith("_") or not inspect.isfunction(fn)
                or getattr(fn, "__module__", None) != J.__name__):
            continue
        assert not (banned_params & set(inspect.signature(fn).parameters)), name
        assert not any(k in name.lower() for k in ("backfill", "replay", "historic")), name
