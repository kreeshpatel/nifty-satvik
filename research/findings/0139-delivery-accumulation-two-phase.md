# 0139 — Delivery accumulation is a real universe alpha, and the wrong phase for the momentum book

**Class: MEASUREMENT.** No promote/kill decision, no screen-ledger row, no trial spent.
**Standing counts: screens 19 · sealed opens 1 · n_trials 2.**
Reproduce: `python pipelines/diagnostics/diag_delivery_accumulation.py --chart research/findings/assets/0139_accumulation_two_phase.png`

## 1. Why this was asked, and the narrow

Owner proposal: detect a delivery-based **accumulation period** per stock and time entries to it, in
combination with the Bhanushali weekly-swing book. Delivery data is not a green field — `0118`
screened it (`dlv_med21` conditional **dR +0.363 [+0.13,+0.58]**, 5/6 yrs, ADV-robust) and `0119`
activation-bounded it as a funding-queue tiebreak at **−1.29 R/yr**: real population information,
priced out at the book's margin (Law II). Every prior delivery/event test used delivery
**cross-sectionally, static at the fixed entry**. The one untested element — named per the
cite-and-narrow rule as a **new formulation** — is the **temporal within-name accumulation-window**
version: does *when* a name is accumulating carry timing information the cross-sectional tests never
asked about? This measurement answers that, and *why*, without spending a trial.

## 2. What was measured

A composite weekly accumulation score `A`, the owner's four facets each as one trailing-only,
per-stock z-component (delivery % = deliv_qty/traded_qty):
- `A_level` elevated vs own 52w norm · `A_trend` rising 8w slope · `A_surge` delivery-qty z minus
  volume z (ADV-residual) · `A_div` on-balance-delivery slope minus price slope (basing).
- **Equal-weight composite, no fitted weights** (Law VIII / 0133 — fitting weights manufactures a
  specification lottery). All inputs trailing-only; delivery is EOD-available and PIT-proven
  (`tests/test_delivery_pit.py`). 677 tradeable names, 228,892 stock-weeks, 2019–2026.

## 3. Result

**[1] The universe signal is real and robust.** Weekly `A` is persistent (AR(1) ρ=+0.807,
half-life **3.2 weeks** — accumulation is a *state*, not daily noise). Cross-sectional IC vs forward
return: **+0.0218 (1w, t=+6.23)**, +0.0196 (4w), +0.0188 (13w); positive in **all 8 years**
(2019–2026). This is genuine cross-sectional alpha, consistent with 0118.

**[2] It collapses on the Bhanushali book.** On the 3,457 actual entries (2019+): raw
corr(A, trade-R) = **−0.027**; corr(A, extension) = −0.173. Controlling for what the strategy already
sees, `OLS R ~ ext + CRS + A` gives A a coefficient of **−0.080, t=−1.16** — nothing detectable,
if anything slightly negative. Matched high-A vs low-A **within** ext×CRS cells: pooled gap
**−0.05 R**, positive in only 3 of 9 cells (all tiny). Matched on extension, so it is *not* a
re-discovery of extension.

**[3] The mechanism — phase mismatch.** As `A` rises across trade terciles: extension falls
(27.7 → 20.3), follow-through **MFE falls (+32.5% → +23.0%)**, hold shortens (17 → 10 wk), and
**stop-outs rise (39% → 47%)**. Accumulating names are *basing*; the momentum book's R comes from
riding *already-extended, following-through* names. The two want opposite phases of the same stock.

**[4] The flip-side confirms it, and finds where the edge lives.** Accumulation-*onset* forward
returns beat a same-week, **extension-matched random null** at every horizon, and the edge **grows**
(+0.23pp @1w → +1.16pp @26w) — a real *timing* edge, not just cross-sectional ranking. Split by
phase: accumulation **in a base** (below the 44w line) pays **+8.31% @13w** vs **+6.26%** when
already extended — **Welch t=+2.56, p=0.010**. The payoff is **pre-breakout**.

Chart: `research/findings/assets/0139_accumulation_two_phase.png`.

## 4. Root-cause readout

> Delivery accumulation is a genuine broad-universe alpha (IC t=6, every year) and it evaporates on
> the Bhanushali book because **Bhanushali only enters names that have already broken out**
> (post-44SMA-touch, top-CRS), while accumulation is the *pre-breakout basing* phase. By the time
> the touch signal fires, the accumulation is spent or the name reverses — less extension, less
> follow-through, more stops. This is the population→book collapse (Law II), now with the specific
> mechanism attached: **not "delivery is weak", but "delivery marks the phase the momentum book
> skips."**

## 5. What this means

The signal's natural consumer is a book that enters **during** accumulation — a **pre-breakout /
base-buying sleeve, or the broad breadth-50 cross-section** (the campaign capstone's named consumer
for banked population edges) — **never** a timing overlay on the concentrated momentum book. This is
input to **Oct-1 §4 (breadth-50)**, not a new overlay on the live book. The magnitude is modest
(edge ~0.85–1.16pp over the null at 13–26w; base-vs-extended +2pp @13w), so whether it survives
transaction costs and the ±10 R/yr composition-noise floor **on a real capitalized book** is a
separate, gated question — not answered here.

## 6. What was deliberately NOT done

This is a **measurement**, and the accounting stays clean: no `n_trials` spent (still 2), **no
screen-ledger row** (no pre-committed adopt/kill bar was run on the honest base — these are IC,
partial-correlation, event-study and forensic characterizations), and **no activation bound** on the
current book (Gate 3 remains unrun; the −1.16 t and −0.05R matched gap strongly predict it would
come back below the floor, as 0119 did, but that prediction is not a verdict). Any promotable use
requires the full verdict-machine gate under the current harness, with a fresh owner sign-off per the
0118 delivery re-open clause.

## 7. Do not re-test unless

- Re-running delivery **cross-sectionally on the current book** (rank/filter/tiebreak/size) is
  refused relitigation — that is 0118/0119, priced out, and the mechanism here (phase mismatch)
  explains why. Do not re-open without a fresh owner sign-off and a mechanism that beats it.
- The **pre-breakout** direction (§3–4) is open, but only as a **different book shape**: a
  base-buying / breadth-50 / longer-horizon consumer that enters *during* accumulation. That belongs
  to the Oct-1 §4 agenda and, if pursued, to the full gate (coverage/PIT → screen → activation bound
  → pre-registered trial), never as an overlay on the touch funnel.

## 8. Reproduction

`pipelines/diagnostics/diag_delivery_accumulation.py` — sections [1] universe IC/persistence,
[2] book partial-correlation, [3] matched-cell mechanism, [4] pre-breakout flip-side + null; emits
the two-phase chart with `--chart`. Delivery layer `nq/data/delivery.py` (PIT: `tests/test_delivery_pit.py`);
substrate `research/substrate/trades.parquet`; delivery raw `data/_delivery_raw.parquet`
(2019–2026-07, harvested by `scripts/harvest_delivery.py`).
