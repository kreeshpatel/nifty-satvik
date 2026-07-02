# Part 1.1 — Field scope & source audit: the FROZEN depth schema (measured, not guessed)

> Deliverable of sub-part 1.1 from [01_part1_data.md](01_part1_data.md). Grounded in a real audit of the
> **211 cached Screener HTML pages** (`data/_screener_cache/`, offline) using the repo's own `_section_table`
> parser — median **12 fiscal years** of annual P&L + Balance Sheet per page; a Quarterly section on all 211.

## What Screener actually provides (coverage = % of the 185 pages that carry a P&L / BS section)

**Profit & Loss (annual):** Expenses / Other Income / Tax % / Net Profit / EPS / Dividend Payout / PBT /
Depreciation / Interest = **100%**; Sales / Operating Profit / OPM % = **95.1%**. The 4.9% that lack
Sales/Operating-Profit are **banks/NBFCs** (they carry `Revenue` / `Financing Profit` / `Deposits` instead).

**Balance Sheet:** CWIP / Investments / Reserves / Total Liabilities / Equity Capital / Other Liabilities /
Other Assets / Fixed Assets / **Total Assets** = **100%**; Borrowings = **95.1%**.

## FROZEN schema — the depth fields we add to the PIT store

Additive to the current 5 (`eps_ttm, book_value_ps, roe, debt_equity, period_end`); same `period_end`-keyed,
availability = `period_end + 90d`. All levels are annual fiscal-year values (₹ cr unless a ratio).

| new store field | Screener row(s) | coverage | notes |
|---|---|---|---|
| `sales` | Sales | 95% | revenue level → growth |
| `operating_profit` | Operating Profit | 95% | → profitability proxy |
| `opm_pct` | OPM % | 95% | operating margin level |
| `net_profit` | Net Profit | 100% | → earnings growth |
| `total_assets` | Total Assets (BS) | 100% | → asset ratios |
| `interest` | Interest | 100% | secondary (coverage/quality) |
| `depreciation` | Depreciation | 100% | secondary |

(`eps_ttm` already stored → EPS growth derives from it; no new field needed for EPS.)

## Derived feature candidates this unlocks (for Part 2 — NOT built here)

Each PIT-clean (trailing-only from the reported annual series), each a Part-2 pre-registerable conviction
feature in the sanctioned F5 family:

- **Growth:** `revenue_yoy` (Sales[y]/Sales[y-1]−1), `eps_yoy`, `np_yoy`, and 3y CAGRs.
- **Profitability (the Novy-Marx-proxy that 0075 wanted but couldn't get):** `op_profit_to_assets` =
  Operating Profit / Total Assets. **True gross-profitability is NOT available** (no COGS row) — this is the
  honest accessible substitute; pre-register it as a *proxy*, not as gross-profitability.
- **Quality/stability:** `op_margin` (= OPM %), `op_margin_delta` (margin trend), `asset_turnover` (Sales/Assets).

## Explicitly EXCLUDED (so Part 2 doesn't chase them)

- **True Gross Profit / gross margin** — Screener lumps COGS into "Expenses"; no clean row (confirms 0075's
  data-gate). Use `op_profit_to_assets` as the proxy.
- **Bank/NBFC financials schema** (`Revenue`/`Financing Profit`/`Deposits`) — the ~5% deposit-taker names are
  already excluded by the solvency filter (data-quality §1.4 W-04); the depth schema targets the ex-financials
  universe the strategy already trades. Do not special-case banks here.

## Risks carried into 1.5 (coverage & quality audit)

- **Restatement lookahead** — Screener shows the *latest restated* figure per fiscal year, not as-first-
  reported. For a growth/margin feature this is a subtle forward-peek. It is the **same** residual the existing
  `eps_ttm`/`roe` already carry (bounded, known), but growth features amplify it → **quantify in 1.5** (how
  often a restatement flips the sign of a YoY feature) before trusting any growth field.
- **Current-universe coverage unknown** — the 211 cached pages are mostly *delisted* names (the earlier
  `--mode delisted` scrape). The Screener *schema* is identical for current names, so the field list is frozen;
  but per-name coverage on the live universe needs a `--mode current` scrape + a coverage re-measure (1.5).
- **Annual vs quarterly** — first cut uses **annual YoY** (median 12y history, cleaner). QoQ is feasible (the
  Quarterly section is on every page) but noisier/lower-coverage → a Part-2 option, not the baseline.

## 1.1 verdict: GO

The depth schema is real, measured, ≥95%-covered on the target universe, PIT-joinable via the existing
`build_pit_frame_from_screener` path (extend the row list; do not rebuild). One honest downgrade
(gross-profit → operating-profit-to-assets proxy) and one risk to quantify (restatement) carried to 1.5.

## Next
Drill/execute **1.2 (scrape-parse extension)**: extend `build_pit_frame_from_screener` to emit the 6 new
fields from the already-parsed P&L/BS tables, with the single-code-path rule, fed by the hermetic test
fixtures (no network). Then **1.4** (the truncation gate) before any feature work.
