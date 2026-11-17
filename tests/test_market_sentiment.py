"""Market sentiment (owner approval 2026-11-17): forward-only, append-only, and it decides nothing."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from nq.research import market_sentiment as M  # noqa: E402


class _Resp:
    def __init__(self, payload, sources=()):
        self.content = [SimpleNamespace(type="text", text=json.dumps(payload))] + [
            SimpleNamespace(type="web_search_tool_result",
                            content=[SimpleNamespace(url=u, title=t, page_age=None) for u, t in sources])]
        self.usage = SimpleNamespace(input_tokens=1200, output_tokens=180)
        self.stop_reason = "end_turn"


class _Client:
    def __init__(self, resp=None, boom=None):
        self.resp, self.boom, self.seen = resp, boom, {}
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kw):
        self.seen = kw
        if self.boom:
            raise self.boom
        return self.resp


OK = {"sentiment": -0.4, "confidence": "medium", "stress_tags": ["rates", "global"],
      "summary": "A weak week for Indian equities on rate worries and global selling.", "n_headlines": 18}


def test_a_reading_is_recorded_with_its_provenance():
    c = _Client(_Resp(OK, [("https://example.com/a", "Markets fall")]))
    row = M.read_market(c, as_of="2026-11-21")
    assert row["ok"] and row["sentiment"] == -0.4 and row["as_of"] == "2026-11-21"
    assert row["model"] == M.MODEL and row["prompt_sha256"] == M.PROMPT_SHA and row["decides_nothing"] is True
    assert row["sources"][0]["url"] == "https://example.com/a"


def test_the_prompt_pins_the_week_and_forbids_a_forecast():
    c = _Client(_Resp(OK))
    M.read_market(c, as_of="2026-11-21")
    sent = c.seen["messages"][0]["content"][0]["text"]
    assert "2026-11-21" in sent and "LAST 7 DAYS" in sent
    assert "Do not search for, or reason about, anything dated after" in sent
    assert "do not say what the market" in sent.lower() and "recommendation" in sent.lower()


def test_a_failure_is_recorded_rather_than_raised():
    row = M.read_market(_Client(boom=RuntimeError("api down")), as_of="2026-11-21")
    assert row["ok"] is False and "api down" in row["error"] and row["as_of"] == "2026-11-21"
    assert M.read_market(_Client(_Resp("not json" if False else {}) ), as_of="x") is not None


def test_bad_json_is_recorded_not_raised():
    bad = SimpleNamespace(content=[SimpleNamespace(type="text", text="sorry, I cannot")], usage=None, stop_reason="end_turn")
    row = M.read_market(_Client(bad), as_of="2026-11-21")
    assert row["ok"] is False and "agreed JSON" in row["error"]


def test_the_file_is_append_only_and_one_row_a_week(tmp_path, monkeypatch):
    import run_market_sentiment as S
    out = tmp_path / "sentiment_forward.jsonl"
    monkeypatch.setattr(S, "OUT", out)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    monkeypatch.setattr(S, "read_market", lambda client, as_of: {"series_id": M.SERIES_ID, "as_of": as_of, "ok": True,
                                                                 "sentiment": 0.1, "confidence": "low", "n_headlines": 3})
    monkeypatch.setitem(sys.modules, "anthropic", SimpleNamespace(Anthropic=lambda: _Client(_Resp(OK))))
    monkeypatch.setattr(sys, "argv", ["x", "--as-of", "2026-11-21"])
    assert S.main() == 0
    first = out.read_text(encoding="utf-8")
    assert S.main() == 0                                   # a re-run of the same week must not add a row
    assert out.read_text(encoding="utf-8") == first
    monkeypatch.setattr(sys, "argv", ["x", "--as-of", "2026-11-28"])
    S.main()
    assert out.read_text(encoding="utf-8").startswith(first) and len(out.read_text(encoding="utf-8").splitlines()) == 2


def test_no_decision_code_reads_the_sentiment_file():
    """It decides nothing: the engine, the scan and the record builders must not mention it."""
    for rel in ("scripts/run_bhanushali_cron.py", "scripts/run_bhanushali_weekly_rank.py", "scripts/run_bhanushali_monitor.py",
                "nq/engine/portfolio.py", "nq/engine/rebalance_book.py", "pipelines/lifecycle/update_records.py"):
        src = (ROOT / rel).read_text(encoding="utf-8")
        for word in ("sentiment_forward", "market_sentiment", "SERIES_ID"):
            assert word not in src, f"{rel} mentions {word}: the sentiment reading decides nothing"
