# "Concentration is the edge" does not survive an adversarial pass — REFUTED / UNDERPOWERED

**MEASUREMENT + adversarial critique. Zero trials, zero screen-ledger rows** — reads the committed
engine on `corrected_universe()`, no banked labels. Standing counts: **screens 19 · sealed opens 1 ·
n_trials 2** (`diagnostics/research/n_trials.json`, `label_screen_ledger.md`).

Two independent skeptic agents (overfit-skeptic, red-team) were pointed at the slot-count sweep and
the claim "5 names beats 10, concentration is the edge." Both reproduced the arithmetic exactly and
both reject the interpretation. This corrects an overstated claim made in-session and a stale rationale
in a live code comment.

Reproduce the base: `run_bhanushali_weekly_rank.backtest` with `LIVE_DISCIPLINE`/`LIVE_EXIT`/
`LIVE_STALENESS` on `corrected_universe()` → CAGR 27.17 / Sharpe 1.279 / MaxDD −39.49 / 130 trades.

## The claim, and why it fails

| # | attack | result |
|---|---|---|
| 1 | **Is 5-vs-10 resolvable?** | Sharpe gap 1.279−0.930 = **0.348**; block-bootstrap 95% CI **[−0.023, +0.687] straddles zero**, and below the 0.59 dSharpe floor (n_eff≈37). **Not resolvable on this data by any method.** |
| 2 | **Jackknife names** | Drop SUVEN → 1.279 → **0.902** (= the 10-name book). Drop top-3 → 0.600. |
| 3 | **Name concentration** | Top-3 tickers = **42.8%** of total R (threshold 30%). ALKYLAMINE and TRIDENT are **single trades** each. |
| 4 | **Peak or plateau?** | One step off the peak (notion 0.17) drops 9 CAGR pts; surface non-monotone (trough at 7 names). A fitted spike. |
| 5 | **The confound** | `max_notional_pct` varies **per-name bet size**, not clean breadth. The 27→16% gap traces to ONE 2019 trade (SUVEN) sized 2× larger: ₹997k at 20% vs ₹376k at 10%. Top-5 trades = **61%** of the 5-name book's profit. Gross exposure is constant (~85%) across arms, so it is **not** a leverage artifact — it is bigger bets on the fat tail. |
| 6 | **Live regime** | Continuous-slice 2022–26 Sharpe: 5-name **0.95** vs 14-name **1.12** — the ordering **inverts**. Concentration's advantage lives in 2017–21 (where SUVEN and the 2020 +106% land); in live conditions the diversified arm is *better*. |

## The honest conclusions

1. **"Concentration is the edge" is refuted as a resolvable return claim.** The 5-vs-10 difference is
   inside the noise floor, driven by one 2019 moonshot getting a 2× slice and by two bull years
   (2017 +50.6%, 2020 +106.5%; ex-both → 16.9% / 0.888, i.e. the 10-name level). It is not an edge
   that was measured — it is variance from bigger bets on winners that cannot be pre-identified.

2. **My in-session claim that "diversifying halves your returns" was wrong.** At fixed capital, 5 and
   10 names are statistically indistinguishable here, and in the recent regime the diversified book
   was *better*.

3. **Diversifying to ~10 names is a defensible risk choice** with no statistically-established return
   penalty, and it reduces exactly the single-name / single-year fragility attacks 2, 3 and 6 expose.

4. **What survives:** holding *long* (3–5 months) was robust across all 9 years (separate finding).
   The *number of names* has no resolvable optimum on this data — pick it on risk preference.

## Two code-level flags for the owner (not changed here)

- `scripts/run_bhanushali_cron.py:78` asserts "concentration is load-bearing — 4-5 names 1.21 > 7 >
  10 on the 22-26 slice." Under the **current** harness the 2022–26 ordering is the reverse (5-name
  0.95 < 14-name 1.12). The comment's performance claim no longer reproduces.
- `max_notional_pct = 0.20` (the ~5-name cap) is **fine as a risk guardrail** — it was adopted as an
  owner risk preference (`:76-77`), not a proven return lever, and the overfit-skeptic agrees the
  guardrail itself is defensible. Only the retrofitted "it makes more money" narrative fails.

## Method note

This is why the adversarial pass exists. The claim reproduced from the committed pipeline as *real
arithmetic* — but the interpretation was fitting. Both agents ran zero adoption configs; nothing is
promoted, and no count moves. The correct clean breadth experiment (fixed per-name notional, vary
`max_positions`) still conflates breadth with deployment and would need leverage past 10 names — so
the fixed-capital sweep here is the right frame for the owner's actual question, read with the
critique above.
