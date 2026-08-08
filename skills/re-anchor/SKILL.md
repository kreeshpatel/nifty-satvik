---
name: re-anchor
description: >
  Migrate the pinned baseline of record to a new dataset or corrected universe, with hash
  verification and citation migration. A governance-class procedure — re-anchoring changes what
  every past finding was measured against.
argument-hint: "[reason for the re-anchor]"
disable-model-invocation: true
allowed-tools: Read Write Edit Glob Grep Bash
---

# /re-anchor — move the number everything else is measured against

This is not a config change. Every finding, every KILL, every ΔSharpe in the registry was measured
against the current anchor. Move it and they all silently mean something slightly different — the
registry still reads the same, and it is no longer true. That is why this is a quarterly-review-class
decision with the owner in the loop, not a task.

**The live case:** the pinned `data/ohlcv.pkl` (sha `f8625a8f…`) is survivor-only — 103 of 813 PIT
members missing. The backfill landed 2026-07-03 and recovered 103/103 into
`data/ohlcv_backfill.pkl`. Finding 0025 measured the bias and found it scales with holding period
(−0.04 Sharpe on tight-stop configs, −0.18 on wide-stop swing). The 63-day-hold `baseline_v1` 0.667
is exposed in the same direction; its corrected re-run is unblocked and **pending an owner decision**.

---

## Before anything: confirm this is authorised

Re-anchoring on your own initiative is out of scope. Confirm the owner has decided, and record where
that decision is written. If it is not written down, the first deliverable is the decision memo, not
the re-run.

## Step 1 — mint and verify the new pin

1. Build the new dataset. Record `sha256` of the exact pickle bytes and the byte length.
2. Publish as a GitHub release asset with a dated tag (`dataset-pin-YYYYMMDD`); the blob is too
   large for git, which is why it is identified by hash rather than by path.
3. **Verify the hash from the release, not from the local build.** The reason the pin exists is that
   an unpinned run drifts 1–2pp CAGR run-to-run on yfinance revisions. A pin you have not checked
   after download is not a pin.
4. Add a `tests/test_stagea_dataset_pin.py`-style assertion for the new hash.

## Step 2 — reproduce the old anchor on the new pin

Before producing the new headline, re-run the **existing** anchor against the new data and record
the delta. This is the measurement that tells you what changed:

- Selection, trade count, win rate, and the golden master all matching ⇒ the delta is data, not
  engine. That is exactly how the `baseline_v0` → `baseline_v1` gap was diagnosed as price vintage
  rather than a code change.
- If the golden master moves, **stop.** The engine changed and the re-anchor is now entangled with
  an engine change. Separate them; land the engine change on its own merits first.

## Step 3 — write the new anchor

New `research/baseline_vN.json`, modelled on `baseline_v1.json`, carrying:
gross metrics · robustness block (bootstrap CI, n_eff, PSR, MinTRL, DSR **at the cumulative trial
count**) · universe block · full provenance (run id, command, engine-equivalence test, fundamentals
vintage, frozen cfg) · pin block (sha256, release tag, asset size, reproduce command) · and a
`delta_vs_previous` block that *explains* the change rather than only reporting it.

The old anchor file stays. It is not superseded, it is dated.

## Step 4 — migrate the citations, which is the part that gets skipped

Every place the old anchor is quoted has to be updated or explicitly marked as measured against the
old pin:

- `CLAUDE.md` · `docs/references/plausibility_anchors.md` · `research/overlay_registry.md`
- `skills/program-laws`, `skills/backtest-rigor`, and any skill quoting the baseline numbers
- `forward/prereg.md` and the paper-gate thresholds

Grep for the old Sharpe, CAGR, drawdown, and the sha prefix. **A registry row measured against the
old anchor that is not marked as such is now a false statement**, and it will be cited as current.
Marking is acceptable; silence is not.

## Step 5 — the guard, and the test

`research/baseline_v1.json` is write-protected by `scripts/guard_protected_paths.py`. Add the new
anchor to `FROZEN` in that file. Add or extend a test asserting the recited anchor values match the
anchor JSON — the same pattern as `tests/test_standing_counts.py`, for the same reason: a number
that appears in prose and in a ledger will eventually disagree, and the ledger has to win.

## Step 6 — record it as governance

An entry in `research/config_CHANGELOG.md` and a decision record under `docs/decisions/`: what
changed, why, who decided, what it invalidates, and what re-runs are now owed. The last item is the
one future sessions need — a re-anchor leaves a queue of stale comparisons behind it, and if that
queue is not written down it is never worked.
