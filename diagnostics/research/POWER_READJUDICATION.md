# Power re-adjudication — "not proven better" is not "proven worse"

**Date:** 2026-08-06 · **Class: VERIFICATION.** Zero trials, zero screens.
**Counts frozen: screens 16 · sealed opens 1 · n_trials 138.**

> **GUARD, stated first and binding: this is a LABELLING correction. It revives nothing. No row
> below is authorised for re-testing, and reclassification is not a re-open condition. Every
> collision rule in [`program-laws`](../../skills/program-laws/SKILL.md) still applies unchanged.**

---

## The conflation this corrects

The record writes one word — KILLED, REJECT — for two different findings:

| claim | what it means | what it licenses |
|---|---|---|
| **NOT PROVEN BETTER** | the book could not resolve a difference; adoption correctly declined | declining adoption. Nothing else. |
| **PROVEN WORSE** | the candidate was measured as inferior | declining adoption **and** treating the territory as closed on evidence |

The programme has been correct to decline adoption in every case. It has **not** been correct to
record all of them as evidence that the candidate is inferior, because on a book with this book's
power most of them could not have been resolved either way.

**The measured resolution band.** Only one verdict on this book ever published a confidence
interval: STAGE4's paired block-bootstrap gave **ΔSharpe +0.148, 95% CI [−0.131, +0.473]** — a
half-width of **±0.302 Sharpe**. That is the only *measured* statement of what this book can resolve,
and it agrees with the independent power arithmetic (`STRUCTURAL_DEFECT_MAP.md` §2: the ±10R/yr
floor is 1.204 annual σ against a book at 1.617σ). **Any |ΔSharpe| below ≈0.30 was never resolvable
on the capped book.**

---

## The re-adjudication

Base of record: Sharpe **1.132**. Δ is against that base unless noted.

| verdict | published Δ | CI | inside ±0.302? | **reclassified** |
|---|---:|---|---|---|
| **STAGE4 config D** (sleeves ×3) | **+0.148** | **[−0.131, +0.473]** | yes, and CI straddles zero | **NOT PROVEN BETTER** — and note the point estimate is *positive* |
| STAGE4 config C (sleeves ×6) | −0.05 | none published | yes | **NOT PROVEN** (either direction) |
| STAGE4 config B (all-setups shared) | +0.19 Sharpe / −0.22 on the 22-26 slice | none published | yes | **NOT PROVEN** — and the two slices disagree in sign |
| `ext_cap 22%` (E2) | −0.149 | none published | yes | **NOT PROVEN WORSE** — already recorded as "defensive", DD −42.4 → −32.4 |
| `drop_rs` | −0.037 | none published | yes | **NOT PROVEN** — already recorded "~NEUTRAL" |
| `first_touch` | −0.269 | none published | yes | **NOT PROVEN WORSE** |
| `base_min` (pre-touch base) | −0.317 | none published | marginal (just outside) | **BORDERLINE** — DD also worse (−53.5%), which is a second axis |
| `ext_cap 12%` | −0.603 | none published | no | PROVEN WORSE stands *(no CI published)* |
| near-SMA LIMIT, strict (E1) | −0.787 | none published | no | PROVEN WORSE stands *(no CI published)* |
| **near_sma fill-priority (E3/E11)** | −0.802 | none published | no | PROVEN WORSE stands *(no CI published)* |
| **ROUTER** (per-branch exits) | −0.58 on the 2022-26 slice (0.71 vs 1.29) | none published | no | PROVEN WORSE stands *(no CI; a sub-slice, so its own band is wider than ±0.302)* |

**Four rows reclassified to NOT PROVEN; two more (`drop_rs`, `base_min`) were already hedged or are
borderline. Four rows keep PROVEN WORSE**, and even those carry a caveat: **none of them published a
CI**, so "proven worse" rests on a point estimate exceeding the only measured resolution band this
book has, not on its own interval.

### The worked example, spelled out

STAGE4 config D is recorded in `STAGE4_sleeves.md` as **"Ship NOTHING"** and *"FAIL (not
significant)"*. Both are correct. What the record does **not** say, and what matters:

- the point estimate was **+0.148 Sharpe — in the candidate's favour**;
- the CI ran **[−0.131, +0.473]**, so the data are consistent with anything from a small loss to a
  large gain;
- the DD point estimate improved (−42 → −34) and its CI **[−0.049, +0.132]** also straddles zero.

The honest sentence is *"config D was not proven better on a book that could not have proven it."*
The sentence the record currently supports on a fast read is *"config D is worse."* Those are
different claims and only the first is evidenced.

### What did NOT change

The **activation bounds** (0117, 0119, 0121, 0127, 0129) are untouched by this. They are not
capped-book ΔSharpe comparisons — they are clairvoyant ceilings, and a ceiling below the floor is a
valid negative result regardless of power: it says *even with perfect foresight there is not enough
there to measure*. Likewise 0130's −10.83%/yr has its own CI and its own unit; it is not in this
table.

The **five pre-entry walls** are untouched: they are population-level nulls with their own CIs, not
capped-book comparisons.

---

## Consequence — and the boundary of it

1. Rows reclassified NOT PROVEN are **not** re-open conditions and **not** candidates. Reclassifying
   a label does not create evidence.
2. Any future re-test of one of them still needs the collision rule — name which of {new data, new
   feature source, new sub-period, new formulation} it brings — **and** must be run somewhere with
   the power to resolve it, which the capped book does not have. That means the population or
   forward.
3. **The class of conclusion this affects is broad.** Where a programme declines many candidates on
   an instrument that cannot resolve them, the resulting picture — "everything fails" — is partly a
   statement about the instrument. That is the honest reading of the 4-for-4 bound record and of the
   entry-lever table together.

---

## Addendum 2026-08-06 — the STANDALONE family line was never tested at all

**Question put to this session:** was STAGE4's per-family standalone line — *touch 1.29 · cup 1.02 ·
box 1.00 · double_bottom 0.94* on the 2022-26 slice — put through the same resolution test as
configs B/C/D?

**Answer: no.** `STAGE4_sleeves.md` contains exactly two confidence intervals, both from
`diag_sleeve_rigor.py`, and both are **config D vs config A** (ΔSharpe +0.148 [−0.131, +0.473];
ΔMaxDD +0.088 [−0.049, +0.132]). **The standalone family line carries no interval, no bootstrap and
no walk-forward.** It is a bare point-estimate table — and it is the line the corpus cites most often
as the reason the zoo is closed.

### Applying the band

| comparison | gap vs touch 1.29 | vs ±0.302 | reclassified |
|---|---:|---|---|
| cup_handle 1.02 | **0.27** | inside | **NOT PROVEN WORSE** |
| box 1.00 | **0.29** | inside | **NOT PROVEN WORSE** |
| double_bottom 0.94 | **0.35** | 16% beyond | **BORDERLINE → NOT PROVEN** once the two corrections below are applied |
| ascending_base 0.64 | 0.65 | outside | worse stands |
| trend_pullback −0.06 | 1.35 | far outside | worse stands |

### Two corrections that both widen the band, and therefore both favour "not proven"

1. **These are sub-slice comparisons.** ±0.302 was measured on the **full period**; the standalone
   line is the **2022-26 slice**, roughly half the span and so roughly half the trades. A CI scales
   about as 1/√n, so the honest band for these gaps is **wider than ±0.302 — plausibly ±0.4 or
   more.** Every one of the three gaps sits inside that.
2. **These books are smaller.** ±0.302 came from config D (484 trades) against A (168). Each
   standalone family runs one funnel on its own ₹10L — config C's six sleeves total 975 trades, so
   roughly 160 per family. **Fewer trades per arm than the comparison the band was measured on**,
   which widens it again.

Transferring the full-period, larger-N band to a sub-slice, smaller-N comparison is therefore
**conservative**: the real uncertainty is larger, and the "not proven" reading is stronger than the
arithmetic above already makes it.

### What this changes, and what it does not

**Changes:** the sentence *"no family beats touch standalone"* is not supported for cup, box or
double_bottom. The supported sentence is *"no family was shown to beat touch standalone, on a slice
that could not have shown it."*

**Does not change:** `ascending_base` and `trend_pullback` remain worse on gaps far outside any
plausible band — consistent with `ZOO_TWO_LENS.md`, where `ascending_base` is *underpowered at
population level* but standalone-worse by 0.65 at portfolio level, and `trend_pullback` is null in
both.

**And it does not change the portfolio verdicts.** Config B/C/D and ROUTER tested whether these
families help *inside a shared, capped book*, and those remain as re-adjudicated above. A family
being not-proven-worse **standalone** says nothing about whether adding it to a shared cap helps —
that is the per-trade-vs-portfolio wall, and it is separately measured.

> **The guard at the top of this document applies here without exception: this is a relabel. It
> revives nothing and authorises no re-test.**

### RESOLUTION — 2026-08-06, the same day: the missing evidence was then supplied

**The relabel stands, and it is no longer where the story ends.** `cup_handle`, `box` and
`double_bottom` were **not proven worse** by STAGE4 — that verdict had no interval. They have since
been **proven worse *in the capped book* by a powered instrument in the arbiter unit**:

| | STAGE4's standalone line | finding 0131 |
|---|---|---|
| instrument | 4 portfolio Sharpes on a sub-slice | per-trade quality, **491 vs 255 trades** |
| interval | **none** | **CI [−3.598, −0.264] % of equity, excludes zero** |
| supporting facts | — | trade count 255→491 (exact); touch44 fills 255→29 (structural) |
| mechanism | none stated | stop width → notional → seats → dilution, each link measured |

**The distinction that matters, and it is the point of this whole document:** the audit did not
merely relabel a verdict it disliked. It **identified that the verdict was missing its evidence, and
then supplied it.** The conclusion the corpus reached — do not put the zoo in the book — survives.
What changes is that it is now *supported*, by an instrument with the power to support it, with a
named arithmetic cause and with both escape routes shown closed.

The reclassification of the **other** rows in this document (STAGE4 configs B/C/D, `ext_cap 22%`,
`first_touch`, `drop_rs`, `base_min`) is untouched by this: they remain NOT PROVEN, and no evidence
has been supplied for them either way.

## Cross-references

`research/substrate/STAGE4_sleeves.md` (the CI) · `research/substrate/ROUTER_RESULT.md` ·
`research/losers_analysis/{SYSTEM,FORENSIC_FINDINGS}.md` (the E levers) ·
`STRUCTURAL_DEFECT_MAP.md` §2 (the power arithmetic) · `UNIT_RESOLUTION.md`
