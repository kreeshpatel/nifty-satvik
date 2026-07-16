# Stage 3 — exit co-optimization per setup family (measurement, no trial)

**Run 2026-07-16.** Per-family exit characterization on the corrected substrate. Pure measurement.

## Exit capture / giveback by family (realized R vs peak MFE-in-R)

| setup | N | meanR | mfe_R | capture | giveback |
|---|---|---|---|---|---|
| touch44 (live) | 1720 | 0.33 | 2.81 | **12%** | **2.48R** |
| trend_pullback | 1167 | 0.34 | 3.17 | 11% | 2.83R |
| sr_pivot | 57 | 0.56 | 2.74 | 20% | 2.18R |
| box | 543 | 0.62 | 2.03 | 31% | 1.41R |
| ascending_base | 106 | 0.63 | 1.95 | 32% | 1.33R |
| cup_handle | 195 | 0.70 | 2.26 | 31% | 1.56R |
| double_bottom | 502 | 0.60 | 1.77 | 34% | 1.18R |

touch44 exit-reason mix: 52.8% stop, 22.4% blowoff_half, 15.9% trail, rest time/wk20/eos.

## Findings

1. **The touch book has poor exit capture (12%) / large giveback (2.48R)** — it reaches ~2.8R peak MFE
   but realizes 0.33R. 67% of touch trades that hit 2R MFE give back ≥1.5R.
2. **This is STRUCTURAL, not a fixable leak.** A 44SMA-pullback entry catches spikes that revert;
   breakout families (box/cup/double_bottom) enter closer to a clean trend and capture 2-3× better
   (31-34%). The giveback is the price of the pullback entry's fat-tail runners — finding 0099 already
   established that capturing more MFE (e.g. `tp_on_high`) TRUNCATES those runners (per-trade≠portfolio).
3. **No new exit lever for the live book.** The live touch book (box OFF) is unchanged by the Stage-4
   stop-fix, so there is NO new data; testing lock-in / tighter-trail exits on it would relitigate
   0084/0085/0099 without a new {data, feature, sub-period, formulation}. Forbidden by the discipline.
4. **The per-family exit difference is real but MOOT** — the zoo families exit better, but Stage 4
   (corrected) showed they don't survive the capital cap even as sleeves. A better exit on families we
   can't profitably trade changes nothing.

## Per-family exit co-optimization (correct entry->exit->sizing order; `scripts/diag_family_exits.py`)

Tested 3 principled exit archetypes per family (P2 book+blowoff / let-run-no-blowoff / tight-capture-
lockin) on the 2022-26 slice, then re-sized with per-family exits. (3x5 = multiple testing; exploratory.)

**Each family's preferred exit (by 2022-26 slice):**
- **touch44 → P2** (1.29 vs let-run 0.77): confirms the touch wants book-half+blowoff; letting it run
  gives back its spikes (DD −34.8→−45%). Its current live exit is right.
- **box → LET-RUN** (1.08 vs P2 1.00; Sharpe 0.91→**1.04**, CAGR 17.8→**21.0%**): **box WAS handicapped
  by the touch exit** — it genuinely wants to run. Owner's methodological point validated.
- cup_handle → tight-capture (noisy, worse overall); ascending → P2 (weak family); double_bottom → P2.

**Re-sizing with per-family exits does NOT change the verdict:**
| config | Sharpe | CAGR | DD | Calmar | 22-26 |
|---|---|---|---|---|---|
| A live touch (P2) | 1.03 | 21.2% | −34.8% | 0.61 | **1.29** |
| D sleeve uniform P2 | 1.07 | 18.6% | −33.9% | 0.55 | 1.19 |
| D* sleeve per-family exits | 1.04 | 18.2% | −34.5% | 0.53 | 1.22 |

Per-family exits (D*) do not beat the uniform sleeve (D), and neither beats the live touch book. Even
correctly-exited, the zoo families are too correlated to touch to lift the combined book.

## Verdict (Stage 3 complete, correct order)

**The exit space is closed for the live touch book** (P2 is right, confirmed). The one real micro-win:
**box + let-run exit** is the strongest zoo family standalone (Sharpe 1.04 / CAGR 21% / 22-26 1.08) — and
box IS the "continuous uptrend, never touches SMA -> consolidation breakout" case. It's a legitimate
ADD candidate (coverage + modest return), routed to the forward wall, but it does not lift the capped
portfolio when combined with the correlated touch book. Fixing the exit-order handicap changed a
single-family number, not the bottom line.
