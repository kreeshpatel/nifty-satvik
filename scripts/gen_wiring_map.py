#!/usr/bin/env python3
"""Generate the PRODUCT wiring map: every value the weekly book publishes, and who reads it.

WHY THIS EXISTS. `skills/repo-map` maps the ENGINE's values -- the frozen cfg, the sizing
kernel, the exit decision -- and it is the reason those cannot drift silently. Nothing mapped
the other half: the path from a field in `results/signals_today_weekly.json`, through the API
routers, to the React page that prints it. Every defect found on 2026-08-28 lived on that path
and none of them was a reasoning error:

  * `buy_zone_low/high` was published for weeks and read by nobody, while both pages printed
    `entry_low/high` -- the signal WEEK's candle, whose low IS the stop. The board told the
    reader to buy at the stop, and the two pages disagreed with each other.
  * `filled_today` was read as "did this signal trigger", which it never meant.
  * `ext_pct_over_sma44`, `crs_rank`, `no_chase_above`, `band_width_pct` and `body_ratio` --
    the model's entire stated rationale -- were produced every week and displayed nowhere.

A field that is produced and never read is not free: it is a decision the model made and the
product silently withheld. A field read from the wrong source is worse. This map makes both
visible as a diff.

WHAT IT IS NOT. It proves REFERENCE, not correctness: it can tell you `entry_low` is read by
ThisWeek.jsx, not whether that is the right field to read. Judgement stays with the reader --
the map's job is to make the question askable at a glance instead of requiring a grep.

Stdlib only, fully sorted, deterministic -- same contract as scripts/gen_depgraph.py, so the
generated doc diffs cleanly and a re-run is a no-op.

    regenerate with: python scripts/gen_wiring_map.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "PRODUCT_WIRING.md"

# Producers: the committed artifacts the live weekly book writes.
PRODUCERS: dict[str, str] = {
    "results/signals_today_weekly.json": "weekly scanner (Saturday)",
    "results/weekly_monitor.json": "daily monitor (weekdays 16:15 IST)",
}

# Consumers, in the order a value travels. Label -> path relative to ROOT.
# `cards lib` holds the pure derivations that were extracted OUT of the pages on
# 2026-08-28 precisely because inline expressions are how four of them went wrong
# unnoticed. It reads field names too, so it belongs on the path.
CONSUMERS: list[tuple[str, str]] = [
    ("api", "dashboard/backend/routers/signals.py"),
    ("api-exec", "dashboard/backend/routers/execution.py"),
    ("recon", "dashboard/backend/services/reconciliation.py"),
    ("cards lib", "frontend/src/lib/cards.js"),
    ("This week", "frontend/src/pages/ThisWeek.jsx"),
    ("Research", "frontend/src/pages/SignalsV3.jsx"),
    ("Dashboard", "frontend/src/pages/DashboardV3.jsx"),
    ("Portfolio", "frontend/src/pages/PortfolioV3.jsx"),
    ("History", "frontend/src/pages/RecommendationHistory.jsx"),
]

# Pairs that are easy to read for one another. The map calls these out explicitly because
# picking the wrong one of a pair is a silent defect: both exist, both are numbers, both look
# plausible on a card. Each entry is (preferred, confusable_with, why).
# A hazard row is only useful if it points somewhere specific: `entry` vs `fill_price` was
# tried here and flagged seven consumers, because `entry` is legitimately read everywhere. A
# row that indicts the whole codebase teaches nothing, so pairs go here only when the wrong
# choice is both plausible AND localised.
ALIAS_HAZARDS: list[tuple[str, str, str]] = [
    ("buy_zone_low", "entry_low",
     "entry_low is the signal WEEK's candle low, which IS the stop. The record buys inside "
     "buy_zone_*, never down to the stop."),
    ("buy_zone_high", "entry_high",
     "entry_high happens to equal buy_zone_high on most cards, which is exactly why reading the "
     "wrong one goes unnoticed until a card where it does not."),
    ("window_filled", "filled_today",
     "filled_today is recomputed against the LAST bar every run and means 'can I buy at today's "
     "open'. window_filled is whether the signal ever triggered."),
]

# Fields that carry a calendar DATE with no time and no zone. `new Date('YYYY-MM-DD')` is UTC
# midnight, so formatting one in a timezone behind UTC renders the previous day.
DATE_FIELDS = {
    "signal_date", "bought_date", "buy_window_until", "close_date", "due_date",
    "filled_on", "as_of", "generated_at",
}

IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def envelope_fields() -> dict[str, dict[str, set[str]]]:
    """{producer: {field: {card shapes it appears on}}} from the committed artifacts."""
    out: dict[str, dict[str, set[str]]] = {}
    for rel in PRODUCERS:
        path = ROOT / rel
        if not path.exists():
            continue
        try:
            blob = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        fields: dict[str, set[str]] = {}
        records: list[tuple[str, dict]] = []
        if isinstance(blob, dict):
            for key in ("signals", "monitors", "missed_exits"):
                for rec in blob.get(key) or []:
                    if isinstance(rec, dict):
                        shape = str(rec.get("status") or rec.get("kind") or key)
                        records.append((shape, rec))
        for shape, rec in records:
            for f in rec:
                fields.setdefault(f, set()).add(shape)
        if fields:
            out[rel] = fields
    return out


def consumer_tokens() -> dict[str, set[str]]:
    """{consumer label: every identifier that appears in its source}."""
    seen: dict[str, set[str]] = {}
    for label, rel in CONSUMERS:
        path = ROOT / rel
        seen[label] = set(IDENT.findall(path.read_text(encoding="utf-8", errors="ignore"))) \
            if path.exists() else set()
    return seen


def render() -> str:
    produced = envelope_fields()
    tokens = consumer_tokens()
    labels = [label for label, _ in CONSUMERS]

    lines: list[str] = [
        "# Product wiring map — what the book publishes, and who reads it",
        "",
        "**Generated — do not edit by hand.** `python scripts/gen_wiring_map.py`",
        "",
        "This is the product-surface twin of [`skills/repo-map`](../skills/repo-map/SKILL.md),",
        "which maps the engine's values. This one maps the path a value travels from the weekly",
        "artifacts, through the API, to the page that prints it.",
        "",
        "It proves REFERENCE, not correctness: a tick means the file mentions the field, not that",
        "it uses the right one. Read the hazards section for the pairs where that distinction has",
        "already cost us.",
        "",
        "A field with no consumer is a decision the model made and the product withheld. That is",
        "not automatically a bug — some fields are engine-internal — but each one should be a",
        "choice somebody made, not an oversight nobody noticed.",
        "",
    ]

    for rel, fields in sorted(produced.items()):
        lines += [
            f"## `{rel}`",
            "",
            f"Written by the {PRODUCERS[rel]}.",
            "",
            "| field | on cards | " + " | ".join(labels) + " | read by |",
            "|---|---|" + "---|" * (len(labels) + 1),
        ]
        unread: list[str] = []
        for field in sorted(fields):
            marks = ["✓" if field in tokens[label] else "·" for label in labels]
            n = sum(1 for m in marks if m == "✓")
            if n == 0:
                unread.append(field)
            shapes = ",".join(sorted(fields[field]))
            lines.append(f"| `{field}` | {shapes} | " + " | ".join(marks) + f" | **{n}** |")
        lines.append("")
        if unread:
            lines += [
                f"**Published and read by nothing ({len(unread)}):** "
                + ", ".join(f"`{f}`" for f in unread) + ".",
                "",
                "Each is a value the model computed and no surface shows. Decide per field:",
                "surface it, or record why it is engine-internal.",
                "",
            ]

    lines += ["## Alias hazards", "",
              "Pairs where both fields exist, both are plausible, and picking the wrong one is",
              "silent. Every one of these has been read wrongly at least once.", "",
              "| prefer | easily confused with | why it matters | wrong one still referenced by |",
              "|---|---|---|---|"]
    for prefer, confusable, why in ALIAS_HAZARDS:
        users = [label for label in labels if confusable in tokens[label]]
        lines.append(f"| `{prefer}` | `{confusable}` | {why} | "
                     + (", ".join(users) if users else "— none") + " |")

    lines += ["", "## Calendar-date fields", "",
              "These carry a day with no time and no zone. In JavaScript, `new Date('2026-08-28')`",
              "is UTC midnight, so formatting it in a timezone behind UTC renders the previous day.",
              "Parse them as LOCAL dates (`parseCalendarDate` in SignalsV3.jsx), never with a bare",
              "`new Date(str)`.", "",
              "| field | referenced by |", "|---|---|"]
    all_fields = {f for fields in produced.values() for f in fields}
    for field in sorted(DATE_FIELDS & all_fields):
        users = [label for label in labels if field in tokens[label]]
        lines.append(f"| `{field}` | " + (", ".join(users) if users else "— none") + " |")

    lines += ["", "## How to use this", "",
              "1. Adding a field to the weekly envelope? Regenerate and check it has a consumer.",
              "2. Reading a field on a page? Check the hazards table first — the plausible name",
              "   is not always the right one.",
              "3. Reviewing a surface that 'looks thin'? Scan the unread list. That is the model's",
              "   own reasoning, already computed, sitting unused.",
              ""]
    return "\n".join(lines)


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
