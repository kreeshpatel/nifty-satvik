---
name: data-quality
description: >
  OHLCV, PIT membership, and corporate-action integrity checks for the
  NiftyQuant long-horizon pipeline. Use when the topic involves "data
  integrity", "ohlcv check", "split", "demerger", "corporate action",
  "survivorship", "bad tick", "stale data", "fundamentals coverage",
  "PIT membership", or "data audit". Run this skill before any data-layer
  change, cache rebuild, or before standing up a new research layer.
triggers:
  - data integrity
  - ohlcv check
  - split
  - demerger
  - corporate action
  - survivorship
  - bad tick
  - stale data
  - fundamentals coverage
  - PIT membership
  - data audit
---

# Data Quality Skill — NiftyQuant Long-Horizon

**Attribution**: Adapted from `claude-trading-skills/skills/data-quality-checker/SKILL.md`
(MIT) and `finance_skills/plugins/client-operations/skills/corporate-actions/SKILL.md`
(MIT). Both are advisory/document-scanning tools for US markets. The principles
(multi-source validation, CA-type awareness, PIT semantics) are ported and made
concrete for our NSE/yfinance/Screener stack. The implementation below replaces
their generic CLI patterns with the project's actual scan tooling and known failure
modes discovered in the Phase-1 wiring audit (2026-06-27, `long_horizon/audit/`).

---

## 0. When to run this skill

Run every check in §1 before:

- Rebuilding the OHLCV cache (`results/ohlcv_cache_lh.json` / `data/ohlcv.pkl`)
- Adding or replacing a fundamentals scrape (`data/fundamentals_pit_screener.pkl`)
- Updating the PIT membership file (`data/nifty500_membership.csv`)
- Promoting a new backtest baseline or cloud re-derivation
- Any time `clean_ohlcv_for_features` or `ohlcv_incremental.py` is modified
- After a demerger, bonus issue, or rights offering announcement for a held/ranked name

Do not run raw OHLCV scans alone and call the pipeline clean. The raw cache is
pre-cleaning; the model trains on the CLEANED series. Run the scan with
`--source cleaned` for the most relevant picture (see §1.1).

---

## 1. The four check tiers

### 1.1 OHLCV structural integrity — `dv_ohlcv_integrity.py`

**Tool**: `diagnostics/dv_ohlcv_integrity.py`

Three source modes — run all three on a cache rebuild:

```bash
# 1. Raw per-symbol CSV cache (legacy):
python -m diagnostics.dv_ohlcv_integrity --source csv

# 2. Live incremental JSON cache (the cache the cron uses):
python -m diagnostics.dv_ohlcv_integrity --source json

# 3. CLEANED series (what the model actually trains on) — most important:
python -m diagnostics.dv_ohlcv_integrity --source cleaned --fail-on-structural
```

The `--fail-on-structural` flag exits 1 if any hard corruption survives cleaning.
Wire it as a CI gate after cache rebuilds.

**What it detects**:

| Check | Flag in output | Threshold | Action |
|---|---|---|---|
| High < Low | `high_lt_low` | any | STOP — structural corruption |
| Close/Open outside [L,H] | `close_open_outside_hl` | any | STOP |
| Non-positive or NaN prices | `nonpositive_px` / `nan_close` | any | STOP |
| Duplicate dates | `duplicate_dates` | any | STOP |
| Unsorted dates | `unsorted_dates` | any | STOP |
| >+60% single-session up | `jump_up_gt60pct` | n, worst_pct | Investigate — likely unadjusted split or bonus (see §2) |
| >−45% single-session down | `jump_down_gt45pct` | n, worst_pct | Investigate — likely demerger/spin-off (see §2) |
| Staleness | `last_date_distribution` | varies | Flag if any name's last bar > 5 trading days old |

Output is written to `diagnostics/data/dv_ohlcv_integrity.json`.

**Limits of this scan**: the jump thresholds (+60%/−45%) were chosen to catch
the MOTILALOFS split (1211→307) and the VEDL demerger (773→272). Sub-threshold
demergers (TRENT −33%, IEX −30%, INDUSINDBK −27%) pass silently today because
their negative slopes are filtered out by the cross-sectional rank. Lower
`DOWN_JUMP` to `−0.25` in `dv_ohlcv_integrity.py` to surface them (W-17, open).

---

### 1.2 Corporate-action classification — demergers vs splits

This is the most dangerous data failure mode in this pipeline, confirmed by W-01.

**The VEDL bug (2026-04-29)**:
- VEDL (Vedanta) demerged its metals business. Raw close: 773.6 → 271.55 on a
  single session (−64.9%).
- `clean_ohlcv_for_features` saw a >50% one-session drop and applied the
  heuristic: treat it as an unadjusted split, scale all pre-event OHLC by
  the factor (271.55/773.6 = 0.351).
- Result: pre-event prices multiplied by 0.351 → sma200_slope_63 fabricated
  from real +2.16 to +24.94 → rank 3/495.
- VEDL was blocked TODAY only by a coincidental solvency fail (D/E 2.22). That
  D/E value rolls to 0.56 on the next Screener scrape → VEDL becomes a live BUY
  on fabricated signal.

**Classification rule** (from `finance_skills` corporate-actions skill, adapted):

| CA type | Raw price move | Adjustment policy |
|---|---|---|
| Forward split / bonus issue | Large drop (>50%) that IS split-adjusted | Back-adjust pre-event OHLC by ratio → feature math is correct |
| Demerger / spin-off | Large drop (>50%) that is NOT a split | Do NOT back-adjust — the subsidiary value left the parent permanently. Back-adjusting fabricates an artificial trend. |
| Bad tick | Large move that REVERSES >=50% next bar | Drop the bar entirely — `clean_ohlcv_for_features` step 4 |

**How to distinguish a split from a demerger** (CA-type lookup, not heuristic):

```python
import yfinance as yf
t = yf.Ticker("VEDL.NS")
# actions returns a DataFrame with 'Stock Splits' and 'Dividends' columns
print(t.actions)  # a real split appears as a non-zero 'Stock Splits' entry on the date
```

If the date has a `Stock Splits` > 0 → back-adjust (split).
If the date has `Stock Splits == 0` → quarantine (demerger).

**Current live guard (W-01, Phase-1 fix, 2026-06-27)**:

`_demerger_suspect_names()` in `long_horizon_cron.py` detects names whose RAW
close (pre-cleaning, from `ds.ohlcv`) has a ≥50% single-session drop within
the last `DEMERGER_LOOKBACK_BARS=263` bars and quarantines them from new entry
signals. This is an emergency stop, not the root fix.

**Root fix (deferred, gated on golden-master regeneration)**:

Wire `yf.Ticker.actions` lookup into `clean_ohlcv_for_features` to confirm CA
type before back-adjusting. The code path is `data_store.py:118`. Until this
ships, run the demerger guard and check suspect names manually after any
announcement of a demerger, spin-off, or restructuring.

**How to check today's quarantined names**:

```python
from src.data.data_store import DataStore
from src.runners.long_horizon_cron import _demerger_suspect_names, DEMERGER_LOOKBACK_BARS, DEMERGER_DROP_THRESH

ds = DataStore()
ds.load_ohlcv()  # raw, pre-cleaning
suspects = _demerger_suspect_names(ds.ohlcv, lookback=DEMERGER_LOOKBACK_BARS, drop_thresh=DEMERGER_DROP_THRESH)
print(suspects)  # {VEDL, SKFINDIA} as of 2026-06-27
```

Look up each suspect in the NSE corporate-actions feed before deciding whether
to keep or lift the quarantine. SKFINDIA had a −31% demerger-like move;
verify before treating it as a real split.

**Sub-threshold demergers (W-17, open)**:
Moves in the 25–49% range (TRENT −33%, IEX −30%) are left as raw
discontinuities and do not trigger back-adjustment. They are currently benign
(negative slopes rank out). Monitor by lowering the `DOWN_JUMP` threshold in
`dv_ohlcv_integrity.py` to −0.25.

---

### 1.3 PIT membership and universe integrity

**Membership file**: `data/nifty500_membership.csv`  
**Code**: `src/data/index_membership.py`

The file holds 813 tickers with real entry/exit dates built from Wayback Machine
snapshots. This is the survivorship-corrected reconstruction; the naive version
(`nifty500_membership_naive.csv`, 497 names all `to_date=2030`) should never be
used for backtest construction.

**Known gap — pre-2018 membership (caveat from audit H2)**: No Wayback snapshots
exist before 2018, so 2011–2018 membership falls back to the 2018 snapshot.
Metrics on 2011–2018 folds remain mildly survivor-biased. Trust ≥2019 folds
most.

**W-02 / AUD-007 — 48 current members invisible (open, observability fix shipped)**:
As of 2026-06-27 there are 48 new current index members (ATHERENERG, GROWW-class
entrants, etc.) that are NOT in `config.NIFTY_500` (which is the 2025-07-20 snapshot).
These names are high-momentum — exactly what `sma200_slope_63` targets — so this is
a systematic top-of-book blind spot. The cron now prints:

```
AUD-007: 48 current index member(s) absent from config.NIFTY_500 (invisible to the live scan)
```

Fix (deferred to Task-8 data work): add new entrants to `config.NIFTY_500` and
back-fill their OHLCV + PIT fundamentals before enabling them. None of the 48
currently have fundamentals coverage, so the universe-union fix without data
is a no-op.

**Running the membership check**:

```python
from src.data.index_membership import load_membership, membership_stats
m = load_membership()
print(membership_stats(m))  # n_tickers, n_intervals, real exit count
```

Expected: ~813 tickers, ~380 real exit records.

**Alert threshold**: `MEMBERSHIP_DIVERGENCE_ALERT = 75` in `long_horizon_cron.py`.
The current divergence (48) is below this; the alert is silent but the number
is now printed. If the divergence exceeds 75 (a new index rebalancing), the
cron degrades and the alert fires (once `DRIFT_ALERT_SLACK_WEBHOOK` is set in
the cron-scanner.yml secrets — W-03, Phase-1 fix shipped).

---

### 1.4 Fundamentals PIT — coverage and freshness

**File**: `data/fundamentals_pit_screener.pkl`  
**Code**: `src/data/fundamentals_pit.py`, `long_horizon/data/sheets.py`

The solvency filter (`0 ≤ D/E < 1.5`) is a PIT merge: each bar uses only the
most-recently-published annual report before that date. The join is
`merge_asof(direction='backward', allow_exact_matches=False)` — strictly before,
no lookahead.

**Known failures**:

| Symptom | Root cause | W-id |
|---|---|---|
| HDFCBANK / ICICIBANK / SBIN / BAJFINANCE all dropped | D/E = NaN for deposit-taking banks+NBFCs: Screener's Borrowings/NetWorth ill-defined for deposit-takers | W-04 |
| ABBOTINDIA / HONAUT / PAGEIND (~27 names) dropped | Absent from the store entirely — scrape never picked them up or they refused | W-10 |

**W-10 observability fix (Phase-1, shipped)**: the cron now separates
"absent from fund store (no coverage)" from "present but D/E ≥ 1.5 fail":

```
solvency coverage: 397/452 large+mid names | 27-28 no-coverage (dropped, not D/E-failed)
```

Check `diag['solvency_no_coverage']` and `diag['solvency_coverage']` in
`cron_health` output. If coverage drops below ~0.55, raise a degrade.

**Staleness check**: the Screener scraper is the sole source for fundamentals.
If `fundamentals_pit_screener.pkl` is not refreshed after a new annual-report
season, the PIT join silently uses stale D/E. Check:

```python
import pickle, pandas as pd
with open("data/fundamentals_pit_screener.pkl", "rb") as f:
    store = pickle.load(f)
# Each ticker's most recent row date:
for ticker, df in list(store.items())[:5]:
    print(ticker, df.index.max())
```

If the most-recent row is >90 days old during annual-report season (March–June for
FY24 financials), a scrape refresh is warranted.

**Financials sector policy (W-04, deferred)**:
The "solvent low-debt" filter permanently excludes the entire deposit-taking
banking + lending-NBFC sector (~62 names including the largest-cap Indian banks).
This is live==backtest (not a parity bug), but it means any strategy claim of
"Nifty-500 large+mid universe" is implicitly "ex-financials". Document this
clearly when reporting coverage or universe breadth. The fix (special-case
capital-adequacy proxy for banks) requires a fundamentals schema change and a
new Screener scrape plan.

---

## 2. Cross-source reconciliation (W-19, open)

yfinance is the sole OHLCV source. The Phase-1 audit confirmed: `grep` of the
scanner code finds zero Kite references on the price path. This means any yfinance
vendor error (wrong split factor, stale data) propagates directly into signals
with no cross-check.

**Minimal viable reconciliation (W-19 fix, not yet wired)**:
After ranking, cross-check the LTP of the ~15 selected names against Kite
`/quote` before publishing:

```python
# Pseudo-code — wire this in long_horizon_cron.py before push_results()
for sig in new_entry_signals:
    kite_ltp = kite_client.quote(sig['ticker'])['last_price']
    yf_close = sig['entry'] / (1 + SLIPPAGE)
    pct_diff = abs(kite_ltp - yf_close) / yf_close
    if pct_diff > 0.01:  # >1% disagreement
        _alert('degraded', f"price mismatch {sig['ticker']}: yf={yf_close:.2f} kite={kite_ltp:.2f}")
```

This is cheap (owner already pays for Kite) and would have caught the VEDL
fabrication even without the demerger guard. Owner approved this as a future
hardening step.

---

## 3. Survivorship bias — the delisted-name problem

**Backtest dataset (cloud `cpcv-research.yml`)**:
The headline backtest rehydrates ~247 names that are no longer live on yfinance
via `scripts/fetch_dropped_ohlcv.py` + the real-exit membership file. This
addresses the first layer of survivorship.

**Residual gap (~114 hard bankruptcies)**:
DHFL, RCAP, SREINFRA, and ~111 similar names that went bankrupt and were
fully delisted are unrecoverable from yfinance (HTTP 404, no historical data).
These are names that, if included, would ADD losses to the backtest (they exited
the index before going to zero or near-zero). Their absence makes the headline
number mildly optimistic.

**Quantitative impact**: unknown precisely. The relative KILL verdicts from prior
research survive (common-mode bias cancels across comparisons). The absolute
headline CAGR is mildly inflated vs a fully-survivorship-corrected universe.
Do not use the headline numbers as a promise to investors; call it "research
backtest with residual ~114 unrecoverable bankruptcy names." Current honest anchor:
baseline_v0 = 26.1% gross CAGR / 23.1% after-tax (supersedes the optimistic-exit 30.26%, 2026-06-27).

**Practical mitigation**: source delisted instrument history from a Kite
instrument dump (Zerodha keeps some historical tick data for delisted names via
their historical API). This is open research infrastructure work.

**Pre-2018 caveat**: membership before 2018 uses the 2018 snapshot (no Wayback
data). Trust ≥2019 folds exclusively for any claim about the live-regime edge.

---

## 4. Zero-volume / holiday phantom bars

`clean_ohlcv_for_features` drops:
1. Bars on NSE trading holidays (from `config.NSE_HOLIDAYS`).
2. Zero-volume flat-OHLC bars (suspension / pre-listing placeholders).

Note: **weekends are NOT dropped**. NSE runs legitimate weekend sessions
(Diwali Muhurat, Budget Saturday). Dropping weekends wholesale would create
false date gaps.

**Check after `NSE_HOLIDAYS` updates**: if a new holiday is added to `config.py`
mid-cache, bars previously accepted as valid are now phantom. Rebuild
the cleaned features after any `NSE_HOLIDAYS` change.

**ALOKINDS / PATANJALI pattern**: the zero-volume flat drop was introduced by
suspension periods creating fake price jumps on resumption. The zero-vol filter
handles these. If a new name shows an implausible jump on the first days after
re-listing, check for zero-volume flat prefixes first.

---

## 5. Backtest dataset reproducibility gate

Before standing up ANY new research layer (Phase 4+), confirm the backtest
dataset is reproducible:

1. `data/ohlcv.pkl` and `data/features.pkl` must exist (they are gitignored; cloud
   run or explicit `DataStore.compute_all_features(persist=True)` generates them).
2. The equity curve must be persisted in `long_horizon/results/` (W-07 fix, shipped).
3. Run: `python diagnostics/dv_ohlcv_integrity.py --source cleaned --fail-on-structural`
4. Check panel coverage: every PIT-membership name in [2019, present) must have
   non-zero OHLCV. The panel-coverage assert (W-07 open item) will gate this
   automatically once wired.

**Headline baseline to anchor on**:
`research/baseline_v0.json` → exit-parity-unified engine, 397 solvent names, 2017–2026 →
**26.1% gross CAGR / 1.02 Sharpe / −41.9% maxDD / 0.62 Calmar; after-tax 23.1% / 0.83**
(supersedes the optimistic-exit 30.26%/1.15 from `cpcv_long_horizon_final_682.json`, 2026-06-27).
The re-derived 34.67% / 1.248 in `cpcv_long_horizon_tradelog_682.json` uses re-derived
params (not what the live cron trades) — never anchor research comparisons on that number.

---

## 6. Quick-reference checklist

Use this before any data-layer change or cloud backtest run:

```
[ ] dv_ohlcv_integrity --source cleaned --fail-on-structural: 0 structural issues
[ ] demerger suspects reviewed: _demerger_suspect_names() output inspected + verified
    against yf.Ticker.actions for all flagged names
[ ] Membership file: load_membership() returns ~813 tickers, ~380 real exits
[ ] AUD-007 divergence: < 75 (print in cron_health)
[ ] Fundamentals coverage: solvency_coverage ≥ 0.55 (cron_health diag)
[ ] Fundamentals freshness: most-recent PIT row ≤ 90 days old during report season
[ ] NSE_HOLIDAYS current: last known holiday in config.py matches NSE calendar
[ ] Equity curve persisted: long_horizon/results/ contains equity_curve artifact
[ ] Panel coverage: no PIT-membership name in [2019,present) has zero OHLCV rows
[ ] Pyarrow installed (pinned): requirements.lock includes pyarrow or cron-scanner.yml
    has a pinned `pip install pyarrow==<ver>` (W-09, check before a cache run)
```

---

## 7. Open items (not yet fixed)

| W-id | Sev | Description | Gating condition |
|---|---|---|---|
| W-01 root | HIGH | CA-type-aware split vs demerger classification in `clean_ohlcv_for_features` | Golden-master regeneration + cloud re-derive |
| W-02 | HIGH | Universe-union fix: add 48 new current members to scan | Task-8 data work (PIT fundamentals coverage first) |
| W-04 | HIGH | Financials sector D/E policy: special-case banks/NBFCs | Schema change + Screener scrape plan |
| W-17 | LOW | Sub-50% demerger monitoring in `dv_ohlcv_integrity` | Lower DOWN_JUMP to −0.25 |
| W-19 | LOW | 2nd-source reconciliation: Kite /quote cross-check on selected names | Wire in entry loop before push_results |

---

## Sources

- `claude-trading-skills/skills/data-quality-checker/SKILL.md` (MIT) — advisory
  mode, severity tiers (ERROR/WARNING/INFO), multi-check CLI pattern
- `finance_skills/plugins/client-operations/skills/corporate-actions/SKILL.md`
  (MIT) — CA lifecycle, split vs spin-off distinction, PIT semantics, cost-basis
  invariants, the "process at the tax-lot level, not position level" discipline
  (translated here: quarantine at the per-name level, not universe-wide)
- `long_horizon/audit/wiring_issues.md` — Phase-1 wiring audit ledger (W-01..W-21)
- `long_horizon/audit/PHASE1_FIXES.md` — closed items and residual open items
- `long_horizon/audit/wiring_report.md` — full wire-map and sub-audit detail
- `diagnostics/dv_ohlcv_integrity.py` — the live scan tool
- `src/data/data_store.py::clean_ohlcv_for_features` — the cleaner whose
  `_CORP_ACTION_MOVE=0.50` heuristic is the root of W-01
- `src/runners/long_horizon_cron.py::_demerger_suspect_names` — the live quarantine guard
