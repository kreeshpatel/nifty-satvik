# 0128 — PEAD Gate-1: does post-earnings drift exist on OUR universe, 2019+?

**Status:** PRE-REGISTERED — committed before any drift statistic is computed.
**Class:** **MEASUREMENT.** No trial. No screen-ledger row (see §0.3). Sealed set and judge log
untouched. No engine change.
**Standing counts: screens 14 · sealed opens 1 · n_trials 138** — unchanged at registration and at close.

**Date:** 2026-07-31. **Owner:** Kreesh Patel.

---

## §0 IMMUTABLE — Gate 0 confrontation

### 0.1 This takes up an OPEN registry row, it does not relitigate a closed one

**`SL-002` (2026-06-28) — "NSE PEAD sleeve", verdict OPEN, "— (not yet measured)".** Its recorded
blockers, scored today:

| blocker (verbatim) | status |
|---|---|
| (a) "India earnings calendar + surprise quantification source (cannot use FMP)" | **calendar RESOLVED** — the 0120 harvest (`data/_earnings_raw.parquet`, 58,871 result events, 2,592 symbols, 2019-01→2026-07) + `nq/data/earnings.py`, truncation-tested (`tests/test_earnings_pit.py`). **Surprise quantification NOT resolved** — see §0.2. |
| (b) "PIT earnings coverage for Nifty 200+ minimum" | **measured in §2** and reported as the coverage census |
| (c) "surprise signal design + lookback stability over 2017–2026" | §1 freezes a *proxy*, and §0.2 states honestly that it is not the signal SL-002 imagined |
| (d) "PEAD window definition + transaction cost model (entry gap risk at announcement)" | Phase 2, not this gate |

### 0.2 The narrowing, stated before the run: this is a PROXY, not analyst surprise

SL-002 imagined an estimate-based surprise (actual vs consensus). **We have no estimate data and
cannot buy it.** This gate therefore uses the standard estimate-free substitute: the **market's own
reaction** to the announcement as the surprise proxy — the "abnormal announcement return" variant of
PEAD in the literature, not SUE.

**What that costs, stated plainly:** the proxy conflates *surprise* with *the market's initial
repricing of it*. A drift found here is drift **conditional on a large announcement reaction**, which
is a weaker and different claim than drift conditional on an earnings surprise. It is the claim the
data can support, and Phase 2 (if any) would inherit exactly that limitation.

### 0.3 Why this is a MEASUREMENT and not a priced screen

The screen ledger's standing rule prices *"screens against the banked context/label dataset"* —
multiplicity on a **fixed banked instrument** whose evidential value deflates with reuse. This gate
builds a **fresh population** from the earnings calendar + daily OHLCV and **never reads
`context_windows.parquet`**. It therefore takes no ledger row and the screen count stays at 14.
**If any later phase touches the banked labels, it gets priced then.**

### 0.4 What this is NOT

**Not 0120/0121.** Those asked whether the incumbent touch funnel should *avoid* known events
(screen-real at −0.383R, activation bound −15.72 R/yr → no trial). This asks whether the event is
itself a **return source** — the opposite sign of the same calendar. Different funnel, different
claim, no collision.

**Not a relitigation of anything closed.** PEAD has never been measured here.

### 0.5 The contested literature, and what our data can and cannot say

Significant 64-day drift reported 2002-2017 (Sen/SCIRP); a null reported 2014-2018 (EconStor/NSE).
**Our calendar starts 2019-01, so this study can replicate neither window.** It tests only whether
the effect is present **in 2019+ on our universe** — which is the decision-relevant question and
also, if drift is absent, a datum on the decay hypothesis. Recorded so no result here is later
reported as adjudicating either paper.

### 0.6 VRP / option-selling — REJECTED without a screen (memo line, per owner)

Short-volatility premium harvesting is **not pursued and gets no screen**, on **risk-shape grounds,
not on expected return**: selling vol concentrates exactly the tail the equity book already carries
— both are short the same crash. A sleeve whose worst quarter coincides with the base book's worst
quarter fails 0115's diversification requirement *by construction*, before any Sharpe is computed.
This is a standing rejection; re-proposing it requires a defined-risk structure (spreads, not naked)
and an explicit demonstration that its tail is not the book's tail.

---

## §1 IMMUTABLE — frozen definitions

### The event-time convention, and the PIT limitation that forces it

**The brief asked for "announcement-day, or announcement+1 if after-close, decided per event from the
two-layer PIT timestamps." That cannot be done with this data, and pretending otherwise would be the
leak.** `ann_ts` is the **intimation** timestamp — when the board meeting was *announced as
forthcoming* (median **7 days before** the event, real time-of-day). It is **not** the
results-release time. Nothing in the harvest records when the numbers actually hit the tape.

**Conservative convention, frozen:**

| element | rule |
|---|---|
| **day 0** | the first NSE trading day ≥ `event_date` |
| **surprise window** | market-adjusted **CAR(0, +1)** — days 0 and +1 inclusive |
| **entry** | the **open of day +2** |
| **drift window** | market-adjusted cumulative return, open(+2) → close(+2+H−1) |
| **horizons H** | **10, 21, 42, 63** trading days |

CAR(0,+1) captures the reaction whether the release landed intraday on day 0 or after the close;
entry at open(+2) is **strictly after the entire surprise window**, so the design is leakage-free
**regardless of release time**. Cost: we forgo whatever drift occurs on day +1. That is the price of
not knowing the release time, and it is paid deliberately.

**Leakage audit:** the only inputs are `event_date` (a calendar fact, known ≥7 days ahead via
`ann_ts`) and prices strictly after the surprise window. No estimate data, no restatement surface, no
post-hoc revision of the event table. A drift result **worse** than zero is not a leak; a
suspiciously large one is guilty until cleared.

### Other frozen parameters

| name | value |
|---|---|
| market proxy | **Nifty-50** (`CRS.NIFTY50_CSV`), the house index of record |
| abnormal return | stock daily return − index daily return (market-adjusted, no beta estimation) |
| **surprise decile** | cross-sectional decile of CAR(0,+1) **within each calendar quarter** — so deciles are comparable over time and not dominated by one quarter's volatility |
| universe | corrected universe ∩ **PIT Nifty-500 membership at `event_date`** ∩ **ADV20 ≥ ₹5cr** at day 0 |
| train years | **2019–2022** (matching the substrate's train split) — the decision basis |
| out-of-window | **2023–2026** reported descriptively, **not** the decision basis (§3) |
| minimum data | a name needs ≥ H+2 trading days after the event, else dropped (count reported) |

No parameter above is swept. One value each, chosen before any outcome was computed.

## §2 IMMUTABLE — what is reported

1. **Coverage census** — events/quarter and /year on the eligible universe, joinable fraction, thin
   years named, and the **famine check** (the Weinstein lesson: 22.5 signals/yr strained the CI).
2. **Drift by surprise decile × horizon**, market-adjusted, train years, with per-year tables.
3. **Top-minus-bottom decile spread** with bootstrap CIs at each horizon.
4. **Confound checks** (§4).
5. Standing counts.

## §3 IMMUTABLE — the pre-committed gate and both doors

**Gate-1 PASSES** only if **all** hold, on **train years**, at the horizon with the largest spread:

1. **Existence:** top-minus-bottom decile drift spread **CI excludes zero**.
2. **Sign consistency:** the spread's sign holds in a **majority of train years**.
3. **Economic magnitude:** the top-decile drift is **> 0.5%** net of a round-trip cost of ~0.26%
   (STT 0.1%×2 + brokerage 0.03%×2 + slippage) — i.e. the effect must survive being traded.
4. **No famine:** ≥ **150 top-decile events/yr** on the eligible universe.

- **FAIL → the door closes here.** Finding + registry row updating **SL-002 from OPEN to a verdict**.
  The contested-literature question is settled *for our universe and period*, cheaply, and the last
  untested premium family is closed.
- **PASS → Phase 2 may be pre-registered.** The horizon for Phase 2 is **chosen from this gate's
  strongest train-year horizon, and frozen, BEFORE any capped result is computed** — per the brief.

## §4 IMMUTABLE — named failure modes, each a KILL if it fires

1. **Momentum contamination.** A high CAR(0,+1) name may simply be a momentum name, and momentum is
   already the house signal. **Reported: drift stratified by trailing 63-day momentum tercile.** If
   the spread lives only in the high-momentum tercile, it is momentum wearing an earnings costume →
   KILL, not a discovery.
2. **Small-cap concentration.** PEAD is documented as concentrated in illiquid names. The ADV ≥ ₹5cr
   filter is the guard; **reported: drift by ADV tercile.** If it survives only in the bottom
   tercile, it is not tradable at this book's size.
3. **Decay.** The literature's dispute is precisely whether the effect died. **The per-year table is
   the instrument**, and 2023-26 is reported separately for exactly this reason.
4. **Reaction-magnitude tautology.** The proxy ranks on the announcement reaction itself. If the
   "drift" is merely continued mean-reversion or continuation of the day-0/+1 move measured with an
   overlapping window, it is an artifact. Guard: the drift window **starts at open(+2)**, sharing no
   bar with the ranking window.

## §5 Reproduce

    python scripts/diag_pead_gate1_0128.py

---

## OUTCOME (appended 2026-07-31 after the run — nothing above this line was touched)

**The drift is REAL. The gate FAILS as written, on leg 4, and leg 4's failure is a partial-year
artifact rather than the famine it was designed to catch.** Finding:
[`research/findings/0128-pead-gate1.md`](../../../research/findings/0128-pead-gate1.md).
**Standing counts: screens 14 · sealed opens 1 · n_trials 138** — unchanged, no ledger row.

| gate leg | result | verdict |
|---|---|---|
| 1 existence — spread CI excludes zero | H=63 spread **+6.645% [+4.234, +9.173]** | **PASS** |
| 2 majority train-year sign | **4/4** (2019 +6.7 · 2020 +2.0 · 2021 +9.6 · 2022 +7.3) | **PASS** |
| 3 economic magnitude net of ~0.26% cost | top decile **+3.48%** net, vs a 0.5% floor | **PASS** |
| 4 famine — >=150 top-decile events/yr | min **49** — but that is **2026, a stub year** (data ends 2026-07, every event needs 63 trading days after it). Every COMPLETE year carries **110-200** | **FAIL (artifact)** |

**Not retuned.** The threshold was not amended and the stub year was not dropped to manufacture a
pass; a gate that can be adjusted after seeing the result is not a gate. The bare FAIL is reported,
and so is the fact that leg 4 caught a construction detail rather than a famine.

**The confounds are the substantive story, and one fires.** Momentum (§4.1): spread is monotone in
trailing-63d momentum — low **+3.17 [-1.04, +7.51] straddles zero**, mid +5.87, high **+9.93**. The
effect is *not established independent of momentum*, and momentum is the house signal. Liquidity
(§4.2): high-ADV tercile **+3.64 [-0.30, +7.61] straddles zero** — the part tradable at size is not
significant. Decay: out-of-window 2023-26 spread **+2.822 [+0.74, +4.86]**, under half the train
magnitude, visible downtrend.

**Recommendation recorded: accept the close — on the confounds, not on leg 4.** A PEAD sleeve's whole
claim is to be a *different return source* (0115); the momentum table says it is substantially the
same one and the ADV table says the tradable part is not significant. That fails 0115's
low-correlation limb on evidence already in hand, before Phase 2 spends anything.

**If the owner instead amends leg 4** (to "per COMPLETE year"), the amendment must be dated and
committed **before any Phase-2 number exists**. It is legitimate only because it corrects a
construction artifact whose direction was fixed before Phase 2 ran.

**Limitations bounding the +6.6%:** the 63-day horizon requirement drops events near a name's data
end, biasing the estimate **upward**; the surprise proxy is announcement reaction, not analyst
surprise; `ann_ts` is the intimation timestamp so the brief's per-event after-close rule was **not
implementable**; and returns are market-adjusted, not beta-adjusted.
