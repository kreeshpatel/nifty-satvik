# Forward signal inspection log

A weekly, human-readable companion to the machine table (`results/signal_quality_forward.csv`, built by
`scripts/collect_signal_quality_forward.py`). One short entry per inspected signal: what the four frozen
quality axes said **at signal time**, reproduced from data, and — later — how it actually resolved.

**Purpose and discipline.** This is the narrative half of the forward wall registered in
[`forward/prereg_signal_quality.md`](../forward/prereg_signal_quality.md) — the 4-axis family
(body_ratio · touch_depth · signal_conviction · crs_rank), owner-frozen 2026-08-17. It is **evidence,
not authorization**: we accumulate instances for a quarter, then judge the family OUT-OF-SAMPLE with the
multiplicity correction (`adjudicate_family`). No entry here changes the strategy; a surviving axis
justifies a *separate, pre-registered* gate trial. `n_trials` is untouched (measurement). Outcomes are
filled in as trades close — never back-edited.

Axes at a glance (hypothesis = higher forward R when…): **body_ratio** ≥0.50 solid > <0.50 doji ·
**touch_depth** <5% deep > 5–10% shallow (min ext over the pullback, *not* signal-week ext) ·
**signal_conviction** normal > low · **crs_rank** stronger RS > weaker.

---

## 2026-08 — seed inspections (pre-inception; reported separately per prereg §2)

### #1 · CCL (CCL Products) — flagged 2026-08-14, grade A, **conviction LOW**
Reproduced independently (fresh bars → live `build_weekly_panel`): body_ratio **0.16 exact**, stop 1116.2
exact, 2R target 1172.6 exact.

- **Met the mechanical gate?** Yes — rising 44w SMA (+8.26%/13w), pullback toward the line, green entry
  week, within the 20% ext cap, passed CRS.
- **Quality read (all four axes weak):** body **0.16** (near-doji, not the "solid green" the pullback
  wants) · touch **shallow** — ext only fell to 8.6%, never reached the <5% zone · conviction **low** ·
  crs **0.0774** — the *weakest* of the week's five fresh signals. R just **1.66%** (stop inside the
  weekly noise). Fires on the first micro-green week after four red weeks — a possible dead-cat pause.
- **Threads:** `preregistry_small_candle` (body<0.50), `deep-near-sma-touch-edge` (5–10% band ≈ +0.094R).
- **Outcome:** _ACTIVE — pending._

### #2 · PTCIL (PTC Industries) — bought 2026-08-07, grade A, conviction normal
Reproduced: sma44 17352 exact, body_ratio **0.80 exact**, stop 17776 exact.

- **Met the mechanical gate?** Yes — same six criteria.
- **Quality read (a genuinely strong instance):** body **0.80** (solid green, closed near the high) ·
  touch **deep** — pulled to **2.5% ext** and based four weeks before firing (the strong zone; the 9.94%
  signal-week ext is post-bounce) · conviction **normal** · crs **0.099** mid-pack · R **5.9%** (healthy,
  2R target ≈ +12%). The one tradeoff: entry sits above the +7.3% bounce week — buying confirmation, not
  the low.
- **Contrast with CCL:** identical grade A, opposite on every quality axis — and the engine's flags
  separated them correctly (normal vs low). This pair is the whole reason the wall is worth running.
- **Outcome:** _ACTIVE, marked ≈ +5.4% at 2026-08-17 (book figure; independent cross-check pending the
  post-08-14 bars)._

---

*Next weeks: append each new FRESH signal (all grades). The machine table carries every signal; this log
keeps the few worth a sentence, plus the resolution of the open ones above.*
