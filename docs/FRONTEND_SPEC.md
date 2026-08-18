# Nifty Satvik — Frontend Design Spec & Data Contract

The source of truth for building the pro frontend efficiently. The visual reference is the
**Daily Command Center** mockup (published as an Artifact, refined-fintech dark instrument). This doc
is the other half: the design system it establishes, and the exact backend data every component reads,
so the Vercel frontend repo can implement it without guessing field names or shapes.

**Why this exists:** the frontend lives in a separate Vercel repo (this repo is backend-only), so the
design can't be run/checked here. The workflow is: **align on the Artifact mockup → implement against
this contract in the frontend repo → deploy.** One design loop, not fifty blind run-check cycles.

---

## 1. Goal

A daily-driver command center for one sophisticated operator (the owner) who executes on their own
broker off self-reported fills. It answers, in priority order, three questions each market day:

1. **Is there anything to sell/trim right now?** (the highest-value action — a profit tranche or a stop)
2. **What's fresh to buy this week, and how good is each?** (with the quality signals that separate a
   PTCIL from a CCL)
3. **How are my holds doing, and where's each vs its stop/target?**

Everything else (research board, execution ledger, breadth-50) hangs off this frame later and inherits
its design system.

## 2. Design system (from the mockup — inherit these tokens exactly)

**Aesthetic:** refined-fintech, dark-committed instrument. Single visual world by intent; a trading
terminal read at market hours. Every color painted explicitly (no reliance on `prefers-color-scheme`).

**Color tokens** (CSS custom properties; semantic colors are separate from the brand accent):

| token | hex | role |
|---|---|---|
| `--bg` | `#0b0e14` | cool slate-black ground |
| `--surface` / `--surface-2` | `#141922` / `#1a212d` | cards / hover |
| `--line` / `--line-2` | `#232c3a` / `#2c3648` | hairlines |
| `--ink` / `--ink-2` / `--muted` / `--faint` | `#e6ebf2` / `#aab6c8` / `#7f8ba0` / `#5a6576` | text ramp |
| `--accent` | `#4c8dff` | brand blue (N→arrow), interactive/buy |
| `--up` | `#3fb98c` | gains, buys, take-profit |
| `--down` | `#f0616d` | losses, stops, sells |
| `--warn` | `#e0a33a` | low-conviction, warnings |

**Type:** system sans (`ui-sans-serif, -apple-system, "Segoe UI"`) for labels + copy; **monospace with
`font-variant-numeric: tabular-nums`** (`ui-mono, "SF Mono", "JetBrains Mono"`) for **every** price, R,
%, and count. For an instrument, aligned mono figures are the typographic personality — and cost no
webfont. Uppercase eyebrows get `.1em–.14em` tracking; headings sit on a fixed scale.

**State encoding (information-design rules):** summary before detail; state must read at a glance, not
only as a number. Left **severity stripe** per card (`--accent` buy · `--warn` low-conviction · `--up`
take-profit · `--down` stop). **Chips** for grade (A), conviction (normal/low), action (TRIM 40%).
P&L always colored. R:R shown as a split bar. Holds show an **entry→current→target progress rail** so
"where is this trade" reads instantly.

**Priority tiers** (vertical, top = most urgent): `Act now (sell/trim)` → `Fresh buys` → `Holding`.

## 3. Screen: Daily Command Center — component tree

```
Header      brand · regime pill · breadth · scan-freshness dot
PortfolioStrip   NAV · from-peak · open-risk · cash · actions-today
Tier "Act now"       SellCard[]     (trim + full-exit)
Tier "Fresh buys"    BuyCard[]      (5 this week)
Tier "Holding"       HoldRow[]      (live P&L + progress rail)
Footer      model id · certification state · cadence
```

## 4. Backend data contract (the wiring)

All endpoints are prefixed `/api` and require the auth cookie (`nq_access`). Base router:
`dashboard/backend/routers/signals.py`.

### `GET /api/signals?model=bhanushali` — the whole screen's primary feed

Returns the envelope `{ signals[], regime, portfolio, model, ...cron health }`.

**`regime`** → `Header` regime pill + breadth:
```
{ "status": "BEAR"|"BULL"|"NEUTRAL", "strength": 39, "vix": 0, "breadth": -35 }
```

**`portfolio`** → `PortfolioStrip` (admin sees `source:"paper"`, others zeroed — tenant rule):
```
{ "source":"paper", "cash":62782, "total_value":1019489, "positions":21, "total_trades":… }
```
NAV = `total_value`; from-peak and inception-return are derived client-side (peak lives in
`results/paper_portfolio_weekly.json.peak_value`; expose via overview if needed).

**`signals[]`** → `BuyCard` (status `FRESH`) and feeds `HoldRow` (status `ACTIVE`). Per-signal fields:

| field | type | component use |
|---|---|---|
| `ticker` | str | title |
| `status` | `FRESH`\|`ACTIVE` | routes to Buy tier vs Hold tier |
| `grade` | `"A"` | grade chip |
| `signal_conviction` | `normal`\|`low` | conviction chip + amber stripe when `low` |
| `entry` / `stop` / `target` | num | price rows; R = `entry-stop`, target = +2R |
| `ext_pct_over_sma44` | num | "ext % over 44w SMA" |
| `body_ratio` | num | entry-candle quality |
| `crs_rank` | num | relative-strength readout (higher = stronger) |
| `buy_window` / `buy_window_until` | str/date | "buy Mon–Fri at open in band" |
| `current_price` | num | live price (overlaid from the monitor — see below) |
| `actionability` | `BUY_OPEN`\|`BUY_CLOSED`\|`EXIT_REQUIRED` | buy affordance / exit flag |
| **`sell_guidance`** | obj\|null | **the SELL surface — see §4.1** |
| `exit_plan.tranches[]` | `{pct,type:target\|pattern\|runner,level\|arm}` | tranche plan; drives trim detection |
| `monitor` | obj | per-ticker live block (current_price, event flags) |

### 4.1 `sell_guidance` — the take-profit / exit surface (shipped this cycle)

Attached to every signal (model-centric page) and to per-user positions. **`null` when the position is
purely Hold/Buy.** Shapes:

```jsonc
// partial take-profit (a scaled-exit target tranche reached, position stays open)
{ "reason":"target_tranche", "tone":"bull", "headline":"+2R target reached — trim 40%",
  "suggested_exit_price":10669, "partial_pct":40, "urgency":"normal", "note":"…Saturday decides the rest" }
// full exits
{ "reason":"stop",   "tone":"bear", "headline":"Stop triggered — exit at market", "urgency":"high" }
{ "reason":"target", "tone":"bull", "headline":"Target hit — exit recommended" }
{ "reason":"time",   "tone":"warn", "headline":"Time exit reached — close position" }
```
`SellCard` renders `headline` + `suggested_exit_price`; a `partial_pct` present → **TRIM** chip and the
green take-profit treatment; `reason:"stop"` → red/high-urgency. This is what makes the profit sells
as prominent as the buys.

### `GET /api/signals/sell-guidance` — the "Act now" tier headline

Thin filter for the sell tier without pulling all positions:
```
{ "positions":[ {…position, "status_for_user":"ACTIONABLE_TRIM"|"ACTIONABLE_SELL", "sell_guidance":{…}} ],
  "count":1, "updated_at":"…" }
```
`ACTIONABLE_TRIM` = sell a tranche, position stays open · `ACTIONABLE_SELL` = full exit. Both belong on
the Act-now tier; the frontend distinguishes them by status + `sell_guidance.partial_pct`.

### Supporting endpoints

| endpoint | feeds |
|---|---|
| `GET /api/signals/history` | closed-trades list (R-multiple, exit_reason) — Hold/History views |
| `GET /api/signals/watchlist` | borderline candidates (`tier:"watchlist"`) — a watchlist strip |
| `GET /api/positions/nq` | per-user positions + P&L + `sell_guidance` (Positions page) |
| `results/weekly_monitor.json` (overlaid into `/api/signals`) | `current_price` + intra-week `flags[]` (`FILLED_TODAY`, `TRANCHE_TARGET_2R`, `STOP_BREACH`, `PATTERN_ARMED`, `RUNNER_BELOW_SMA`) — live re-price + event banners between Saturday recomputes |

## 5. Freshness & cadence (must be visible)

The weekly engine recomputes **only Saturday 18:00 IST**; the daily monitor re-prices Mon–Fri. The
header must show scan freshness (from the envelope's `generated_at` + cron-health block) so a viewer
never mistakes a stale card for a fresh decision. The certification state (`UNDERPOWERED · DSR 0.89 ·
not certified`) stays in the footer — the book is a forward-watch paper record, not a certified signal.

## 6. Build notes (efficiency)

- Implement in the frontend repo against this contract; the Artifact mockup is the visual reference.
- Inherit the §2 tokens verbatim so every future screen is one system.
- No localhost needed to iterate on *design* — redeploy the Artifact mockup for design review; wire real
  data only once the layout is signed off.
- The backend already emits everything above (`sell_guidance` incl. `partial_pct`/`ACTIONABLE_TRIM`
  shipped 2026-08-18). No further backend work is required for this screen.
