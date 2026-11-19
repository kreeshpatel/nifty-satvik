# After-tax value of standard Indian tax practices — 2026-11-18

**This is analysis, not tax advice.** Every rate comes from `config/tax_india_fy2627.yaml`, and every value there is
marked **CONFIRM WITH CA**.

**Class:** MEASUREMENT. Owner request 2026-11-18, branch `research/india-tax-practices`. Nothing live changes, no
trial is spent, and nothing sealed is read.

**Standing counts:** screens 24 · sealed opens 4 · n_trials 3 (unchanged).

**Mission line.** The mission is judged after tax. This measures how much of the fallback books' after-tax return
depends on how the money is held (vehicle, cash instrument, harvesting, family split), as distinct from what it holds.

## Method (stated before results)

**Simulator.** The lot-level engine from `explore_after_tax_comparison.py`, generalised in
`pipelines/diagnostics/explore_india_tax_practices.py`; the docstring holds every formula.

- **Capital and window:** ₹20,00,000 invested on 2019-03-05, everything sold on 2024-06-28.
- **Rules applied:** FY 2026-27 rules, applied to the whole window.
- **Tax payment:** each 31 March.

**Books.**

- Static 60/40 and 65/35: the Midcap150 Momentum 50 index fund plus the cash leg, re-weighted each March.
- The 11% blend, for reference.

**Individual tax.**

| item | rule |
|---|---|
| Slabs | new-regime table, 4% cess |
| Assumed other income | Kreesh ₹30L (30% slab); 5% person ₹6L; 0% person nil |
| Equity STCG | 20% |
| Equity LTCG | 12.5% above ₹1.25L per person per year |
| 0%-slab person | unused basic exemption set against capital gains (CA question 3) |
| Surcharge | 0 (total income ≤ ₹50L) |
| Losses | STCL against STCG then LTCG; LTCL against LTCG only; carry forward 8 years; no wash-sale rule |

**Cash leg.**

- **Liquid fund:** 6.5% gross less 0.15% TER, taxed as debt (slab). This is a proxy; the repo has no liquid-fund index.
- **Arbitrage fund:** the liquid fund's net return less 0.3% a year, taxed as equity. This is also a proxy: the Nifty
  50 Arbitrage Index TRI couldn't be fetched on 2026-11-18, because the niftyindices endpoint returned HTML even for a
  cached index.
- **STT drag:** the extra 0.3% from April 2026 is in the config but inert in this window.

**Scenarios** (each adds to the one before):

| scenario | what changes |
|---|---|
| S0 | individual, liquid fund cash leg |
| S1 | arbitrage fund as the cash leg |
| S2 | + harvesting each March: losses realised and bought back; long-term gains realised up to the exemption and bought back; buy-backs are the newest lots |
| S3 | S2 split across N adult PANs; capital given as an **irrevocable gift** |
| S4 | S2 inside a private company under s.115BAA |

S3 detail: Kreesh plus N−1 others, all others at one slab. This models adult children or parents only. A spouse or a
son's wife is excluded, because gifts to them are clubbed back to the donor under s.64.

S4 detail:

- Debt gains are taxed at 25.17%.
- Equity gains are taxed at 20% / 12.5%, with 10% surcharge and 4% cess on top.
- There is no ₹1.25L exemption.
- Compliance costs ₹75,000 per FY, pro-rated, not deductible.
- Results are reported without and with a final dividend of everything to Kreesh at 35.88%.

**Added scope** (stated before results): a like-for-like row. Retained profits paid out as a dividend today, then
invested personally under S2.

**Metrics.**

- After-tax CAGR and final value, on the liquidation basis.
- Tax, trading costs, fund expenses and compliance.
- 156-week p95 drawdown: stationary bootstrap, mean block 8 weeks, 10,000 draws, on the after-tax mark-to-market NAV.

**Sensitivity.** Each rate is moved ±5pp (floored at 0) and each cost ±50%, one at a time. Recorded: whether the
ranking of the 60/40 scenarios, or the book ranking at S2, changes.

**Anchor (rule 4).** S0 with cess set to 0 reproduces the earlier study exactly: 60/40 **21.76%**, 65/35 **23.02%**,
blend **19.26%** [measured].

**Added after first look** (rule 5):

1. **Buy-back position in FIFO order.** Buy-backs first went in at the front of the FIFO queue. That was a bug: a fresh
   lot is the newest, so it belongs last.
2. **Harvest date.** Harvesting on the 31-March tax day itself made S2 *lose* ₹40.5k (60/40) against S1. A lot bought
   back on 31 March is sold by the next 31-March rebalance after exactly 365 days, which is short-term. Harvesting now
   happens on the first session on or after 15 March. The tax-day result is kept in the JSON
   (`first_look_same_day_harvest_S2`).
3. **Break-even at maximum surcharge.** With surcharge 0, S4 never breaks even, so the break-even search was repeated
   with the individual at maximum surcharge.

## Results — book × scenario (₹20L, 2019-03 to 2024-06)

Artifact: `diagnostics/research/explore/2026-11-18_india_tax_practices.json` [measured].

**60/40**

| scenario | after-tax CAGR | final value | tax | trading costs | fund expenses | compliance | 156w p95 DD |
|---|---|---|---|---|---|---|---|
| S0 liquid | 21.67% | ₹56,74,731 | ₹5,77,775 | ₹250 | ₹44,134 | — | 22.9 |
| S1 arbitrage | 21.86% | ₹57,22,853 | ₹4,97,839 | ₹250 | ₹63,688 | — | 22.9 |
| S2 + harvest | 21.92% | ₹57,36,313 | ₹4,83,065 | ₹403 | ₹63,673 | — | 23.0 |
| S3 N=2, other at 0% | 22.40% | ₹58,58,134 | ₹3,68,147 | ₹559 | ₹63,766 | — | 22.9 |
| S3 N=2, other at 5% or 30% | 22.18% | ₹58,03,257 | ₹4,22,816 | ₹559 | ₹63,763 | — | 22.9 |
| **S3 N=3, others at 0%** | **22.86%** | **₹59,75,199** | ₹2,51,099 | ₹594 | ₹63,767 | — | 22.9 |
| S3 N=3, others at 5% or 30% | 22.43% | ₹58,65,676 | ₹3,60,344 | ₹594 | ₹63,763 | — | 22.9 |
| S4 company, money stays inside | 18.31% | ₹48,88,874 | ₹5,49,480 | ₹296 | ₹58,678 | ₹3,99,247 | 26.5 |
| S4 + final dividend to Kreesh | 8.82% | ₹31,34,746 | ₹23,03,608 | ₹296 | ₹58,678 | ₹3,99,247 | 26.5 |
| like-for-like: dividend today, then S2 | 22.08% on ₹12.82L | ₹37,04,865 | ₹2,87,386 | ₹292 | ₹40,885 | — | 22.9 |

**65/35**

| scenario | after-tax CAGR | final value | tax | 156w p95 DD |
|---|---|---|---|---|
| S0 | 22.92% | ₹59,92,389 | ₹6,16,189 | 24.8 |
| S1 | 23.09% | ₹60,35,038 | ₹5,44,577 | 24.9 |
| S2 | 23.13% | ₹60,47,386 | ₹5,30,876 | 24.9 |
| S3 N=3, others at 0% | 24.03% | ₹62,85,397 | ₹2,98,861 | 24.8 |
| S4 | 19.55% | ₹51,68,420 | ₹5,96,112 | 28.3 |
| S4 + final dividend | 9.96% | ₹33,13,991 | ₹24,50,541 | 28.3 |

**Blend at 11% (reference)**

| scenario | after-tax CAGR | final value | tax | trading costs | 156w p95 DD |
|---|---|---|---|---|---|
| S0 | 19.07% | ₹50,59,614 | ₹8,11,394 | ₹2,20,976 | 26.6 |
| S1 | 19.26% | ₹51,02,244 | ₹7,78,941 | ₹2,21,860 | 26.4 |
| S2 | 19.12% | ₹50,71,156 | ₹7,79,886 | ₹2,43,092 | 26.5 |
| S3 N=3, others at 0% | 21.74% | ₹56,91,195 | ₹3,59,274 | ₹2,55,459 | 25.0 |
| S4 | 15.30% | ₹42,62,577 | ₹8,10,265 | ₹2,22,508 | 32.0 |

Harvesting costs the blend money. Every harvest trade pays stock costs, about 0.42% round trip.

## Rupee value each step adds over the window [measured]

| step | 60/40 | 65/35 | blend |
|---|---|---|---|
| S0 → S1 (arbitrage cash leg) | **+₹48,122** | +₹42,649 | +₹42,630 |
| S1 → S2 (harvesting, mid-March) | **+₹13,460** | +₹12,348 | −₹31,088 |
| S1 → S2, first look (harvest on the tax day) | −₹40,528 | −₹41,452 | −₹23,629 |
| S2 → S3, N=2, other at 0% | +₹1,21,821 | +₹1,21,070 | +₹3,50,324 |
| S2 → S3, N=2, other at 5% or 30% | +₹66,944 | +₹66,263 | +₹23,803 |
| S2 → S3, N=3, others at 0% | **+₹2,38,886** | +₹2,38,011 | +₹6,20,039 |
| S2 → S3, N=3, others at 5% or 30% | +₹1,29,363 | +₹1,28,381 | +₹30,505 |
| S2 → S4 (company, no payout) | **−₹8,47,439** | −₹8,78,966 | −₹8,08,579 |
| S2 → S4 + final dividend | −₹26,01,567 | −₹27,33,395 | −₹23,37,991 |

**Why S3 at slab 5% equals S3 at slab 30%.** With the arbitrage cash leg, every gain is equity. The other person's
slab then matters only through a 0%-slab person's unused basic exemption. So 5% and 30% give the same result, and the
whole S3 gain at those slabs comes from the extra ₹1.25L LTCG exemption each person adds.

## S4 break-even capital

Break-even means the capital at which S4's final value, as a multiple of capital, matches S2's.

| assumption | without dividend | with final dividend |
|---|---|---|
| Config surcharge (0) | **none up to ₹500 crore** | none |
| Kreesh at maximum surcharge *(added after first look)* | **₹5.5 cr** (60/40), ₹5.3 cr (65/35) | none |

With surcharge 0, every company rate sits above the individual rate, so no capital closes the gap. Maximum surcharge
here means 25% on slab income and the 15% cap on capital gains.

**Like-for-like.** If the ₹20L is retained profit, the comparison is between two paths:

- Pay the dividend today and invest ₹12.82L personally: **₹37.05L**.
- Invest ₹20L inside the company and pay the dividend at the end: **₹31.35L**.

Paying out today wins by ₹5.70L [measured].

## Sensitivity (one at a time, 60/40 scenario ranking; book ranking at S2)

**Base ranking.**

- Scenarios: S3 (N=3, others at 0%) > S2 > S1 > S0 > S4 > S4 with dividend.
- Books: 65/35 > 60/40.

| changed | to | result |
|---|---|---|
| STCG | 15% or 25% | none |
| LTCG | 7.5% or 17.5% | none |
| Kreesh's slab | 25% or 35% | none |
| Cess | 0% or 9% | none |
| Surcharge | 5% | none |
| Company debt rate | 20.17% or 30.17% | none |
| Dividend rate | 30.88% or 40.88% | none |
| Liquid gross return | 11.5% | none |
| **Liquid gross return** | **1.5%** | **S0 moves above S1**: a liquid fund beats arbitrage when yields are very low. Top and bottom unchanged |
| Every cost (TERs, arbitrage spread, MF stamp and STT, compliance) | ±50% | none |

What changes the ranking: only the cash yield, and only the S0/S1 order. **No change moves S3 off the top, lifts S4
above S2, or reorders the books** [measured, `sensitivity.rows`].

## Artifact check (rule 2)

1. **Harvest timing.**
   - Shown: the same practice on the tax day lost ₹40.5k.
   - The S1→S2 step (+₹13k) depends on scheduling rather than on harvesting itself.
   - Ruled in and disclosed.
2. **Proxies.** Arbitrage is the liquid fund less 0.3%, and liquid is a flat 6.5%.
   - Real arbitrage returns track the futures basis and were well below liquid-fund yields in 2020–21.
   - Not ruled out. S0→S1 rests on the proxy; the CA questions and a fetch of the real index can settle it.
3. **One window, one path.**
   - Every rupee figure is one 5.3-year history. Not ruled out.
   - The step ranking survives every ±5pp / ±50% sensitivity.
4. **Family split.** The split assumes each extra person has no other gains of their own using the exemption, and
   that the gift is real and irrevocable.
   - The 0%-slab gain depends on the basic-exemption set-off (CA question 3).
   - Not ruled out.
5. **Company costs.** ₹75k a year is about 3.75% of ₹20L each year.
   - Halving it still leaves S4 at 19.87% vs S2 21.92%.
   - Ruled out as the sole cause.
6. **FY 2026-27 rules over 2019–24.** This is the owner's spec. The actual taxes paid in those years differed.

**Re-derivation (rule 3):** see the end of this file.

## Questions for the CA

1. **Company LTCG exemption.** Does the ₹1.25L s.112A LTCG exemption apply to a private company? (Default here: no.)
2. **87A rebate.** Under the new regime, can the s.87A rebate be set against s.111A / s.112A gains for a family member
   with low income? (Not modelled.)
3. **Basic exemption against gains.** Can a resident family member with income below ₹4L set the unexhausted basic
   exemption against STCG and LTCG? (Default: yes. This drives the S3 0%-slab gain.)
4. **Gifts to family.**
   - Confirm that gifts to adult children and parents are outside s.64 clubbing, and that the income on them is theirs.
   - Confirm s.56(2)(x) treats such gifts as gifts from a relative.
   - What documentation makes the gift irrevocable?
5. **Same-day buy-back.**
   - Is selling and buying back the same fund on the same day accepted for both gains and losses, given India has no
     wash-sale rule?
   - Is there any GAAR or "colourable device" risk at this scale?
6. **Arbitrage fund status.** Does an arbitrage fund keep equity-oriented status (65%+ equity) after the April 2026 STT
   change? How should its post-2026 return drag be modelled?
7. **Liquid fund units.** Is the slab rate correct for liquid-fund units, including any bought before 1 April 2023?
8. **Company tax.**
   - Under s.115BAA, does the 10% surcharge apply to the company's capital gains?
   - Is the compliance cost deductible against investment income?
   - What is the correct effective dividend rate to Kreesh at his income?
   - Does s.2(22)(e) bite if he takes money out as a loan?
9. **Surcharge.** Which surcharge applies on Kreesh's capital gains at his actual total income (the 15% cap)?
10. **Advance tax.** Paying once a year on 31 March is a simplification. Would advance-tax instalments and s.234B/C
    interest change any ranking?

## Re-derivation (rule 3)

A fresh `blind-replica` rebuilt the 60/40 book from the spec and the config only.

| scenario | replica | this study | gap |
|---|---|---|---|
| S0 | ₹56,74,703 | ₹56,74,731 | — |
| S0, cess 0 (anchor) | 21.76% | 21.76% | — |
| S1 | ₹57,22,825 | ₹57,22,853 | — |
| S2 | ₹57,34,389 | ₹57,36,313 | −₹1,924, 0.03% |
| S3, N=3 at 0% | ₹59,74,939 | ₹59,75,199 | — |
| S4 | ₹48,88,851 | ₹48,88,874 | — |
| S4 + dividend | ₹31,34,731 | ₹31,34,746 | — |

The S1→S2 *step* differs by more than 5% relative: +₹11,564 in the replica against +₹13,460 here.

**Reconciled.** The step depends on which fund's same-date lots are harvested first, when the index fund and the
arbitrage fund carry lots bought on the same day. The replica took index lots first. Its arbitrage-first variant gives
S2 = ₹57,36,285, within ₹28 of this study.

**Reading.** The harvesting step is about **₹12–13k** over the window, and its exact size depends on lot-ordering
conventions. It is small next to the other steps.
