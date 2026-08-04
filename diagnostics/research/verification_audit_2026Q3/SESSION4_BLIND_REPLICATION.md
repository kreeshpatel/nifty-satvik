# Session 4 — blind adversarial replication: intake

**Filed 2026-07-31 by the closeout session. Verification class; counts frozen 14 / 1 / 138.**

## Provenance — read this first

**This is an intake record, not a verification.** The blind session ran separately, under a prompt
the owner holds, with only pinned data and the claim. **Its report is not in this repo** — there is
no artifact under `diagnostics/research/` and nothing on `main` carries its output.

The findings below are **filed from the owner's summary**, not from a report this audit read or
re-derived. They are recorded so October has them; they are **not independently confirmed here**,
and each carries an action rather than a verdict.

**If the raw report is added to the repo, this file should be replaced by it.**

## Findings as reported

### F1 — `gate_quantile` is INERT

The parameter has no effect on the anchor over the range tested. A knob that does nothing is not
neutral: it invites future sessions to "tune" it and read noise as signal.

**Action: constitution row + owner door.** No code change. Record it as a known-inert parameter so a
future sweep does not spend a trial rediscovering it.

### F2 — `risk_per_trade` is INERT, then CHAOTIC (cash-scramble)

Inert across a wide band, then chaotic beyond it — the mechanism being **cash-scramble reordering**:
past a threshold, position sizes change which signals the cash gate can fund, and the book reshuffles
non-monotonically.

This is the **same mechanism** as three standing results: `max_positions` knife-edge overfit (Phase-3,
0.24-Sharpe swings per one-position change), 0109's disaster-floor (17 exits reshuffled the whole cash
path), and 0112's selector (a real per-trade lift lost at the fill margin). **A fourth sighting of
composition noise.**

**Action: constitution row + owner door.** No code change. The row should name the mechanism, not
just the parameter, so it generalises.

### F3 — published decimals are OVER-PRECISE under risk-based sizing

Anchors are quoted to more decimals than the sizing convention can support: risk-based sizing moves
the figure in a digit the publication treats as fixed.

**Action: `precision` field in the anchor manifest** (`ANCHOR_MANIFEST.md` §7) + owner door on how
many decimals the binder should print.

### F4 — the period label is wrong: **8.43 years, not "2017–2026"**

The engine needs a 44-week SMA warm-up, so **the first tradeable date is 2018-01-19**. Every
"2017-2026" label implies a tradeable 2017 that does not exist.

**Action: binder correction, everywhere.** Now a required manifest field
(`ANCHOR_MANIFEST.md` §6: `first_tradeable_date`, `span_years`).

## Binder corrections required (October)

1. **Replace every "2017–2026" span label** with the true tradeable period — **2018-01-19 onward,
   8.43 years.** This affects the anchors, the corrected-anchor table and the swing record.
2. **Place the standalone-CI sentence adjacent to the pair-alpha sentence**, so October reads both
   together rather than the headline alone. Specifically, the alpha decomposition's
   **pair α +10.03%/yr, 95% CI [+3.34, +16.72], β 0.751** must sit beside the individual sleeves'
   CIs — **low-vol's is [+0.06, +12.21], which barely excludes zero.** Reading the pair's alpha
   without the sleeve CIs overstates how well-established the components are.

## Constitution rows to add (no code changes)

| id | subject | content | door |
|---|---|---|---|
| — | `gate_quantile` | inert over the tested range; do not tune | owner |
| — | `risk_per_trade` | inert then chaotic; mechanism = cash-scramble reordering; 4th sighting of composition noise | owner |
| — | published precision | decimals exceed what risk-based sizing supports | owner |

**All three are records, not changes.** The audit made no code change on their account.
