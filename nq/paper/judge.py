"""The informed judge — one frozen, structured verdict per issued card (pre-reg 0125).

**FORWARD MEASUREMENT ONLY.** This module is deliberately incapable of a historical run: it takes a
card as the scanner just issued it and fetches news at call time. There is no `as_of` parameter, no
backfill path, and none may be added — the model's training data contains the outcomes, and the
design cannot be blinded (news + event dates identify the stock and the week). See pre-reg §1.

The verdict is **logged, never acted on**. Nothing in the engine, the book, or the card reads it.

Frozen per pre-reg §3 — any change is a dated amendment that starts a new evaluation cohort:
  model `claude-opus-5` · effort `high` · one independent call per card · this prompt · this schema.

`temperature` is NOT set: it was removed on the Opus 4.7+ family and returns HTTP 400 on the pinned
model. Effort is the determinism control, exactly as 0123 froze it.
"""
from __future__ import annotations

import base64
import hashlib
import json
from typing import Any, Mapping

MODEL = "claude-opus-5"          # pinned; a substitution is a different instrument (pre-reg §6)
EFFORT = "high"                  # frozen determinism control (see module docstring)
MAX_TOKENS = 4000
WEB_SEARCH_TOOL = {"type": "web_search_20260209", "name": "web_search", "max_uses": 4}

# Opus 5 pricing, $/MTok — logged per run so cost is attributable, not estimated later.
USD_PER_MTOK_IN, USD_PER_MTOK_OUT = 5.0, 25.0

JUDGE_PROMPT = """You are reviewing ONE issued stock recommendation card for an Indian (NSE) weekly \
swing-trading system, as a second opinion. The system has already decided to issue this card; you are \
NOT the system and you do not control it. Your verdict is recorded for later study and is not acted on.

You are given: the weekly chart, the card's own arithmetic (entry zone, stop, target, reward:risk), \
where the entry sits relative to the 44-week SMA, the name's cross-sectional relative-strength rank, \
its point-in-time earnings-calendar status, and whatever current news you find by searching.

The chart alone has already been studied on this exact funnel and carries no separating information — \
winners and losers look the same at the decision point. So do not re-litigate the chart. Your job is \
to ask whether anything OUTSIDE the price series — company news, sector news, an imminent event, a \
disclosure, a corporate action, a macro or regulatory development — makes this specific card better or \
worse than its arithmetic suggests.

Search for current news on this company before deciding. If you find nothing material, say so plainly \
and let that inform a neutral verdict; absence of news is a legitimate finding, not a failure.

Return exactly:
- verdict: "take" if you would act on this card as printed, "skip" if you would not act on it at all, \
"wait" if you would act only after something resolves (name what, in primary_reason).
- conviction: 1 (barely held) to 5 (strong), for whichever verdict you gave.
- primary_reason: ONE line, the single most load-bearing reason. Name the specific fact, not a category.
- risk_flag: the one concrete risk that would most change your mind, or "none".

Do not hedge across verdicts. Do not restate the card's numbers back. Do not recommend position sizes."""

PROMPT_SHA = hashlib.sha256(JUDGE_PROMPT.encode()).hexdigest()

VERDICT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["take", "skip", "wait"]},
        "conviction": {"type": "integer", "enum": [1, 2, 3, 4, 5]},
        "primary_reason": {"type": "string"},
        "risk_flag": {"type": "string"},
    },
    "required": ["verdict", "conviction", "primary_reason", "risk_flag"],
    "additionalProperties": False,
}


class ModelDriftError(RuntimeError):
    """The pinned model is unavailable. Alarm and stop — never silently substitute (pre-reg §6)."""


def assert_model_available(client: Any) -> None:
    """Drift alarm. Raises :class:`ModelDriftError` rather than letting the run fall to another model."""
    try:
        got = client.models.retrieve(MODEL)
    except Exception as exc:                                    # noqa: BLE001 — any failure is drift
        raise ModelDriftError(f"pinned model {MODEL!r} could not be retrieved: {exc!r}") from exc
    ident = getattr(got, "id", None)
    if ident != MODEL:
        raise ModelDriftError(f"pinned model {MODEL!r} resolved to {ident!r}")


def build_card_context(card: Mapping[str, Any], *, sma44: float | None,
                       ext_vs_sma_pct: float | None, ext_band: str | None,
                       event_status: Mapping[str, Any] | None) -> str:
    """The non-chart inputs, rendered verbatim from the card (D5 parity — never re-derived)."""
    entry, stop, target = card.get("entry"), card.get("stop"), card.get("target")
    rr = None
    try:
        risk = float(entry) - float(stop)
        if risk > 0:
            rr = round((float(target) - float(entry)) / risk, 2)
    except (TypeError, ValueError):
        rr = None
    ev = dict(event_status or {})
    return json.dumps({
        "ticker": card.get("ticker"),
        "signal_date": card.get("signal_date"),
        "entry_zone": [card.get("entry_low"), card.get("entry_high")],
        "printed_entry": entry, "printed_stop": stop, "printed_target": target,
        "reward_to_risk": rr,
        "stop_distance_pct": (round(100.0 * (float(entry) - float(stop)) / float(entry), 2)
                              if entry and stop else None),
        "sma44_signal_week": sma44,
        "ext_vs_sma_pct": ext_vs_sma_pct, "ext_band": ext_band,
        "crs_rank": card.get("crs_rank"), "grade": card.get("grade"),
        "pattern": card.get("pattern"),
        "earnings_calendar_pit": {
            "days_to_known_event": ev.get("days_to_known_event"),
            "known_event_within_14cd": ev.get("known_event_within_14cd"),
        },
    }, sort_keys=True, default=str)


def _search_metadata(content: Any) -> list[dict[str, Any]]:
    """Source + fetch provenance for every web_search result the model actually saw (pre-reg §3.6).

    Search errors arrive as HTTP 200 with an error object rather than an exception, so branch on the
    shape: a success `content` is a LIST of results, an error `content` is a single object.
    """
    out: list[dict[str, Any]] = []
    for block in content or []:
        btype = getattr(block, "type", None)
        if btype == "server_tool_use" and getattr(block, "name", None) == "web_search":
            out.append({"kind": "query", "input": getattr(block, "input", None)})
        elif btype == "web_search_tool_result":
            inner = getattr(block, "content", None)
            if isinstance(inner, list):
                out.append({"kind": "results", "results": [
                    {"url": getattr(r, "url", None), "title": getattr(r, "title", None),
                     "page_age": getattr(r, "page_age", None)} for r in inner]})
            else:
                out.append({"kind": "error",
                            "error_code": getattr(inner, "error_code", None) or str(inner)})
    return out


def judge_card(client: Any, *, card: Mapping[str, Any], chart_png: bytes, context_json: str,
               as_of: str, fetched_at: str) -> dict[str, Any]:
    """ONE independent call. Returns a log row — **never raises** on an API failure (pre-reg §6).

    A failure is recorded as a row with ``ok: False`` and its error, so the record shows what was
    attempted. A transport-level retry inside the SDK returns the same content and is not a re-roll;
    this function makes exactly one scored call and never re-asks for a better answer.
    """
    row: dict[str, Any] = {
        "as_of": as_of, "ticker": str(card.get("ticker")),
        "signal_date": str(card.get("signal_date")),
        "model": MODEL, "effort": EFFORT, "prompt_sha256": PROMPT_SHA,
        "news_source": "anthropic.web_search_20260209", "news_fetched_at": fetched_at,
        "context": context_json, "chart_sha256": hashlib.sha256(chart_png).hexdigest(),
    }
    try:
        resp = client.messages.create(
            model=MODEL, max_tokens=MAX_TOKENS,
            output_config={"effort": EFFORT,
                           "format": {"type": "json_schema", "schema": VERDICT_SCHEMA}},
            tools=[WEB_SEARCH_TOOL],
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                             "data": base64.standard_b64encode(chart_png).decode()}},
                {"type": "text", "text": JUDGE_PROMPT},
                {"type": "text", "text": f"CARD CONTEXT (verbatim from the issued card):\n{context_json}"},
            ]}],
        )
    except Exception as exc:                                    # noqa: BLE001 — never block the scanner
        row.update(ok=False, error=f"{type(exc).__name__}: {exc}")
        return row

    stop_reason = getattr(resp, "stop_reason", None)
    row["stop_reason"] = stop_reason
    usage = getattr(resp, "usage", None)
    if usage is not None:
        tin = int(getattr(usage, "input_tokens", 0) or 0)
        tout = int(getattr(usage, "output_tokens", 0) or 0)
        row["usage"] = {
            "input_tokens": tin, "output_tokens": tout,
            "cache_read_input_tokens": int(getattr(usage, "cache_read_input_tokens", 0) or 0),
            "cache_creation_input_tokens": int(getattr(usage, "cache_creation_input_tokens", 0) or 0),
        }
        row["cost_usd"] = round(tin / 1e6 * USD_PER_MTOK_IN + tout / 1e6 * USD_PER_MTOK_OUT, 6)
    row["search"] = _search_metadata(getattr(resp, "content", None))

    # Check stop_reason BEFORE reading content: a refusal returns HTTP 200 with empty/partial content.
    if stop_reason == "refusal":
        row.update(ok=False, error="refusal",
                   refusal_category=getattr(getattr(resp, "stop_details", None), "category", None))
        return row

    text = next((b.text for b in (getattr(resp, "content", None) or [])
                 if getattr(b, "type", None) == "text"), None)
    if not text:
        row.update(ok=False, error="no text block in response")
        return row
    try:
        verdict = json.loads(text)
    except json.JSONDecodeError as exc:
        row.update(ok=False, error=f"unparseable verdict: {exc}", raw_text=text[:2000])
        return row

    row.update(ok=True, verdict=verdict.get("verdict"), conviction=verdict.get("conviction"),
               primary_reason=verdict.get("primary_reason"), risk_flag=verdict.get("risk_flag"),
               raw_text=text)
    return row
