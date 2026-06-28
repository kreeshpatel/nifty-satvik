# Survivorship fix — #5 in the hardening checklist

> **Status (2026-04-21):** scope choice made. We are NOT pursuing the fix.
> See [diagnostics/survivorship_methodology.md](../diagnostics/survivorship_methodology.md)
> for the decision, rationale, and whitepaper caveat language. This doc
> remains as reference for the scaffolding that shipped and the data
> sources evaluated, in case the decision is reversed later.

Code is ready; **data acquisition is the blocker.** Expected impact when fix lands: CAGR 72% → 30-50%, Sharpe 3.9 → 1.5-2.2.

---

## What's already shipped (code-side)

- [src/data/index_membership.py](../src/data/index_membership.py) — owns the data contract, parses the CSV, applies the filter. Missing file = no-op.
- [src/data/data_store.py](../src/data/data_store.py) — `get_period()` accepts `apply_membership_filter=True` (default). Membership is pulled transparently on every call.
- Backtest (`diagnostics/run_backtest.py`) and training (`train.py`) both call `get_period()` — both pick up the filter automatically once the CSV exists.

Smoke test confirmed: with a 4-ticker synthetic membership CSV, `get_period("2025-01-01", "2025-04-22")` returns only the 2 tickers active in that window (149 rows). Without the CSV, it returns the full 496-ticker set (36,835 rows). **Drop-in.**

---

## What you need to get

A single file: `data/nifty500_membership.csv` with schema:

```
ticker,from_date,to_date
RELIANCE,2010-01-01,2026-04-22
SWANENERGY,2020-01-01,2023-07-15
HYUNDAI,2024-10-22,2026-04-22
PEL,2010-01-01,2023-03-18
```

Rules:
- **ticker** — NSE symbol, no `.NS` suffix
- **from_date** — first date in index (inclusive), YYYY-MM-DD
- **to_date** — last date in index (inclusive). For tickers still in the index today, use today's date (or any far-future date).
- Multiple rows per ticker are allowed if a stock was dropped and later re-included.

Expected row count: ~800-1000 rows (500 currently active + ~300-500 historical tickers that cycled through the index at some point 2010-2025).

---

## Where to get the data (in order of difficulty)

### Option 1 — Kite Connect (EASIEST, you already have access)

Kite Connect provides historical instrument dumps. Each dump timestamps when a symbol was added/removed from index listings. Query approach:

```python
from kiteconnect import KiteConnect
kite = KiteConnect(api_key=os.environ["KITE_API_KEY"])
# Kite's "instruments" endpoint returns current active; for history you need
# to correlate with quarterly index-review announcements.
```

Kite's own instruments table isn't indexed by date, so you'd still need to cross-reference with announcement dates. Talk to Zerodha support — they sometimes share historical datasets on request for paid subscribers.

### Option 2 — NSE Index Review circulars (FREE, tedious)

NSE publishes quarterly "Nifty Indices — Index Maintenance" circulars every March / June / September / December. Each announces additions + deletions for the upcoming quarter.

Starting point: https://www.nseindia.com/regulations/exchange-circulars
Search: "Nifty 500 Index Review"

Parsing these is manual or semi-automated scraping. Pattern is consistent enough to script:
- Circular format: inclusions + exclusions, 20-40 tickers per review
- Going back to 2010 → ~60 circulars
- Expected effort: 1-2 days scraping + cleanup

### Option 3 — Paid vendors

- **Tickertape** (₹999/mo)  — has historical constituents API; documented
- **Upstox Pro API** — similar
- **Sensibull** — quantitative data, includes historical benchmark compositions

Most cost-effective if the data isn't critical long-term: buy 1 month, pull the full history, cancel.

### Option 4 — Open-source Python libraries

- [nsepython](https://github.com/aeron7/nsepython) — check if `nse_historical_constituents()` or similar exists
- [nsepy](https://nsepy.xyz/) — primarily OHLCV, but has some index-level queries

Reliability varies. Good to try before paying.

---

## Once you have the CSV

1. Drop it at `data/nifty500_membership.csv`

2. Validate:
   ```bash
   python -m src.data.index_membership
   ```
   Prints `{n_tickers, n_period_rows, earliest_from, latest_to, tickers_still_active, tickers_historical_only}`. Sanity: `n_tickers` should be 800-1000; `earliest_from` should be ≤ 2010; `latest_to` should be ≥ today.

3. Run the survivorship-clean backtest:
   ```bash
   python -m diagnostics.run_backtest
   ```
   No code change needed — `get_period()` picks up the CSV automatically. Watch for the `(membership-filtered)` tag in the output.

4. Compare new metrics vs current:
   - Expected: CAGR drops from 72% → 30-50%
   - Expected: Sharpe drops from 3.89 → 1.5-2.2
   - Expected: Max DD worsens from -11.7% → -15% to -20%
   - Expected: WR stays roughly unchanged (~60%)

5. If the drops are gentler than expected (say CAGR stays above 60%), double-check the CSV covers enough historical names. A too-sparse CSV produces artificially-close-to-current numbers.

6. Retrain the model if desired:
   ```bash
   python train.py
   ```
   Training data gets the same filter automatically, so the model sees only constituent-valid rows during training.

---

## Commitment to honesty (from the hardening checklist)

When new numbers land, hold to the predicted range:
- **35% CAGR / Sharpe 1.7** → real system, build the product
- **8% CAGR / Sharpe 0.6** → smaller edge, pivot product strategy
- **60% CAGR / Sharpe 2.5** → something's still contaminated, keep looking

Don't rationalise surprises.
