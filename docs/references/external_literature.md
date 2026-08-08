# External literature — published bands for Indian equity momentum

**Status: POPULATED 2026-08-08** from the owner's research compendia (two documents, bibliographies
reproduced below). Before this date the file was a deliberate empty stub, because a band quoted from
memory is unciteable and this programme's central rule is that a number informing a decision must be
reproducible from something committed.

Read this **with** [`plausibility_anchors.md`](plausibility_anchors.md), not instead of it. The
internal anchors are what our engine actually produces; these are what the outside world reports for
the same kind of strategy. The useful signal is the **gap between them**, and the last column below —
what differs, and which direction it should push — is the part that does the work.

---

## 1. The headline band

| Claim | Value | Source |
|---|---|---|
| Durable net CAGR, Indian midcap momentum | **14–18%** | Compendium §TL;DR and §1.2; "low-20s only for the best regime-managed, vol-targeted, quality-filtered combinations" |
| Expected max drawdown | **−50% to −70%** | Compendium §1; §7 "plan for -50% to -70%" |
| Pure momentum, 18.5y NSE, survivorship-corrected | 15.23% gross / **14.01% net**, MaxDD **−70.53%**, Sharpe 0.58 | BacktestIndia (T. Desai, guided by Prof. Mayank Joshipura, NMIMS), Dec 2006–Jun 2025, top-200 universe, 1,700+ names incl. delisted |
| + scaled-turnover quality filter | 19.47% gross / **17.95% net**, MaxDD **−61.70%**, Sharpe 0.86 | same study |
| Low-vol variant | 12.38% net, MaxDD −44.55% | same study |
| Nifty 50 over the same window | 10.42% | same study |

**The 30–40% figures are artifacts.** The compendium attributes them to bull-window slices (2007
+87.5%, 2009 +81.8%, 2021 +52.6%), survivorship-biased universes, gross-of-cost backtests, or
leverage. Treat any such number as refuted on arrival.

## 2. The band for OUR specific configurations

| Our study | Its published analogue | Published band | Source |
|---|---|---|---|
| **0001** — NSE Normalized Momentum Score, MID band, top-30, monthly, rank buffer | Strategy B′ "Nifty Midcap150 Momentum 50, accelerated to monthly" | **~15–18% net CAGR** (gross higher, "largely surrendered to ~20% STCG"), **MaxDD 55–65%** | Swing compendium, Strategy B and comparison table |
| The swing book (weekly rotation, top-N, keep-buffer) | Strategy C "Weekly rotational momentum, Mi-series style" | **~14–18% net CAGR**, MaxDD 30–45% *with a cash regime* | Swing compendium, Strategy C |
| **baseline_v1** — long-horizon 63d momentum | pure cross-sectional momentum | 14% net, −70% DD | BacktestIndia |

## 3. Survivorship — the number that explains most gaps

- Overstatement of returns: **~1–4pp/yr** generally, larger in extreme small-caps; the compendium
  calls a 20–25% overstatement "a plausible upper bound … not a central estimate."
- **Understatement of drawdown: ~14 percentage points.**
- ~24% of the 2015 top-500 Indian stocks are invisible to a naive current-listing fetch
  (`backtest-bias`, PyPI).

### ⚠ The 14pp does NOT transfer to our books — corrected 2026-08-09

An earlier version of this section stated that survivorship explained 0001's shallow drawdown
(−37.2% + 14pp ≈ −51%, back inside the band). **That was wrong on two counts and is retracted.**

1. **Study 0001 was already survivorship-corrected.** `pipelines/research/run_0001_xsec_momentum.py:115`
   calls `corrected_universe()` (`scripts/run_bhanushali_path1.py:26`), which merges the pinned cache
   with `data/ohlcv_backfill.pkl` and `data/delisted_alias_map.json`. It has done so since the study's
   first commit. The published 21.73 / 1.130 / −37.17 was never a survivor-only number.
2. **Measured on this book, survivorship is worth ~1.5pp of drawdown, not 14pp** — survivor-only
   21.37% / 1.121 / −35.70% against the corrected run of record 21.73% / 1.130 / −37.17%. The
   correction slightly *raised* CAGR and Sharpe.

**Why the literature's figure is an order of magnitude larger here, and it is not a contradiction:**
momentum ranking with a rank-45 buffer ejects failing names before they die, so the book never owns
the corpse. The same correction moves the **passive** benchmark −47.68% → −52.51%, a **−4.83pp**
swing, 3.3× the book's. Passive owns what momentum has already sold. This is consistent with finding
0025's measured result that the bias **scales with holding period** — 0001's effective hold is 72.5
days, far below the wide-stop swing configurations where 0025 measured −0.18 Sharpe.

**Take the 14pp as what it is: a figure for buy-and-hold-style exposure to a survivor-biased
universe.** It is not a correction to apply to a fast-rotating ranked book, and applying it was the
error above. Our own measurement governs.

*Reproduction status: the 1.5pp differential currently exists only as a transcript number. It is not
citeable until the `--survivor-only` switch specified in `docs/PLAN_2026Q3_STRATEGY.md` §2.1 is
committed and the arm re-run from the pipeline.*

## 4. Cost and tax, for checking that "net" means net

STT **0.1% per leg, delivery, both buy and sell**; exchange transaction charges ~0.003%; SEBI
turnover fee 0.0001%; GST 18% on (brokerage + exchange charges); stamp duty 0.015% buy-side; DP
charges per-scrip on sell. BacktestIndia models ~**0.11% per trade all-in plus 0.05% slippage**;
midcap slippage 10–25 bps/side calm, 50–100+ bps for small/illiquid, widening in stress.

**STCG 20%** (holdings <12 months — i.e. essentially all swing and monthly-rebalanced trades),
**LTCG 12.5%** above ₹1.25 lakh. The compendium is explicit that tax drag of ~1.5–2%+/yr belongs
*inside* the compounding, not subtracted at the end.

## 5. What each published number differs from ours in — read before comparing

| Their setup | Ours | Direction it should push |
|---|---|---|
| Top-200 or Nifty-500 universe | MID band (turnover rank 101–250), or the swing funnel | narrower universe ⇒ higher idiosyncratic risk, usually deeper DD |
| Survivorship-corrected (incl. delisted) | **survivor-only pin** | ours flattered: returns high, drawdown shallow |
| Semi-annual or monthly rebalance | monthly (0001) / weekly (swing) | faster ⇒ more STCG, more cost |
| Gross of tax in index figures | after-tax reported separately | index headlines not comparable to our net |
| Price-return (BacktestIndia excludes dividends) | ours also excludes | comparable |
| Dec 2006–Jun 2025 | 2017-01 → 2026-06 | ours misses 2008; theirs includes it ⇒ theirs should show deeper DD |

That last row matters and cuts the other way: **our window excludes the GFC entirely**, so part of
the drawdown gap is sample period, not bias. Do not attribute the whole −18pp to survivorship
without checking.

## 6. Ideas in these documents that this programme has NOT tested

Cross-referenced against `research/overlay_registry.md` and `research/findings/` on 2026-08-08:

**⚠ Methodological correction, 2026-08-09.** An earlier version of this table read registry hits as
proof of "untested". **Registry hits count STUDIES RUN, not code present.** Two of the four rows
below were wrong on that basis. Check the source tree before calling anything new.

| Idea | Actual status |
|---|---|
| **Clenow volatility-adjusted slope** — `exp(slope of ln-price regression over 90d)^250 − 1`, × R² | **The code already exists**: `nq/signals/__init__.py:132` `clenow_score`, `:166` `above_sma`, `:173` `max_gap`, with four tests at `tests/test_signals.py:224-266` including PIT truncation. Committed in `4b528ca` and **never wired into a study** — which is why the registry is empty. The gap is wiring and a head-to-head, not implementation. |
| **Turnover / liquidity bucketing** — the claimed low-turnover 19.43% vs high-turnover 8.51% | **Already measured here, and it does not replicate.** `research/findings/0136-universe-buckets.md` ran PIT turnover buckets per date: equal-weight buy-and-hold earns **15.80% / 15.40% / 15.59%** across LARGE / MID / SMALL — within 0.4pp, not 10.9pp. Caveats: measured on the Supertrend+Pivot book, not 0001, and its absolutes were withdrawn by 0138 (relative rankings survive). |
| **…and the two external claims contradict each other** | BacktestIndia says *low* turnover wins; Medhat–Schmeling say high turnover ⇒ momentum, low turnover ⇒ reversal. For a monthly momentum book at 63d these predict **opposite** signs. The compendium presents them as mutually supporting; they are not. Our one internal measurement — `research/eng-02-membership-proxy.md`, where names admitted at the bottom edge of the turnover band earn **+2.44pp more forward-63d** — sides with Medhat–Schmeling and *against* BacktestIndia. Any test must be a direction-agnostic quintile map, never a confirmation. |
| **Scaled-turnover anti-speculation gate** (monthly traded value ÷ mcap) | **Computable — the "market cap isn't reconstructable" note at `pipelines/build/build_ff_india_factors.py:10-13` is stale.** `shares = net_profit / eps_ttm` from `data/fundamentals_pit_depth.pkl` (653 names, 98.4% of rows). And mcap is not even needed: `ΣPV / PS = ΣV / S`, so **scaled turnover = volume ÷ shares outstanding** and price cancels. Measured near-orthogonal to rupee-turnover rank (Spearman ~0.21), so it is a genuinely new instrument. PIT coverage on MID name-days: **85.8%**, and the missingness is not random. |
| **Sector exposure caps** (30–35%) | Untested as risk control. O-004 killed sector *selection*, a different thing. |

**Not reproducible here at all:** the claim that the scaled-turnover gate flagged DHFL and YES Bank
12–24 months early. DHFL is absent from the pinned OHLCV — the pin deletes exactly the population
the gate exists to catch.

Already closed here, and the documents do not overturn them: 52-week-high as a ranker (0079 — IC is
real, does not convert to portfolio Sharpe), vol-targeting on the swing book (0095, ΔSharpe −0.398),
RSI/reversal entries (0020/0022/0024, triple-killed), regime-as-entry-gate (O-001), PEAD (0128 —
drift measured real at +6.645%, closed on differentiation, and re-openable).

## 7. Sources

Both documents are research compendia prepared for the owner. Primary works they cite, which are
the actual authorities:

Jegadeesh & Titman (1993) *JF* 48(1):65–91 · George & Hwang (2004) *JF* 59(5):2145–2176 ·
Barroso & Santa-Clara (2015) *JFE* 116:111–120 · Daniel & Moskowitz (2016) *JFE* 122:221–247 ·
Medhat & Schmeling (2022) *RFS* 35(3):1480–1526 · Bailey & López de Prado (2014) *JPM* 40(5):94–107 ·
Agarwalla, Jacob & Varma (IIMA four-factor, WML 21.9%/yr 1994–2014, SSRN 2334482) ·
Raju (2023) 52-week-high India, SSRN 4587697 · Harshita, Singh & Yadav (2018) PEAD India ·
Ranse, survivorship in NIFTY Smallcap 250, SSRN 5833162 · NSE Indices Nifty Midcap150 Momentum 50
methodology and whitepaper · Clenow, *Stocks on the Move* (2015) · BacktestIndia 18.5-year NSE study.

**Caveat carried from the compendia themselves:** the NSE Midcap150 Momentum 50 index was launched
2022-08-16 with history backfilled to a 2005 base, so its 20.4% is partly synthetic and gross of
cost and tax. The Clenow India test was explicitly **not** survivorship-corrected and its author
called the results "too unreal." Vendor figures (Weekend Investing, smallcase) are self-reported over
a 2016-onward bull window. None of these is an anchor; they are context.
