# 0127 — HEG-class approach: the activation bound (exclusion vs conditional management)

**Status:** PRE-REGISTERED — committed, and the ledger row appended, **before the run**.
**Class:** **ACTIVATION BOUND** — ledger row **#14** (it touches outcomes, so it is priced).
**No trial. Sealed set untouched. Judge log unread. No engine change.**
**Standing counts at registration: screens 13 · sealed opens 1 · n_trials 138.**
**At close: screens 14 · sealed opens 1 · n_trials 138.**

**Date:** 2026-07-31. **Owner:** Kreesh Patel.
**Standing law it satisfies** (`label_screen_ledger.md`): *no usage trial may be pre-registered until
a zero-trial clairvoyant activation bound has been run.* Here the bound runs **before** the screen,
not after — the cohort is large enough that the bound is the cheaper discriminator.

---

## §0 IMMUTABLE — the claim, and the two different claims inside it

**The archetype (owner, 2026-07-31):** a name makes a high, then declines on the daily chart for
**4 weeks or more**, and that decline is what carries it back to the 44-week SMA where the signal
fires. The claim is **not** that these are worse trades — that is the pre-entry wall and it is dead
five times. The claim is that they are **different trades that want different handling**.

That sentence contains **two claims with different ceilings**, and this bound prices them
**separately** because conflating them is how a null gets read as a hint:

| | claim | ceiling it is measured against |
|---|---|---|
| **(a) EXCLUSION** | refusing the cohort improves the book | the **Law III bookend**: what the refused trades actually earned, and what share of book R they carry. Removing a positive-EV cohort costs that R; the slot is not free. |
| **(b) CONDITIONAL MANAGEMENT** | handling the cohort differently from everything else improves the book | the **clairvoyant conditional gain**: with perfect hindsight over a frozen set of managements, what does *conditioning on cohort membership* buy over the best single management applied to everyone? |

**(b) is the owner's actual claim.** (a) is priced anyway because it is the cheaper and more common
mistake, and because Law III requires the bookend before any subtractive rule is argued.

## §1 IMMUTABLE — frozen definitions

Computed from the committed weekly panel (`nq.data.weekly.build_weekly_panel`) over the Stage-1
uncapped substrate (`research/substrate/trades.parquet`), `setup == "touch44"`.

| name | definition |
|---|---|
| **peak** | the highest weekly **high** in the **13 completed weeks** before the signal week |
| **`descent_duration`** | weeks from the peak week to the signal week |
| **`descent_depth`** | `(peak − signal_close) / peak × 100` |
| **`descent_velocity`** | `descent_depth / descent_duration` (%/week) |
| **HEG-class (PRIMARY, frozen)** | `descent_duration ≥ 4` **AND** `descent_depth ≥ 20%` |
| **pre-registered robustness** | `(≥4wk, ≥15%)` and `(≥6wk, ≥20%)` — **reported, never used to choose.** The decision is made on the PRIMARY only. |
| **window** | `entry_date ≥ 2019-01-01` (the programme trusts ≥2019 only) |

**Management set M (frozen, four members, no sweep):** `as-is` · `take-profit @ +2R` ·
`take-profit @ +3R` · `tighten stop to −0.5R`. Modelled from the substrate's `mfe_pct` / `mae_pct`
normalised by `risk_pct`.

**Stated approximation:** excursion *ordering* is unknown (we know the trade's best and worst
excursions, not which came first), so a modelled take-profit assumes the favourable excursion was
reachable. **This inflates the ceiling.** Inflation is the conservative direction for a bound whose
purpose is to fail — a bound that fails while inflated fails decisively.

**Population note, same logic:** the bound runs on the **uncapped** substrate, which carries more
trades and therefore more R/yr than the capped ₹10L book. That also inflates both bounds. A bound
that clears the floor here is therefore **not** a pass — it would owe a capped re-check. A bound
that fails here has failed on the friendliest population available.

## §2 IMMUTABLE — the gate, pre-committed

A bound **PASSES** only if **both** legs hold:

1. **Magnitude:** |bound| **> 10 R/yr** — the ±10R/yr path-noise floor (0109 / 0117). Below it, an
   effect cannot be certified on this book *no matter how real it is*.
2. **Sign consistency:** the bound's sign holds in a **majority of trusted years** (≥2019).

Wrong-signed at any magnitude is a **FAIL** — that is 0119's mode (a real population gradient that
inverted at the decision margin).

## §3 IMMUTABLE — the two branches, and the closing clause

- **BOUND FAILS (either leg, either alternative)** → **NO screen #14.** Finding + registry row +
  ledger row #14 closed. Nothing is proposed, nothing is shipped, HEG-class names stay fully
  tradeable and identically managed.
- **BOUND PASSES** → screen #14 **may be pre-registered** (it is still a screen: its own pre-reg, its
  own ledger row, its own multiplicity price). A passing bound is permission to ask, not evidence.

### The closing clause (owner, condition 2 — verbatim)

**This is the FINAL reformulation of the line-hugger instinct this quarter.** A bound-fail here, or a
screen-#14 fail downstream, **closes the thread until genuinely new data (habit-ledger labels)
exists**. No further phrasings: not a different descent window, not a different depth threshold, not
a per-name variant, not a "but what about velocity instead". The instinct will have been given a
base-rate test (0126) and a kinematics test (0127) and that is the quarter's allowance.

## §4 IMMUTABLE — named failure modes, quoted verbatim

Each is an adverse prior this bound must be read against. **Quoted, not paraphrased**, per the
owner's condition.

1. **0116's sealed flip, on the nearest feature family.** From
   [finding 0116](../../research/findings/0116-context-window-selection.md): *"`path_eff`:
   conditional top-vs-bottom tercile spread **−0.23R [−0.43,−0.02]**, median −0.31R, sign 5/6 train
   years. Story: efficient approaches = blow-off class (bad); choppy approaches = base-building
   (good)."* — and it **inverted on the sealed set**. `descent_*` is the nearest living relative of
   that family. A clean-looking number here carries that precedent as its prior.
2. **`dist_52wh`'s gradient points against the cohort.** From
   [`STAGE2_ml.md`](../../research/substrate/STAGE2_ml.md): *"`dist_52wh_pct` | 39 → 46 → 50 → 54 →
   55 | **buy near the 52-week high** (O'Neil)"*. A spike-then-bleed name is **further** from its
   52-week high by construction, so the banked evidence already leans against this cohort being the
   better half of anything.
3. **Exit geometry is closed unconditionally.** From
   [`skills/program-laws`](../../skills/program-laws/SKILL.md) §V: *"Exit geometry is separately
   closed unconditionally (0105 tighten, 0106 widen, 0109 disaster-floor — all KILL, the 0094 stop is
   a robust optimum unmovable in either direction)."* Bound (b) proposes conditional exits; it must
   beat a geometry that is already optimal unconditionally.
4. **Law V — post-entry is hindsight-only.** From `program-laws` §V: *"The price path carries no
   exploitable conditional information anywhere on this funnel beyond the original signal and
   week-relative selection. The book's R is earned by holding through noise the information cannot
   resolve — which is why every 'manage it smarter' lever dies."* Bound (b) is a "manage it smarter"
   lever. This is the law it is trying to be the exception to.

## §5 IMMUTABLE — what is reported

1. **The cohort table, recomputed from this committed script** (owner condition 3 —
   reproduce-before-trust; the 2026-07-31 ad-hoc numbers inform nothing until reproduced here).
2. **Bound (a) exclusion:** cohort share of trades and of **total book R**; cohort mean R; R/yr
   refused; the clairvoyant version (refuse only the cohort's *losers*) as the exclusion ceiling.
3. **Bound (b) conditional management:** best M for cohort + best M for the rest − best single M for
   everyone, in R/yr, with the per-M table shown so the choice is auditable.
4. **Per-year signs** for both.
5. **Robustness thresholds** reported, decision on the PRIMARY only.
6. **Standing counts** stated.

## §6 Reproduce

    python scripts/diag_hegclass_bound_0127.py

---

## OUTCOME (appended 2026-07-31 after the run — nothing above this line was touched)

**VERDICT: FAIL on both alternatives → NO screen #14.** Finding:
[`research/findings/0127-hegclass-activation-bound.md`](../../../research/findings/0127-hegclass-activation-bound.md).
**Standing counts: screens 14 · sealed opens 1 · n_trials 138.** Sealed slice never read.

**The cohort is real and descriptively worse:** N=229 of 1,415 (**16.2%** of touches), meanR
**+0.062 vs +0.494**, win **40.6% vs 48.1%** — a 0.43R per-trade gap. The owner saw something real.

| bound | value | gate | outcome |
|---|---|---|---|
| **(a) exclusion** — refusing the cohort | **1.92 R/yr** cost (cohort is +14.3R total = **2.4% of book R** from 16.2% of trades) | vs ±10 R/yr floor | **FAIL** — Law III exactly as written: a marginally positive-EV cohort's slot is not free |
| (a) clairvoyant *refuse-only-losers* ceiling | 26.22 R/yr | clears magnitude, but the **sign test is a tautology** (positive by construction) and it is **unreachable** — perfect loser-foresight is the five-wall pre-entry problem; 0121 showed redeployment dominates | **FAIL (not a pass; flagged so it is not quoted out of context)** |
| **(b) conditional management** — handling the cohort differently | **0.0 R/yr, and exactly 0.0 in all 8 years** | vs ±10 R/yr floor | **FAIL BY IDENTITY** — best M for cohort = best M for rest = best single M for all = **TP@3R**. The optimum does not move. |

**Bound (b) is the owner's actual claim and it failed in the strongest form available:** given
perfect hindsight over the frozen management set, the HEG-class cohort wants the *identical*
treatment to everything else. Not a small gain, not a straddling CI — a gain of zero by identity.

**Do not misread the management table:** TP@3R appearing to beat as-is on the whole book (678.1 vs
600.6) is an artifact of the pre-registered excursion-order approximation (deliberately optimistic,
to inflate the ceilings), **not** evidence about exits. Exit geometry stays closed (0105/0106/0109).

**Named failure modes (§4):** `dist_52wh`'s adverse gradient was **corroborated** (40.6% vs 48.1% win
sits exactly where it predicted); exit-geometry closure and Law V were both **reinforced** — bound
(b) handed the rule hindsight and it still bought nothing; 0116's sealed flip was never engaged
because there was no train-clean effect to flip.

**§3 branch taken: FAIL → no screen #14.** HEG-class names stay fully tradeable and identically
managed. **The §3 closing clause is now in force: this was the FINAL reformulation of the
line-hugger instinct this quarter (0126 base rate, 0127 kinematics); the thread is closed until
habit-ledger labels exist.**

**Banked outcome-independently:** `descent_duration` / `descent_depth` / `descent_velocity` added to
the habit-ledger schema §1.2 — not because they predict (this finding says they do not), but so the
next kinematics question does not re-derive them from raw bars.
