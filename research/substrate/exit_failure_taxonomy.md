# EXIT failure taxonomy — touch+box book (160-trade AI-vision exit search)

## 1. Headline: the dominant error is too-LATE (giveback), not too-early

Verdicts split evenly (`too_late 25 == too_early 25`, `about_right 110`), but the
**issue** layer is lopsided: `gave_back_from_peak 56` vs `sold_before_bigger_run 25`
— **~2.2× more giveback than cut-runner**. So the modal defect is holding *past* the peak,
not selling before it.

**Reconcile with the two known facts:**
- The book keeps only **~12% of peak MFE** → structural giveback is real and expected; the
  56-count is that structure showing through, trade by trade.
- Finding **0099**: capturing more MFE **truncates the runners** (per-trade ≠ portfolio).
  Crucially, `exited_into_collapse_good = 48` — nearly as many exits *correctly* dumped
  ahead of a collapse. Much of the "giveback" is the **price paid** for the fat right tail:
  the same loose exit that bleeds 88% of an average peak is what lets the handful of
  +100% blow-off runners run. **Giveback is dominant but only partly a defect.**

## 2. Ranked failure modes (deep-flaw pass, 45 flagged)

| Mode | Count | Direction | Mechanically avoidable? |
|---|---|---|---|
| `no_flaw_unavoidable` (nominal) | 25 | — | n/a — **but ~18 are FILE-NOT-FOUND/path-mismatch placeholders, not real verdicts**; genuine near-optimal exits ≈7 |
| `held_through_blowoff_giveback` | 10 | too-late | Yes — arm a peak-trail once >1.5–2R |
| `trail_too_tight_cut_runner` | 6 | too-early | Partly — single-bar blow-off trigger fires mid-trend |
| `stop_too_tight_whipsaw` | 4 | too-early | Partly — sub-ATR stop, no close-confirmation |

Among **genuine** flaws: giveback (10) ≈ cut-runner+whipsaw (10). The verdict-level tie is
real; giveback only dominates at the softer issue layer.

## 3. Candidate PIT-safe exit rules → forward wall

Each trims givebacks **and** clips some runners — net effect is unknowable in-sample.

1. **Blow-off-aware peak trail**: once a weekly bar closes >2.5×ATR above the 44w SMA,
   tighten to ~15% below the running peak. Trades giveback-capture for occasional early
   exit on names that keep extending (the 6 cut-runner cases).
2. **Close-confirmed ATR-floored stop**: `max(fixed%, 1.5× weekly ATR)`, trigger only on a
   weekly *close* beyond the level. Kills the 4 whipsaws; risks a wider realized loss on
   genuine breakdowns.
3. **44w-SMA trend-exit replacing the time-cap**: hold while weekly close > rising 44w SMA.
   Frees runners the calendar cut short; adds giveback on names that roll over slowly.

**⚠ Reuse guard:** lock-in / chandelier / generic trail variants were already tested
**UNDERPOWERED** (0084 / 0085 / 0099). Any reuse must declare a *new lever* (blow-off
ATR-extension gate and close-confirmation are the candidates) and be judged **forward on
the wall, not re-run in-sample**.

## 4. Caveats

- **Outcome-aware judging**: the vision saw +12wk-after, so verdicts embed hindsight the
  live rule cannot use — treat "too-late/too-early" as directional, not sizing.
- **Touch+box only**: does not transfer to the momentum sleeve or other entries.
- **+12wk window truncates very long runners**: multi-quarter trends look "topped" inside
  the frame, biasing toward *over*-counting giveback and *under*-crediting held runners.
