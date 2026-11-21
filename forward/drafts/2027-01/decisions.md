# January 2027 review — owner decisions (one page)

DRAFT, 2026-11-20. Each item has the options, a recommendation from the lead quant, and a one-line reason with its
evidence path. **None is decided until the owner names the item.** Standing counts: screens 25 · sealed opens 4 ·
n_trials 3. Facts are in `forward/drafts/2027-01/review_dossier.md` (§ numbers below).

| # | decision | options | recommendation | one-line reason (evidence) |
|---|---|---|---|---|
| 0 | **Expectation** | acknowledge: yes · no | **Acknowledge** | The recommended core (60/40, fund 150738 / arbitrage 119771) is expected to earn **about 15% a year after tax**, at a **p95 drawdown of about 24%**. The base is 15.67% / 23.97 on 2017–26. Adding the measured 1.05pp a year fund drag to the index leg (60% of the book) gives **14.97% / 24.22** (§4). The 2019–24 figure of about 23% came from a strong window. The company engine (0153) is the only route above this, and only if it passes its gates. Owner acknowledges: yes / no. |
| 1 | **Core capital** | (i) 60/40 index fund 150738 / arbitrage fund 119771, both sleeves paper-only · (ii) retire swing, 0001 paper · (iii) status quo | **(i)** | 60/40 is the highest static mix under −25% on 2017–26 (15.64% / p95 23.99; 15.67 / 23.97 with 119771 alone; ≈15.0 with the real fund's drag) and the blend won 0 of 28 rolling windows after tax (§3, §4). |
| 2 | **Swing: retire or paper** | retire · keep on paper | **Paper** | Paper keeps the 26-week forward clock at no capital cost; the backtest shows no edge (alpha −3.08%, t −0.45; permutation p 0.09/0.13) but only the forward record can settle it, and no path is killed without a run (§2). |
| 3 | **0001 on paper** | paper · retire | **Paper** | Full-run net t 0.44 against a 3.57 hurdle fails, but 2019–24 gross t 2.31 and 2024–26 net +3.97% leave the forward record as the cheapest test (§1). |
| 4 | **Sign 0153 (company engine)** | sign · amend · defer | **Sign** | Phase 0 data, holdout guard and gate harness are on main; D/E limited to add-on (2026-11-20 note); results gaps cluster in insurers and pre-history, not size (§9). |
| 5 | **Sign the exploration lane** | sign · amend · defer | **Sign** | A counted 15-trial-per-quarter budget, pre-registered kills and the wall rule keep the search inside the books, with no capital without 26 weeks of paper (`exploration_lane_amendment.md`). |
| 6 | **11% vol-target amendment** | sign · drop | **Sign, low stakes** | With the blend paper-only it moves no money now; it only sets which blend the paper record and its frozen bands measure. Signing keeps the paper record on the design that would get capital if it ever earned it (p95 23.35 → 23.48 with real price bands: condition precedent met, §3; `forward/drafts/2026-11-18_amendment_blend_vt11_DRAFT.md`). |
| 7 | **Cash leg after CA question 6** | keep arbitrage 119771 · switch to a liquid fund | **Keep arbitrage unless the CA says it loses equity-oriented status; then switch at the next quarterly review** | Arbitrage beat liquid by +0.69pp a year, P 0.9995, under equity taxation (§8). If Q6 says slab taxation, the edge is the tax treatment and the choice must be re-run. |
| 8 | **Proposed candidate gate** (dossier §10) | adopt · amend | **Adopt** | 0001 passes t ≥ 2 in 2019–24 but not over its full run; full-history testing removes window choice (§1, §10). |
| 9 | **Results gaps (BSE blocked)** | (a) retry BSE from another network · (b) owner hand-downloads the 607 interior-gap quarters · (c) accept the gaps | **(c): financials excluded from L1 entirely and from L5's fundamental inputs only (L5 price features keep them); the 425 pre-first-filing quarters are not gaps; the remaining interior gaps stay NaN, never interpolated, and the L1 study must report forecast points lost to them. If more history is needed later, a browser-based BSE fetch is the fallback (scripts get 403).** Rule recorded in 0153 (note 2026-11-20, PR #221). | api.bseindia.com refused 5 of 5 calls (403); the gaps are 21.96% in financials vs 5.08% elsewhere and show no size cluster (§9; `diagnostics/research/explore/2026-11-20_bse_gap_fill_attempt.json`). |
| 10 | **Mission fallback wording in CLAUDE.md** | apply draft · amend · leave | **Apply after item 1** | The draft names exposure 0.60 at 8-week blocks on 2017–26, which matches item 1 (`forward/drafts/2026-11-18_mission_fallback_DRAFT.md`). |

## CA questions outstanding (all 10 from `diagnostics/research/2026-11-18_india_tax_practices.md`, none answered)

1. Does the ₹1.25L s.112A LTCG exemption apply to a private company?
2. Can the s.87A rebate be set against s.111A / s.112A gains for a low-income family member (new regime)?
3. Can a family member below ₹4L income set the unexhausted basic exemption against STCG and LTCG?
4. Are gifts to adult children and parents outside s.64 clubbing, treated as from a relative under s.56(2)(x), and
   what makes them irrevocable?
5. Is same-day sell-and-buy-back of the same fund accepted for gains and losses, and is there GAAR risk at this scale?
6. **Does an arbitrage fund keep equity-oriented status after the April 2026 STT change, and how should its
   post-2026 return drag be modelled?** (drives item 7)
7. Is slab rate correct for liquid-fund units, including those bought before 1 April 2023?
8. Company: s.115BAA surcharge on capital gains; deductibility of compliance cost; effective dividend rate to the
   owner; s.2(22)(e) on loans.
9. Which surcharge applies to the owner's capital gains at actual total income (the 15% cap)?
10. Would advance-tax instalments and s.234B/C interest change any ranking?

Items 1 and 7 depend on Q6; the family-split gain (+₹81.1k median) depends on Q3 and Q4; the company route on Q1, Q8
and Q9 (§8).
