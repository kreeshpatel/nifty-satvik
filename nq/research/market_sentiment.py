"""Market-level news sentiment, recorded forward-only (owner approval 2026-11-17).

One reading a week, for the Indian market as a whole, written with the Saturday scan and frozen. It decides nothing:
no signal, rank, size, stop or exit may read it. The per-signal reading proposed alongside it was **dropped by the
owner**; this module is market-level only, and adding a per-ticker reading later is a new decision.

**Why forward-only.** Sentiment cannot be reconstructed point-in-time — a model reading a 2021 article today has seen
what happened next (`long_horizon/charter.md` §4). So nothing here is ever backfilled, and the series starts the day
it starts.

**What is frozen** (changing any of it starts a NEW series, under a new `series_id`): the model, the prompt, the
schema, and the question asked. Every row carries the prompt hash and the model name so a later change is visible.

The evaluation is pre-committed in `research/BACKLOG.md` and read at 26 weeks, not before: sentiment quartiles against
the mean R of trades entered in those weeks, needing a monotone relation AND a top-minus-bottom gap of at least 0.5R
with a bootstrap interval that excludes zero. Anything else is a KILL for the reading, with no retune.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

SERIES_ID = "market-v1"
MODEL = "claude-opus-5"              # pinned, like the judge's: a substitution is a different instrument
EFFORT = "medium"
MAX_TOKENS = 2000
WEB_SEARCH_TOOL = {"type": "web_search_20260209", "name": "web_search", "max_uses": 5}

PROMPT = """You are recording a market-sentiment reading for the Indian equity market. It is used for research only
and must never be a trading recommendation.

Search for Indian market and economy news published in the LAST 7 DAYS up to and including {as_of}. Read headlines and
lead paragraphs only. Do not search for, or reason about, anything dated after {as_of}.

Then answer, about the mood and the conditions of the Indian equity market over that week ONLY:

1. `sentiment`: a number from -1.0 (broadly bad news: selling, downgrades, macro stress) to +1.0 (broadly good news:
   inflows, upgrades, benign macro). 0.0 means mixed or quiet.
2. `confidence`: "low", "medium" or "high" — how clear the week's picture was, not how strong the sentiment.
3. `stress_tags`: zero or more of exactly these: policy, rates, currency, global, earnings-season, liquidity, scandal.
4. `summary`: one sentence, at most 30 words, describing the week. No prediction, no advice.
5. `n_headlines`: roughly how many distinct headlines informed the reading.

Judge the week that happened. Do not forecast, do not mention any stock to buy or sell, and do not say what the market
will do next."""

SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["sentiment", "confidence", "stress_tags", "summary", "n_headlines"],
    "properties": {
        "sentiment": {"type": "number", "minimum": -1.0, "maximum": 1.0},
        "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
        "stress_tags": {"type": "array", "items": {"type": "string",
                        "enum": ["policy", "rates", "currency", "global", "earnings-season", "liquidity", "scandal"]}},
        "summary": {"type": "string", "maxLength": 240},
        "n_headlines": {"type": "integer", "minimum": 0},
    },
}
PROMPT_SHA = hashlib.sha256(PROMPT.encode()).hexdigest()[:16]


def sources(resp: Any) -> list[dict]:
    """Every web result the model actually saw, so a row can be audited later (the judge's §3.6 pattern)."""
    out: list[dict] = []
    for block in getattr(resp, "content", []) or []:
        if getattr(block, "type", None) == "web_search_tool_result":
            for r in getattr(block, "content", []) or []:
                u, t = getattr(r, "url", None), getattr(r, "title", None)
                if u:
                    out.append({"url": u, "title": t, "page_age": getattr(r, "page_age", None)})
    return out


def read_market(client: Any, *, as_of: str) -> dict:
    """One frozen reading for the week ending `as_of`. Never raises: a failed reading is recorded as a failed row."""
    row: dict[str, Any] = {"series_id": SERIES_ID, "as_of": as_of, "model": MODEL, "effort": EFFORT,
                           "prompt_sha256": PROMPT_SHA, "schema_version": 1,
                           "news_source": "anthropic.web_search_20260209",
                           "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                           "decides_nothing": True}
    try:
        resp = client.messages.create(
            model=MODEL, max_tokens=MAX_TOKENS,
            output_config={"effort": EFFORT, "format": {"type": "json_schema", "schema": SCHEMA}},
            tools=[WEB_SEARCH_TOOL],
            messages=[{"role": "user", "content": [{"type": "text", "text": PROMPT.format(as_of=as_of)}]}],
        )
    except Exception as exc:                                    # noqa: BLE001 — never block the scanner
        return row | {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    text = "".join(getattr(b, "text", "") for b in getattr(resp, "content", []) or [] if getattr(b, "type", None) == "text")
    try:
        data = json.loads(text)
    except ValueError:
        return row | {"ok": False, "error": "the model did not return the agreed JSON", "raw": text[:400]}
    usage = getattr(resp, "usage", None)
    if usage is not None:
        row["usage"] = {"input_tokens": int(getattr(usage, "input_tokens", 0) or 0),
                        "output_tokens": int(getattr(usage, "output_tokens", 0) or 0)}
    return row | {"ok": True, "sources": sources(resp), "stop_reason": getattr(resp, "stop_reason", None)} | data
