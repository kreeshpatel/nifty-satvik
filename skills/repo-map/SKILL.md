---
name: repo-map
description: >
  A living map of every formula, value, and file that matters to the long-horizon program —
  where it lives, who else reads it, and what breaks if it drifts. Use this BEFORE changing
  any value, formula, or structural file so you know the full blast radius. Trigger words:
  "where is", "what depends on", "did this value change", "structure", "where does X live",
  "before changing a formula", "single source of truth", "which file owns", "what calls",
  "how does X flow", "is this duplicated", "parity between live and backtest", "what is the
  canonical", "where are the constants", "map of the codebase", "file inventory".
---

# Repo Map — NiftyQuant Long-Horizon

**Why this exists (plain language).** The long-horizon program spans many files across
`long_horizon/`, `src/`, `data/`, `models/`, `results/`, `docs/`, and the live cron
workflow. Values that appear in more than one place drift. The Phase-1 wiring audit found
this is the primary source of live-vs-backtest parity defects — not the signal math, but
the *plumbing* around it. This skill is the pre-flight reference you open before touching
any formula, constant, or structural decision, so you know what else would need to change.

**When to use this.** Open it when you are about to:
- Change a sizing formula, cost constant, or exit parameter anywhere.
- Add a new column to the universe filter or solvency mask.
- Edit `config.py`, `long_horizon/config.py`, or `models/long_horizon/config.json`.
- Ask "does the backtest agree with the live cron on this?".
- Look for where a specific value comes from.
- Run a research experiment and want to know which files the harness actually reads.

Cross-reference: [`data-quality`](../data-quality/SKILL.md) before any OHLCV/CA change;
[`backtest-rigor`](../backtest-rigor/SKILL.md) before trusting any harness number.

---

## Part 1 — Shared Kernels (single sources of truth)

These are the files that are the *authoritative* source for the value or formula. If you
see the same value somewhere else, that copy is a derivative — and a drift hazard.

### 1.1 Frozen strategy config — `models/long_horizon/config.json`

**The live scanner reads this at startup and fails loud if it is corrupt.** Every parameter
value in the cron, the backtest, and the paper-broker must trace back here.

```
models/long_horizon/config.json
  └── cfg block (the frozen strategy params the live scanner trades):
        signal            = "sma200_slope_63"
        gate_quantile     = 0.5
        stop_atr_mult     = 3.67
        target_pct        = 22.52
        trailing_activate_pct = 4.0
        trailing_pct      = 4.27
        min_hold_days     = 10
        max_hold_days     = 63
        risk_per_trade_pct = 3.0
        max_position_pct  = 15.0
        max_adv_participation_pct = 5.0
        max_positions     = 15
  └── live_overlays block (paper-book sizing equity only; NOT in frozen cfg; harness unaffected):
        vol_target_annual = 0.15
        vol_window        = 42
        vol_floor         = 0.40
```

**Load path (live cron):** `long_horizon.config.load_frozen_cfg()` reads
`models/long_horizon/config.json`, falling back to in-code constants in
`long_horizon/config.py` only when the JSON is absent (standalone tooling). The cron calls
`validate_frozen_cfg(cfg)` immediately after load and aborts on any malformed value.

**In-code mirrors** (must stay in sync with the JSON):
- `long_horizon/config.py` constants (`STOP_ATR_MULT`, `TARGET_PCT`, etc.) — the fallback
  AND the cross-check. If the JSON changes, update these too.
- `long_horizon/backtest/portfolio.py::simulate` reads them from the `derived` dict, which
  is always `load_frozen_cfg()` output — never hardcoded inside `simulate`.

**Rule:** Do not edit `models/long_horizon/config.json` directly during a live scan window
(4:15 PM IST weekdays). The cron loads it at startup; a mid-run edit has no effect.
Any cfg change that changes feature values requires a **golden-master regeneration** in the
same PR (`python -m diagnostics.build_golden_fixture`).

---

### 1.2 Sizing formula — `long_horizon/backtest/portfolio.py::base_risk_qty`

**This is the single sizing kernel used by BOTH the backtest and the live cron.** Keeping
one function means they cannot drift.

```python
# long_horizon/backtest/portfolio.py, line 57
def base_risk_qty(equity, fill, risk_per_share, adv, risk_pct,
                  *, max_position_pct=15.0, max_adv_participation=0.05) -> int:
    # qty = floor(risk_pct% of equity / risk_per_share)
    #       capped by floor(max_position_pct% of equity / fill)
    #       and       floor(max_adv_participation * ADV / fill)
```

**Callers:**
- **Backtest** (`portfolio.py::simulate`, line 275): `base_risk_qty(equity * vol_scalar * exposure_t, ...)`
- **Live cron** (`src/runners/long_horizon_cron.py`): imported directly via
  `from long_horizon.backtest.portfolio import base_risk_qty`

**Parity invariant:** Both callers pass `max_position_pct` and `max_adv_participation` from
the frozen cfg dict (not the function defaults). The backtest multiplies sizing equity by
`vol_scalar` (vol-target scalar) and `exposure_t` (market-state scalar) before passing to
`base_risk_qty`. The live cron applies the vol-target scalar to the paper-book equity from
`results/portfolio_history.csv` (same `vol_target_scalar` function, same formula — see 1.3
below). If you change `base_risk_qty`, the golden master will catch any drift.

**Cost constants** (declared at module level, lines 31–37):
```python
BROKERAGE_PCT = 0.0003   # 0.03% per leg
STT_PCT       = 0.001    # 0.10% (both legs on the sell side — effectively per round trip)
LEG_COST      = BROKERAGE_PCT + STT_PCT
SLIPPAGE = {"LARGE_CAP": 0.0005, "MID_CAP": 0.0022, "SMALL_CAP": 0.0040}
MAX_ADV_PARTICIPATION = 0.05
```
These are intentional local copies so the module imports standalone in research tooling.
They must stay byte-identical to `config.py` and `src/trading/execution_model.py` — check
all three if you ever change a cost constant.

---

### 1.3 Vol-target formula — `long_horizon/backtest/portfolio.py::vol_target_scalar`

**Single shared formula for both backtest and live paper-book.** Scales sizing equity DOWN
when realized portfolio vol exceeds `vol_target_annual` (0.15 = 15%/yr). Never scales up
(capped at 1.0). Floor at `vol_floor` (0.40 = never de-gross below 40% exposure).

```python
# long_horizon/backtest/portfolio.py, line 82
def vol_target_scalar(equities, target_vol, *, vol_window=42, vol_floor=0.40) -> float:
    # rv = annualized realized vol of trailing vol_window daily equity returns (ddof=1, ×√252)
    # returns max(vol_floor, min(1.0, target_vol / rv))
```

**Callers:**
- Backtest: called each day on `[e["equity"] for e in equity_curve]`
- Live cron: called on the trailing `results/portfolio_history.csv` equity before sizing

This is the pre-reg 0068 "V2" arm. Both callers use the same function from the same module.
The `live_overlays` block in `models/long_horizon/config.json` carries the canonical values
(vol_target_annual=0.15, vol_window=42, vol_floor=0.40).

---

### 1.4 Exit decision — `engine/exit_logic.py::decide_exit`

**The stop / target / trailing / time decision is shared.** Both the live `signal_tracker`
and the backtest `portfolio.simulate` call the same `decide_exit` function so they cannot
diverge on exit logic.

```
engine/exit_logic.py::decide_exit(pos_dict, today_ohlc, signals, cfg, days_held)
  → Decision(close_reason, exit_price, new_peak, extend_time_stop)
```

**Callers:**
- **Backtest** (`portfolio.py`, line 322): `decide_exit(pos_dict, {"open": o, "high": h, "close": c}, {}, exit_cfg, p.days_held)`
- **Live** (`src/trading/signal_tracker.py`, line ~466): `decide_exit(pos_dict, today_ohlc, {}, cfg, exit_days_held)`

**Phase-1 fix (W-05):** the live caller now passes `today_ohlc = {"open": current_open, ...}` so
gap-fill stops use the real opening price, matching backtest behaviour. Before this fix, the live
path produced optimistic stop fills on 20.4% of stop exits (297 of 1,453 stops, avg −17%). This
was fixed in `signal_tracker.py:478` and covered by `tests/test_lh_live_exit_parity.py`.

**Phase-1 fix (W-11):** aging parity. Live now computes `exit_days_held = max(0, days_since - 1)`
(age from the t+1 fill day, matching backtest) before passing to `decide_exit`. The
human-facing `sig['days_since']` is preserved unchanged.

**If you change `decide_exit`:** the golden master test (`tests/test_long_horizon_golden.py`)
will catch it. Regenerate the baseline with `python -m diagnostics.build_golden_fixture` in
the same PR. This is a **hard gate** — do not merge without a byte-identical golden master
OR an intentional regeneration.

---

### 1.5 Universe and solvency filter — `long_horizon/backtest/ohlc_panel.py`

Three functions live here that define WHO is in the tradeable universe:

```
ohlc_panel.py::restrict_to_large_mid(panel, min_adv_rs=5e7)
    # Keeps only rows where adv_rupees_20d >= 5 cr (rolling-median 20d rupee ADV)
    # Correct per-row PIT — near-inert on the liquid live universe

ohlc_panel.py::solvent_universe_mask(fund_df, ...)
    # Returns a boolean mask: 0 <= D/E < 1.5, derived from fundamentals_pit_screener.pkl
    # via merge_asof(backward, allow_exact_matches=False) — strict PIT, no leak

ohlc_panel.py::cross_sectional_rank(panel, signal_col="sma200_slope_63", ...)
    # per-date groupby rank(pct=True) on the solvent large+mid universe
    # gate_quantile=0.5 → top 50% by rank eligible (top 15 fill slots)
```

**Who calls these:**
- **Backtest** (`long_horizon/backtest/portfolio.py::simulate`): panel is pre-built with
  `ohlc_panel.build_ohlc_panel`, then `restrict_to_large_mid` + `solvent_universe_mask`
  applied before `cross_sectional_rank`.
- **Live cron** (`src/runners/long_horizon_cron.py::_build_ranked_universe`): same three
  functions imported directly from `long_horizon.backtest.ohlc_panel`.

**Known gap (W-04 / Stage B):** Banks and lending NBFCs (HDFCBANK, ICICIBANK, SBIN,
BAJFINANCE, ~62 names) have D/E = NaN from the Screener fundamentals store (Borrowings /
net-worth is not the right ratio for deposit-takers). They silently fall out of the
solvency mask. Live and backtest agree (not a parity bug), but the spec says financials
should be included via a capital-adequacy proxy. This is fixed at Stage B (`B3`).

**Known gap (W-02 / Stage B):** 48 current index members (new entrants post-2025-07-20)
are invisible because `config.NIFTY_500` is a 2025-07-20 snapshot. These names have no
PIT fundamentals, so the fix (universe union `current_members ∪ NIFTY_500`) is deferred
to Stage B when the fundamentals pipeline covers them. The divergence is now logged every
run (`AUD-007:` print, `long_horizon_cron.py:354`).

---

### 1.6 Feature contract — `long_horizon/features/contract.py`

**This is the single source of truth for which factors are in the long-horizon model.**

```python
# long_horizon/features/contract.py
LONG_HORIZON_FEATURES = [
    "sma200_slope_63",   # primary signal (+1, HAC t +5.2)
    "mom_252_21",        # 12-1 momentum (+1)
    "mom_126",           # 6-month momentum (+1)
    "donchian_pos_126",  # 126d channel position (+1)
    "rs_rank_sector_126", # 126d sector-relative strength (+1)
    "ep",                # earnings yield (+1)
    "bp",                # book-to-price (+1)
    "low_debt",          # solvency flag (−1: junk premium)
]  # 8 factors, enforced by assertion

RISK_FACTORS = ("vol_126", "atr_pct_63")  # carry columns, not alpha legs
```

These 8 factors are what the Stage-C conviction model and Stage-D hybrid layers must work
within. `FACTOR_SIGN` maps each factor's IC direction so a higher composite score = higher
expected return. Do not add or remove factors without a pre-registration and a full walk-
forward re-derivation (the conviction model is trained on these; changing the set = retrain).

**Where these columns come from:** computed by `src/data/data_store.py::_compute_stock_features`
on the OHLCV + fundamentals data. That function is the technical feature source of truth.
Do NOT add new technical features by duplicating logic elsewhere — extend `_compute_stock_features`.

---

### 1.7 Honest baseline anchor — `research/baseline_v0.json`

**This is the number every stage is measured against.** Do not cite the old 30.26% or
~32% figures — those are historical provenance from before the exit-parity unification.

```
research/baseline_v0.json
  universe:  397 (solvent, large+mid, corrected-682 membership)
  period:    2017-01-01 → 2026-06-25
  gross:     CAGR 26.11%  /  Sharpe 1.0155  /  maxDD −41.87%  /  Calmar 0.62
             trades/yr 155.88  /  WR 59.72%
  after-tax: CAGR 23.13%  /  Sharpe 0.8339  /  maxDD −45.59%  /  Calmar 0.51
```

The exit-parity unification (shared `decide_exit`, Phase-1 fix W-05) cost ~4 pp CAGR vs
the previous optimistic fill. After-tax STCG 20% costs a further ~3 pp / ~0.18 Sharpe.

Stage B (`baseline_v1`) will likely move these numbers further down when the +284 delisted
names from the corrected universe are added (survivor-only data flatters returns). Accept
the honest new number at Stage B — do not try to defend the current figure.

---

## Part 2 — Duplication Hazards

These are the places where the same concept appears in more than one file. They are the
most common source of silent drift.

### 2.1 Cost constants (three locations, must stay in sync)

| Location | Constants |
|---|---|
| `long_horizon/backtest/portfolio.py` lines 31–37 | `BROKERAGE_PCT`, `STT_PCT`, `LEG_COST`, `SLIPPAGE`, `MAX_ADV_PARTICIPATION` — the backtest source |
| `config.py` (root) | `BROKERAGE_PCT`, `STT_PCT` — the live-cron source imported by most modules |
| `src/trading/execution_model.py` | Tiered slippage used by the v1-era execution model |

If you change any cost constant, grep for all three locations and update them together.
The Phase-1 audit confirmed they were in sync as of 2026-06-27; a future drift will not
be caught by the golden master (which only checks signal/exit/sizing, not cost calibration).

### 2.2 The solvency filter — was 13 files, B3 made `solvent_universe_mask`, but runners may inline it

After Stage B fixed B3, `ohlc_panel.py::solvent_universe_mask` became the canonical
solvency function. Before that, 13 different files each applied a variant of the
`0 <= D/E < 1.5` filter inline. Verify that no runner re-inlines this filter by checking
`grep -rn "D/E\|low_debt" src/ long_horizon/` whenever you add a new data pipeline step.

### 2.3 Demerger reference — `data/data_store.py::load_demerger_reference`

The VEDL lesson: a demerger is NOT a split, but `clean_ohlcv_for_features` back-adjusts
any >50% single-session close drop as a split, fabricating a soaring `sma200_slope_63`
(VEDL: slope +2.16 → +24.94, rank 3/495). The Phase-1 live-path quarantine guard
(`src/runners/long_horizon_cron.py::_demerger_suspect_names`) catches this on the raw
close BEFORE the cleaner runs — but it is a detection-only guard. The ROOT fix (CA-type-
aware back-adjustment in `clean_ohlcv_for_features`) is gated on Stage B and a golden-
master regeneration (W-01 in `long_horizon/audit/wiring_issues.md`).

**Any corporate-action change:** see [`data-quality`](../data-quality/SKILL.md) first.

### 2.4 Macro/sector column lists — `data/feature_enrichment.py` (v1 path only)

For the v1 14-day model (now retired), `data/feature_enrichment.py` was the single source
of truth for `ENRICH_MACRO_COLS`, `ENRICH_SECTOR_COLS`, `MACRO_DEFAULTS`, `SECTOR_DEFAULTS`.
The long-horizon live cron does NOT call `enrich_with_layers` (grep confirms zero references),
so the macro/sector columns that caused drift in the v1 era do not affect the long-horizon
path. If you ever add a macro or sector feature to the long-horizon path, it must be
added via `_compute_stock_features` in `data_store.py` — not via `enrich_with_layers`.

### 2.5 In-code fallback constants vs JSON

`long_horizon/config.py` contains Python constants (`STOP_ATR_MULT = 3.67`, etc.) that
are fallbacks when `models/long_horizon/config.json` is absent. These must stay in sync
with the JSON. After any cfg change, verify both:
```python
from long_horizon.config import load_frozen_cfg, STOP_ATR_MULT
cfg = load_frozen_cfg()
assert cfg["stop_atr_mult"] == STOP_ATR_MULT   # should be True
```

---

## Part 3 — Live-vs-Backtest Parity Points

The Phase-1 wiring audit confirmed the following are byte-identical between live and
backtest. If you change any of them, re-run the golden master.

| What | How parity is maintained | Risk if it drifts |
|---|---|---|
| Exit logic | Both call `engine.exit_logic.decide_exit` | Wrong stop/target/time exits in live |
| Gap-fill stop | Live now passes `today_ohlc={open: current_open}` (W-05 fix) | Optimistic stop fills in live — corrupts paper track record |
| Position aging | Live uses `exit_days_held = max(0, days_since - 1)` (W-11 fix) | Min-hold / 63d cap fire one session early in live |
| Sizing kernel | Both call `base_risk_qty` from `portfolio.py` | Different share counts live vs backtest |
| ADV cap | Both read `max_adv_participation_pct` from frozen cfg (not the function default) | Different position caps for names near the 5% ADV floor |
| Vol-target scalar | Both call `vol_target_scalar` from `portfolio.py` | Different de-gross in high-vol regimes |
| OHLCV cleaning | Both call `clean_ohlcv_for_features` via `ohlc_panel.clean_ohlcv_dict` | Adjusted vs unadjusted price mismatch within a trade |

**Items NOT yet at parity (deferred):**
- Kill-equity curve books entry at `close(t)`, not `open(t+1)` (W-12, deferred).
  Portfolio history is ~1.4% optimistic on the entry leg.

---

## Part 4 — Canonical Maps (start here for deeper exploration)

| Need | File |
|---|---|
| File-level inventory of every committed file | `FILE_MAP.md` (root) |
| Phase-1 wiring audit — all 21 W-id findings | `long_horizon/audit/wiring_issues.md` |
| Phase-1 fixes — what was actually changed | `long_horizon/audit/PHASE1_FIXES.md` |
| Full wiring diagram (live path, module-to-module) | `long_horizon/audit/wiring_report.md` §(b) |
| Roadmap (Stages A–G, gates, owner decisions) | `docs/ROADMAP.md` |
| Strategy full spec (all formulas, parameters, KILLs) | `long_horizon/STRATEGY_FULL.md` |
| KILL ledger (levers already rejected — do not re-open) | `long_horizon/STRATEGY_FULL.md §11` |
| Pre-registration log | `long_horizon/preregistry/` |
| Honest baseline numbers | `research/baseline_v0.json` |
| Frozen cfg (production values) | `models/long_horizon/config.json` |
| Feature contract (8 factors, signs) | `long_horizon/features/contract.py` |
| Governance protocol (when/how to change frozen cfg) | `docs/LIVE_OVERLAY_PROTOCOL.md` |

---

## Part 5 — Procedure Before Changing a Formula or Value

**Before touching any value, formula, or structural file:**

1. Open this map. Find the section for the value you want to change. Read "who else reads this."
2. If the value is in `models/long_horizon/config.json` or `long_horizon/config.py`: this is
   a **heavy-path re-derivation** per `docs/LIVE_OVERLAY_PROTOCOL.md`. It requires a full
   walk-forward, a new baseline JSON, and a golden-master regeneration in the same PR.
3. If the value is in `long_horizon/backtest/portfolio.py` (`base_risk_qty`, `vol_target_scalar`,
   `simulate`, `compute_metrics`): run the golden master immediately after the change.
   Any byte difference = the change is live. Decide intentionally.
4. If the value is `decide_exit` in `engine/exit_logic.py`: same golden-master requirement
   as 3. The live signal tracker and the backtest both call this — a change affects both.
5. If the value is a cost constant (brokerage, STT, slippage): update all three locations
   (§2.1 above). The golden master does NOT catch cost-only drift.
6. If the change touches the solvency filter or the universe mask: grep for inline copies (§2.2).
7. After any change to a file in the live cron path, check the parity table (Part 3) and
   confirm every live-vs-backtest pair is still symmetric.
8. Update `FILE_MAP.md` + this skill if you add or remove a file or change a file's role.
   One-line edit, same PR. A stale map is worse than no map.

**After the change:**
```bash
python -m diagnostics.build_golden_fixture   # if engine changed
python -m pytest tests/test_long_horizon_golden.py -v   # must be byte-identical or intentionally regenerated
python -m pytest tests/ -v --tb=short        # full suite (1,814 passed as of Phase-1)
```

---

## Cross-references

- [`data-quality`](../data-quality/SKILL.md) — OHLCV cleaning, split vs demerger, the VEDL
  lesson, corporate-action hygiene. Open before any OHLCV/CA change.
- [`backtest-rigor`](../backtest-rigor/SKILL.md) — before trusting any harness number;
  covers the survivorship, lookahead, and multiple-testing guards.
- [`overlay-testing`](../overlay-testing/SKILL.md) — the promotion bar and pre-registration
  framework for Stage C/D work.
- [`sell-replace-logic`](../sell-replace-logic/SKILL.md) — capital reallocation (Stage D);
  the `reallocation_enabled` flag in `portfolio.simulate` is the backtest entry point.
- [`research-log`](../research-log/SKILL.md) — where findings go after a map-informed change.
