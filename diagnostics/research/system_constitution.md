# System Constitution — the live weekly-swing (bhanushali) path

**Audit date:** 2026-07-29 · **Session class:** read-only code audit — zero screens spent, zero
trials spent, no tests run against outcomes. **Program counts as of this audit (unchanged by it):
screens 11, sealed opens 1, n_trials 138.** Forward-wall performance logs were not read
(no-peeking holds); every row below is sourced from code, not results.

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
| E2 | Card **entry** = current close if inside the band, else band midpoint; card **stop** = signal-week low; card **target** = entry + 2×(entry−stop) | cron:229-237 | The prices printed on the buy card | **DIVERGENT** (D5): the modeled book fills at next-week's in-range OPEN with the stop LIFTED to max(low, 0.9×entry) (R94:759, 821-822) | The card's entry/stop/target ≠ the book's entry/stop/target for the same trade | The owner's real R, target level, and resting-limit price all differ from what the record books |
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
| G9 | Positions absent today's bar: exit logic silently skips (`i is None → continue`) — a suspended/delisted holding can NEVER exit | R94:412-414 | No stale-position handling (contrast: momentum engine force-closes after 10 absent sessions, nq/engine/portfolio.py:43) | INCIDENTAL⚠ (nobody chose this; see Broken list B-1) | Backtest same code — but the pinned dataset has no forward suspensions; live will | Zombie positions freeze capital in the ₹10L book and distort NAV (see B-1) |

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
| I1 | NAV = cash + Σ shares × today's close; names missing today's bar are marked at **ENTRY price** | R94:864-865 | Daily mark | INCIDENTAL⚠ (the `else p["en"]` fallback — see Broken B-1) | Same code | A −40% suspended name is marked at entry: NAV flattered; scorecard Sharpe/MaxDD gates (I4) read this NAV |
| I2 | The whole book — positions, ledger, NAV history — is **recomputed from inception every run**; nothing is append-only | cron:12 (docstring, "known mutable-record caveat, finding-0035 TODO"); cron:574-580 | Idempotent, stateless design | **DIVERGENT** (D2): the "record" can rewrite its own past when input data changes (yfinance revisions, re-adjustments, membership edits) | Run of record pinned; live unpinned | The forward record is only as immutable as yfinance's history; documented drift exists (ohlcv.py:330-335) |
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

## 2. THE DIVERGENT LIST (highest-value finds — no fixes applied; each is a mid-quarter change decision)

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

**D2 — The forward record is mutable: every Saturday rewrites the whole book from inception off refreshed data.**
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

**D5 — Card prices ≠ book prices for the SAME trade.**
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
| M1 | C7 — no golden master for the R94 engine (the byte-identical claims are comment-discipline only) | The momentum path's engine invariant is enforced by `tests/test_stage2_golden.py`; the swing engine's "default OFF ⇒ byte-identical" claims are enforced by nothing | Freeze one committed reference run (ledger CSV sha) of `backtest()` all-defaults on the pinned dataset; assert byte-equality in CI — pure harness, no new information |
| M2 | G6 — no time cap of any kind (52-week backstop silently absent under P) | Indefinite holds concentrate the book in aging names; the cron docstring still advertises a backstop that doesn't exist | On the EXISTING 0094-P ledger/state: distribution of `held_weeks`; count positions that would have hit a 52-week backstop; max concurrent age |
| M3 | F1 — strict band boundaries + open-only fill | Fills lost to a one-tick boundary or to weeks where price traded inside the band but never OPENED inside it | On the existing uncapped ledger + cache: count signal-weeks where no open landed in-band but some LOW did; count opens within 0.1% of a band edge |
| M4 | F4 — alphabetical tie-break; cash-cap fill ordering | Deterministic but arbitrary preference when CRS ranks tie or cash is short | On the existing paper ledger: how many entry days had `skipped_cash > 0`; re-sort those days' candidates by ticker-reversed order and diff the fill set (pure replay of one rule) |
| M5 | G5 — stop never moves (no breakeven after tp1) | Post-2R givebacks ride to the full initial stop; the taught rule's giveback profile was the exit forensic's main finding | On the existing ledger: among trades that booked tp1 then exited `stop_part`/`sma_break`, compute R lost below breakeven — a column arithmetic pass |
| M6 | B8 — no demerger/bad-tick guard on the swing path | One value-leaving demerger mid-hold fabricates a stop/sma_break or an entry touch | Run `demerger_suspect_names` (existing function, ohlcv.py:245) over the live cache and intersect with current cards/holds — read-only scan |
| M7 | B10/B1 — membership CSV + NIFTY_500 snapshot refresh cadence (manual; last 2026-06-29) | Sept semi-annual rebalance lands BEFORE the Oct-1 review; removed names keep trading, added names invisible | Diff `NIFTY_500` + membership actives against the current NSE constituent list (one download, no engine touch) |
| M8 | B7 — the 300-bar prep floor as a universe rule | Names appear the week they cross 300 bars, with exactly-warm SMA windows | Count cache names within 250–350 bars today; check whether any current card is within 10 weeks of its own warm-up edge |
| M9 | B4 — ADJ_JUMP 0.5% threshold + monthly rebuild | Sub-threshold dividend drift accumulates inside a month | Histogram overlap-close shifts from one warm refresh (the guard already computes them; log instead of discard) |
| M10 | A6 — `NSE_HOLIDAYS` ends 2026 | 2027 Jan/Apr review dates could mis-place the "first trading day"; the cleaner's phantom-bar drop (unused here) also stales | Eyeball: add-2027-list decision at the Oct review; zero-compute |
| M11 | H4 — mark-to-market compounding of the 2% risk base | Risk-per-trade grows/shrinks with unrealized P&L — sequencing sensitivity | On the existing NAV curve: recompute sizes off fixed EQ0 and diff realized risk % per fill (column arithmetic on the ledger) |
| M12 | E8 — regime chip thresholds (60/40, 10-bar) | Display-only today; becomes a rule if anyone ever gates on it | None needed while display-only; constitution note is the guard |
| M13 | K5 — UTC/IST date framing works by schedule luck | A future cron time near IST midnight flips `date.today()` | Grep-level check on any future schedule change; note in workflow comments |
| M14 | I5 — win = R>0 counts scratches | Cosmetic WR inflation vs a ±0.1R deadband | One-line recount on the existing ledger with a deadband |

---

## 4. Outright broken (bug, not convention) — reported, NOT fixed (live-path changes are quarterly-review class)

**B-1 (HIGH, latent): absent-bar positions are unmanageable and marked at ENTRY price.**
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

**B-2 (LOW, doc rot that misstates the live exit): the cron docstring and constants describe the wrong engine and a nonexistent backstop.**
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
