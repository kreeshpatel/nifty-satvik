<!-- Provenance: Phase-1 wiring audit, 2026-06-27.
Method: 9 parallel auditors each ran python probes against the REAL data files
(results/ohlcv_cache_lh.json, data/nifty500_membership.csv, data/fundamentals_pit_screener.pkl)
+ read the live code; every red/HIGH finding was adversarially re-verified by a second agent;
the two top red wires (W-01 VEDL demerger-as-split, W-02 AUD-007 universe gap) were then
independently re-confirmed by the lead with exact numbers (VEDL slope 2.156->24.944,
splits_adjusted=1; current-members-invisible = 48 < 75 alert threshold).
This is a LIVE-WIRING + DATA-INTEGRITY audit; it does NOT re-validate the headline backtest
(see the reproducibility verdict -- that needs a cloud cpcv-research.yml run). -->

# Long-Horizon Strategy — Phase 1 Wiring Report

## (a) Executive summary & overall trust verdict

The long-horizon scanner's **core math is honest and the decision layer is byte-identical between backtest and live**. Across 9 audit dimensions and dozens of python probes against the real data files, the load-bearing correctness claims hold: features are backward-only and lookahead-clean (hand-verified to 6 decimals + a truncation test), the PIT membership mask is a genuine per-date filter (not a blunt current-member screen), the fundamentals/solvency join is strict-before (no D/E leak), sizing is a single shared `base_risk_qty` kernel with identical caps, the vol-target overlay is correctly quarantined to live (the research backtest + golden master are untouched), atomic writes are crash-safe, same-day re-runs are idempotent, and the golden master passes under pandas 3.0.1.

**The danger is NOT in the math — it is in the data plumbing and the gap between what the backtest measured and what the live book actually books.** Two structural live biases (a fabricated demerger BUY signal; a 48-name high-momentum universe blind spot), a monitoring blackout (all alerts are no-ops), two booking-layer parity defects (live records stop exits optimistically and ages positions +1 day), and a hard fact that **the headline 30.3% CAGR cannot be reproduced locally** (the backtest dataset is absent; the survivor-only live cache is not a substitute).

**Trust verdict: CONDITIONAL TRUST.** The engine is safe to run as a *paper* scanner (it has never traded a live rupee, which is correct). It is NOT yet trustworthy enough to (i) put real capital behind, or (ii) build a new research layer on top of, until the four CRITICAL/HIGH wires below are fixed and the headline is re-derived on the cloud expanded universe. The relative KILL verdicts from prior research survive (common-mode bias cancels); the absolute headline number does not, locally.

---

## (b) File-by-file wire map — live long-horizon path

| Module | Inputs | Outputs | Depends on | Wire |
|---|---|---|---|---|
| `.github/workflows/cron-scanner.yml` | schedule 10:45 UTC; secrets (GITHUB_TOKEN) | runner env, `python -m src.runners.long_horizon_cron` | requirements.lock **+ unhashed pyarrow** | 🟠 amber (pyarrow out-of-lock SPOF; no DRIFT_ALERT secret) |
| `src/data/ohlcv_incremental.py` | yfinance (sole source), local cache, GitHub raw fallback | `ds.ohlcv` dict | yfinance only — **no 2nd source** | 🟠 amber (single-vendor; split-heal can't fix demergers/aged events) |
| `results/ohlcv_cache_lh.json` | committed cache (495 names) | warm-start panel | `actions/checkout` restore | 🟠 amber (NOT in .gitignore allowlist — untrack → 600d cold-start) |
| `src/data/data_store.py::clean_ohlcv_for_features` | raw OHLCV, NSE_HOLIDAYS | cleaned OHLCV | `_CORP_ACTION_MOVE=0.50` heuristic | 🔴 **red** (back-adjusts demergers as splits) |
| `src/data/data_store.py::compute_all_features` | cleaned ohlcv | 89-col feature frames | `_compute_stock_features` | 🟢 green (lookahead-clean) / 🟠 amber (silent per-name `except: pass`; ~44 dead cols) |
| `src/data/index_membership.py::filter_features_dict` | features, membership CSV | PIT-masked features | `data/nifty500_membership.csv` (PIT, 380 real exits) | 🟢 green (genuine per-date mask) |
| `src/runners/long_horizon_cron.py` (universe build) | config.NIFTY_500, membership | ranked universe | config snapshot 2025-07-20 | 🔴 **red** (AUD-007: 48 current members invisible) |
| `long_horizon/backtest/ohlc_panel.py::restrict_to_large_mid` | panel | ADV≥5cr names | rolling-median ADV | 🟢 green (correct per-row; near-inert on liquid live universe) |
| `long_horizon/data/sheets.py::_value_quality_series` | fundamentals_pit_screener.pkl | D/E series | `merge_asof(backward, allow_exact_matches=False)` | 🟢 green join / 🟠 amber (financials sector all-NaN D/E → silent drop) |
| solvency filter (`long_horizon_cron.py:359`) | low_debt | solvent universe | — | 🟠 amber (NaN-fails-both → silent coverage drop, no diag) |
| `cross_sectional_rank` | solvent universe, SIGNAL | trend_rank | per-date `groupby.rank(pct=True)` | 🟢 green (as_of-only) |
| `_size_position` / `base_risk_qty` (`portfolio.py:73`) | entry, stop, adv, cfg | shares | frozen cfg (15% cap binds) | 🟢 green (floor-int, shared w/ backtest) / 🟠 amber (0-share signal published if entry>15% book) |
| `src/trading/signal_tracker.py::track_signals` | signals_history, OHLCV | exit decisions, equity | `engine.exit_logic.decide_exit` | 🟢 green decision / 🟠 amber (no `open` → optimistic stop fill; +1 aging; close-based equity) |
| `src/trading/paper_broker.py` | signals, cash | paper ledger | re-prices entry to open(t+1) | 🟢 green entry / 🟠 amber (copies close-based stop/target verbatim) |
| `src/utils/atomic_io.py::atomic_write_json` | dict | result files | temp+fsync+os.replace | 🟢 green (crash-safe, verified) |
| `src/data/github_push.py::push_results` | result files | GitHub commits | per-file REST PUT | 🟠 amber (returns True on PARTIAL push → no alert) |
| `src/monitoring/alert_publisher.py` | cron_health | Slack/SMTP alert | DRIFT_ALERT_* env | 🔴 **red** (unset everywhere → every alert a no-op) |
| `results/kill_log.jsonl` | kill verdicts | observe audit trail | push list | 🔴 **red** (written but never pushed/tracked → discarded each run) |

---

## (c) Four Phase-1 sub-audits

### 1. Data fetch integrity

**Green (verified correct):**
- Within a single name, signal / ATR / ADV / entry / stop all share ONE adjustment basis — no within-trade adjusted/unadjusted mismatch (`ohlc_panel.py:38-58`, `long_horizon_cron.py:295,476-480`). The shared-clean invariant holds; the problem is the *shared basis is wrong for demergers*, not that metrics disagree.
- `config.NIFTY_500` is byte-exact to the 2025-07-20 official snapshot (500/500); `load_membership` reads the real PIT CSV (`nifty500_membership.csv` == `_v2.csv`, md5 47e6c5db…), not the naive backfilled file.

**Red/amber:**
- 🔴 **demerger-as-split** (`data_store.py:118`): `_CORP_ACTION_MOVE=0.50` back-adjusts ANY >50% single-session drop as a split. **VEDL Vedanta demerger (2026-04-29 773.6→271.55, −64.9%) → splits_adjusted=1, raw slope63 +2.16 inflated to +24.94 → rank 3/495**, the ONLY split-adjusted name in the top-20. EMPIRICALLY RE-CONFIRMED this session. SKFINDIA likewise (−30.67→−7.83).
- 🔴 **sub-50% demerger** (severity corrected MEDIUM→LOW): TRENT −33%, IEX −30%, INDUSINDBK −27% left as raw discontinuities (splits_adjusted=0). Currently benign (negative slopes pushed out); latent future false-positive. `dv_ohlcv_integrity` DOWN_JUMP=−0.45 doesn't even record them.
- 🟠 **split-heal blind spot** (`ohlcv_incremental.py:161-176`): only compares the most-recent shared bar, so aged events (ABFRL ~270 days back) and demergers can never re-heal.
- 🟠 **yfinance sole source** — Kite is dashboard-only (grep: zero kite refs in the price path); no second-source reconciliation.

### 2. Cron & refresh flow

**Green (verified correct):**
- **Scanner is GitHub Actions, NOT Render** — `render.yaml` deleted (commit 7c4aa15; `ls render.yaml` → not found). Live trigger is `.github/workflows/cron-scanner.yml` (`45 10 * * 1-5`). The audit-prompt/STRATEGY.md Render references are STALE.
- **No cold-start on normal runs**: `results/ohlcv_cache_lh.json` is a TRACKED committed file (`git ls-files` confirms) restored by checkout → 5-day incremental path, not 600d. Confirmed: 495 names, all last-bar 2026-06-25.
- Execution order matches the documented pipeline exactly; integrity scan runs on the CLEANED series the panel consumes; frozen-config validation fail-fasts BEFORE the expensive download.
- GitHub-raw fallback is a second warm-start net before any cold-start.

**Red/amber:**
- 🟠 **cache outside .gitignore allowlist** (`.gitignore:23-41`): persists only because already-tracked. `git check-ignore` exits 1 only for that reason. An untrack/`git rm --cached`/clean → `results/*` rule hides it → every run flips to a 600d cold-start. Fix: add `!results/ohlcv_cache_lh.json`.
- 🟠 **pyarrow out-of-lock** (`cron-scanner.yml:36-42`): a separate UNHASHED `pip install pyarrow` outside `requirements.lock`. Without it `load_fund_store()` fails → every D/E NaN → solvency empties the universe → 0 signals. A PyPI blip = full outage.

### 3. Model wiring & one-symbol trace

**Green (verified correct):**
- `sma200_slope_63`, `atr_pct_63`, `adv_rupees_20d` are backward-only — hand-computed match to pipeline to 6 dp AND a truncation test (drop last 30 bars) gives bit-identical values at date t.
- `enrich_with_layers` is NEVER called on the live path (grep) — no macro/sector merge can drop rows; the 18 macro/sector v1 columns never exist live.
- The v1-contract `dropna` only strips the ~58-bar technical warm-up (none of the long-horizon/label columns are in the v1 contract), well before the 263-bar slope requirement. **0/495 names lose their as_of bar.**
- Cross-sectional rank and regime/breadth use only the as_of slice.

**Red/amber:**
- 🟠 **silent per-name `except: pass`** (`data_store.py:254-260`): a crash in ANY of ~44 unused columns silently drops the whole name (incl. its good slope) with no log. 0/495 trip it today — latent reliability hole.
- 🟠 **dead-column bloat**: ~44 of 89 computed columns are unused on the live path (forward labels, triple-barrier O(n·horizon) loops, candlestick loops) — wasted compute + crash surface.
- 🟠 **fund-store relative path** (`build_measurement_panel.py:26`): `'data/fundamentals_pit_screener.pkl'` is cwd-relative; any non-repo-root invocation → store=None → all D/E NaN → empty universe (masked behind a generic "empty universe" message). Works in prod (`python -m` from root).

### 4. Sizing & parity

**Green (verified correct):**
- Whole-share `floor()`-to-int on every path; never fractional, never negative.
- "Sizing largely inert — 15% cap binds" is EMPIRICALLY TRUE: the position cap binds for 494/495 names; risk% is near-dominated; the effective knob is `max_position_pct`, not `risk_per_trade_pct`.
- Live and backtest share byte-identical first-pass `base_risk_qty` with identical args/caps, both sourced from the frozen cfg.
- Vol-target overlay is LIVE-only: `load_frozen_cfg` drops `live_overlays`; `simulate()` never sets `target_vol_annual` → research backtest + golden master byte-identical.

**Red/amber:**
- 🟠 **live stop-fill optimistic** (HIGH): live tracker passes no `open` to `decide_exit` and overwrites `close_price=stop`, so it records stop exits AT the stop; backtest fills at `min(open,close)`. 848/20k fuzz bars diverged; **297/1453 stop exits (20.4%, avg −17%, 199 worse than −15%)** are gap-throughs where live paper P&L is optimistic on its worst trades. Surfaces in `signals_history.json` outcomes → WR/kill-criteria stats (the exact rollback-trigger source).
- 🟠 **+1 aging offset**: live ages from `signal_date(t)`, backtest from fill day `(t+1)` → 63d cap & 10d min-hold fire one session early live.
- 🟠 **kill-equity close-entry**: the always-on signal_tracker equity curve (feeds the kill gate) books entry+stop+target at close(t), not open(t+1) — internally inconsistent with the paper_broker ledger.
- 🟠 **0-share signal** (LOW): no `shares==0` guard, so a name priced >₹150k (>15% of ₹10L book) publishes a 0-share BUY card. Latent (MRF ₹129,550 = 1 share today).
- 🟠 **financials silently dropped** (HIGH): solvency filter drops 78-79 large+mid names, 62 of them the ENTIRE banks+NBFC block (HDFCBANK/ICICIBANK/SBIN — D/E=NaN from Screener's Borrowings/net-worth derivation). Live==backtest (not a parity bug), but the "solvent low-debt" universe is far narrower than the spec implies, for a DATA reason not leverage. (Note: 26 financials WITH clean D/E — insurers/AMCs/exchanges — DO survive, so "can NEVER signal a bank" overstates it to specifically deposit-taking banks + lending NBFCs.)

---

## (d) One-symbol end-to-end trace — RELIANCE @ 2026-06-25

| Stage | Value | Notes |
|---|---|---|
| sma200_slope_63 (SIGNAL) | **−1.864181** | hand == pipeline to 6 dp; truncation-test lookahead-clean |
| atr_pct_63 | **2.132238** | trailing ATR |
| adv_rupees_20d | **₹2,397 cr** (23,973,437,444) | far above ₹5cr floor |
| trend_rank | **0.5088** (mid-pack) | NOT selected; top-5 = NATIONALUM 1.0, HINDCOPPER 0.997, HFCL 0.994, GVT&D 0.991, ADANIPOWER 0.988 |
| PIT D/E | **0.444** | merge_asof backward, strict-before; passes 0≤D/E<1.5 |
| entry | close 1318.1 × (1+0.0005) = **1318.76** | indicative (close-based) |
| stop | 1318.76 × (1 − 3.67·2.132238/100) = **1215.56** (7.83% = 3.67×ATR) | |
| target | 1318.76 × (1+22.52/100) = **1615.74** (+22.52%) | |
| size | base_risk_qty → **113 shares = ₹149,020 = 14.9%** | **15% cap binds** (sizing inert, as documented) |

Contrast with VEDL (the broken wire): cleaned slope **+24.94** (raw +2.16) → fabricated **rank 3/495**; blocked from the book today only by PIT D/E=2.22 (solvency fail), not by the signal.

---

## (e) Reproducibility verdict

See the dedicated reproducibility field. In one line: **the headline is NOT reproducible in this worktree** (data/ohlcv.pkl + data/features.pkl absent; survivor-only live cache is not a backtest dataset; no equity_curve persisted). The cloud `cpcv-research.yml` path already rehydrates the expanded universe (recovers ~247 dropped names via `fetch_dropped_ohlcv.py` + real-exit membership), so the headline was NOT survivor-only as first feared — but a **residual ~114 hard-bankruptcy names** (DHFL/RCAP/SREINFRA…) are unrecoverable from yfinance and need a Kite instrument dump to fully close survivorship. Re-derive on the cloud, persist the equity curve, add a panel-coverage assert, and trust only ≥2019 folds before standing up any new research layer.

---

## Lead independent re-confirmation (2026-06-27)
Before publishing, the two load-bearing red wires were re-run from scratch by the lead:
- **W-01 VEDL** -- `clean_ohlcv_for_features` returns `splits_adjusted=1`; `sma200_slope_63` raw **2.156** vs cleaned **24.944**. The 2026-04-30 demerger (773.6 -> 271.6, -64.9%) is back-adjusted as a 1:2.85 split, fabricating a near-top trend. CONFIRMED.
- **W-02 AUD-007** -- `config.NIFTY_500`=500, current index members=500, **48 current members invisible** to the scan (ATHERENERG/GROWW/MEESHO...), 48 config names correctly exited; max divergence 48 < `MEMBERSHIP_DIVERGENCE_ALERT` 75 -> alert silent; 0 of the 48 present in the cache. CONFIRMED.
