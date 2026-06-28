---
name: leakage-audit
description: >
  The pre-trust integrity gate that catches the highest-cost defects in this
  engine — bugs that make a backtest look great then collapse on live capital.
  Run BEFORE any cloud backtest of a new feature, label, or pipeline change, and
  before anchoring on any headline number. Trigger words: "leakage", "lookahead",
  "look-ahead bias", "train/serve skew", "offline vs live", "survivorship",
  "purge", "embargo", "walk-forward leak", "is this feature safe", "before I
  trust this backtest", "feature contract", "PIT join", "demerger".
triggers:
  - leakage
  - lookahead
  - look-ahead bias
  - train/serve skew
  - offline vs live
  - survivorship
  - purge
  - embargo
  - walk-forward leak
  - is this feature safe
  - before I trust this backtest
  - feature contract
  - PIT join
  - demerger
---

# Leakage Audit — NiftyQuant Long-Horizon

**Why this skill exists.** Every other failure in a quant engine is recoverable: a
weak signal just earns nothing, a slow scrape just delays research. *Leakage is
different.* It makes a backtest look excellent — high CAGR, high Sharpe, smooth
equity curve — using information the strategy could never have had at decision
time. You promote it, trade real money, and it collapses. For a paid service
making real financial decisions for ~10 users, this is the single most expensive
class of bug. **This skill is the gate you run before trusting any number that
will inform a promotion, a pre-registration, or a live config change.**

It complements two siblings:
- [`skills/backtest-rigor`](../backtest-rigor/SKILL.md) — broader "is this result
  trustworthy" checklist (sample size, multiple-testing, DSR). This skill is the
  *correctness-of-information* deep-dive within that.
- [`skills/data-quality`](../data-quality/SKILL.md) — the OHLCV / corporate-action
  /survivorship data-layer checks. §2 and §5 below hand off to it.

**Automated helper.** The [`flaw-hunter`](../../.claude/agents/flaw-hunter.md) agent
runs this exact hunt over the code (Read/Grep/Bash, cites file:line). Launch it on
any new feature/label/pipeline change; this skill is the manual procedure +
plain-language "why it matters" that backs it up.

---

## 0. When to run this — the gate

Run the full §1–§6 sweep BEFORE:

- Submitting **any cloud backtest** of a new feature, label, or universe change.
- Re-deriving / re-freezing the cfg (Stage B `baseline_v1`, or any heavy-path
  re-derivation per [`docs/LIVE_OVERLAY_PROTOCOL.md`](../../docs/LIVE_OVERLAY_PROTOCOL.md)).
- Anchoring a headline in a commit, a pre-reg, or a verdict.
- Promoting any overlay through the Stage-A harness.

The signal under audit is the long-horizon spine: **`sma200_slope_63` top-15
cross-sectional rank** on the PIT-membership-masked, large+mid (ADV≥5cr), solvent
low-debt universe; frozen cfg in `models/long_horizon/config.json`. The honest
anchor is `research/baseline_v0.json` (gross CAGR 26.1% / Sharpe 1.02 / DD −41.9%,
397-name universe). A leakage bug is anything that would beat that for the wrong
reason.

**The cheap-test mindset.** Each check below has a concrete test that runs in
minutes. Running them before a multi-hour cloud backtest is always the better
trade — a leaked result wastes the compute *and* risks a bad promotion.

---

## 1. LOOKAHEAD — features use only data at or before t

**What it is (plain language).** A feature is a number the strategy knows *on the
day it decides*. If that number secretly peeks at tomorrow's price, the backtest
"predicts" the future and looks brilliant. Live, the future isn't there yet, so
the edge evaporates.

**The rule for this engine.** A *feature* at bar `i` may use only `close[..i]`
(backward-only). A *label/target* may use the future window `[i+1, i+h]` — that's
what a label is, and it's allowed *only* as a training target, never fed back in
as a feature. (`long_horizon/data/labels.py` is correct by construction: `fwd_*`,
MFE, MAE all NaN the trailing `h` bars.)

**How to test it HERE:**

1. **Backward-rolling check.** Every indicator in
   `src/data/data_store.py::_compute_stock_features` must use trailing windows.
   `sma200_slope_63` (data_store.py ~L728–738) is
   `sma200[i] / sma200[i-63] - 1` — both points are ≤ `i`. Good. Any new feature
   must follow this `.shift(+k)` / trailing-window pattern. **A `.shift(-k)`,
   a centered window, or `[i+1:]` slice in a feature is a P0 bug.** (Precedent:
   the dip_count centered-convolution bug, F4/#147.)
2. **The truncation test (the definitive lookahead probe).** Compute the feature
   on the full series, then recompute it on the series *truncated at date d* (drop
   all bars after d). The feature value at date d must be **byte-identical** in
   both runs. If truncating the future changes a past value, the feature is
   peeking. Run this on `sma200_slope_63` and on any new feature for ~10 random
   `(ticker, d)` pairs.
3. **No `fwd_*` in the feature set.** Grep the columns actually fed to the ranker
   /model — confirm no `fwd_`, `target`, MFE/MAE, or `_label` column leaked in.

**Fix:** rewrite the feature with trailing windows only; if it genuinely needs a
forward window it is a label, not a feature.

---

## 2. PIT JOINS — fundamentals merge strictly-before, CA-correct

**What it is.** Value/quality factors (E/P, ROE, D/E) come from filings published
*weeks after* the period they describe. If you join a quarter's fundamentals to a
date *before* the market could have seen them, you're trading on unpublished
information.

**How it's done HERE (the correct pattern).** `long_horizon/data/sheets.py::
_value_quality_series` joins fundamentals with:

```python
pd.merge_asof(left, right, left_on="date", right_on="avail",
              direction="backward", allow_exact_matches=False)  # avail < date, STRICT
```

`allow_exact_matches=False` is load-bearing: it enforces `available_date STRICTLY
before decision_date`. Same semantics as `fundamentals_pit.point_in_time_row`,
vectorized per ticker. The dates must be sorted ascending (the caller sorts) so
the join is row-aligned with no reordering.

**How to test it HERE:**
1. Confirm any new fundamentals join uses `direction="backward"` **and**
   `allow_exact_matches=False`. An exact-match-allowed join leaks same-day filings.
2. Confirm the merge key is the **availability date** (`avail` = when the figure
   became public), never the fiscal period-end.
3. Confirm dtype normalization (`datetime64[ns]` on both sides) — a silent dtype
   mismatch makes `merge_asof` raise or misalign.

**The W-01 demerger-as-split correctness lesson (read this).** PIT-correctness is
not only about *timing* — it's about *price-series correctness*. VEDL demerged its
metals business: raw close 773.6 → 271.55 in one session (−64.9%). The old cleaner
treated any ≥50% drop as an unadjusted split and back-scaled all pre-event prices
by 0.351 — **fabricating** `sma200_slope_63` from a real +2.16 to +24.94 (rank
3/495). A demerger value *left the company permanently*; back-adjusting invents a
trend that never existed. The live cron now demerger-guards (`long_horizon_cron.py`
~L73, `DEMERGER_LOOKBACK_BARS=263`) and NaNs the slope until clean post-event bars
accumulate. **For any held/ranked name with a >50% single-session drop, classify
split vs demerger before trusting its trend feature** — hand off to
[`skills/data-quality §1.2`](../data-quality/SKILL.md).

---

## 3. TRAIN/SERVE SKEW — offline build == live build

**What it is.** The backtest computes features one way (offline pickle builder);
the live cron computes them another way. If the two diverge by even a default
value or a column order, your live signal is not the signal you validated — the
backtest is measuring a different strategy than the one trading.

**The single source of truth.** Both paths read column lists + defaults from
`src/data/feature_enrichment.py` (`ENRICH_MACRO_COLS`, `ENRICH_SECTOR_COLS`,
`MACRO_DEFAULTS`, `SECTOR_DEFAULTS`). Built-in `assert`s in that file already
enforce `MACRO_DEFAULTS.keys() == ENRICH_MACRO_COLS` (etc.). **Adding a macro/
sector column means editing THAT ONE FILE — never re-introduce a hardcoded column
list or default in a caller** (the historical #1 skew hazard; AUD-014/015 were
exactly this).

**The two paths that MUST agree:**
- Offline: `data_store.compute_all_features` / `enrich_with_layers`.
- Live: `src/runners/long_horizon_cron.py` (calls `ds.compute_all_features(
  persist=False)` then the shared `ohlc_panel` helpers).

**How to test it HERE (the 10-pair parity check):**
1. Pick 10 random `(ticker, date)` pairs.
2. Compute the feature row offline (`compute_all_features`) and as the live cron
   would (same call path).
3. Diff every feature value + default. **Any mismatch is train/serve skew → P0.**
   Watch especially for a feature that defaults differently when data is missing
   (a macro col vs sector col mix-up — the `nifty_ema_trend` MACRO-vs-SECTOR bug).

**Fix:** route both paths through `feature_enrichment.py`; never branch the build.

---

## 4. TRAIN/TEST LEAKAGE — purge + embargo, re-derive per fold

**What it is.** In walk-forward, the test period is "the future." If a training
observation's *forward label window* overlaps the test block, the model trained on
the answer. And params re-derived using the whole series (including test) are
overfit to data they shouldn't have seen.

**How it's done HERE:**
- `src/validation/walk_forward.py` — expanding-window folds (7-yr initial train,
  annual step, disjoint future test). Train window grows; never trains on data
  after the test period.
- `src/validation/cpcv.py` — Combinatorial Purged CV with **purge** (drop train
  obs whose label window `[j, j+horizon]` overlaps a test block) and **embargo**
  (drop obs immediately after each test block, killing serial-correlation leak).
  The distribution of OOS paths feeds PBO / Deflated Sharpe
  (`validation.overfitting`).

**How to test it HERE:**
1. **Embargo ≥ horizon.** For the 63-trading-day hold, the label looks ~63 bars
   forward — set `embargo >= horizon` (cpcv.py docstring: "Set `embargo >=
   horizon` for full two-sided purging"). **An `embargo=0` default silently
   leaks** (precedent: V2/AUD-006, `run_overfitting` defaulted embargo=0). Confirm
   the actual call site, not just the function's existence.
2. **Re-derive per fold on TRAIN ONLY.** The cfg (stop_atr_mult, target_pct, etc.)
   must be re-derived inside each fold using only that fold's training slice — the
   sanctioned re-derivation path per `LIVE_OVERLAY_PROTOCOL.md`. A cfg derived once
   on the full history and then "walk-forward tested" is not a walk-forward — it's
   in-sample dressed up. (This is what separates the honest `baseline_v0` frozen-cfg
   arm from a re-derived-every-fold result.)
3. Confirm the fold-pass gate (≥60%), positive 2022–2026 sub-period, and bootstrap
   CI-excludes-0 are computed on the purged/embargoed splits — not the raw timeline.

**Fix:** pass `embargo>=horizon`; move cfg derivation inside the per-fold train loop.

---

## 5. SURVIVORSHIP — delisted names present for backtest dates

**What it is.** If your universe is *today's* surviving Nifty-500 members applied
to past dates, you've quietly deleted every company that went bankrupt or got
delisted. The backtest only ever picks from winners-that-lasted → inflated CAGR
**and** suppressed drawdown (the losers that would have hit stops simply aren't
there).

**How it's handled HERE:**
- Live + backtest mask to **point-in-time index membership**
  (`src/data/index_membership.py::filter_features_dict` + `current_members`;
  `data/nifty500_membership.csv`). A name counts only on dates it was actually a
  member (cron Stage 2, the §10.4 survivorship/look-ahead fix).
- **The survivor-only cache trap (AUD-007/F2).** `data/features.pkl` can silently
  become survivor-only when a background job rebuilds it from current names. A
  membership mask over a survivor-only cache still leaks — the delisted names were
  never in the cache to begin with. The cron logs `AUD-007` when a current member
  is absent from the scan set.
- **The recovery this enables.** Stage B's correction adds **~284 delisted names**
  to re-derive `baseline_v1`. Expect this to move the headline **DOWN** —
  survivor-only data flatters returns (`docs/ROADMAP.md` Stage B, L75/L484). A
  *lower* corrected number is the honest one; treat a result that *doesn't* drop
  after adding delisted names as suspicious.

**How to test it HERE:**
1. Confirm membership masking is applied (`filter_features_dict`) on the exact
   feature dict the backtest scores — not a later copy.
2. Confirm the underlying cache contains delisted names for the backtest dates
   (spot-check 2–3 known delistings appear with PIT OHLCV). If absent → survivor-
   only cache → rebuild from `data/ohlcv.pkl` via `load_ohlcv → compute_all_features
   → enrich_with_layers` before trusting the run. Hand off to
   [`skills/data-quality`](../data-quality/SKILL.md).
3. For any "OOS on unseen names" claim, confirm the manipulation/penny screen ran
   (`diagnostics/oos_manipulation_screen.py`) — unscreened smallcap OOS can be
   survivor-only or manipulated → false confidence.

---

## 6. FEATURE-CONTRACT violations — no silent column drift

**What it is.** The ranker/model expects a fixed feature set in a fixed order.
Adding, removing, or reordering features without acknowledging it produces silently
miscalibrated output — the model reads column N expecting feature A but gets B.

**How to test it HERE:**
1. New macro/sector columns enter via `feature_enrichment.py` ONLY (see §3); the
   built-in `assert`s catch a default/column mismatch at import.
2. A new *available* column must not silently enter the scored feature set — adding
   a ranked/modeled feature is a deliberate, retrain-/re-derive-gated change, not a
   side effect of computing it. Confirm the panel composer
   (`sheets.py::compose_panel`, `keep` list) carries exactly the intended columns.
3. If a label horizon or the signal column changes, the frozen cfg / golden master
   must be regenerated in the *same* PR (`diagnostics.build_golden_fixture`).

---

## Checklist — run before any cloud backtest / promotion

```
[ ] §1 LOOKAHEAD
    [ ] New/changed features use trailing windows only (no .shift(-k), no centered, no [i+1:])
    [ ] Truncation test passes on 10 random (ticker,date) — past value unchanged by dropping future
    [ ] No fwd_*/target/MFE/MAE/_label column in the scored feature set
[ ] §2 PIT JOINS
    [ ] Fundamentals join is merge_asof(direction="backward", allow_exact_matches=False)
    [ ] Merge key = availability date, not fiscal period-end; dtypes normalized to ns
    [ ] Any >50% single-session drop classified split-vs-demerger (W-01) before trusting its trend
[ ] §3 TRAIN/SERVE SKEW
    [ ] Columns/defaults sourced ONLY from feature_enrichment.py (no hardcoded list in a caller)
    [ ] 10-pair offline-vs-live parity diff = identical values + defaults
[ ] §4 TRAIN/TEST LEAKAGE
    [ ] embargo >= horizon at the actual call site (not just defined) — purge applied
    [ ] cfg re-derived per fold on TRAIN ONLY (not once on full history)
    [ ] fold-pass ≥60% / 2022–2026 positive / bootstrap CI excludes 0 on purged splits
[ ] §5 SURVIVORSHIP
    [ ] PIT membership mask applied to the exact scored feature dict
    [ ] Cache contains delisted names for backtest dates (not survivor-only — AUD-007)
    [ ] Manipulation/penny screen ran for any unseen-names OOS claim
[ ] §6 FEATURE-CONTRACT
    [ ] New columns via feature_enrichment.py only; no silent entry into the scored set
    [ ] Golden master / frozen cfg regenerated in-PR if signal/horizon/contract changed
[ ] flaw-hunter agent run on the change → "clean — verified X/Y/Z" or P0/P1 fixed
[ ] Result reconciled against research/baseline_v0.json (a too-good number is guilty until cleared)
```

**Verdict rule.** If any §1–§6 check fails, the backtest number is **not
trustworthy** — fix the leak and re-run before it informs any decision. A clean
sweep is logged the same way a finding is, per
[`skills/research-log`](../research-log/SKILL.md): state what you verified
("lookahead clean via truncation test on X; parity confirmed on 10 pairs;
embargo=63 at call site") — a confident, evidenced "clean" is as valuable as a
bug found.
