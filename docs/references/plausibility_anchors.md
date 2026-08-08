# Plausibility anchors — what a number in this programme is allowed to look like

Every figure below is read from a committed artifact in this repo, and the artifact is named. This
file exists so that "does that number look right?" is answered against a source rather than against
a recollection — including the model's own. Nothing here is remembered; if a value disagrees with
its cited artifact, the artifact is right and this file is stale.

**Regenerate the values by reading the sources, not by trusting this page.** It is a map of where
the anchors live as much as a copy of them.

---

## 1. The pinned anchor of record — `baseline_v1`

Source: [`research/baseline_v1.json`](../../research/baseline_v1.json) · frozen cfg
`models/long_horizon/config.json` · dataset pin `dataset-pin-20260701`, ohlcv sha256 `f8625a8f…`
· window 2017-01-01 → 2026-06-30 · 710 names with data, 225 distinct names traded.

| | gross |
|---|---|
| Sharpe | **0.667** |
| CAGR | **15.46%** |
| Max drawdown | **−46.26%** |
| Calmar | 0.33 |
| Trades | 1,279 |
| Win rate | 60.36% |

After-tax CAGR 12.76%, annualised vol 27.1% (stated in `CLAUDE.md`).

Robustness, same file: block-bootstrap 95% Sharpe CI **[−0.022, 1.428]** at block size 63, n_eff 34
windows; PSR(>0) = 97.4%; MinTRL(95%) = 6.2 years against ~9.5 years of data; DSR 0.287 at 82 trials.

Read that CI before quoting the Sharpe. The point estimate is 0.667 and the 95% interval very nearly
touches zero: the base is *certifiable* (PSR), not *precise*. Any claim that rests on distinguishing
0.667 from, say, 0.85 is not supported by this data.

## 2. The cautionary anchor — `baseline_v0`

Same file, `anchor_baseline_v0`: CAGR **26.11%**, Sharpe **1.0155**.

This is not a better result. It is the same engine on a different price vintage — selection, win
rate and the golden master all matched, so the entire 10.65pp CAGR gap is OHLCV vintage. Unpinned
runs drift 1–2pp run-to-run (14.2 / 15.6 / 16.25 observed). **A headline Sharpe near 1.0 for this
strategy is the shape of a vintage-favourable in-sample number, not of an improvement.**

## 3. Resolution floor — what this data can and cannot decide

Source: [`diagnostics/research/n_trials.json`](../../diagnostics/research/n_trials.json), measured
2026-08-07.

> n_eff = **37 independent 63-day windows** on 2017–2026 Indian daily equity data ⇒ dSharpe
> confidence half-width **0.59**.

**No edge below roughly 0.6 Sharpe is resolvable on this data by any method at any trial count.**
This is the single most useful plausibility check in the programme: before asking whether a ΔSharpe
of 0.1 is real, note that it is a quarter of the measurement error. Resetting the trial counter
lowers a bar; it does not sharpen the instrument.

## 4. Cost stack — what "net" has to include

Source: [`config.py`](../../config.py).

| component | value |
|---|---|
| Brokerage | 0.03% per leg (`BROKERAGE_PCT = 0.0003`) |
| STT (delivery) | 0.10% **per leg — buy *and* sell** (`STT_PCT = 0.001`) |
| Slippage | 0.05% large cap · **0.22% mid cap** · 0.40% small cap (`SLIPPAGE`) |
| Impact | `IMPACT_ETA · σ_daily · √(position_value / adv_rupees)`, η = 1.0 |

A gross number compared against a net baseline is not a comparison. Delivery STT charged once
instead of twice roughly halves the cost of the strategy and is an easy, invisible error.

## 5. Sub-period gate — the correct base

Source: `CLAUDE.md`, "Reproduce-before-trust".

| 2022–26 base | Sharpe | MaxDD |
|---|---|---|
| **Correct** — continuous slice of one full run | **0.570** | **−46.3%** |
| Phantom — fresh-capital re-run from the window start | 0.762 | −40% |

The phantom gate produced false KILLs (it wrongly downgraded 0071). If a sub-period number is
suspiciously kinder than the full-period one, suspect the re-run before believing the result.

## 6. Swing book (Bhanushali / the live model) — separate anchors

Source: [`research/overlay_registry.md`](../../research/overlay_registry.md), frozen 0094 rows.

Frozen 0094: Sharpe **~1.132**, CAGR **24.7%**, MaxDD **−42.4%**, 2022–26 slice **+1.19**.
Touch branch 2022–26 slice **1.29**, DD −34.8%, CAGR 21.2%; box branch Sharpe 1.04 / CAGR 21.0%
([`research/CONTEXT_ROUTER_SPEC.md`](../../research/CONTEXT_ROUTER_SPEC.md)).

Both stop directions are KILLed (tighten 0105, widen 0106), and the entry side is exhausted — every
perturbation of frozen 0094 deflates. **A new swing variant that beats ~1.13 in-sample is a defect
signal, not a discovery**, unless it comes with a mechanism the registry has not already killed.

## 7. Known bias, unpriced

The pinned `data/ohlcv.pkl` is **survivor-only**: 103 of 813 PIT members are missing. Finding 0025
measured the bias and found it **scales with holding period** (−0.04 Sharpe on tight-stop configs,
−0.18 on wide-stop swing configs). The 63-day-hold `baseline_v1` 0.667 is exposed in the same
direction and its corrected re-run is pending. Any comparison of a corrected-universe result against
`baseline_v1` is comparing across that bias — say so.

---

## 8. External literature — **NOT POPULATED**

See [`external_literature.md`](external_literature.md). Until that file is filled in by the owner,
**this repo has no committed external band for Indian midcap momentum returns or drawdowns**, and no
session may state one as fact. The internal anchors above are reproducible; a remembered published
range is not, and stating one with false confidence is precisely the failure this file exists to
prevent.

## How to use these

1. Put the new number beside the anchor that governs it.
2. If it is *better*, treat it as a defect until explained. Every expensive bug in this programme
   presented as good news.
3. Name the difference that would explain the gap — vintage, universe correction, gross-vs-net,
   sub-period slicing, holding period, survivorship — and check that one specifically.
4. If nothing explains it, do not write it up yet.
