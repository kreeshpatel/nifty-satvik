"""0123 — Vision grader harness for the chart-structure screen.

Renders each sampled trade BLIND + entry-truncated (render_blind_chart) and grades it with a
frozen claude-opus-5 vision call using a forced single-tool schema (structured, version-robust).
Rubric + Phase-1.5 annotations come back in ONE structured response per chart. All raw grades are
committed as artifacts (reproduce-before-trust). Each chart is an INDEPENDENT call (no context bleed).

Modes:
  --render-only        FREE: render every sampled chart, report failures. No API call.
  --grade              PAID: render + grade all (skips ids already in the output jsonl -> resumable).
  --self-consistency   PAID: re-grade a 10% subsample a 2nd time (independent call).
  --truncation N       PAID: re-render N ids at hist_weeks=90 and grade (leakage truncation-trick).

Frozen: model, prompt, effort, output schema. Determinism pinned via those (Opus 5 rejects temperature).
"""
from __future__ import annotations
import sys, json, base64, argparse
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from render_blind_chart import render_blind, OUTDIR

SAMPLE = ROOT / "research" / "substrate" / "sample_0123.csv"
ART = ROOT / "research" / "substrate" / "grades_0123"           # committed artifacts
ART.mkdir(parents=True, exist_ok=True)
GRADES = ART / "grades.jsonl"
GRADES_SC = ART / "grades_selfconsistency.jsonl"
GRADES_TR = ART / "grades_truncation.jsonl"

MODEL = "claude-opus-5"
EFFORT = "medium"
SEED_FRACTION_SC = 0.10

# ---- FROZEN PROMPT (no outcome language anywhere) ----
SYSTEM = (
    "You are a disciplined discretionary swing trader grading a weekly stock chart. The chart is shown "
    "blind: no ticker, no dates, no company. It is truncated at the current decision point — the most "
    "recent completed weekly bar is the far right candle; there are NO future bars. The solid blue line is "
    "the 44-week simple moving average; the orange dashed line is the 20-week SMA; the lower panel is weekly "
    "volume. Grade ONLY the pre-decision structure you can see. Judge the setup as it stands right now; do "
    "not speculate about what happens next. Be strict and consistent."
)
RUBRIC_TOOL = {
    "name": "record_grade",
    "description": "Record the structural grade and structure annotations for this chart.",
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "base_length_score": {"type": "integer", "minimum": 0, "maximum": 5,
                "description": "Quality of the consolidation/base LENGTH before the current bar (0=none/erratic, 5=long well-formed base)."},
            "base_tightness_score": {"type": "integer", "minimum": 0, "maximum": 5,
                "description": "Tightness of that base (0=wide/loose, 5=very tight orderly range)."},
            "volume_dryup_score": {"type": "integer", "minimum": 0, "maximum": 5,
                "description": "Volume dry-up during the base (0=no dry-up/erratic, 5=clear contraction into the base)."},
            "sr_proximity_score": {"type": "integer", "minimum": 0, "maximum": 5,
                "description": "How cleanly price sits relative to nearby support/resistance (0=messy/mid-air, 5=clean level structure)."},
            "breakout_stage": {"type": "string", "enum": ["pre", "at", "extended"],
                "description": "Is price PRE a breakout (still basing), AT a breakout (right at/just through a level), or EXTENDED (already run well past)."},
            "setup_grade": {"type": "string", "enum": ["A", "B", "C", "D", "F"],
                "description": "Overall discretionary setup grade A(best)..F(worst)."},
            "take_now": {"type": "boolean",
                "description": "Would a disciplined swing trader BUY this now (true) or WAIT (false)?"},
            "reason": {"type": "string", "description": "One short line (<=25 words) for the take/wait call."},
            # Phase-1.5 structure annotations (price bands on the visible chart, 0=bottom of price axis, 1=top)
            "sr_zones": {"type": "array", "maxItems": 4, "items": {
                "type": "object", "additionalProperties": False,
                "properties": {"low_frac": {"type": "number"}, "high_frac": {"type": "number"},
                               "kind": {"type": "string", "enum": ["support", "resistance"]}},
                "required": ["low_frac", "high_frac", "kind"]},
                "description": "Support/resistance zones as vertical price bands, y as fraction 0..1 of the visible price axis (0=bottom,1=top)."},
            "box_region": {"type": ["object", "null"], "additionalProperties": False,
                "properties": {"low_frac": {"type": "number"}, "high_frac": {"type": "number"},
                               "start_bars_ago": {"type": "integer"}},
                "required": ["low_frac", "high_frac", "start_bars_ago"],
                "description": "The consolidation/box region if one is present (y-fractions of price axis + how many bars back it starts), else null."},
            "setup_type": {"type": "string",
                "enum": ["flat_base_box", "sr_breakout", "pullback_to_ma", "cup_handle", "ascending_base",
                         "double_bottom", "no_clear_setup", "other"],
                "description": "Best-fit setup classification for what is visible."},
        },
        "required": ["base_length_score", "base_tightness_score", "volume_dryup_score", "sr_proximity_score",
                     "breakout_stage", "setup_grade", "take_now", "reason", "sr_zones", "box_region", "setup_type"],
    },
}


def _client():
    import anthropic
    return anthropic.Anthropic()   # resolves env/profile creds


def _grade_image(client, png_path):
    b64 = base64.standard_b64encode(Path(png_path).read_bytes()).decode()
    kwargs = dict(
        model=MODEL, max_tokens=2000, system=SYSTEM,
        tools=[RUBRIC_TOOL], tool_choice={"type": "tool", "name": "record_grade"},
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}},
            {"type": "text", "text": "Grade this chart via record_grade."},
        ]}],
    )
    try:
        resp = client.messages.create(extra_body={"output_config": {"effort": EFFORT}}, **kwargs)
    except Exception:
        resp = client.messages.create(**kwargs)   # fallback if effort param unsupported
    for blk in resp.content:
        if getattr(blk, "type", None) == "tool_use":
            return blk.input
    raise RuntimeError(f"no tool_use in response for {png_path}")


def _done_ids(path):
    if not path.exists():
        return set()
    return {json.loads(l)["id"] for l in path.read_text().splitlines() if l.strip()}


def _params(png_path):
    """The FROZEN grader request, identical to _grade_image (same model/system/tools/effort).
    Used by both interactive and Batch paths so the instrument is one and the same."""
    b64 = base64.standard_b64encode(Path(png_path).read_bytes()).decode()
    return {
        "model": MODEL, "max_tokens": 2000, "system": SYSTEM,
        "output_config": {"effort": EFFORT},
        "tools": [RUBRIC_TOOL], "tool_choice": {"type": "tool", "name": "record_grade"},
        "messages": [{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}},
            {"type": "text", "text": "Grade this chart via record_grade."},
        ]}],
    }


def _run_batch(client, jobs, out_path, extra):
    """jobs: list of (custom_id, png_path, extra_fields_dict). Submits ONE batch at 50% cost,
    polls to completion, writes tool_use inputs to out_path. Same frozen params via _params()."""
    import time
    reqs = [{"custom_id": cid, "params": _params(p)} for cid, p, _ in jobs]
    meta = {cid: ef for cid, _, ef in jobs}
    batch = client.messages.batches.create(requests=reqs)
    print(f"batch {batch.id} submitted ({len(reqs)} reqs). polling...")
    while True:
        b = client.messages.batches.retrieve(batch.id)
        if b.processing_status == "ended":
            break
        print(f"  {b.processing_status}: {b.request_counts.processing} processing", flush=True)
        time.sleep(30)
    n = 0
    with out_path.open("a") as fh:
        for res in client.messages.batches.results(batch.id):
            if res.result.type != "succeeded":
                print("  batch item failed", res.custom_id, res.result.type); continue
            for blk in res.result.message.content:
                if getattr(blk, "type", None) == "tool_use":
                    fh.write(json.dumps({"id": res.custom_id, **meta[res.custom_id], **blk.input}) + "\n")
                    n += 1
    print(f"batch wrote {n} -> {out_path}")


def run(mode, trunc_n=0):
    df = pd.read_csv(SAMPLE)
    if mode == "render":
        ok = fail = 0
        for _, r in df.iterrows():
            p = render_blind(r["ticker"], r["entry_date"], hist_weeks=60)
            if p:
                ok += 1
            else:
                fail += 1; print("RENDER FAIL", r["id"], r["ticker"], r["entry_date"])
        print(f"render-only: ok={ok} fail={fail} / {len(df)}")
        return

    client = _client()
    if mode == "grade":
        done = _done_ids(GRADES)
        with GRADES.open("a") as fh:
            for _, r in df.iterrows():
                if r["id"] in done:
                    continue
                p = render_blind(r["ticker"], r["entry_date"], hist_weeks=60)
                if not p:
                    continue
                g = _grade_image(client, p)
                fh.write(json.dumps({"id": r["id"], "hw": 60, **g}) + "\n"); fh.flush()
        print(f"graded -> {GRADES}")
    elif mode == "grade_batch":
        done = _done_ids(GRADES)
        jobs = []
        for _, r in df.iterrows():
            if r["id"] in done:
                continue
            p = render_blind(r["ticker"], r["entry_date"], hist_weeks=60)
            if p:
                jobs.append((r["id"], p, {"hw": 60}))
        if not jobs:
            print("nothing to grade (all done)"); return
        print(f"batching {len(jobs)} remaining grades at ~50% cost")
        _run_batch(client, jobs, GRADES, {})
    elif mode == "trunc_batch":
        sub = df.sample(n=min(trunc_n, len(df)), random_state=20260730)
        done = _done_ids(GRADES_TR)
        jobs = []
        for _, r in sub.iterrows():
            if r["id"] in done:
                continue
            p = render_blind(r["ticker"], r["entry_date"], hist_weeks=90)
            if p:
                jobs.append((r["id"], p, {"hw": 90}))
        if not jobs:
            print("nothing to grade (all done)"); return
        print(f"batching {len(jobs)} truncation probes at ~50% cost")
        _run_batch(client, jobs, GRADES_TR, {})
    elif mode == "self":
        # Self-contained: grade a seeded 10% subsample TWICE (two independent calls), both passes
        # into GRADES_SC. Runs BEFORE --grade, so it does not depend on GRADES existing. Resumable.
        sub = df.sample(frac=SEED_FRACTION_SC, random_state=20260730)
        have = _done_ids(GRADES_SC)   # ids already double-graded (either pass counted below)
        counts = {}
        if GRADES_SC.exists():
            for l in GRADES_SC.read_text().splitlines():
                if l.strip():
                    j = json.loads(l); counts[j["id"]] = counts.get(j["id"], 0) + 1
        with GRADES_SC.open("a") as fh:
            for _, r in sub.iterrows():
                need = 2 - counts.get(r["id"], 0)
                if need <= 0:
                    continue
                p = render_blind(r["ticker"], r["entry_date"], hist_weeks=60)
                for pas in range(counts.get(r["id"], 0) + 1, 3):
                    g = _grade_image(client, p)
                    fh.write(json.dumps({"id": r["id"], "hw": 60, "pass": pas, **g}) + "\n"); fh.flush()
        print(f"self-consistency: {len(sub)} ids x2 passes -> {GRADES_SC}")
    elif mode == "trunc":
        sub = df.sample(n=min(trunc_n, len(df)), random_state=20260730)
        with GRADES_TR.open("a") as fh:
            for _, r in sub.iterrows():
                p = render_blind(r["ticker"], r["entry_date"], hist_weeks=90)
                g = _grade_image(client, p)
                fh.write(json.dumps({"id": r["id"], "hw": 90, **g}) + "\n"); fh.flush()
        print(f"truncation-probe ({len(sub)}) -> {GRADES_TR}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--render-only", action="store_true")
    ap.add_argument("--grade", action="store_true")
    ap.add_argument("--grade-batch", action="store_true")
    ap.add_argument("--self-consistency", action="store_true")
    ap.add_argument("--truncation", type=int, default=0)
    ap.add_argument("--truncation-batch", type=int, default=0)
    a = ap.parse_args()
    if a.render_only:
        run("render")
    elif a.grade:
        run("grade")
    elif a.grade_batch:
        run("grade_batch")
    elif a.self_consistency:
        run("self")
    elif a.truncation:
        run("trunc", a.truncation)
    elif a.truncation_batch:
        run("trunc_batch", a.truncation_batch)
    else:
        print("pick a mode: --render-only | --grade | --self-consistency | --truncation N")
