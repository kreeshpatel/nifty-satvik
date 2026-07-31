# 0126 — The line-hugger hypothesis: name-level signal base rate against the banked labels

**Status:** PRE-REGISTERED — committed **before any label contact**.
**Class:** **LABEL SCREEN** — ledger row **#13**. One screen, serialized.
**No trial. Sealed set untouched. Judge log unread. No engine change.**
**Standing counts at registration: screens 12 · sealed opens 1 · n_trials 138.**
**At close: screens 13 · sealed opens 1 · n_trials 138.**

**Date:** 2026-07-31. **Owner:** Kreesh Patel.
**Instrument:** the banked 0116/0117 per-trade label dataset,
`research/substrate/context_windows.parquet` (4,025 trades). No new adjudicator is built.

---

## §0 IMMUTABLE — the collision register and the narrowing

**The instinct being tested:** some names sit on their 44-week line for months and fire the touch
signal repeatedly ("choppers", "line-huggers"); others touch rarely. Does that name-level property
carry information the funnel does not already have?

**This is five-wall territory and must be narrowed explicitly.**

| colliding verdict | what it killed | why this is not that |
|---|---|---|
| **Law I — the pre-entry wall** (bar-level ML, loser forensics, path shape, formula structure, perception) | predicting *which entry becomes a winner* from pre-entry information | This proposes **no oracle**. Q1 tests a discriminator, but Q2 — the question that matters — asks whether the **already-certified ext-band structure sub-divides**, i.e. whether a band we already trust is heterogeneous. That is a refinement of a certified fact, not a new prediction. |
| **0116 — the 21d path-shape family** (`path_eff`, `gap_share`, `gap_max`, `runup21`, `dd_hi21`, `updays`, `accel`, `range_comp`, `vol_burst`, `rs21`) — `path_eff` train-clean then **sign-flipped on the sealed set → KILL** | the shape of the **approach window** into a given entry | The hug index is **not in that feature list** and is not an approach-window shape. It is a **name-level base rate over 52 weeks** — a property of the *name's relationship to its own line*, computed over a window that mostly predates the approach. Different object, different window. **The 0116 flip is carried as the governing adverse prior (§4).** |
| **`base_min` — "require a pre-touch base near the SMA before the touch"** → **REJECT, DD −53.5%** (`losers_analysis/SYSTEM.md`) | an 8-week approach-window base requirement used as an **entry filter on the capped ₹10L book** | Closest existing formulation and the one this must not be confused with. Differences, all three load-bearing: **window** (8w approach vs 52w name history), **object** (a filter that changes which trades exist vs a screen that describes trades that already happened), **question** (does filtering improve the book — answered, no — vs does the band's core sub-divide — unasked). No filter is proposed here. |
| **The near-SMA lever family** (E1 near-SMA limit → win 59→41%; E2 `ext_cap` → defensive-only; `near_sma` fill-priority → −0.80 Sharpe) | *manufacturing* or *prioritising* near-line entries | Q2 proposes neither. It asks whether the naturally-occurring `<5%` cohort is one thing or two. |
| **0024 practitioner 10-day cooldown** | a cooldown tested **inside a whole taught system**, never isolated on the incumbent funnel | Q3 isolates it as a **mechanical, name-local comparison** (re-touch within 8 weeks of a stop-out vs the same name's cold touches) and reports it as a screen result, not a rule. |
| **Law VI — the ±10R/yr floor** | certifying micro-edges in-sample | Acknowledged. A screen result is a population measurement; **no usage claim is made here**, and §5 pre-commits that the activation bound runs before any rule is proposed. |

**The stated basis for touching the wall, verbatim for the record:** this is a **name-level
signal-base-rate feature** (how often this name fires the signal), not a path-shape feature of the
approach window, and it **interacts with the certified ext-band structure** rather than proposing a
new oracle.

## §1 IMMUTABLE — frozen definitions (fixed before any join)

Computed from the committed weekly panel (`nq.data.weekly.build_weekly_panel`), **PIT**: for a signal
in week *k*, the window is the **52 completed weeks strictly before k** — week *k* itself is never in
its own window.

| name | definition |
|---|---|
| **`hug_index`** | share of the trailing 52 weeks with **\|close/sma44 − 1\| < 5%** |
| **`median_abs_ext`** (secondary) | median of \|close/sma44 − 1\| over the same 52 weeks, in % |
| **`touch_count`** (secondary) | count of weeks in the window firing the **house** touch condition: `wlow ≤ wsma×1.07` **and** `wclose > wsma` |
| **coverage rule** | a window needs ≥ **40** of 52 weeks with a finite `sma44`, else the trade is **excluded** and the exclusion count is reported |
| **rare vs chronic** | **median split of `hug_index` within the analysis population.** A median split, not a swept threshold — there is no grid in this study. |
| **`N` for Q3** | **8 weeks**, frozen. |

The line is the **44-week SMA, never an EMA.**

## §2 IMMUTABLE — the three questions

All in **matched ext-band × CRS-tercile cells**, **train years only**, with CIs and per-year signs.

- **Q1 — discrimination.** Does `hug_index` separate `false_touch` from `noise_stop` / winners
  **beyond the cells**?
- **Q2 — the refinement question, the one that matters.** Split the **`<5%` ext band's `+0.717R`
  core** by `hug_index` (rare-touch vs chronic-hugger). Does the edge concentrate in **rare**
  touches? **Report the band's R in each half with N.**
- **Q3 — the cooldown formulation.** After a **stop-out** on a name, do that name's **re-touches
  within 8 weeks** underperform its **cold** touches (same name, no stop-out in the prior 8 weeks)?

## §3 IMMUTABLE — train-only discipline

- **`split == "train"` AND `entry_date ≤ 2024-06-30`**, both enforced.
- Sealed rows (2024H2+) are **dropped at read time, before any statistic is computed**. They are not
  subset, not described, not counted in any table beyond the single "rows dropped" number.
- **No sealed open is authorized this session.** Standing sealed opens remain **1**.
- `pre2019_untrusted` rows are excluded (the programme trusts ≥2019 only).

## §4 IMMUTABLE — named failure modes, each a KILL if it fires

Pre-committed so a confound cannot be reinterpreted as a discovery after the fact.

1. **`hug` ≈ inverse-CRS.** A weakly-trending name hugs its line and ranks low. **If the ext × CRS
   cells absorb the effect, that is a KILL — the ranker already knew**, and hug is a redundant
   re-encoding of `rank_crs`. Reported as the correlation `corr(hug_index, rank_crs)` and as the
   marginal-vs-conditional effect gap.
2. **`hug` ≈ low-vol proxy.** A low-ATR name deviates less from any moving average by construction.
   Reported as `corr(hug_index, atr_pct)`. **A hug effect that vanishes when stratified by ATR
   tercile is a KILL** — low-vol is O-016 territory and already routed elsewhere.
3. **The 0116 flip precedent.** `path_eff` was CI-clean, 5/6 years consistent, and **inverted on the
   sealed set**. Therefore: **a train-clean PASS here is explicitly NOT a validated effect.** It is a
   candidate whose only honest next step is the activation bound (§5), and its sealed validation
   would be a separate, priced governance event that is **not** part of this study. Any readout that
   omits this sentence is misreporting the result.

## §5 IMMUTABLE — the doors, pre-committed

**Pre-committed bar for a PASS on any leg** (verdict-machine Gate 2 — ALL legs required):
conditional separation with a **CI excluding zero** beyond ext × CRS; **per-year sign consistency
≥ 5/6** train years; **ADV-tercile sign-robustness** (ADV joined from the pinned cache at entry —
the substrate carries no ADV column); and the §4 confound checks clear.

- **KILL** → finding + `overlay_registry.md` row + ledger row #13 closed. **HEG-class names stay
  fully tradeable** and the line-hugger instinct is **retired with receipts**.
- **PASS on any leg** → **NO gate. NO non-tradeable list. No change of any kind.** The
  **activation bound** runs next per the standing law: *what fraction of signals / trades / R would a
  hug threshold have refused* — the **Law III bookend**, and ext-adjacent filters have historically
  refused the tail. Any usage shape after that is a **trial at the owner's door**, priced in
  `n_trials`.
- **Mechanism-matched consumer if Q2 passes** (recorded now so it is not invented later): **not
  exclusion** — a **refinement of the deep-touch band's definition** (rare-touch `<5%` as the true
  core), feeding the same unshipped sizing question and the card UI's band label.

## §6 Reproduce

    python scripts/diag_hug_index_screen_0126.py

---

## OUTCOME (appended 2026-07-31 after the run — nothing above this line was touched)

**VERDICT: KILL on all three legs.** Finding: [`research/findings/0126-line-hugger-screen.md`](../../../research/findings/0126-line-hugger-screen.md).
**Standing counts: screens 13 · sealed opens 1 · n_trials 138.** No trial spent; sealed set untouched.

| leg | result | vs the pre-committed bar |
|---|---|---|
| **Q1** discrimination | conditional +0.022 R **[-0.192, +0.243]**; false_touch -0.4pp [-3.8,+3.0]; noise_stop -2.0pp [-5.5,+1.5]; ADV terciles +0.026 / -0.052 / +0.023 | **FAIL** (CI straddles on every form) |
| **Q2** deep-band refinement | band N=122 +0.681R; **rare N=62 +0.418**, **chronic N=60 +0.954**; delta (rare-chronic) **-0.536 [-1.493, +0.334]** | **FAIL — and the point estimate is WRONG-SIGNED vs the hypothesis** |
| **Q3** cooldown (8wk) | hot N=136 +0.446 vs cold N=1483 +0.459; delta -0.013 [-0.843,+0.617]; conditional +0.094; activation 8.4% | **FAIL (dead null)** |

**The §4 failure modes did NOT fire.** corr(hug, rank_crs) = -0.181, corr(hug, atr_pct) = -0.274 —
mild and right-signed but not dominant; corr(hug, touch_count) = +0.762 confirms the instrument
measures what it claims. The feature is genuine, independent and well-measured, and still separates
nothing. That is a stronger null than a confound-explained one.

**Doors taken:** the KILL branch. HEG-class names stay fully tradeable; no gate, no non-tradeable
list, no band relabel. **The activation bound was NOT run** — it was pre-committed to a PASS, and
spending a measurement to price a rule nobody may propose would be waste.

**Two limitations that bound the claim** (both in the finding): the train window is **4 years**
(2019-22), because `split=="train"` intersected with the date cut is stricter than the sealed
boundary required — so the "≥5/6 years" leg was unattainable by construction and the achievable bar
was 4/4; and **Q2 is UNDERPOWERED, not merely null** (N=122; the delta CI spans ~1.8R and excludes
neither a +0.5R nor a -0.5R effect).
