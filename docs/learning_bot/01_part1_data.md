# Part 1 — DATA: the new-information layer (fundamentals-depth), PIT-clean

> Drill-down of Part 1 from [00_master_plan.md](00_master_plan.md). Goal: give the learner information the
> price does not contain, **point-in-time-clean**, so nothing here can leak the future. Starts NOW (zero
> trials, no in-sample fit). Each sub-part below is a leaf we can drill further and build/test independently.

## Why this part is the whole game

The learner is only as good as its inputs. Every conviction feature (Part 2) is a transform of this data, so
a leak here silently inflates every downstream backtest. The current PIT store carries only **5 fields**
(`period_end, eps_ttm, book_value_ps, roe, debt_equity`). "Depth" = the orthogonal fundamentals the price
doesn't encode: **revenue, revenue/EPS growth (YoY, QoQ), gross profit & margins, operating profit**. These
map to the sanctioned F5 earnings-momentum feature family and are PIT-joinable via the existing
`value_quality_series` `merge_asof(backward, allow_exact_matches=False)` pattern.

## The PIT contract for this part (non-negotiable)

Every field, for every `(ticker, period)`, is stamped with an **availability date** = `period_end + 90d`
(the publication lag already used by the store). A feature computed for signal date `t` may read only the
most-recent period with `availability ≤ t`. **Truncating all future filings must leave every past value
byte-identical** (the same truncation test that cleared the macro rebuild, `tests/test_macro_pit.py`).

## Sub-parts

### 1.1 — Field scope & source audit ✅ DONE → [02_part1.1_field_scope.md](02_part1.1_field_scope.md)
**GO.** Audited the 211 cached Screener pages (median 12y annual history). Frozen schema = add `sales,
operating_profit, opm_pct, net_profit, total_assets, interest, depreciation` (≥95% coverage on the
ex-financials universe). **Downgrade:** true gross-profit unavailable (no COGS row) → use
`op_profit_to_assets` proxy. **Risk to 1.5:** restatement lookahead. Bank/NBFC schema excluded (already
solvency-filtered). Derived features (Part 2): `revenue_yoy/eps_yoy/np_yoy`, `op_margin`, `op_profit_to_assets`.

### 1.2 — Scrape / parse extension
Extend the Screener parser to pull the new rows and compute the derived series (growth = latest vs
year-ago period from the *reported* series, trailing-only). One code path, reused offline + live (the
`conviction-features` §1c single-code-path rule). No network in tests — parse from saved Screener fixtures.

### 1.3 — PIT store schema extension
Add the new columns to `fundamentals_pit_screener.pkl` (still `period_end`-keyed, availability = `+90d`),
**backward-compatible** so `value_quality_series` and every current caller keep working unchanged. New fields
are additive; existing 5 fields byte-identical.

### 1.4 — Truncation / leakage test *(the gate)*
`tests/test_fundamentals_pit_depth.py`: build the store truncated at date `d`, assert every value at periods
available `≤ d` equals the full-build value. Any forward-looking op (using a restated figure, a filing dated
after the period without the lag) fails it. This is the `leakage-audit` gate for the data layer — Part 2
cannot start until it is green.

### 1.5 — Coverage & quality audit
Via the `data-quality` skill: for each new field, report coverage (% of the ~500-name universe × history
with a non-null value), unit consistency (₹ cr vs ₹, per-share vs absolute), outlier/restatement flags. **Key
risk to surface: restatement lookahead** — Screener shows the *latest* restated figure, not as-first-reported;
quantify how often this bites and whether it materially moves a growth feature. Document the residual caveat.

### 1.6 — Pin & provenance
Persist the extended store, record a builder + manifest (the provenance the old `macro_data.pkl` lacked), so
finding-grade numbers are byte-reproducible. Commit with the data-layer test green + full suite green.

## Definition of done for Part 1
Extended PIT store carrying the depth fields; truncation test green; coverage/quality audit written with the
restatement caveat quantified; existing callers + golden master unaffected; builder + manifest committed. No
model, no trial — pure trustworthy data.

## Risks / open questions (resolve while drilling 1.1)
- **Restatement lookahead** (1.5) — the main PIT subtlety; may cap which growth fields are trustworthy.
- **Coverage** — small/mid names may lack clean quarterly history pre-2018; a sparse field is a weak feature.
- **Quarterly vs annual** — QoQ needs quarterly P&L (noisier, less coverage) vs annual YoY (cleaner, laggier).

## Next step
Drill **1.1 (Field scope & source audit)** into its sub-sub-parts (per-field source check + schema freeze),
then build 1.2→1.4. (`02_part1.1_field_scope.md`.)
