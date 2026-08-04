# The Anchor Manifest — what a published anchor must state to be reproducible

**Created 2026-07-31 by the 2026Q3 verification audit (drill gap G4).**
**Verification class. Counts frozen: screens 14 · sealed opens 1 · n_trials 138.**

## Why this exists

The audit found the same defect twice, in the two most-cited numbers in the programme:

| # | number | defect | remedy |
|---|---|---|---|
| **D1** | 0115 two-sleeve blend `1.22 / −33%` | no producer script; the ERC **vol lookback was never named** | remedied session 3 — `scripts/build_two_sleeve_blend.py`, lookback recovered as 126d |
| **D2 / G4** | `baseline_v1` `0.667 / 15.46 / −46.26` | **no producer script**; only consumers of `baseline_v1.json` | this manifest + the designation below |

Both were *unverifiable*, not wrong. The pattern is identical: a headline is published, the script
that made it is not committed, and the parameters it depended on live only in the author's session.
**A number without a producer is a claim, not a measurement.**

**The standard: an anchor is not "published" until its manifest is complete.** Every field below must
be stated in the anchor's own JSON, not inferred from a plan document or reconstructed by a reader.

---

## The required fields

### 1. `producer` — the committed script that regenerates the anchor
Path, and the exact invocation. If regenerating requires arguments, they belong here.

### 2. `costs` — **values**, not a reference
Read from `config.py` at the time of writing (2026-07-31), and stated numerically so a future
change to `config.py` is visible as a divergence rather than silently re-writing history:

| item | value | source |
|---|---|---|
| brokerage per leg | **0.0003** (3 bps) | `config.BROKERAGE_PCT` |
| STT per leg | **0.001** (10 bps) | `config.STT_PCT` |
| slippage — LARGE_CAP | **0.0005** (5 bps) | `config.SLIPPAGE` |
| slippage — MID_CAP | **0.0022** (22 bps) | `config.SLIPPAGE` |
| slippage — SMALL_CAP | **0.0040** (40 bps) | `config.SLIPPAGE` |
| impact coefficient | **1.0** | `config.IMPACT_ETA` |
| impact form | Almgren √ term above ~0.5% of ADV | `config` comment |
| ADV tier — large | **≥ ₹50 cr** | `config.ADV_LARGE_CAP_RS` |
| ADV tier — mid floor | **≥ ₹5 cr** | `config.ADV_MID_CAP_RS` |
| max ADV participation | **5%** | `config.MAX_ADV_PARTICIPATION` |

**Not modelled, quantified by the audit (session 1, item A8):** exchange txn, SEBI, stamp, GST, DP
— together **≈ 4.8 bps round-trip**, materially smaller than the slippage term that *is* charged.
An anchor's manifest must say whether these are in or out. **They are OUT of every current anchor.**

### 3. `fill_convention`
Which bar, which price, and what happens on a gap. (Swing record: next-Monday first daily open
inside `[siglow, sighigh]`; buy-stop variants state their trigger and order lifetime.)

### 4. `sizing_convention`
Risk per fill, capital base, slot cap, and the fill-ordering rule. **Sizing is not cosmetic** — the
blind-replication session found `risk_per_trade` inert over a wide band and then chaotic
(cash-scramble reordering), so an anchor that omits it is not reproducible in principle.

### 5. `universe_filter_inputs` — **release-pinned**
Every dataset the filter reads, with its release tag and sha256. This is where **drill gap G3**
(`fundamentals_pit_depth.pkl` in neither git nor any release) closes: **solvency/value-quality
inputs must be release-attached, not assumed present.**

### 6. `true_period` — first *tradeable* date, not the data start
**This is the correction the blind-replication session forced.** Every "2017–2026" label in the
programme implies a tradeable 2017. It is not: the engine needs a 44-week SMA warm-up, so the
**first tradeable date is 2018-01-19** and the true span is **8.43 years**, not ~9.5.

**Any anchor labelled "2017-2026" is mis-stated.** The manifest must carry `first_tradeable_date`
and `span_years` explicitly.

### 7. `precision`
Published decimals must not exceed what the sizing convention supports. The blind session found the
anchors' decimals **over-precise** under risk-based sizing — a number quoted to three decimals whose
sizing rule moves it in the second is false precision. **State the meaningful precision.**

---

## Application to the three anchors

| anchor | producer | manifest status |
|---|---|---|
| **`baseline_v1`** (0.667 / 15.46 / −46.26) | **TO BE DESIGNATED** — the blind-replication session validated a reproduction; that script's path must be written into `baseline_v1.json` as `producer` | **INCOMPLETE — blocked on the session-4 script path** |
| **corrected anchor** (`run_corrected_anchor.py`) | ✅ `scripts/run_corrected_anchor.py` — verified in the clean-clone drill | **needs `true_period` + `precision`** |
| **swing record** (1.132 / 255) | ✅ `scripts/run_bhanushali_weekly_rank.py` — reproduced exactly in the clean-clone drill | **needs `true_period` + `precision`** |
| **two-sleeve blend** (1.237 reproducible) | ✅ `scripts/build_two_sleeve_blend.py` | ✅ complete (session 3) |

### The one thing this audit could not close

**`baseline_v1`'s `producer` field cannot be filled from this session.** The blind-replication
session validated a reproduction, but **its report is not in the repo** — no artifact under
`diagnostics/research/`, and nothing on `main` names a baseline producer. The manifest standard is
written and the other fields are determinable, but the designation itself needs the session-4
script path.

**Owner action:** supply the validated script's path (or commit the script), and
`baseline_v1.json` gets its `producer` field plus a regeneration from it. **Until then D2 stays
open** — the anchors are corroborated by an independent session but still not reproducible from the
repo alone, which is the standard the drill applied to everything else.
