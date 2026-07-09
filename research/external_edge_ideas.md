# External Literature — Candidate Edge Ideas (deep-research, 2026-07)

> **What this is.** Output of a deep-research harness run (5 search angles → web search →
> fetch/extract from primary academic sources → synthesis) scoped to: orthogonal/improving
> edges for a **long-only, cross-sectional, ~3-month-hold (≈63 trading-day) equity strategy on
> NSE large+mid caps**, currently momentum/trend-led (rank by 200-day trend slope, hold top ~15).
>
> **Provenance caveat.** The harness's 3-vote adversarial verify step did **not** complete (the
> session token limit was hit mid-verify; it falsely marked all claims "refuted"). The fetch
> step DID succeed — claims below are from real, mostly-primary sources. Confidence ratings here
> are from **source quality + project-aware judgment**, NOT the automated refute-vote. To get the
> formal adversarial stamp, re-run the verify pass (after the limit resets) — see "Next steps".
>
> **Project context the next chat must keep in mind.** The entry signal `sma200_slope_63` is
> validated (entry-only book Sharpe ~1.15 / +8.4%/trade; the C4 horse-race re-confirmed it beats
> mom_252_21 / mom_126 / donchian as a sole ranker). Open levers right now: **conviction within
> top-15 (Stage C)**, **exit-structure / "let winners run" (Stage D)**, **orthogonal predictors**,
> and the **−42% drawdown** weakness. Every candidate below must clear the promotion bar
> (post-tax post-cost ΔSharpe ≥ +0.10, ΔCalmar ≥ +0.05, 2022–26 positive, WF fold-pass ≥ 60%,
> bootstrap CI-low > 0, turnover ≤ +30%, 1-sentence mechanism) and respect the §11 do-not-relitigate
> log. "Overlap tag" below flags where a candidate brushes a prior KILL **and why it's still a
> distinct, untested variant**.

---

## Bucket 1 — Orthogonal cross-sectional predictors (India / EM)

### 1. Quality / gross profitability — Hanauer & Lauterbach (2019), *The Cross-Section of Emerging-Market Stock Returns*
- **Source:** SSRN 3233614 (primary; Emerging Markets Review). https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3233614
- **Mechanism:** cash-flow-to-price, **gross profitability**, and composite equity issuance are pervasive cross-sectional return predictors across 28 EMs.
- **Effect/horizon:** significant across equal- and value-weighted sorts and Fama-MacBeth regressions; alternative factor definitions beat FF5 out-of-sample in EM. Monthly/quarterly.
- **Data:** fundamentals — gross profit/assets, CF/P, shares outstanding (PIT Screener store already in repo).
- **India evidence:** EM-wide incl. India (not India-isolated).
- **Orthogonal to 200d trend:** **YES.**
- **Failure mode:** quality is slow; weak at a single quarter. (Note: the repo's `ep`/`bp` value legs were weak at 63d — but *gross profitability* ≠ value and is untested here.)

### 2. Accruals / earnings quality — Sloan (1996), *Do Stock Prices Fully Reflect Information in Accruals and Cash Flows…*
- **Source:** SSRN 259691 (primary; The Accounting Review). https://papers.ssrn.com/sol3/papers.cfm?abstract_id=259691
- **Mechanism:** firms whose earnings are driven by accruals (not cash) underperform; accruals are negatively associated with future returns controlling for earnings/profitability.
- **Effect/horizon:** ~1-year. Classic anomaly.
- **Data:** balance-sheet accruals from fundamentals.
- **India evidence:** classic is US → needs an India test.
- **Orthogonal:** **YES** — complements the kept low-debt filter ("avoid low-quality names").
- **Failure mode:** longer horizon than 63d; US effect has decayed since publication (crowding).

### 3. Betting-Against-Beta, India-specific — *Betting Against Beta in the Indian Market*
- **Source:** researchgate 270315530 (secondary). https://www.researchgate.net/publication/270315530_Betting_Against_Beta_in_the_Indian_Market
- **Mechanism:** long low-beta / short high-beta; the Indian security-market-line is flat, so low-beta is underpriced.
- **Effect/horizon:** reported to **dominate size, value, and momentum** returns in India.
- **Data:** rolling beta from price.
- **India evidence:** **YES, specifically.**
- **Orthogonal:** partial (low-beta tilts away from high-beta momentum names).
- **⚠️ Overlap tag:** brushes §11 "low-vol blend" KILL — but that kill *blended* low-vol into the trend signal; this is a **standalone long-only low-beta tilt with India-specific evidence**, a different question. Reopen as a separate sleeve/tilt, not a blend.

---

## Bucket 2 — Momentum-quality improvements

### 4. Residual / idiosyncratic momentum — Blitz, Huij & Martens (2011), *Residual Momentum*
- **Source:** SSRN 2319861 (J. Empirical Finance); related replication SSRN 2947044 (secondary). https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2319861 · https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2947044
- **Mechanism:** momentum computed on **multi-factor (Fama-French) residual** returns, stripping systematic factor exposure.
- **Effect/horizon:** ~**2× the Sharpe** of total-return momentum in the literature; persists in developed *and* emerging markets. 6–12m formation.
- **Data:** price + Fama-French factor returns for India (build a rolling residual regression).
- **India evidence:** "persists across emerging markets" (not India-isolated).
- **Orthogonal:** No — it *improves* momentum.
- **⚠️ Overlap tag — the important one:** §11 KILLed *single-beta* residual momentum; this is the **multi-factor residual**, which the repo's `methodology-synthesis` explicitly flagged as the **distinct, untested (L5)** variant. Cleanest "genuinely new construction" reopen. (Note: not in the C4 horse-race.)

### 5. Momentum-crash management / volatility-scaled (dynamic) momentum — Daniel & Moskowitz (2016), *Momentum Crashes*
- **Source:** NBER w20439 (primary; JFE). https://www.nber.org/system/files/working_papers/w20439/w20439.pdf
- **Mechanism:** momentum has rare, large, negatively-skewed crashes after bear markets / in high-vol; **scaling exposure by inverse realized momentum-volatility** manages the crash.
- **Effect/horizon:** dynamic (vol-scaled) momentum roughly doubles the unconditional Sharpe and cuts the worst drawdowns; crashes are partly predictable (occur during market rebounds).
- **Data:** price only (realized vol, market state).
- **India evidence:** US/global classic → needs India test.
- **Orthogonal:** No — risk overlay on the momentum book.
- **⚠️ Overlap tag:** brushes §11 "regime gate" KILL — but that was a **binary** market-timing gate; this is **continuous volatility-scaling of the book** (= `methodology-synthesis` candidate #30, India-VIX size-scaling). **Directly targets the −42% DD weakness** — high relevance.

---

## Bucket 3 — Holding period / exit structure (confirms the Stage-D lead)

### 6. Optimal momentum holding ≈ 3 months; hyperbolic alpha decay
- **Sources:** Quantpedia rebalancing study (secondary, https://quantpedia.com/how-often-should-we-rebalance-equity-factor-portfolios/); hyperbolic-decay arXiv 2512.11913 (secondary, https://arxiv.org/pdf/2512.11913).
- **Mechanism / findings:** momentum is the **fastest-decaying** factor; information-optimal rebalance ≈ **3 months**; cross-sectional factor returns maximize at **12-month formation + 3-month holding**; momentum alpha decays **hyperbolically** α(t)=K/(1+λt) (R²=0.65 > linear 0.51 / exp 0.61, FF 1963-2024).
- **Data:** price.
- **India evidence:** general/US.
- **Implication for the repo:** *validates the ~63-day hold* AND sharpens the **Stage-D "let winners run" tension** — let winners run, but momentum alpha decays fast → there is an optimal give-back point, not "hold forever." Use to set exit-widening bounds, not as a new selection factor.

### 7. India "physical momentum" (inverse-turnover weighting) — NSE-500 study
- **Source:** SAGE 23197145211023001 (primary). https://journals.sagepub.com/doi/abs/10.1177/23197145211023001
- **Mechanism:** momentum weighted by **inverse turnover rate** as a "mass"; physics-analogy momentum.
- **Effect/horizon:** 6-2 month medium-horizon highest monthly mean 4.32% (~51.8% annualized) BUT vol 5.31%, **Sharpe only 0.36**; clear continuation (not reversal) weeks→years.
- **Data:** price + turnover.
- **India evidence:** **YES (NSE-500).**
- **⚠️ Caveat:** profits **concentrated in the loser basket** (bad for long-only — winners weaker), and the headline return is gross/high-vol. Takeaway = the **inverse-turnover weighting** idea, not the strategy.

---

## Bucket 4 — Conviction / position-weighting

### 8. Two-level uncertainty — *When Alpha Breaks: Two-Level Uncertainty for Safe Deployment of Cross-Sectional Stock Rankers*
- **Source:** arXiv 2603.13252 (primary; recent preprint — treat as fresh/unreplicated). https://arxiv.org/abs/2603.13252
- **Mechanism:** translate a ranked signal into weights via (a) a strategy-level regime-trust gate (whether to trade) + (b) a position-level epistemic tail-risk cap.
- **Key counter-intuitive finding:** **inverse-uncertainty sizing DEGRADES performance** (it de-levers your strongest signals — signal strength and uncertainty correlate ~0.6); instead **cap only the most-uncertain names**.
- **Data:** needs an uncertainty estimate (ensemble / ML ranker dispersion).
- **India evidence:** none (method paper).
- **Orthogonal:** sizing-layer — **feeds Stage-C conviction + the ML-ranker idea (C3) directly.**

---

## Out-of-scope / low-confidence (flagged, NOT recommended)
- **Two-week momentum** (arXiv 2505.24250) — short-horizon; overlaps killed fast-rebalance; out of the 63d scope.
- **ESG-loser-outperforms** (same arXiv 2505.24250) — speculative preprint, ESG-policy-regime-specific → LOW confidence, not actionable.
- **Daily momentum in EM is retail-driven** (Xiong et al., Princeton, https://wxiong.mycpanel.princeton.edu/papers/DailyMomentum.pdf) — daily horizon, out of scope for direct use; useful only as *mechanism* support (why momentum works in India = retail noise traders predicting their own future losses).

---

## Ranked shortlist — candidates to pre-register

| # | Candidate | Orthogonal to 200d trend? | Data needed | Why worth a trial |
|---|---|---|---|---|
| **1** | **Vol-scaled / dynamic momentum** (Daniel-Moskowitz) | No (improves mom) | price only | Targets the **−42% DD** directly; continuous-sizing reopen of the killed *binary* regime gate |
| **2** | **Gross profitability / quality overlay** (Hanauer-Lauterbach) | **Yes** | fundamentals (have it) | Strong EM evidence, untested at 63d, ≠ weak ep/bp value |
| **3** | **Multi-factor residual momentum** (Blitz et al.) | No (improves mom) | price + FF India factors | The *genuinely-new* (L5) variant of the killed single-beta residual; ~2× Sharpe in lit |
| **4** | **Accruals / earnings-quality screen** (Sloan) | **Yes** | fundamentals | Orthogonal quality filter; complements kept low-debt screen |
| **5** | **Two-level uncertainty conviction-weighting** (When Alpha Breaks) | **Yes** (sizing) | ML ranker + uncertainty | Feeds Stage-C; "cap the uncertain, don't inverse-vol-weight everything" |
| **6** | **Composite / net share issuance** (Hanauer-Lauterbach) | **Yes** | shares outstanding | Pervasive EM predictor, cheap, untested here |
| **7** | **BAB low-beta tilt, India** (India BAB paper) | Partial | price (beta) | India-specific dominance; standalone tilt, not a blend |
| **8** | **Holding-period / decay calibration** (Quantpedia + hyperbolic) | — (exit) | price | Not a new factor — *sets bounds* for the live Stage-D exit-widening |

**Genuinely orthogonal to the 200-day trend:** #2 (quality), #4 (accruals), #5 (conviction-uncertainty), #6 (issuance), partially #7 (low-beta).
**Momentum improvements (not orthogonal):** #1 (vol-scaled), #3 (residual).
**Exit-structure (no new selection):** #8.

**Two highest-EV, lowest-overlap picks:** **gross-profitability quality (#2)** (orthogonal predictor) and **vol-scaled momentum (#1)** (DD lever) — both PIT-backtestable from data already in the repo.

---

## Source quality ledger (from the harness)
**Primary (yielded claims):** SSRN 3233614 · SSRN 259691 · NBER w20439 · arXiv 2505.24250 · Princeton DailyMomentum · arXiv 2603.13252 · SAGE 23197145211023001.
**Secondary:** SSRN 2947044 (idiosyncratic mom) · quantpedia rebalancing · arXiv 2512.11913 (hyperbolic decay) · researchgate 270315530 (BAB India).
**Returned empty / paywalled ("unreliable" on fetch):** several SSRN abstract pages + paywalled journals (tandfonline, sciencedirect, pm-research, CME/JPM pdf) — not used.

---

## Next steps (for the continuing chat)
1. **Pre-register #1 (vol-scaled momentum) and #2 (gross-profitability quality)** as candidate overlays → run through the Phase-1 harness (paired same-cache deltas, ≥2019 folds, DSR, bootstrap) under the promotion bar.
2. Optionally **re-run the deep-research verify pass** (after the session limit resets at 3am Asia/Calcutta) to get the 3-vote adversarial stamp on these claims — the script is at
   `~/.claude/projects/C--project/.../workflows/scripts/deep-research-wf_85aa7ca3-0e2.js`
   (already model-tiered: scope=sonnet, search/fetch=haiku, verify=sonnet, synth=opus), resume with `resumeFromRunId: "wf_e406ab99-10a"`.
3. Keep the §11 do-not-relitigate discipline: each "overlap tag" above is the *specific* new-evidence condition that justifies the reopen — cite it in the pre-registration.
