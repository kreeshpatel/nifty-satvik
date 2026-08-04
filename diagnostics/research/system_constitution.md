# System Constitution — the live weekly-swing (bhanushali) path

**Audit date:** 2026-07-29 · **Session class:** read-only code audit — zero screens spent, zero
trials spent, no tests run against outcomes. **Program counts as of this audit (unchanged by it):
screens 11, sealed opens 1, n_trials 138.** Forward-wall performance logs were not read
(no-peeking holds); every row below is sourced from code, not results.

> **REMEDIATED 2026-07-29** (same day, separate session — see the log below). A golden master for
> the live engine was built **first**, then three defects were fixed against it, each with a
> committed diff. Rows that moved are marked **✅ REMEDIATED** in place with their fix commit; the
> DIVERGENT list in §2 has shrunk from 9 to 6. Counts still unchanged.
>
> | Item | Fix | Commit |
> |---|---|---|
> | **M1** — no golden master for R94 | Byte-identical golden: frozen-0094 cell, live cell, B-1 diff cell, card arithmetic; hermetic synthetic fixture | `1170470` |
> | **B-1** — absent-bar holdings freeze and mark at entry | `stale_absent_days` (= momentum's `STALE_ABSENT_DAYS` 10), force-close at last traded price; census first found **zero instances to date**, so it landed with a provably zero record diff | `0c7e490` (census), `d3b4d5e` (fix) |
> | **D5** — cards priced off the raw week-low, book off the lifted stop | Cards now use `_record_stop()` reading `LIVE_DISCIPLINE`; targets + all tranches re-derived; `ext_cap` skip surfaced | `66491e3` |
> | **D2** — mutable forward record | Write-once dated snapshots + input fingerprint + restatement/drift log, wired into the Saturday cron; baseline `results/archive/2026-07-24/` | `7e016b9` |
> | **B-2 (doc half)** — cron docstring described a superseded engine and a nonexistent backstop | Docstring corrected; the missing time cap is an owner decision, not a fix | `7e016b9` |
>
> Free diagnostics run (no trials, no screens): **M2** hold-age, **M6** demerger scan, **M7**
> universe freshness — reports in this directory. M2's result **changed a binder recommendation**.
> Owner doors: [oct1_binder_decisions.md](oct1_binder_decisions.md).

**What "the live system" is.** The live model is the weekly-swing book
(`weekly-swing-0094-rank-P`). Two GitHub Actions crons run it:

1. `.github/workflows/cron-bhanushali-scanner.yml` — Saturday 18:00 IST. Runs
   [scripts/run_bhanushali_cron.py](../../scripts/run_bhanushali_cron.py), which refreshes OHLCV,
   re-runs the 0094 engine (`scripts/run_bhanushali_weekly_rank.py`, "R94") **from inception
   2026-07-04 each time**, and commits the dashboard envelope (`results/*_weekly.*`) to `main`.
2. `.github/workflows/cron-bhanushali-monitor.yml` — weekdays 16:15 IST. Runs
   [scripts/run_bhanushali_monitor.py](../../scripts/run_bhanushali_monitor.py), an observational
   re-pricer of the frozen Saturday cards, plus the forward-data accumulators sidecar.

The book of record is **modeled fills** (forward-watch): no broker connection, no fill ingestion.
The owner executes manually off the dashboard cards; the paper NAV/ledger is what the engine says
would have happened, not what the owner did.

Classes: **DELIBERATE** (chosen and examined — finding/pre-reg cited), **CONVENTION** (chosen,
never examined), **INCIDENTAL** (fell out of the implementation), **DIVERGENT** (live applies one
thing, the backtest-of-record another — or the card the owner acts on differs from the book that
records it).

"Backtest parity" below compares the live cron run against the **0094 run of record**
(`run_bhanushali_weekly_rank.py::main`, Sharpe 1.132 / 255 trades, corrected universe, all live
overlays OFF) — the same `backtest()` function, so *engine* parity is by construction; the
divergences are in **data, universe, and the switched-on owner overlays**.

---

## 1. The rules table

### A. Scheduling and calendar

| # | Rule | Where | What it does | Class | Backtest parity | Risk if wrong |
|---|------|-------|--------------|-------|-----------------|---------------|
| A1 | Saturday-evening recompute cadence | cron-bhanushali-scanner.yml:15 (`30 12 * * 6`); run_bhanushali_cron.py:9-12 | Signals are computed once weekly, after Friday's close, from Saturday's download | DELIBERATE (weekly-close cadence is the strategy definition; docstring + monitor guard both encode it) | Backtest decides at weekly close too — same bar | A silently skipped Saturday leaves stale cards; see K4 |
| A2 | Buy window = the FULL trading week after the setup Friday | run_bhanushali_cron.py:241-246 (`buy_window_until = fri+7d`); R94:326-328 (`edays = weeks[k+1]`) | Owner may buy Mon–Fri of the following week; engine attempts fills on each day of that ISO week | DELIBERATE (fault fix 2026-07-13; matches engine window) | Identical — engine window is the source | Backend fallback (2-calendar-day momentum rule, nq_positions.py:164-169) would wrongly close Friday signals by Monday if the field were dropped |
| A3 | Week = ISO calendar week (Mon–Sun), weekly bar = ticker's own trading days in that ISO week; "weekend" = the ticker's last trading day of the week | R94:67-78, 307 | Weekly OHLC aggregation and the decision bar. A Saturday NSE special session lands in the same week and becomes the decision day | CONVENTION (0117 confirmed SIGNAL anchor-robustness; the live consumer uses this same ISO grouping — verified here — but the choice itself was never separately examined for the swing book's exits) | Identical both sides | Different anchor (W-FRI resample) would shift some weekly closes; 0117 says signal is robust, exits untested |
| A4 | Completed-week guard: only surface cards from a COMPLETED weekly bar; a mid-week run steps back one week | R94:330-343 (`weekday() >= 4` = complete; `li -= 1` if partial) | Prevents signals off a partial weekly bar; a Monday-data run still shows last week's buys | DELIBERATE (fault F7 + 2026-07-13 fix, cited in code) | Backtest only ever sees completed weeks | Without it, partial-bar signals emit/retract mid-week |
| A5 | Monday holiday ⇒ fills/exits execute on the ticker's next available bar | R94:411-415 (pending executes on the next bar the ticker trades); entry loop iterates every day of the window | No special holiday handling needed; the day-loop naturally lands on Tuesday | INCIDENTAL (emergent from the day-loop; nobody chose "Tuesday") | Identical both sides | None material — matches what an owner told "sell Monday open" would actually do on a holiday |
| A6 | Quarterly-review dates = first trading day of Jan/Apr/Jul/Oct per `NSE_HOLIDAYS` | bhanushali_review_scorecard.py:40-48 | The Oct-1 promote/kill machinery's calendar | DELIBERATE (forward/prereg.md §8) | n/a (governance) | `NSE_HOLIDAYS` ends at 2026-12-25 (config.py:170-174) — 2027 review dates could land on an unlisted holiday; see menu item M10 |

### B. Data acquisition and refresh

| # | Rule | Where | What it does | Class | Backtest parity | Risk if wrong |
|---|------|-------|--------------|-------|-----------------|---------------|
| B1 | Download universe = `build_universe("current")` = the pinned `NIFTY_500` snapshot (2025-07-20, 500 names) | run_bhanushali_cron.py:434; run_cpcv.py:58-67; config.py:76-77 | Only snapshot names are ever downloaded/scanned live | **DIVERGENT** (D1) | Run of record uses `corrected_universe()` (pinned + backfill + delisted aliases, run_bhanushali_path1.py:26-41) | Post-snapshot index entrants are invisible to the live book; survivorship direction flatters the backtest (finding 0025: bias scales with hold; this book has no time cap) |
| B2 | Data source = yfinance `auto_adjust=True`; all signal math runs on adjusted prices | nq/data/ohlcv.py:266-306 (293) | Splits/dividends back-adjusted into history each fetch | CONVENTION (inherited from the momentum path; never separately examined for the swing book) | Run of record uses the pinned blob (same yfinance basis, frozen) | Adjusted last-week band edges can differ from the raw prices on the owner's broker after an ex-dividend week (see D5) |
| B3 | Per-ticker incremental refresh: warm names get a 25-day top-up; cold/thin (<300 bars) get full history from inception−520d | run_bhanushali_cron.py:406, 435-447 | Cheap weekly refresh; a transient yfinance miss keeps cached bars | DELIBERATE (2026-07-18, resilience rationale in docstring) | Backtest data is static — no equivalent | A miss silently serves week-old bars for that name (guarded by A4 stepping back) |
| B4 | Corporate-action guard: >0.5% shift on an overlapping close ⇒ full clean re-fetch of that ticker | run_bhanushali_cron.py:407, 448-453, 460-479 (`ADJ_JUMP`) | Prevents mixed adjustment bases poisoning the 44-week SMA | DELIBERATE (documented rationale; monthly cache-key roll bounds residual drift) | Pinned data never re-adjusts | Sub-0.5% dividend drift persists until the monthly rebuild (menu M9) |
| B5 | Monthly cache rebuild: the actions/cache key rolls with the month; first run each month re-downloads everything on one adjustment basis | cron-bhanushali-scanner.yml:41-57 | Bounds slow adjustment drift | DELIBERATE (comment in workflow) | n/a | A yfinance outage on the month's first Saturday = cold run on empty cache; falls back per B3's exception handler (run_bhanushali_cron.py:455-457) to an EMPTY book rather than crashing |
| B6 | yfinance `end` is exclusive → bumped +1 day so the just-closed session is included | nq/data/ohlcv.py:279-286 | Fixes the one-day-stale dashboard bug | DELIBERATE (bug documented in code) | n/a | Regression re-introduces the stale-day lag |
| B7 | Names with <50 usable bars are dropped by the downloader; <300 cached bars excluded by `prep` | nq/data/ohlcv.py:301; run_bhanushali_sixstep.py:63 | Warm-up floor for the 44-week SMA | INCIDENTAL (300 chosen as "can't warm up the SMA", never examined as a universe rule) | Same filter both sides | Recently-listed names flicker into the universe the week they cross 300 bars (menu M8) |
| B8 | **No OHLCV cleaner on this path**: `clean_ohlcv_for_features` (holiday phantom bars, bad ticks, demerger-aware back-adjust) is never called; no demerger quarantine | run_bhanushali_cron.py:568 → sixstep prep:59-89 (raw frames) — contrast nq/data/ohlcv.py:84-207, 245-261 | The swing engine trusts yfinance adjustment plus B4's re-fetch guard | CONVENTION (shared by the run of record — so NOT a parity gap; but nobody decided the swing book should skip the demerger guard the momentum path has) | Parity holds (both raw) | A value-leaving demerger mid-hold appears as a huge red weekly bar: distorts the 44w SMA, can trigger a spurious stop/sma_break — or a fake "touch" for entry (menu M6) |
| B9 | CRS denominator = pinned Nifty-50 CSV, refreshed from `^NSEI` with `auto_adjust=False`; fetch failure falls back to the committed series | run_bhanushali_cron.py:482-500; R94:62 | The RS ratio's denominator | DELIBERATE (finding 0037: Nifty-50 is the owner-intended index) | Same CSV both sides | A silently stale index ffills forward (R94:99) — RS levels drift up, ranks mostly preserved (ffill is uniform across names) |
| B10 | Membership file = `data/nifty500_membership.csv`, committed, manually refreshed (last write 2026-06-29); current members carry a 2030-12-31 sentinel; 500 rows active today | nq/data/membership.py:37, 88-94; file inspected | Entry gate (F2) and card gate (E1) consult it | CONVENTION (no refresh automation; cadence unexamined) | Backtest uses the same file with historical periods (PIT) | Sept semi-annual rebalance before the Oct-1 review: removed names keep trading live, added names never appear (menu M7) |
| B11 | `load_membership()` returns None when the file is missing → **all membership filtering silently disables** | nq/data/membership.py:63-65; R94:716 (`mem is None or …`); cron:227 | Fail-open design | INCIDENTAL (a graceful-degrade default nobody revisited for the live path) | Backtest would fail-open identically | A bad checkout/path regression silently trades non-members with no error |

### C. Signal computation (the frozen 0093-N50 rule set)

| # | Rule | Where | What it does | Class | Backtest parity | Risk if wrong |
|---|------|-------|--------------|-------|-----------------|---------------|
| C1 | The line is a 44-**week SMA** of weekly closes — never EMA | R94:84 (`rolling(44).mean()`); also `wsma_at` R94:314; audit panel cron:503-511 | The entry/runner reference | DELIBERATE (owner mandate; R94 conformant, W89's EMA path quarantined — memory `swing-line-is-sma-not-ema`) | Identical (same array) | EMA would change every touch/exit |
| C2 | Slope floor: 44w SMA up ≥3% over 13 weeks | R94:40, 92, 192 | Uptrend gate | DELIBERATE (pre-reg 0093; kept from 0092) | Identical | — |
| C3 | Touch: week's low ≤ SMA×1.07 AND weekly close > SMA | R94:40 (`TOUCH_BAND=0.07`), 95, 192 | The pullback definition (loose band restored per finding 0035) | DELIBERATE (0091/0093) | Identical | — |
| C4 | Quality green: close>open AND close in upper half of the week's range | R94:94, 192 | Bounce confirmation | DELIBERATE (0093) | Identical | — |
| C5 | CRS gate: weekly RS (close/Nifty-50) > its 40-week SMA; `crs_dist = RS/SMA40(RS) − 1` is the rank | R94:101-106, 192 | Comparative-strength filter + fill-priority score | DELIBERATE (0093 gate, 0094 rank; rank-IC pre-declared) | Identical | — |
| C6 | Index series is forward-filled onto stock trading days before weekly sampling | R94:99 | Handles index/stock calendar mismatches | INCIDENTAL (a reindex default) | Identical | ffill across a long index gap would freeze the denominator — benign while B9 refreshes daily |
| C7 | All research levers in `prep_weekly_rank`/`backtest` (box/trend/SR/zoo entries, hard_stop, disaster floor, chandelier, etc.) default OFF; live passes only `LIVE_DISCIPLINE` + `LIVE_EXIT` | R94:43-56, 367-386; cron:574-580 | The frozen 0094 signal set + owner overlays, nothing else | DELIBERATE (cfg-gating is the engine invariant) | Run of record = all defaults; live = discipline+P on (see D3) | A default drifting from the frozen value silently changes both books — guarded only by the pre-reg record, no golden master exists for this engine (menu M1) |
| C8 | Signal-week stop reference = the signal week's LOW (`_stop_arr = wlow`) | R94:199, 326-328 | 1R definition at signal time | DELIBERATE (taught rule) | Identical | — |
| C9 | Weekly ATR(10) and 20-week SMA are computed and carried but read by NO live code path (`stop_atr_mult`, `wk20_trail_pct` off under P) | R94:89-91, 311, 719 | Dormant data plumbing | INCIDENTAL | Inert both sides | None while dormant |

### D. Grading and selection

| # | Rule | Where | What it does | Class | Backtest parity | Risk if wrong |
|---|------|-------|--------------|-------|-----------------|---------------|
| D1g | Grade A = top-5 by CRS distance among the setup week's signals; **only A is surfaced and only A is traded** | R94:347-364 (`grade_a_entries`, `top_n=5`); cron:255-260, 569-571 | The owner rule "never surface or buy Grade B" | DELIBERATE (owner rule; A-only-vs-all-grades routed to the forward wall, memory `swing-forward-wall-decision`) | Run of record trades ALL signals (a_grade=None) — the A-only live book is the §10.2 watched variant, a recorded difference | — |
| D2g | The engine's A-set and the card's A-set are computed differently: `grade_a_entries` takes top-5 of ALL signals (no membership / entry>stop filter); the card list filters membership + `entry<=stop` FIRST, then takes top-5 | R94:347-364 vs cron:226-260 | Two top-5 sets that can disagree at the margin | INCIDENTAL | Book uses the engine set | A non-member (or degenerate-band) name in the global top-5 consumes a book slot it can never fill, while the card promotes the global #6 the book will never buy — owner buys a name the record doesn't hold (see DIVERGENT list, D6) |
| D3g | A name held from a PRIOR week is suppressed from fresh-buy cards; a name entered THIS (incomplete) week stays a BUY card | cron:261-274 | Fixes the 2026-07-13 all-cards-showed-HOLD fault | DELIBERATE (fault documented) | n/a (presentation) | Regression re-breaks mid-week runs |

### E. Order construction — the cards the owner acts on

| # | Rule | Where | What it does | Class | Backtest parity | Risk if wrong |
|---|------|-------|--------------|-------|-----------------|---------------|
| E1 | Card membership gate: only currently-listed index members get cards (checked on the setup Friday) | cron:226-228 | No cards for non-members | DELIBERATE (forward book trades listed names only) | Book checks membership at activation day instead (R94:716) — one-trading-day skew, benign | — |
| E2 | Card **entry** = current close if inside the band, else band midpoint; card **stop** = **the record's stop** `max(week_low, entry×(1−max_risk_pct))`; **target** = entry + 2×(entry−stop); raw low surfaced as `stop_week_low`; `ext_cap` skip surfaced as `record_would_skip_as_extended` | cron `_record_stop`/`_ext_flags` + the card block | The prices printed on the buy card | ✅ **REMEDIATED** (`66491e3`) → DELIBERATE. Was DIVERGENT D5 (card used the raw low, book the lifted stop, so even the blow-off arm and runner lines were mispriced) | **Parity restored** — card stop/target/tranches are the arithmetic the book books. Pinned as a *relationship* in `tests/test_swing_card_record_parity.py` + golden `fresh_cards` receipt (MIKEX: stop 3176.06→3328.92, target 4744.28→**4438.56**) | Regression would resume telling the owner a different R and a +2R limit ~6.9% off the booked tranche |
| E3 | Buy instruction: "buy Mon–Fri this week, at the open inside the band [low, high] — fund strongest CRS rank first" | cron:250-253 | Human protocol mirroring the engine's fill rule | DELIBERATE | Mirrors F1 | — |
| E4 | Exit-plan card derives tranches from `LIVE_EXIT` (single swap point); nothing downstream hard-codes config P | cron:79-153 | 40% @+2R resting limit / 40% blow-off pattern (Sat decides) / 20% runner to the 44w SMA | DELIBERATE (Stage-1 config-swappable interface) | Card tranche math uses the model's lifted stop for HELD cards (cron:296) — consistent with the book | — |
| E5 | Pending weekly-close exits render as SELL-Monday-open cards (`EXIT_REQUIRED` + reason text) | cron:304-320 | The Saturday run tells the owner exactly what to sell Monday | DELIBERATE | Book fills the same exit at the next bar's open (R94:411-421, 444-461) — parity | — |
| E6 | Closed-trade exit reasons map to the legacy status vocabulary (`pattern`→HIT_TARGET, `sma_break`→HIT_STOP, `eos`→EXPIRED…) | cron:86-91 | Frontend compatibility | INCIDENTAL | Presentation only | Analytics grouped by these labels blur distinct exit mechanisms |
| E7 | Decision memos (APPROVED/WATCHLIST/REJECTED rubric) generated per signal — reporting only | cron:595-605 | Logs the owner's manual call against a fixed rubric | DELIBERATE (forward_plan Tier-3; fights measured execution-decay) | n/a | — |
| E8 | Regime chip = breadth/strength heuristic (≥60% above 10-bar SMA & advancers>decliners = BULL, ≤40% & negative = BEAR, else CHOPPY); VIX hardcoded 0 (dashboard overlays live quote) | cron:168-209 | Display-only context | CONVENTION (thresholds never examined; O-001 regime gating stays killed for the base) | Not an input to any trade decision | None while display-only |

### F. Modeled fills (the book of record)

| # | Rule | Where | What it does | Class | Backtest parity | Risk if wrong |
|---|------|-------|--------------|-------|-----------------|---------------|
| F1 | Fill = the FIRST day in the entry week whose OPEN is strictly inside (low, high); fill price = that open | R94:724-726, 759-775 | The in-range-open entry (0089 convention) | DELIBERATE (0089; buy-stop alternative tested and rejected, pre-reg 0088) | Identical engine | Strict `<` boundaries: an open exactly at the band edge is no fill (menu M3) |
| F2 | Activation requires: not already held, no live order, Grade-A, index member on activation day | R94:713-716 | Entry eligibility | DELIBERATE | Identical | — |
| F3 | Extension cap: skip the fill if the open is >20% above the signal-week SMA | cron:53-54 (`ext_cap=0.20`); R94:765-767 | Owner risk-appetite override ("selection, not stop truncation") | DELIBERATE (docs/decisions/0009; measured Sharpe 1.004→1.055, NOT certified — recorded owner override) | **Off** in the run of record (D3) | — |
| F4 | Fill priority under the cash cap = strongest CRS first, ties alphabetical by ticker | R94:786-800 (`_key`, sorted) | Who gets scarce cash | DELIBERATE (the 0094 change itself) / tie-break INCIDENTAL | Identical | Alphabetical tie-break is invisible bias at equal rank (measure: menu M4) |
| F5 | Unfilled orders expire at the end of the entry week | R94:859-863 | No carry-over chasing | DELIBERATE (taught rule) | Identical | — |
| F6 | Two books per run: capital-capped ₹10L paper book (NAV) + UNCAPPED ledger (every A signal, fixed-EQ0 sizing) drives the signals page | cron:572-580; R94:394-397, 783-785 | Signal lifecycle tracked independently of affordability | DELIBERATE (documented dual-book design) | Run of record = capped book | Confusing the two books' stats (uncapped NAV is meaningless by design, R94:397) |
| F7 | No broker/fill feedback: the book records MODELED fills regardless of what the owner actually did | run_bhanushali_cron.py:14-17 (docstring); no ingestion code exists | Forward-watch record, not a ledger | **DIVERGENT** (D4) by explicit design | n/a | The paper record and the owner's real book are two different equity curves; gates (scorecard) read the modeled one |

### G. Exits and position management (config P live)

| # | Rule | Where | What it does | Class | Backtest parity | Risk if wrong |
|---|------|-------|--------------|-------|-----------------|---------------|
| G1 | Tranche 1: 40% at entry+2R, filled intraweek AT the level when the week's high touches it (resting limit) | cron:76-77; R94:553-578 | The banked base hit | DELIBERATE (docs/decisions/0010; owner override, FAILS the 2022-26 gate — recorded) | **Off** in run of record (D3) | Gap-up through the level books AT the level (real limit fills at the better open) — model conservatively understates; direction favors live |
| G2 | Tranche 2: 40% on the blow-off pattern — a new-high week closing in its lower third, armed at MFE ≥ +2.5R; decided at weekly close, filled next bar's open | cron:76-77; R94:617-628 | The exhaustion tell (validated exit; entry-zoo IC≈0, finding 0079) | DELIBERATE (0010) | Off in run of record | — |
| G3 | Runner 20%: held until a weekly CLOSE below the 44-week SMA (no buffer); filled next bar's open | cron:76-77; R94:630-632 | Trend-death exit | DELIBERATE (0010) | Off in run of record | — |
| G4 | Stop: weekly CLOSE ≤ stop ⇒ sell remainder at next bar's open. **No intraday stop of any kind live** (hard_stop KILLED 0105; disaster floor 0109 not adopted) | R94:623-624, 501, 529 (both off) | Weekly-close-confirmed risk line | DELIBERATE (0105 kill recorded; disaster floor is an un-adopted pre-reg) | Identical (both weekly-close) | Intra-week collapse fills at Monday's open, far below the stop — real and modeled alike; the card warns via the monitor (STOP_BREACH flag) |
| G5 | The stop NEVER moves after entry under config P (no breakeven ratchet, no trail; `p["stop"]` untouched in the scaled branch) | R94:603-635 (no stop mutation) | Initial risk line is the only risk line until SMA break | CONVENTION (implied by 0010's three-tranche design but never separately examined) | Identical | Post-tp1 givebacks ride back through breakeven to the full stop (menu M5) |
| G6 | **No time cap at all**: the scaled-exit weekly branch `continue`s before the cap check, so neither the 13-week cap nor P2's 52-week backstop ever applies | R94:603-635 (continue at 635) vs 704-706 (unreached) | Positions can be held indefinitely until stop/SMA-break/targets | INCIDENTAL⚠ (docs/decisions/0010 chose "no cap"; but the 52-week BACKSTOP that P2 carried silently vanished with the P swap — cron:42-48 docstring still describes the backstop) | Identical engine behavior both sides when P is on | A name that hugs its rising SMA forever is never force-reviewed; HOLD_DAYS_DISPLAY=65 on the card is fiction (cron:42-43) |
| G7 | Tranches book in order (tp2 requires tp1); pattern tranche requires not-already-booked; realized R accumulates by fraction | R94:557-576, 625-628 | Deterministic tranche sequencing | INCIDENTAL (implementation ordering) | Identical | — |
| G8 | Exit R accounting: `R = realized_r + frac_left × r_rest`; costs (brokerage+STT+tiered slippage) on every leg, buy-side STT included | R94:439-452; sixstep:52-56; config.py:45-48; nq/engine/portfolio.py:61-75 | Net-of-cost trade records | DELIBERATE (cost model shared with research runs) | Identical | Cost constants live in config.py + faithful's local COST_LEG (drift hazard noted in repo-map §2.1) |
| G9 | Positions absent today's bar: after `stale_absent_days` (=10, the momentum engine's `STALE_ABSENT_DAYS`) consecutive absent sessions the position is force-closed at its **last traded price**, reason `stale`, with `stale_absent_sessions` on the ledger row | R94 absent-bar branch; `LIVE_STALENESS` in cron; `nq/engine/portfolio.py:43` (shared constant) | Stale-position handling, live | ✅ **REMEDIATED** (`d3b4d5e`) → DELIBERATE. Was INCIDENTAL⚠ / bug B-1 | cfg-gated: default OFF ⇒ frozen 0094 byte-identical; ON in the live cron. Golden pins both cells + asserts the diff is isolated to the stale name | Regression re-freezes suspended holdings; guarded by `test_b1_fix_diff_is_isolated_to_the_stale_position` |

### H. Sizing and cash

| # | Rule | Where | What it does | Class | Backtest parity | Risk if wrong |
|---|------|-------|--------------|-------|-----------------|---------------|
| H1 | Risk sizing: shares = sizing_equity × 2% / (entry − stop) | R94:799, 829; sixstep:46 (`RISK=0.02`) | Fixed-fractional risk | DELIBERATE (frozen 0084 line) | Identical | — |
| H2 | Stop lift: stop = max(signal-week low, entry × 0.90) — caps R at 10% | cron:55-57 (`max_risk_pct=0.10`); R94:821-822 | Owner override that DEVIATES from the taught candle-low rule (explicitly acknowledged in code) | DELIBERATE (docs/decisions/0009; return-neutral, uncertified — recorded) | **Off** in run of record (D3) | — |
| H3 | Notional cap: no name exceeds 20% of sizing equity | cron:58-60; R94:834-835 | Anti-concentration guardrail (concentration is load-bearing — FINDING_more_slots cited in code) | DELIBERATE (0009) | Off in run of record | — |
| H4 | Sizing equity = current mark-to-market equity (paper book) or fixed ₹10L (uncapped ledger), × vol-target scalar (OFF live) | R94:776-785; faithful:27 (`EQ0=1_000_000`) | Compounding risk base | CONVENTION (mark-to-market compounding never examined vs fixed-base for this book) | Identical | — |
| H5 | Cash is the ONLY capacity constraint: no max-positions cap live (`max_positions=0`), buy skipped if notional+costs > cash (`skipped_cash`) | R94:804-805 (inert), 836-837, 858 | Frozen 0084 philosophy ("cash-limited only") | DELIBERATE (0084 pre-reg) | Identical | — |
| H6 | **Fractional shares**: share count is a float; no integer rounding, no lot handling, no minimum order | R94:829 (`sh = …` never floored) | Modeled sizing precision | **DIVERGENT** (D7) vs the owner's integer-share reality (contrast: momentum path's `base_risk_qty` floors) | Backtest identical (shared fiction) | Small-price × small-book distortion; at ₹10L/2% risk the error is bounded but nonzero per trade |
| H7 | Sizing invariants enforced by `assert` — a violation CRASHES the whole cron run | R94:848-851, 866 | Fail-loud on sizing bugs | INCIDENTAL (assert-as-guard in a production path) | Same asserts in research runs | One pathological candidate (en≈st float dust) aborts Saturday's entire publish, leaving stale cards (see K4) |

### I. NAV, ledger, analytics

| # | Rule | Where | What it does | Class | Backtest parity | Risk if wrong |
|---|------|-------|--------------|-------|-----------------|---------------|
| I1 | NAV = cash + Σ shares × today's close; a name missing today's bar marks to its **last traded close** while the staleness gate is on (gate off ⇒ the old entry-price mark, for byte-identity) | R94 NAV line + `_absent_mark` | Daily mark | ✅ **REMEDIATED** (`d3b4d5e`) → DELIBERATE. Was INCIDENTAL⚠ (the `else p["en"]` fallback) | Gate off ⇒ identical to the frozen run | Regression re-flatters NAV, which the Oct-1 gates read |
| I2 | The book is still **recomputed from inception every run**, but each run now writes a **write-once dated snapshot** (book, NAV, ledger, analytics + input fingerprint: OHLCV/membership/index sha256 + engine config) and appends a **drift row** recording restated / vanished / appeared closed trades and the NAV delta | `scripts/archive_weekly_snapshot.py`; scanner workflow archive step; `results/archive/` | Mutable working copy, immutable audited record | ✅ **REMEDIATED** (`7e016b9`) → DELIBERATE. Was DIVERGENT D2 | Baseline `results/archive/2026-07-24/`. **Gates must read a named snapshot** — scorecard still reads the working copy (deliberately not repointed mid-quarter; binder §0) | Recomputation drift is now attributable, not silent; yfinance mutability itself is unchanged by design |
| I3 | Open positions are NOT marked-to-close in the live state (`return_state=True` skips the end-of-series realization) | R94:869-885 | Correct live semantics (eos is a backtest convention) | DELIBERATE | Run of record realizes at window end (`eos`) — a recorded convention difference in TRADE COUNT, not engine logic | — |
| I4 | Scorecard gates (Oct-1): ready = ≥40 closed OR 4 quarters; PROMOTE = expectancy>+0.10R AND MaxDD>−25%; KILL = Sharpe<0; HALT = MaxDD≤−50%; Sharpe/MaxDD computed from the recomputed NAV CSV | bhanushali_review_scorecard.py:30-36, 51-75 | Mechanical pre-committed review | DELIBERATE (forward/prereg.md §4/§8/§10.2) | n/a | Inherits I1/I2's NAV fragility; gates evaluated on a mutable curve |
| I5 | Analytics: win = R>0; avg_r, win_rate from closed ledger only | cron:363-371 | Envelope stats | INCIDENTAL (R>0 counts a +0.001R scratch as a win) | Same convention as research prints | — |

### J. Intra-week monitor and dashboard delivery

| # | Rule | Where | What it does | Class | Backtest parity | Risk if wrong |
|---|------|-------|--------------|-------|-----------------|---------------|
| J1 | The daily monitor NEVER recomputes signals or moves frozen levels; only the +2R target tranche is ever `actionable` intra-week; pattern + runner are watch-only ("Sat decides") | run_bhanushali_monitor.py:8-14, 80-125 | Protects the weekly cadence the record is certified on | DELIBERATE (keystone cadence rule, documented at length) | Matches engine semantics (tp1 intraweek limit; pattern/runner weekly-close) | If it ever flips pattern/runner to actionable, the owner front-runs decisions the record makes at Saturday's close |
| J2 | Monitor buy-fill flag uses INCLUSIVE band (`lo <= open <= hi`); engine fill is STRICT (`lo < open < hi`) | monitor:248 vs R94:759 | Boundary mismatch | INCIDENTAL | — | Exact-boundary open: owner told "buyable", book records no fill (edge-case card/book split) |
| J3 | Monitor stop flag = daily close ≤ stop (`STOP_BREACH`, "weekly close will confirm"); NEAR_STOP at 2% | monitor:184, 234-243 | Lead-time warnings, honest about confirmation | DELIBERATE | Consistent with G4 | — |
| J4 | Monitor refresh downloads ~120 calendar days for card tickers only (50-bar downloader floor documented) | monitor:128-149 | Cheap daily re-price | DELIBERATE (empty-monitor bug documented in docstring) | n/a | — |
| J5 | Backend overlays monitor price WITHOUT touching frozen entry/stop/target; actionability read from cron-written field, fallback = buy_window_until, last resort = 2-calendar-day momentum rule | dashboard/backend/routers/signals.py:199-255; services/nq_positions.py:137-172 | Delivery-layer merge | DELIBERATE (PR2) / the 2-day fallback is INCIDENTAL legacy | n/a | If `buy_window_until` were ever dropped from cards, Friday signals silently close Monday (the pre-fix fault) |
| J6 | First-serve snapshot freeze (immutable floor) — each signal frozen the first time it is served; best-effort, never blocks serving | signals.py:422-428 | The one append-only record in the system | DELIBERATE (Stage-2) | n/a | Best-effort `except: pass` — a silent freeze failure loses the immutability floor with no alarm |

### K. State, failure, and timezones

| # | Rule | Where | What it does | Class | Backtest parity | Risk if wrong |
|---|------|-------|--------------|-------|-----------------|---------------|
| K1 | State store = git commits to `main` (results/*.json/csv); push = pull --rebase --autostash ×3 retries, RED on failure | scanner yml:71-95; monitor yml:50-68 | Publish mechanism; the silent-swallow bug (2026-07-11) is fixed and documented | DELIBERATE | n/a | A 3× push failure leaves computed-but-unpublished state; RED makes it visible |
| K2 | Concurrency: each cron has its own group, `cancel-in-progress: false`; scanner (Sat) and monitor (Mon–Fri) never overlap by schedule | scanner yml:17-19; monitor yml:18-20 | Duplicate-run guard | DELIBERATE | n/a | Manual `workflow_dispatch` of both simultaneously could race the git push (retry loop absorbs it) |
| K3 | Idempotency: recompute-from-inception means a re-run or missed run needs no state repair | cron:12 | Restart semantics | DELIBERATE | — | But see D8: a MISSED Saturday is healed with modeled fills the owner never saw |
| K4 | A crashed run (assert, download-code exception outside the guarded block) publishes NOTHING — dashboard silently serves last week's cards; cron_status STALE surfaces it in the UI | R94 asserts (H7); signals.py:405-407 | Fail-stop, stale-visible | CONVENTION | n/a | Owner acting on week-old FRESH cards if the STALE badge is missed |
| K5 | Timezones: schedules in UTC cron; `date.today()` on the runner is UTC — Saturday 12:30 UTC and weekday 10:45 UTC both map to the same IST calendar day, so date arithmetic holds; card week-logic uses the DATA's last date, not wall clock | yml schedules; cron:265-267, 582-583; monitor:50 | Consistent day framing | INCIDENTAL (works because both crons run afternoon-IST; nobody wrote a tz-safety layer) | n/a | Moving a cron near IST-midnight would silently shift `today` by a day |
| K6 | Local runs of the cron/monitor with downloads OVERWRITE `data/ohlcv.pkl` — the same path as the pinned research dataset (f8625a8f) | nq/data/ohlcv.py:38, 309-315; cron:454; monitor:145 | One path, two masters (CI cache vs local pin) | INCIDENTAL⚠ | Pinned runs verify by sha and would FAIL loudly after a clobber | A casual local `run_bhanushali_cron.py` without `--no-download` destroys the local pinned blob (recoverable via `gh release download dataset-pin-20260701`) |
| K7 | No kill-switch runs on this book: the momentum kill_criteria system is not wired here; the only automatic brake is the scorecard's DISPLAYED §4 halt (−50% MaxDD), which changes no behavior | scorecard:36, 100-111 (surfaces state, "NEVER … makes a decision") | Human-in-the-loop only | DELIBERATE (forward/prereg.md: log and leave alone; halt is mechanical but operator-executed) | n/a | Nothing in code stops new entries at −50%; it relies on the owner reading the scorecard |
| K8 | Forward accumulators sidecar: append-only, content-key dedup, 5-session staleness alarm, `\|\| true` (never blocks the monitor) | run_forward_accumulators.py:1-53; monitor yml:47-49 | Data collection only, analysis unauthorized | DELIBERATE (owner-signed 2026-07-28) | n/a | — |
| K9 | Blend-hybrid paper log runs after the scanner with `\|\| true` — observational, own output file | scanner yml:66-70 | Watched book (finding 0107) | DELIBERATE | n/a | — |

---

## 2. THE DIVERGENT LIST — **9 → 6 open** after the 2026-07-29 remediation

**Closed with receipts:** ~~D2~~ (append-only archive + drift log, `7e016b9`), ~~D5~~ (card/record
parity, `66491e3`), and the B-1 bug behind D-class NAV flattery (`d3b4d5e`). Their entries are kept
below, struck through, because a divergence that was once real is part of the record.

> Direction key: *flatters backtest* = the certified/recorded number looks better than live reality
> would; *flatters live record* = the modeled forward book looks better than the owner's real book.

**D1 — Universe: live trades the 2025-07-20 snapshot ∩ current members; the certified backtest ran the corrected (backfilled + delisted-alias) universe.**
Mechanism: cron:434 (`build_universe("current")`) + cron:561-563 (deliberate: backfill is a
backtest-only tool) vs path1:26-41. The engine is shared; the OPPORTUNITY SET is not. Worst case:
**flatters the backtest** — finding 0025 measured survivorship bias scaling with holding period,
and this book has NO time cap (G6), the configuration where the bias was largest (−0.18 Sharpe
class). Additionally, post-snapshot index entrants can never generate live signals, an
unmeasured live-side drag/gain. *Acknowledged in code; the snapshot's refresh cadence is not
automated (see M7).*

**~~D2~~ — CLOSED (`7e016b9`). The forward record is mutable: every Saturday rewrites the whole book from inception off refreshed data.**
*Resolution:* recomputation still happens (that is the design), but each run now archives a
write-once dated snapshot with an input fingerprint and logs restatements/vanishings against the
previous snapshot, so a rewritten past is an attributable event. Baseline
`results/archive/2026-07-24/`. **Residual owner action:** the Oct-1 gates must be pointed at a named
snapshot — `bhanushali_review_scorecard.py` still reads the mutable working copy (binder §0).
Original finding below.
Mechanism: cron:12 (docstring flags it as the finding-0035 TODO) + I2. yfinance history drift is
documented in-repo (ohlcv.py:330-335: identical commands produced CAGR 14.2/15.6/16.25). A
corporate-action re-adjustment or data revision can change PAST weekly bars → different past
signals/fills → a different "forward record" than the one previously published. Worst case:
**either direction, silently** — the Oct-1 gates (I4) are evaluated on a curve that is not
guaranteed to be the curve that was accruing. The only immutable trace is the dashboard
snapshot freeze (J6) and the git history of the committed envelopes.

**D3 — The live book runs a configuration the certified number never ran.**
Mechanism: the 0094 run of record (Sharpe 1.132, DSR 0.89 UNDERPOWERED) is all-defaults;
live switches on `LIVE_DISCIPLINE` (ext_cap 0.20 / max_risk_pct 0.10 / max_notional_pct 0.20)
and `P_EXIT` (40/40/20 scaled), each an owner-override with recorded in-sample measurement but
explicitly **no certification** (cron:44-77 records the P config FAILS the 2022-26 continuous
slice at 0.91 and runs −39.5% DD). Worst case: **flatters expectations** — anyone reading
"1.132 / 255 trades" as the live book's pedigree is reading a different strategy. This is a
DELIBERATE, documented divergence (docs/decisions/0009 + 0010), listed here because it is still
a live-vs-certified-backtest mismatch the constitution must carry.

**D4 — No fill feedback: the record is modeled, the owner's book is real, and nothing reconciles them.**
Mechanism: cron:14-17 by design (no-broker-connection decision, ADR 0011). Late, partial,
skipped, or extra owner fills leave zero trace in the record; the scorecard gates measure the
model, not the money. Worst case: **flatters the live record** whenever the owner's execution
is worse than the model's Monday-open fiction (the measured execution-decay that motivated the
decision memos, E7). The two-equity-curves problem, live.

**~~D5~~ — CLOSED (`66491e3`). Card prices ≠ book prices for the SAME trade.**
*Resolution:* the card now prices off `_record_stop()` — the engine's own
`max(week_low, entry×(1−max_risk_pct))` read from `LIVE_DISCIPLINE`, not a hard-coded copy — and the
target plus every exit tranche derive from it; the raw low is kept as `stop_week_low`, and a fill the
engine's `ext_cap` would refuse is flagged `record_would_skip_as_extended`. Pinned as a relationship
(not a snapshot) in `tests/test_swing_card_record_parity.py`, with a permanent golden receipt showing
the closed gap (MIKEX: risk 14.13%→10.00%, target 4744.28→4438.56). Original finding below.
Mechanism: the buy card prints entry = current close (or band midpoint), stop = signal-week
low, target = card-entry + 2×card-R (cron:229-237). The book fills at next week's first
in-range OPEN with stop = max(low, 0.9×entry) (R94:759, 821-822). An owner following the card
literally rests a +2R limit at a DIFFERENT price than the tranche level the model books, and
sizes off a stop the model may have lifted ~10 points higher. HELD cards heal this (they print
model values, cron:284-302), but the initial buy decision is made off the divergent card.
Worst case: **either direction per trade; systematically it distorts the owner's realized R
vs the recorded R** — invisible because of D4.

**D6 — Two different top-5 "Grade A" sets (engine vs cards) at the margin.**
Mechanism: D2g above — `grade_a_entries` ranks ALL signals; the card pipeline filters
membership/degenerate bands BEFORE ranking. When they disagree, the book holds a slot for a
name it can't buy while the card promotes a name the book will never record. Worst case:
**owner buys a card the record doesn't hold** (compounds D4/D5). Small edge frequency, but
structural.

**D7 — Fractional-share sizing.**
Mechanism: R94:829 sizes in float shares; the owner buys integers. Both backtest and paper
book share the fiction, so it is parity-clean internally but diverges from every real fill.
Worst case: small, **flatters the record** slightly (perfect risk-fit, no rounding drag).

**D8 — A missed/failed Saturday run is healed with modeled history the owner never saw.**
Mechanism: K3 idempotency — the next successful run back-fills the missed week's signals and
fills as if published. The owner could not have acted on them. Worst case: **flatters the live
record** in any week where the unseen modeled fills won (and vice versa); the record stops
being "what the owner could have executed."

**D9 — Monitor/engine band-boundary mismatch (inclusive vs strict).**
Mechanism: J2. An open exactly on the band edge flags FILLED_TODAY on the dashboard while the
engine records no fill. Worst case: single-tick edge; another card-vs-book seam. Trivial but
should be one character's decision, not an accident.

---

## 3. CONVENTION / INCIDENTAL menu — ranked by plausible impact, each with its FREE diagnostic

*(Diagnostics are robustness checks on existing artifacts/runs — zero screens, zero trials.
Menu only; nothing was run this session.)*

| Rank | Row | Why it could matter | The free diagnostic |
|------|-----|---------------------|---------------------|
| ~~M1~~ | ✅ **DONE** (`1170470`) — `tests/test_r94_golden.py` pins the frozen-0094 cell, the live cell, the B-1 fix diff, and the card arithmetic on a hermetic synthetic fixture | — | — |
| ~~M2~~ | ✅ **DONE** — [m2_hold_age.md](m2_hold_age.md). Median 18w, max **201w**, 13.8% past a year; mean R **monotonic** in hold (−1.72R → +18.71R); longest decile = **64.3% of total R**; survivorship correction *strengthened* the tail | **Changed a recommendation:** a 52-week cap would cut the only profitable cohort | — |
| M3 | F1 — strict band boundaries + open-only fill | Fills lost to a one-tick boundary or to weeks where price traded inside the band but never OPENED inside it | On the existing uncapped ledger + cache: count signal-weeks where no open landed in-band but some LOW did; count opens within 0.1% of a band edge |
| M4 | F4 — alphabetical tie-break; cash-cap fill ordering | Deterministic but arbitrary preference when CRS ranks tie or cash is short | On the existing paper ledger: how many entry days had `skipped_cash > 0`; re-sort those days' candidates by ticker-reversed order and diff the fill set (pure replay of one rule) |
| M5 | G5 — stop never moves (no breakeven after tp1) | Post-2R givebacks ride to the full initial stop; the taught rule's giveback profile was the exit forensic's main finding | On the existing ledger: among trades that booked tp1 then exited `stop_part`/`sma_break`, compute R lost below breakeven — a column arithmetic pass |
| ~~M6~~ | ✅ **DONE** — [m6_demerger_scan.md](m6_demerger_scan.md). 2 suspects (SKFINDIA, VEDL), **neither** in the book or on a card; both already in the committed reference | **CLEAR**, but latent: the reference is manually curated and the swing engine has no quarantine hook | Follow-on: run the scan as a standing cron step |
| ~~M7~~ | ✅ **DONE** — [m7_universe_freshness.md](m7_universe_freshness.md). Symmetric **48/48** gap; the 48 active-but-unsnapshotted names **can never signal live**; sentinel handling verified sound (500 rows, parsed) | Snapshot is 12 months stale, membership 1 month | Owner door D1; refresh before the Sept rebalance |
| M8 | B7 — the 300-bar prep floor as a universe rule | Names appear the week they cross 300 bars, with exactly-warm SMA windows | Count cache names within 250–350 bars today; check whether any current card is within 10 weeks of its own warm-up edge |
| M9 | B4 — ADJ_JUMP 0.5% threshold + monthly rebuild | Sub-threshold dividend drift accumulates inside a month | Histogram overlap-close shifts from one warm refresh (the guard already computes them; log instead of discard) |
| M10 | A6 — `NSE_HOLIDAYS` ends 2026 | 2027 Jan/Apr review dates could mis-place the "first trading day"; the cleaner's phantom-bar drop (unused here) also stales | Eyeball: add-2027-list decision at the Oct review; zero-compute |
| M11 | H4 — mark-to-market compounding of the 2% risk base | Risk-per-trade grows/shrinks with unrealized P&L — sequencing sensitivity | On the existing NAV curve: recompute sizes off fixed EQ0 and diff realized risk % per fill (column arithmetic on the ledger) |
| M12 | E8 — regime chip thresholds (60/40, 10-bar) | Display-only today; becomes a rule if anyone ever gates on it | None needed while display-only; constitution note is the guard |
| M13 | K5 — UTC/IST date framing works by schedule luck | A future cron time near IST midnight flips `date.today()` | Grep-level check on any future schedule change; note in workflow comments |
| M14 | I5 — win = R>0 counts scratches | Cosmetic WR inflation vs a ±0.1R deadband | One-line recount on the existing ledger with a deadband |

---

## 4. Outright broken (bug, not convention) — reported, NOT fixed (live-path changes are quarterly-review class)

**~~B-1~~ — FIXED (`d3b4d5e`, census `0c7e490`).** Census first: **zero instances in the book's
entire history**, ₹0.00 NAV flattery — so the fix landed with a provably zero diff on the record.
Fix: `stale_absent_days`, mirroring the momentum engine's `STALE_ABSENT_DAYS` (10) by importing the
same constant; after N absent sessions the holding force-closes at its **last traded price**
(reason `stale`), and NAV marks to last-traded rather than entry. cfg-gated (default OFF ⇒ frozen
0094 byte-identical), ON in the live cron. The golden pins pre-fix behaviour, post-fix behaviour, and
asserts the diff touches **only** the stale position. Original finding below.

**B-1 (as originally found — HIGH, latent): absent-bar positions are unmanageable and marked at ENTRY price.**
[run_bhanushali_weekly_rank.py:412-414](../../scripts/run_bhanushali_weekly_rank.py) skips all
exit logic when a held ticker has no bar today (`i is None → continue`), and
[line 864](../../scripts/run_bhanushali_weekly_rank.py) marks such names at `p["en"]` — the
**entry price** — in the NAV sum (`… if d in didx[t] else p["en"]`). A holding that suspends or
delists mid-hold (a) can never exit — no stop, no SMA break, nothing, forever; and (b) is carried
at cost in the ₹10L NAV regardless of its last traded price. A name suspended after −40% is
marked at entry: NAV and the scorecard's Sharpe/MaxDD gates (I4) are silently flattered. The
momentum engine has an explicit guard for exactly this (`STALE_ABSENT_DAYS = 10`,
nq/engine/portfolio.py:43); the swing engine has none. Evidence is the code itself; no live
instance was checked (that would mean reading the book's state). *Decision needed: a
stale-absent policy for the swing engine — quarterly-review class since it touches the engine.*

**B-2 — DOC HALF FIXED (`7e016b9`); SUBSTANCE IS AN OWNER DOOR.** The docstring now states what
actually runs (R94 + `LIVE_DISCIPLINE` + config P + the staleness guard) and that there is **no time
cap of any kind**; `HOLD_DAYS_DISPLAY` is labelled a card hint that bounds nothing. The missing cap
itself was **not** changed. [M2](m2_hold_age.md) since measured the consequence and **reversed the
provisional recommendation**: mean R rises monotonically with hold (0–4w −1.72R … >104w +18.71R) and
the longest decile earns 64.3% of total R, so reinstating the 52-week backstop would truncate the
book's entire positive expectancy. Binder item 2 now recommends adopting an explicit no-cap policy
and attacking the *short*-hold loss cohort instead. Original finding below.

**B-2 (as originally found — LOW, doc rot that misstates the live exit): the cron docstring and constants describe the wrong engine and a nonexistent backstop.**
[run_bhanushali_cron.py:3-4](../../scripts/run_bhanushali_cron.py) says the cron re-runs
"prep_weekly_sma + weekly_full.backtest (finding 0034)" — it actually runs
`R94.prep_weekly_rank` + `R94.backtest` (lines 568-580). Line 42-43's held-card copy
(`HOLD_DAYS_DISPLAY = 65`, "52-week backstop") describes the P2 exit; under the live P config
there is **no time cap and no backstop** (G6). Nothing computes wrongly, but the file that IS
the live system misdescribes itself — an audit or a future session trusting the docstring
inherits a false rule. *One-line doc fixes; left untouched per the session's read-only rule.*

**B-3 (LOW, edge): the two Grade-A definitions can disagree** — described as D6. It is listed
in the DIVERGENT section because the mechanism is a design seam, but the non-member-in-top-5
case is arguably a bug in `grade_a_entries` (it ranks names the book is barred from buying,
R94:347-364 vs the membership check applied only later at R94:716). No live instance verified.

**B-4 (COSMETIC): monitor `window_open` uses the DATA as-of date, not today**
([run_bhanushali_monitor.py:249-250](../../scripts/run_bhanushali_monitor.py) — string-compares
`as_of.date()` against `buy_window_until`). With a stale cache (download failure), an expired
buy window still shows open. Bounded by J4's daily refresh; cosmetic until a multi-day feed
outage.

---

*End of constitution. Nothing in this session was changed, tested, or tuned; screens/trials
counters are untouched (screens 11, sealed opens 1, n_trials 138). This document is a standing
Oct-1 binder input; every DIVERGENT item and the B-1 bug are owner decisions, not session fixes.*

---

# Appendix S — Scheduler-layer audit (2026-07-30)

**Session class:** read-only scheduler audit + one mechanical plumbing fix. Zero screens, zero
trials (counts 11 / 1 / 138 unchanged); forward-wall logs unread; no strategy-behaviour change.
The constitution above audits what each job does *when triggered*; this appendix audits the
*triggering* — is every job registered, does it fire on time, and does it fail loudly?

All firing evidence is from GitHub Actions run history (`gh run list`) cross-checked against the
dated cron commits on `origin/main` and the committed proof-artifacts — never from intention.

## S.1 Inventory — every scheduled job

| # | Job | Host | Trigger spec | Spec TZ → needed | Cadence | Proof artifact |
|---|-----|------|-------------|------------------|---------|----------------|
| J1 | **weekly scanner** (cards + record; runs `run_bhanushali_cron.py`, scorecard, D2 archive, blend) | GitHub Actions `cron-bhanushali-scanner.yml` | `30 12 * * 6` | UTC 12:30 Sat → 18:00 IST Sat ✅ | weekly (Sat, post-Friday-close) | `chore(weekly)` commit + `results/*_weekly.*` |
| J2 | **daily monitor** (re-price frozen cards; runs `run_bhanushali_monitor.py`) | GitHub Actions `cron-bhanushali-monitor.yml` | `45 10 * * 1-5` | UTC 10:45 → 16:15 IST (post-15:30-close) ✅ | weekday | `chore(weekly-monitor)` commit + `results/weekly_monitor.json` |
| J3 | **forward accumulators** (bulk/block + ratings; `run_forward_accumulators.py`) | piggybacks J2's workflow (step after the monitor) | inherits J2 | inherits J2 ✅ | weekday | `results/forward_accum_health.json` + `bulkblock_forward.csv` / `ratings_forward.csv` |
| J4 | **review scorecard** (`bhanushali_review_scorecard.py`) | piggybacks J1's workflow | inherits J1 | inherits J1 ✅ | weekly | `results/weekly_review_scorecard.json` |
| J5 | **D2 archive** (`archive_weekly_snapshot.py`) | piggybacks J1's workflow | inherits J1 | inherits J1 ✅ | weekly | `results/archive/<date>/` |
| J6 | **blend-hybrid paper** (`run_blend_paper.py`, non-blocking) | piggybacks J1's workflow | inherits J1 | inherits J1 ✅ | `results/blend_hybrid_paper.json` |
| J7 | **intraday shadow scan** (`run_intraday_scan.py`) | GitHub Actions `cron-intraday-scan.yml` | `0 9 * * 1-5` | UTC 09:00 → **14:30 IST, intent = pre-15:30-close** ⚠ | weekday | `results/intraday_scan/*` |
| J8 | **Kite session refresh** (`refresh_kite_session.py`) | GitHub Actions `cron-kite-refresh.yml` | `45 0 * * 1-5` | UTC 00:45 → 06:15 IST (post-06:00 expiry) ✅ | weekday | Actions run only (no commit; `contents:read`) |
| — | CI | GitHub Actions `ci.yml` | push / PR only | n/a | not scheduled | not a cron |
| — | Fly.io backend | Fly.io `nifty-satvik-api` | always-on (`auto_stop_machines=off`, `min_machines_running=1`) | n/a | **no scheduler** — it *consumes* cron artifacts (reads `generated_at`, computes `cron_health`); the `while True` loops in `main.py` are the WebSocket push loop, not job scheduling | `/health` every 30s |
| **J9** | **forward-wall log** (3-book hash-chain; `run_paper_cron.py` → `nq.paper.wall_cron.update_wall`, line 152) | **NONE** | **no trigger anywhere in the repo** | — | intended "daily" per CLAUDE.md | **never produced by CI** |
| — | local OS scheduler | this laptop | checked: `Get-ScheduledTask` + crontab | n/a | **none** — no Task Scheduler entry or crontab references the project | — |

**Timezone verdict:** every spec is written in UTC and every conversion to IST is *correct* for its
stated intent (IST has no DST, so the offsets are stable). No wrong-TZ spec exists. The one intent
mismatch (J7) is a *delay* problem, not a TZ problem — see S.3.

## S.2 Firing history — fired / late / missed (evidence, not intention)

Actual scheduled-run start times (UTC) vs spec. GitHub Actions scheduled runs are best-effort and
queue under load; the measured lag is consistent.

| Job | Spec | Last 8 scheduled firings (UTC) | Verdict |
|-----|------|-------------------------------|---------|
| J1 scanner | Sat 12:30 | 07-25 14:08, 07-18 13:56 (+ 2 manual 07-18) | **all fired, ~+1.5h late.** Only 2 scheduled runs — the workflow went live ~07-17, so 07-04/07-11 predate it (not misses). Consecutive Saturdays 07-18, 07-25 present. |
| J2 monitor | weekday 10:45 | 07-20 12:54, 07-21 12:10, 07-22 12:14, 07-23 12:12, 07-24 12:05, 07-27 13:29, 07-28 12:24, 07-29 12:32 | **8/8 fired, ~+1.5–2.7h late.** No missed weekday. |
| J3 accumulators | (rides J2) | health file `last_fetch 2026-07-28 21:01`; monitor commits 07-27/28/29 | **fired with J2.** Both feeds' own `stale:false` agrees with the independent commit reconstruction. |
| J7 intraday | weekday 09:00 | 07-20 11:33, 07-21 10:54, 07-22 10:56, 07-23 10:56, 07-24 10:52, 07-27 12:08, 07-28 11:07, 07-29 11:12 | **8/8 fired, ~+2–3h late → all land 16:2X–17:3X IST, AFTER the 15:30 close.** Fires reliably; its pre-close *purpose* is defeated (S.3). |
| J8 kite-refresh | weekday 00:45 | 07-20 04:26 … 07-29 03:55 (8/8) | **8/8 fired, ~+3–3.7h late — but every run is a clean no-op SKIP** (`go=false`, "secrets not set"), inert by design. |
| J9 forward-wall | — | **zero runs, ever** | **NOT SCHEDULED.** |

No job with a live schedule shows an unexplained gap. The only "missing" job is J9, which has no
schedule to miss.

## S.3 Host-reliability traps

- **GitHub Actions best-effort timing (measured):** every scheduled job runs **~1.5–3.7h after**
  its spec minute — a documented Actions behaviour, not a bug in our specs. Consequence by job:
  J1/J2/J8 tolerate it (same-evening / post-expiry windows are hours wide). **J7 does not** — a
  09:00-UTC spec meant to snapshot the *forming* trend at 14:30 IST fires at 16:2X–17:3X IST, after
  the close, so it captures a settled bar, not a pre-close one. Since J7 is observational (no
  strategy action) this is a defeated-purpose flag, not a live risk.
- **60-day auto-disable:** GitHub disables scheduled workflows after 60 days of *repository*
  inactivity. J2 (+J3) commit to `main` every weekday, so the repo is never inactive → **auto-disable
  risk is currently nil.** The subtle coupling: the daily monitor's commits are the *keep-alive* for
  ALL scheduled workflows. If the monitor stops during a quiet stretch (post-review, no manual
  commits), the 60-day clock starts for every cron at once. Flagged for the Sep–Oct quiet window.
- **Local-machine dependence:** none. No job runs on this laptop (S.1), so "laptop asleep at trigger
  time" cannot silently miss anything today. (It *would* matter if J9 were ever scheduled as a local
  crontab — it is not scheduled anywhere.)
- **Fly.io stop/start:** the backend is pinned always-on (`auto_stop_machines=off`), and it schedules
  nothing, so Fly's stop/start model affects no job.
- **Overlap / double-run guards:** every workflow sets `concurrency.group` with
  `cancel-in-progress:false`, so a slow run never overlaps its own next firing. Idempotency under a
  re-run is by construction: J1/J4/J5/J6 recompute from inception (constitution I2/K3); J3 dedupes on
  a content key (`run_forward_accumulators._append_dedup`); J5 snapshots are write-once
  (`archive_weekly_snapshot`, tested). No missing guard found.

## S.4 Failure visibility — the dead-man's-switch question

*If a job silently stops, what tells me, and how fast?*

| Job | Existing alarm | Delivery path | Reaches the owner? |
|-----|---------------|---------------|--------------------|
| J1 scanner | dashboard `cron_health` banner (`signals.py`) | dashboard | ⚠ **miscalibrated** — see below |
| J2 monitor | — | — | ❌ nothing watches the monitor itself |
| J3 accumulators | `forward_accum_health.json` `stale` flag + 5-session alarm | committed file | ❌ file nobody opens |
| J5 D2 archive | `drift_log.jsonl` (drift only, not absence) | committed file | ❌ file nobody opens |
| J9 wall | — | — | ❌ no producer, no alarm |

Two findings:

1. **The one human-facing alarm is miscalibrated for the weekly cadence.** `cron_health`
   (`signals.py:359-407`) flags `FAILED_TODAY` at 26h and `STALE` at 48h — thresholds written for a
   *daily* scanner. The live book is *weekly*: `signals_today_weekly.json.generated_at` holds the
   Friday data date and the monitor never rewrites it, so by Tuesday every week the envelope is
   >48h old and the banner reads **STALE on a perfectly healthy book**. An alarm that is red most of
   the week trains the eye to ignore it, and it therefore cannot distinguish a genuinely-missed
   Saturday scan from normal weekly staleness. The classic broken dead-man.
2. **Every other freshness signal is a file nobody opens** — the accumulator `stale` flag and the D2
   drift log are written and committed, never surfaced.

**Fix applied (S.5):** the dead-man reconstruction now rides J2 — the one job proven to fire every
weekday. **Flagged (S.6):** surfacing it on the dashboard + recalibrating `cron_health` for the
weekly cadence (both touch the always-on backend serving path).

## S.5 Fixes applied — with receipts

**F-S1 — dead-man scheduler-health reconstruction on the daily heartbeat.**
New pure module `scripts/scheduler_health.py`: for each scheduled job it reconstructs the last
firing from that job's committed proof-artifact and flags any job overdue for its own cadence
(cadence-aware coarse bounds that absorb weekends + the measured Actions delay).
`run_bhanushali_monitor.py` now calls it (defensively wrapped — a probe fault can never break
re-pricing) and folds a `scheduler_health` block into `results/weekly_monitor.json`, plus prints a
one-line status to the Actions log. Because J2 fires every weekday, the reconstruction runs daily on
a proven heartbeat with **no new service**; if the monitor itself dies, the block's `checked_utc`
goes stale and a dead heartbeat is visible from one timestamp. The forward wall is reported as a
static *unscheduled* gap **without reading its log** (no-peek preserved). Tested hermetically in
`tests/test_scheduler_health.py` (fresh→OK, overdue→OVERDUE, missing→MISSING, wall→unscheduled,
accumulator prefers `last_fetch_ts` over mtime, garbage never raises). Live offline run confirms the
block writes and the status line prints.

*Why this is the only mechanical fix:* every scheduled spec is already TZ-correct (S.1); the timing
lateness is GitHub's best-effort behaviour, not fixable by editing a spec (an earlier spec minute
does not reduce the queue delay); and the remaining gaps (J9 unscheduled, `cron_health`
recalibration, dashboard surfacing) change *when the strategy acts* or the *always-on serving path*,
so they are flagged, not fixed.

## S.6 Flags — owner doors (not fixed)

| ID | Finding | One-line disposition |
|----|---------|---------------------|
| **S-F1** | **J9 forward-wall log has no scheduled producer** — `run_paper_cron.py` (→ `wall_cron.update_wall`) is invoked by no workflow; CLAUDE.md calls it the "only certifier … logged daily." | Decide: is the momentum-sleeve wall intentionally dormant (sleeve suspended), or should it be scheduled? If active, it needs a workflow or a droplet crontab — today it runs **never**. |
| **S-F2** | **`cron_health` banner miscalibrated for the weekly cadence** (26h/48h daily thresholds vs a weekly book whose `generated_at` is the Friday date) → reads STALE mid-week on a healthy book. | Recalibrate to the weekly cadence (healthy if the last Saturday scan is present; let J2's own freshness cover intra-week). Touches the always-on backend serving path → owner door, not a mid-quarter plumbing edit. |
| **S-F3** | **`scheduler_health` block is produced but not surfaced** — the backend overlays `weekly_monitor.json` onto cards but does not yet read its new block. | One backend line to surface `overall`/attention on the dashboard; pairs with S-F2. |
| **S-F4** | **J7 intraday scan fires post-close** (~+2h Actions delay defeats the 14:30-IST pre-close intent). | Observational only; if the pre-close snapshot ever matters, move J7 off Actions cron (droplet). No action while shadow-only. |
| **S-F5** | **D2 archive (J5) is dormant until this branch merges** — the archive step is on `research/selection-funnel-and-noise-floor`, not on `main`; `origin/main`'s scanner has no archive step and `results/archive/` is absent on main. | Snapshots begin only at the next Saturday scan *after* merge. Until then the baseline `2026-07-24` is the only snapshot. |
| **S-F6** | **J8 kite-refresh is a clean no-op skip** (secrets unset) and, once enabled, would fire ~3.5h after the 06:00-IST token expiry. | Inert today. If enabled, the ~3.5h Actions delay leaves the owner Kite session dark 06:00–~09:30 IST (overlapping the 09:15 open) — run it from the droplet if it matters. |
| **S-F7** | **60-day auto-disable coupling** — the daily monitor's commits are the keep-alive for every scheduled workflow. | Nil risk while J2 commits daily; the S.5 dead-man now flags a stopped monitor. Revisit if a long no-commit window is planned. |

---

# Appendix S2 — Scheduler migration session (2026-07-30)

**Session class:** scheduler classification + one read-only cloud probe. Zero screens, zero trials
(counts **12 / 1 / 138** unchanged); no strategy-behaviour change; engine untouched. The probe
workflow was added to `main`, run once, and removed (`9199fa5` → `ebaed9e`).

## S2.1 The premise was already satisfied — and one audit row was wrong

Appendix S established that **no job runs on this laptop** (`Get-ScheduledTask` + crontab both
clean). "Make the daily jobs laptop-independent" was therefore already true, and **§5's Task
Scheduler miss-proofing has no target** — there is no local job to miss-proof. What the migration
framing did surface is a different and more serious failure mode.

**GitHub Actions registers workflows — for `schedule:` and `workflow_dispatch` alike — only from the
default branch.** This was confirmed the hard way: dispatching the probe from the research branch
returned `HTTP 404: workflow not found on the default branch`. Consequently **any cron component
that lives only on an unmerged branch never runs, no matter how correct its wiring looks.**

Four components are in exactly that state:

| Component | On `main`? | Real status |
|---|---|---|
| J3 forward accumulators (`run_forward_accumulators.py` + the monitor accumulator step) | **NO** | **never fired on schedule** |
| J5 D2 archive (`archive_weekly_snapshot.py`) | **NO** | dormant (already flagged S-F5) |
| F-S1 dead-man `scheduler_health.py` (the fix "applied" in S.5) | **NO** | **not running** |
| J9 forward-wall (`run_paper_cron.py`) | yes | no trigger anywhere (S-F1) |

**Correction to S.1/S.2 — the J3 row is wrong.** It records J3 as "fired with J2, 8/8", inferred
from J2 firing plus the committed `forward_accum_health.json` and its `stale:false`. That inference
was circular: both artifacts were produced by *local manual runs* on this branch, not by the cron.
The tell is in the data — `last_fetch_ts 2026-07-28 21:01:15` is neither a cron time nor a UTC cron
lag, and it is the exact timestamp of the local PROBE-contamination incident. A live re-fetch on
2026-07-30 found **137 uncollected bulk/block rows**, i.e. the feed has been collecting nothing on
schedule since inception. S-F5 applied the branch-vs-main reasoning to J5 but not to J3.

*Lesson for the audit method:* "the proof artifact exists and is fresh" is not evidence a job fired
**if that artifact can also be produced by hand**. Firing evidence must come from run history on the
default branch, cross-checked against a commit authored by the runner.

## S2.2 Job classification by real constraint

| Bucket | Jobs | Data dependency | Write target | Verdict |
|---|---|---|---|---|
| **CLOUD-SAFE** | J1 scanner, J2 monitor, J4 scorecard, J5 archive, J6 blend | yfinance + git only | commits to `main` | already on GH Actions (J5 pending merge) |
| **IP-SENSITIVE** | J3 accumulators (bulk/block + ratings); the delivery / MTO / bhavcopy harvesters | NSE endpoints | append-only accumulators | **cloud-safe after all — see the matrix below** |
| **TOKEN-BOUND** | J8 Kite refresh | Kite OAuth | none (Actions run only) | cannot be unattended anywhere; documented, not migrated. Inert today (`go=false`, secrets unset) |
| **UNSCHEDULED** | J9 forward-wall | — | hash-chained wall log | no trigger; owner door S-F1 |

## S2.3 NSE reachability matrix — endpoint x host (run 30538093904, 2026-07-30)

Read-only GETs from a GitHub-hosted `ubuntu-latest` runner:

| Endpoint | Status | Bytes | Verdict |
|---|---|---|---|
| `www.nseindia.com/` (session bootstrap) | 403 | 368 | **BLOCKED** (bot-wall) |
| `archives.../equities/bulk.csv` | 200 | 12,194 | ALLOWED |
| `archives.../equities/block.csv` | 200 | 292 | ALLOWED |
| `archives.../indices/ind_nifty500list.csv` | 200 | 32,766 | ALLOWED |
| `www.../api/corporate-credit-rating` | 200 | 156,906 | ALLOWED |
| `www.../api/corporate-board-meetings` | 200 | 558,922 | ALLOWED |
| `archives.../sec_bhavdata_full_*.csv` | 200 | 372,734 | ALLOWED |
| `archives.../mto/MTO_*.DAT` | 200 | 116,822 | ALLOWED |

**7/8 ALLOWED. GitHub runner IPs are not walled for any data endpoint.** Only the homepage
bot-wall 403s — and notably the `www.../api/*` endpoints returned full payloads *without* a cookie
bootstrap, so that 403 does not block the collectors (their bootstrap call is best-effort and they
proceed regardless).

**Migration consequence:** the IP-SENSITIVE bucket needs **no Fly.io machine and no deploy key**.
The Fly-maa fallback in the migration plan is **not required**; cost of the chosen path is **zero**.
The remedy for J3 is therefore not a migration at all — it is **merging its existing wiring to
`main`**.

## S2.4 What this session did NOT do, and why

- **Did not merge the research branch to `main`.** That is the single action that would activate J3,
  J5 and the F-S1 dead-man, but it carries 42 commits including an entire research programme — a
  governance-class decision, not scheduler plumbing. **Owner door.**
- **Did not schedule J9.** Unchanged from S-F1: whether the momentum-sleeve wall should log daily is
  a strategy decision (the sleeve is suspended), not a host decision.
- **Did not deliver the migration plan's "one full day of post-migration evidence."** No migration
  was performed, and a day of firing evidence cannot be produced inside a session — it requires a
  day to elapse. The honest substitute is the reachability matrix above plus the S.2 run history.
- **Did not touch job times.** Every spec is already TZ-correct (S.1); the ~1.5-3.7h lateness is
  GitHub best-effort queueing and is not fixable by editing a spec.

## S2.5 Job x host x schedule x alarm-path (current truth)

| Job | Host | Schedule (UTC → IST) | Fires today? | Alarm path |
|---|---|---|---|---|
| J1 scanner | GH Actions (`main`) | `30 12 * * 6` → 18:00 Sat | yes (~+1.5h) | dashboard `cron_health` (miscalibrated, S-F2) |
| J2 monitor | GH Actions (`main`) | `45 10 * * 1-5` → 16:15 | yes (~+1.5-2.7h) | none directly (S.4) |
| J3 accumulators | **branch only** | would ride J2 | **NO** | `forward_accum_health.json` (file nobody opens) |
| J4 scorecard | GH Actions (`main`) | rides J1 | yes | — |
| J5 D2 archive | **branch only** | would ride J1 | **NO** | drift log (file nobody opens) |
| J6 blend paper | GH Actions (`main`) | rides J1 | yes | — |
| J7 intraday | GH Actions (`main`) | `0 9 * * 1-5` → 14:30 | yes, but post-close (S-F4) | — |
| J8 kite refresh | GH Actions (`main`) | `45 0 * * 1-5` → 06:15 | yes, no-op skip | — |
| J9 forward-wall | **nowhere** | — | **NO** | — |
| F-S1 dead-man | **branch only** | would ride J2 | **NO** | would print + write into `weekly_monitor.json` |

**Cross-host aggregation is not yet real**, and the reason is not host-splitting — it is that the
aggregator itself is unmerged. Once `scheduler_health.py` is on `main` it rides J2 and covers every
job in one status block; surfacing that block somewhere the owner looks daily remains S-F3.

## S2.6 Flags added

| ID | Finding | Disposition |
|----|---------|-------------|
| **S2-F1** | **J3 has never fired on schedule** — wiring is branch-only; its "8/8 fired" record in S.2 was inferred from locally-produced artifacts. 137 rows uncollected as of 2026-07-30. | Merging the branch to `main` activates it. Until then the forward accumulators collect **nothing** automatically. Owner door (merge). |
| **S2-F2** | **The F-S1 dead-man's-switch is itself unmerged** — the fix recorded as "applied" in S.5 does not run. | Same merge. Until then no job has an automated absence alarm. |
| **S2-F3** | **Audit-method correction** — a committed proof-artifact is not firing evidence when that artifact is hand-producible. Require default-branch run history plus a runner-authored commit. | Recorded here; applies to every future scheduler audit. |

## S2.7 Post-merge status (2026-07-30, after `a2befea`)

The branch merged via PR #53 (44 commits, no squash — the history is the research record). CI was
green on the head commit `44dda60`. Registry verified on `main` immediately after the merge:

| Component | Registered on `main` | Evidence |
|---|---|---|
| J3 forward accumulators | **YES** | `cron-bhanushali-monitor.yml:49` (`run: python scripts/run_forward_accumulators.py`) + the git-add at `:56` |
| J5 D2 archive | **YES** | `cron-bhanushali-scanner.yml:74` (`run: python scripts/archive_weekly_snapshot.py`) |
| F-S1 dead-man | **YES** | `scripts/scheduler_health.py` present; invoked from `run_bhanushali_monitor.py:311-312`, folding a `scheduler_health` block into `weekly_monitor.json` |

**Catch-up (front door, `workflow_dispatch` run 30539245191, conclusion success).** One dispatch of
the daily monitor so the collectors absorbed the dormant window through the normal append path with
real timestamps. Bulk/block **149 → 286 rows (+137, all 29-JUL-2026)**; ratings **88 → 93 (+5)**.
Outputs committed to `main` as `3c2aac5 chore(weekly-monitor): daily re-price 2026-07-30`.

**Permanent gap: none** — coverage is continuous (bulk/block 28-JUL + 29-JUL; ratings 21-JUL →
30-JUL). The dormancy was ~1 day, shorter than both sources' rolling windows. Recorded honestly in
`results/FORWARD_ACCUMULATORS_README.md` **together with the near-miss**: bulk/block is a rolling
current-file endpoint with no working historical API, so a longer dormancy would have been
permanently unrecoverable. The accumulator's own reason for existing is the thing a silent outage
destroys.

**Commit identity note:** the cron commits as `kreeshpatel <kreeshvasistha@gmail.com>`, not a
distinct bot identity. Harmless today, but it means a runner-authored commit is not distinguishable
from an owner-authored one by author line alone — which weakens the S2-F3 rule (firing evidence =
run log + runner-authored commit). Consider setting the workflow's git identity to a bot.
**S2-F4**, below.

## S2.8 Updated job × host × schedule × alarm-path

| Job | Host | Schedule (UTC → IST) | Status after merge | Alarm path |
|---|---|---|---|---|
| J1 scanner | GH Actions (`main`) | `30 12 * * 6` → 18:00 Sat | live (~+1.5h) | dashboard `cron_health` (miscalibrated, S-F2) |
| J2 monitor | GH Actions (`main`) | `45 10 * * 1-5` → 16:15 | live (~+1.5–2.7h) | dead-man block (now produced) |
| **J3 accumulators** | GH Actions (`main`) | rides J2 | **ACTIVATED** — first dispatch 30539245191 ✅; first *scheduled* firing pending | `forward_accum_health.json` + dead-man |
| J4 scorecard | GH Actions (`main`) | rides J1 | live | — |
| **J5 D2 archive** | GH Actions (`main`) | rides J1 | **ACTIVATED** — first firing due Sat 2026-08-01 | drift log + dead-man |
| J6 blend paper | GH Actions (`main`) | rides J1 | live | — |
| J7 intraday | GH Actions (`main`) | `0 9 * * 1-5` → 14:30 | live, fires post-close (S-F4 orig.) | — |
| J8 kite refresh | GH Actions (`main`) | `45 0 * * 1-5` → 06:15 | live, no-op skip | — |
| **J9 forward-wall** | **nowhere** | — | **still unscheduled — OPEN OWNER QUESTION** | — |
| **F-S1 dead-man** | GH Actions (`main`) | rides J2 | **ACTIVATED** | writes into `weekly_monitor.json`; surfacing = S-F3 |

**J9 — deliberately not scheduled.** Whether the 3-book forward wall should log daily is a strategy
decision, not a host decision: the momentum sleeve is suspended, and CLAUDE.md calls the wall "the
only certifier." Carried as an **open owner question for the September wall audit**. Scheduling it
without deciding what it certifies would manufacture a record nobody has agreed to read.

## S2.9 Flags updated / added

| ID | Status |
|----|--------|
| **S2-F1** (J3 never fired) | **RESOLVED** by the merge + catch-up. Awaiting its first *scheduled* firing for full confirmation per S2-F3. |
| **S2-F2** (dead-man unmerged) | **RESOLVED** — registered and invoked; surfacing to a place the owner reads daily remains S-F3. |
| **S2-F3** (audit-method) | Standing. Firing evidence = Actions run log, cross-checked against a runner-authored commit. |
| **S2-F4** (new) | **Cron commits are authored as the owner, not a bot** — a runner-authored commit cannot be told from a hand-made one by author line. Weakens S2-F3's cross-check. One-line workflow fix; owner door because it changes the commit record's appearance. |
| **S2-F5** (new) | **The R94 golden master is flaky on CI** — the same commit (`44dda60`), with identical dependency versions (numpy 2.5.1 / pandas 3.0.5 / scipy 1.18.0), failed once on `curve_hash` (`54deb7e3…` vs golden `84cc3d09…`) and passed on re-run; it does not reproduce locally across five hash seeds. A guardian of engine reproducibility that is intermittently red on healthy code decays into an ignored alarm — the same pathology as the miscalibrated `cron_health` banner (S-F2). Needs a root-cause pass (non-determinism in the fill/curve path, or a runner-level numeric difference), not a threshold change. |

## S2.10 First heartbeat after activation — and its first false alarm

The dead-man produced its first output on the catch-up run and reports **`overall: MISSING`**:

| job | dead-man status | truth |
|---|---|---|
| weekly-scanner | OK | fired 07-25 ✅ |
| **forward-accumulators** | **OK** | activated, caught up ✅ |
| review-scorecard | OK | ✅ |
| d2-archive | OK | activated; first firing due Sat 2026-08-01 |
| **intraday-scan** | **MISSING** | **fired 2026-07-30 10:56 UTC, success — 8/8 historically** |

**S2-F6 (new) — the dead-man is blind to jobs that do not commit an artifact.** J7 is healthy and
fired today, but `results/intraday_scan/` is never committed, so the reconstruction cannot see it
and reports MISSING, which drags `overall` to MISSING on a healthy system. This is the same
pathology as the miscalibrated `cron_health` banner (S-F2): an alarm that is red in the normal
case teaches the reader to ignore it, and it will therefore fail to be believed on the day it is
right.

It is also, precisely, the flaw named in **S2-F3**: *firing evidence is the Actions run log, never a
committed artifact alone.* The dead-man reconstructs from committed artifacts by design, so it
inherits that weakness structurally. Two candidate fixes, neither applied here (both change what the
heartbeat reports, which is an owner door): give the reconstruction an Actions-API source for jobs
with no committed output, or declare J7 artifact-less and exclude it from `overall` with its status
surfaced separately. Until then, read `overall: MISSING` as "check which job" rather than "a job
failed".

## S2.11 S2-F5 — the flaky golden: two hypotheses falsified, root cause NOT found

**Status: OPEN, narrowed. Not closed, and deliberately not papered over.** Diagnostic run
30577724843 (temporary workflow, since removed).

### Hypothesis (a) — threading / parallel reduction order: FALSIFIED for free, before spending CI

`ci.yml` already pins `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS` and `MKL_NUM_THREADS` to `1`, and
the failing run's own env dump carried those values. A flake that occurs **under** single-threaded
BLAS cannot be caused by parallel reduction order. The planned unpinned-vs-pinned matrix was
therefore not run: the experiment's answer was already in the failing run's log.

*Consequence for the "byte-reproducible" claim:* it remains conditional on the stated environment
(single-threaded BLAS, pinned in `ci.yml`), and the September memo runs must use the same pinning.
That conditionality was already true; it is now written down.

### Hypothesis (b) — hash-order / test-order pollution: FALSIFIED

| Leg | Design | Result |
|---|---|---|
| A | golden test **isolated**, `PYTHONHASHSEED` swept **0-19**, threads pinned | **0/20 failed** |
| B | golden in **suite context** x20, default (random) seed | **0/20 failed** |

Environment captured: 4 cores, numpy 2.5.1, pandas 3.0.5 — identical to both the failing and the
passing run of commit `44dda60`.

**40 consecutive clean CI runs. The flake did not reproduce.** Its rate is therefore below
1-in-40, and no fix can be validated against the "20/20 green" bar — the suite was already 40/40
green *without any change*, so that criterion proves nothing here. Claiming S2-F5 closed on this
evidence would be a false all-clear.

### What was done instead: make the next sighting decisive

A flake that cannot be reproduced can still be diagnosed **if its one occurrence is informative**.
The original assertion failed on the **first differing key in alphabetical order**, so the single
sighting told us only that `curve_hash` differed — not whether `trades`, `n_ledger`, `sharpe` or
`final_equity` moved with it. Those separate two very different root causes:

- trades/ledger identical, curve hash different → numeric or ordering noise in the curve path;
- trade-level values different → selection-level divergence.

The golden now reports **every** key together with a interpretation line naming which of those two
it is. **The comparison is not widened** — each key is still compared exactly and any single
mismatch still fails. `PYTHONHASHSEED` is additionally pinned to `0` in `ci.yml`: seed order was
exonerated as a *cause*, but leaving it unpinned makes any recurrence undiagnosable after the fact.

### ROOT CAUSE FOUND — the instrumentation paid off on its first run

The enriched report fired on the very next CI run (30578319525) and settled it in one observation:

```
[DIFF] curve_hash:   got='54deb7e30a293cb9' golden='84cc3d09d2c040f0'
[ok  ] ledger_hash:  57a7b375f6029115   (IDENTICAL)
[ok  ] trades: 47 · n_ledger: 47 · final_equity: 107926269.82 · sharpe · cagr · max_dd · win_rate
```

**Every value except the curve hash is identical, including the ledger hash.** The trades, their
order in the ledger, and the final equity to the cent are the same. Note also that the wrong hash is
*the same wrong value* as the original sighting — the failure is **bimodal, not random**, which rules
out ordinary float jitter (that would produce many distinct hashes).

The mechanism is the curve key's precision. `_curve_key` hashes
`(str(date), round(float(v), 4))` per point, and this cell's equity is of order **1.08e8** — so
4 *absolute* decimals demand roughly **13 significant digits** of reproducibility, close to float64's
15-16. A few ULPs of accumulated difference in any intermediate equity value flips the fourth
decimal and changes the hash. `final_equity` survives because it is recorded at 2dp, i.e. two orders
of magnitude coarser.

What varies those last bits is **summation/iteration order**: pinning `PYTHONHASHSEED=0` made the
failure **deterministic**, which is how it was caught. Hash order changes set/dict iteration, hence
the order positions are accumulated, hence the last bits of an intermediate equity value. Leg A had
swept seeds 0-19 *in isolation* and leg B ran the suite with *random* seeds — the one combination
never tested was **seed 0 in suite context**, which is exactly what fails.

**The pin was reverted.** It converted a rare flake into a permanent red, which is worse than what
it diagnosed; CI is back to the unpinned (occasionally flaky) state until the real fix lands.

### The fix is an owner door

Every durable fix changes the recorded hash, which this session was explicitly forbidden to touch:

1. **Coarsen the curve key** to a precision proportional to magnitude (relative rounding, or 2dp to
   match `final_equity`). Correct and minimal — but re-records `curve_hash`.
2. **Make the accumulation order deterministic** at its source (replace the offending set/dict
   iteration with a sorted traversal). Strictly better, since it fixes the engine rather than the
   test — but it may itself change the recorded hash, and it touches engine code.
3. Pin a known-green seed — **rejected**: it masks the defect and is fragile to any suite change.

Recommended: (2) then (1), in a dedicated change that re-records the golden deliberately and states
the diff — precisely what the fixture's own error message calls for. **S2-F5 stays OPEN**; it is now
a one-line fix waiting on a decision rather than an unexplained ghost.

### Superseded note

The mechanism was unidentified when this section was first written. Remaining candidates, none tested: a rare numeric difference in the
runner's libm/BLAS build; non-determinism in a pandas groupby/sort path that only manifests on
particular data orderings; or a genuinely transient runner fault. **Next sighting is the trigger** —
the enriched report should immediately classify it as curve-path vs selection-level, which halves
the search space in one observation.

## S2.12 S2-F6 — CLOSED: the heartbeat now reads the run log

`scheduler_health` took its firing truth from committed artifacts, so `intraday-scan` — which fires
every weekday and commits nothing — read MISSING and dragged `overall` red on a healthy system. That
is the S-F2 pathology (an alarm red in the ordinary case stops being read) and it was also the exact
weakness named in S2-F3 (firing evidence is the run log, never an artifact alone).

**Fix (option a, as directed).** The reconstruction now queries the Actions run API for each job's
most recent **successful scheduled run** (`event=schedule&status=success`), using `GITHUB_TOKEN`
from within the monitor job (`permissions: actions: read` added). Committed artifacts are demoted to
**corroboration**: each row carries `source` (`run-log` | `artifact` | `none`), the `run_id`, the
artifact's own timestamp, and `artifact_corroborates` — false when the artifact is more than six
hours newer than the last scheduled run, which is how a hand-made artifact now announces itself
instead of impersonating a firing.

Alarm semantics are unchanged: **MISSING = no successful scheduled run within the job's cadence
window**; OVERDUE beyond it. Degradation is graceful — with no token (local runs) or on any API
failure it falls back to artifacts and says so in `source_of_truth`, and the probe still never
raises into the monitor.

Pinned by `tests/test_scheduler_health_runlog.py` (12 tests, API injected — no network): an
artifact-less job reads OK from the run log; an empty results directory with a healthy run log is
OK overall; no successful scheduled run is MISSING; a stale run is OVERDUE; missing token and API
exceptions both fall back; a hand-made artifact newer than the run is flagged, not alarmed.

**Live verification remains outstanding** — the next real heartbeat (tomorrow's monitor) must report
`overall: OK` with `intraday-scan` green and `source: run-log`. See S2.13.

## S2.13 Activation verification (S2-F3 evidence standard: run log first, artifact corroborating)

| Job | Evidence | Verdict |
|---|---|---|
| **J3 forward accumulators** | **schedule**-triggered run **30541739128**, 2026-07-30 12:14 UTC, success; `forward_accum_health.json.last_fetch_ts = 2026-07-30 12:15:15` matches it; committed as `6330c0a` | **VERIFIED LIVE** |
| **J5 D2 archive** | first firing due **Sat 2026-08-01 ~12:30 UTC** (weekly scanner) | **PENDING** — unreachable this session |
| **Dead-man (F-S1/S2-F6)** | rebuilt on run-log truth, 12 tests green | **PENDING live** — next monitor run |

**J3 note, stated precisely:** the scheduled run added **0 rows** and that is the correct outcome,
not a failure. The 11:36 catch-up had already absorbed 29-JUL, and NSE published nothing new in the
38 minutes between them; the content-key dedup keeps first-seen timestamps, so an idempotent re-run
appends nothing. Firing is evidenced by the run log and the health file's fetch timestamp, exactly
as S2-F3 requires — **not** by row growth.

### Hand-back checks (expected values)

```bash
# 1. J3 — a *schedule* (not workflow_dispatch) run, then the health stamp must match it
gh run list --workflow=cron-bhanushali-monitor.yml --limit 3 --json event,createdAt,conclusion
python -c "import json;print(json.load(open('results/forward_accum_health.json')))"
#    expect: event=schedule, conclusion=success; last_fetch_ts within ~2 min of the run start

# 2. J5 — after Sat 2026-08-01
ls results/archive/            # expect a NEW <date>/ directory
git log origin/main -1 --stat -- results/archive/   # in a scanner-authored commit

# 3. Dead-man — after the next monitor run
python -c "import json;h=json.load(open('results/weekly_monitor.json'))['scheduler_health'];\
print(h['overall'], h['source_of_truth']);\
[print(' ',j['job'],j['status'],j['source'],j['run_id']) for j in h['jobs']]"
#    expect: overall=OK, source_of_truth=actions-run-log,
#            intraday-scan OK / source=run-log / a real run_id  <- the S2-F6 fix
#    a MISSING now means a genuinely absent scheduled run, not an absent artifact
```

---

## S2.14 S2-F7 — the silent `git add`: five instances, and the guarantee that ends them

**Date:** 2026-08-05. **Class:** fail-loud hardening. Counts frozen (screens 14 · sealed opens 1 ·
n_trials 138); zero research.

### The mechanism

`git add` on a path that `.gitignore` ignores and nothing tracks **exits 0 and stages nothing**.
There is no error to catch, no annotation, no red run. Wrapped in the house `|| true` idiom it is
undetectable from the outside: the workflow succeeds, the heartbeat stays green, S2-F3's run-log
evidence standard confirms the job *fired* — and nothing was published.

S2-F6 closed the gap between "an artifact is missing" and "a run is missing". This closes the gap
between **a run firing and a run producing**.

### The five instances

| # | artifact | discovered | cost |
|---|---|---|---|
| 1 | `results/weekly_monitor.json` | 2026-07-18 | dead for weeks; the dashboard's intra-week overlay never reached production |
| 2 | `results/archive/` (D2 snapshots) | S2 build | the append-only record the Oct-1 gates read was not accruing |
| 3 | judge cohort — `results/judge_log.jsonl` | 2026Q3 audit, session 5 | **17 verdicts, $4.0507, destroyed**; the hash chain restarted from GENESIS every Saturday |
| 4 | PROBE | S2-F5 instrumentation | delayed the flaky-golden root cause |
| 5 | **`results/intraday_scan/`** | **2026-08-05, by the new guard test on its first run** | **every shadow scan since inception silently discarded** |

**Instance 5 — the binder line.** The 14:30 IST intraday shadow scan has been firing, scanning and
committing nothing **from inception until 2026-08-05**. The push path had already been repaired
(autostash + retry + exit RED), which is precisely why it looked healthy: the failure was upstream
of the push, in an `add` that staged an empty set, so `git commit` reported "nothing to commit" and
the workflow exited 0. **The past scans are unrecoverable** — the artifacts existed only in the
runner's filesystem and died with it. There is no backfill: the scans are intraday snapshots of a
live book and cannot be reconstructed after the fact. **Persistence begins 2026-08-05.** Any
partial→close survival statistic must therefore be dated from that day, and the run of scans before
it must be treated as **absent evidence, not negative evidence**.

A sixth instance was caught during the fix itself: `results/output_contracts.json` — the manifest
whose entire purpose is to make this failure visible — was about to be silently dropped by the same
`results/*` rule.

### The guarantee

1. **`tests/test_workflow_output_paths.py`** — parses every path any workflow declares to `git add`
   (all three declaration forms, matched anywhere on the line) and asserts each is tracked or not
   ignored. A future session that ignores a results file **breaks CI the same day**. This test found
   instances 5 and 6.
2. **`results/output_contracts.json` + `scripts/output_contracts.py`** — each cron declares the
   artifacts its scheduled run must commit; the checker finds the job's last cron commit and diffs
   it against the declaration. **S2-F3's receipt standard applied to outputs, not just firings.**
   Required artifact absent → red row in `scheduler_health` + `::error` on the next monitor run.
   Conditional artifacts (the judge log needs an API key) warn instead.
3. **No silent guard.** All nine `|| true` / `2>/dev/null` sites were classified
   ([GUARD_AUDIT.md](verification_audit_2026Q3/GUARD_AUDIT.md)): three legitimate, six failure-hiding.
   Non-fatal is still permitted where the primary artifact must publish regardless, but it is spelled
   `|| echo "::warning::…"` and every surviving guard's comment **names the watcher** that covers its
   failure mode. A test fails on any reintroduction.

### The standing rule

> **Every scheduled job has a declared output contract, an independent checker, and no silent guard.**

A new cron is not finished when it runs. It is finished when its contract is declared, its paths are
whitelisted, and the checker has seen one real commit satisfy it.
