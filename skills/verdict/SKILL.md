---
name: verdict
description: >
  Adjudicate a completed run against its pre-committed thresholds and write the record — finding,
  registry row, counts. Reads the pre-registration first and compares it to what actually ran, so a
  moved threshold cannot pass unnoticed.
argument-hint: "[NNNN or study slug]"
disable-model-invocation: true
allowed-tools: Read Write Edit Glob Grep Bash
---

# /verdict — score the run against what was promised, not against what you hoped

By the time you invoke this, the verdict has already been decided — it was decided in the
pre-registration. Your job is to read it out honestly, and to notice if anything moved.

---

## Step 1 — diff the pre-reg against the run

Open the pre-registration and the run's config side by side. Compare **parameter by parameter**:
universe, screens, signal, selection, buffer, weights, costs, window, and every threshold in the
outcome table.

Any difference is the headline. A threshold that moved after the numbers arrived invalidates the
trial regardless of the result — report that and stop. Do not adjudicate a trial whose bar changed.

## Step 2 — check the gate arithmetic before the gate verdict

- Sub-period gates are a **continuous slice of one full run**. Verify the code path slices
  (`nq.runner.research.evaluate_overlay`). A fresh-capital re-run reseeds the equity peak and
  manufactures a pass — this produced false KILLs here, including 0071.
- DSR uses the **cumulative** count from `diagnostics/research/n_trials.json`, not a per-run value.
- Gross against gross, net against net. Delivery STT is per leg, buy and sell.
- Run `/plausibility-check` on every headline number. A result better than its anchor is guilty
  until explained.

## Step 3 — fill the outcome table

Reproduce the pre-committed table with the actual values in it, bar by bar, each marked pass or
fail. Not a narrative — the table.

Then the verdict, which the table determines:

- **PROMOTE** — every bar cleared. Route to the forward wall (`forward/prereg.md`); certification
  happens there, not here.
- **UNDERPOWERED** — the effect is inside the resolution band (n_eff ≈ 37 windows ⇒ dSharpe
  half-width ~0.59). Record the bound. Adopt nothing. This is a real, reportable result.
- **KILL** — any bar failed. Registry row, root cause, move on.

**Do not retune.** Not one parameter, not "just to see". A retuned pass is not a pass, and the
retune is not recoverable once it has happened.

## Step 4 — write the record

1. **Finding** — `research/findings/NNNN-*.md` (or `result.md` in the study folder). Required: the
   outcome table, the verdict, the **root-cause readout** (*why* it did what it did — mechanism, not
   restatement), and the next setup. A finding without a root cause teaches nothing and the next
   session pays for it again.
2. **Registry row** — `research/overlay_registry.md`, in the existing column shape: id, date,
   description, hypothesis, result with numbers, verdict with the trial count, links, root cause.
3. **Counts** — confirm `n_trials.json` was incremented *before* the run. If it was not, say so in
   the finding and in the increment log. Record the breach; do not quietly fix it.
4. **Transferability** — state which book this verdict binds. Most verdicts here were measured on a
   book that is not the live one, and a verdict cited without its transferability row is a verdict
   applied to the wrong strategy.

## Step 5 — before you believe your own write-up

Spend `red-team` on it — fresh context, no memory of why you expected this. If the result is
favourable, spend `overfit-skeptic` as well. A confirmation that lists nothing it attacked is not a
confirmation.

---

Close with the standing counts read from the ledgers: **screens N · sealed opens N · n_trials N**.
Read them; do not carry them from earlier in the session.
