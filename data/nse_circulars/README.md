# `data/nse_circulars/` — NSE Index Review circulars + curated transitions

This directory feeds the Phase 2 §2.1 survivorship-bias fix. The companion
script [`scripts/scrape_nse_membership.py`](../../scripts/scrape_nse_membership.py)
reads `transitions.csv` from here and emits `data/nifty500_membership.csv`,
which [`src/data/index_membership.py`](../../src/data/index_membership.py)
then uses to filter the backtest universe at every historical date.

## Artifacts in this directory

| File | Purpose | Tracked in git? |
|------|---------|-----------------|
| `*.pdf` | Downloaded NSE Index Review circulars (raw source) | no (gitignored, large) |
| `transitions.csv` | Extracted + hand-curated add/remove events | **yes** |

Only `transitions.csv` (and this README) are tracked. PDFs are gitignored;
they're redistributable from NSE directly if anyone needs to reproduce
the parsing step. Mix auto-extracted and hand-curated rows in the same
file — the build step doesn't distinguish.

## `transitions.csv` schema

```
effective_date,action,ticker,source
2019-03-29,add,IRCTC,circular_2019q1.pdf
2019-03-29,remove,JETAIRWAYS,circular_2019q1.pdf
2024-10-22,add,HYUNDAI,circular_2024q3.pdf
```

- **effective_date** — ISO date (`YYYY-MM-DD`). The first day the change
  was live in the index. NSE usually phrases this as "w.e.f. <date>" in
  the circular.
- **action** — `add` (ticker newly included) or `remove` (ticker dropped).
- **ticker** — NSE symbol without `.NS` suffix. Match the spelling in
  `config.NIFTY_500`.
- **source** — free-text audit trail (filename, URL, or note). Not used by
  the build step; exists so a reviewer can verify a row against the
  original circular.

## Status — REVERSED + BUILT 2026-06-08 (free, via Wayback)

> The 2026-04-30 rejection (preserved below) assumed **"yfinance can't
> provide delisted names"** and that transitions need NSE-circular PDFs or a
> paid feed. **Both premises were wrong.** yfinance serves most delisted NSE
> names free, and the constituent CSV was archived ~12× by the Wayback Machine
> (2018-2026). The survivorship fix is now implemented WITHOUT this manual
> transitions.csv path:
>
> - `scripts/reconstruct_membership_wayback.py` diffs dated Wayback snapshots →
>   `data/nifty500_membership_v2.csv` (**849 tickers, real exits + re-entries**)
>   and `transitions_wayback.csv` (825 diffs) + `dropped_names.csv` (349).
> - `scripts/fetch_dropped_ohlcv.py` recovered **247/349** dropped names' OHLCV
>   → `dropped_available.csv`.
> - `.github/workflows/survivorship-rebaseline.yml` measures the impact
>   (survivor-only vs corrected walk-forward).
>
> The hand-curated `transitions.csv` + `scripts/scrape_nse_membership.py`
> backward-walk remain valid (and still work), but are now the FALLBACK — the
> Wayback path supersedes them. Adoption of `membership_v2` as the active filter
> is gated on the re-baseline result + an adversarial audit; see
> `diagnostics/research/data_foundation_2026_06_08.md`.

### (Historical) Tier 2 Phase 2 REJECTED (2026-04-30)

The transitions.csv currently shipped is **empty (header only)** — the original
plan assumed it would stay that way without paid data.

Re-examination on 2026-04-30 found that L4 alone (correcting date
ranges in the existing 497-ticker list) only touches ~0.1-0.2% of
ticker-years and impacts headline CAGR by ~1-2pp — not the 8-18pp the
audit originally estimated. The 8-18pp figure assumed we could ALSO
add price histories for fully-delisted names (DHFL, RCOM, JETAIRWAYS),
~~which yfinance can't provide~~ **(false — see 2026-06-08 reversal above:
yfinance DOES provide RCOM/JETAIRWAYS and most others free).**

**(Superseded) Decision:** accept the survivor-universe backtest scope. The
existing `data/nifty500_membership.csv` (`scripts/build_ohlcv_membership.py`)
**remains the active filter only until `membership_v2` is adopted** post-re-baseline.

Known events that would be relevant once data is acquired:

| Ticker | Approximate removal | Reason |
|---|---|---|
| DHFL | ~2019 | Insolvency (NCLT) |
| RCOM | ~2019 | Insolvency (NCLT) |
| JETAIRWAYS | ~2019 | Delisting (NCLT) |
| ZEEL | ~2024 | Sony merger fallout |

| Ticker | Approximate addition | Reason |
|---|---|---|
| HYUNDAI | 2024-10-22 | IPO Oct 2024 |

Future workflow (when reversing the decision):

```bash
python scripts/scrape_nse_membership.py build
python scripts/scrape_nse_membership.py validate
```

After build, CI gate baselines (`diagnostics/data/baselines/*.json`)
re-publish in a single PR. Gate machinery doesn't change.

## Where to get circulars

NSE publishes Index Review circulars roughly quarterly. Sources, in order
of preference:

1. **NSE archives** — https://www.nseindia.com/regulations/exchange-circulars.
   Filter by "Index" category. Dates back to ~2010. NSE aggressively
   rate-limits non-browser traffic — a manual download session is often
   faster than scripting against their WAF.
2. **NSE press releases** — https://www.nseindia.com/resources/exchange-communication-press-release.
   The announcement text is often easier to parse than the circular PDF.
3. **Kite Connect historical instrument dumps** — if you're subscribed to
   Market Data. Less granular (snapshots, not events) but authoritative.
4. **Paid vendors** — Tickertape, Upstox, Sensibull all expose historical
   constituent datasets at various price points.

## Workflow

Until `scripts/scrape_nse_membership.py fetch` and `parse` are implemented
(currently stubbed), the loop is manual:

1. Download a circular PDF into this directory.
2. Read the "addition" and "removal" tables.
3. Append one row per ticker to `transitions.csv`.
4. Run `python scripts/scrape_nse_membership.py build` to regenerate
   `data/nifty500_membership.csv`.
5. Run `python scripts/scrape_nse_membership.py validate` to sanity-check.

## Known quirks

- **Semi-annual reviews pre-2015** — NSE switched to quarterly reviews
  around 2014. Earlier reviews are semi-annual and their circulars have
  a different table format.
- **Spin-offs and demergers** — when a company demerges (e.g. RELIANCE →
  JIOFIN in 2023), NSE typically ADDs the new ticker without a
  corresponding REMOVE. That's fine — the backward walk handles
  one-sided events gracefully as long as both sides of the true
  add/remove events are recorded.
- **Renames** — if a ticker is renamed (e.g. BAJAJFINSV), NSE may issue a
  separate "name change" circular that is NOT a membership event. Do not
  record renames as add/remove. Update `config.NIFTY_500` instead.
- **Reinstatements** — tickers removed and later re-added show up as
  multiple `add` events. The build step produces multiple inclusion
  intervals for them. No special handling needed on your side.

## Sanity checks after `build`

- `validate` prints coverage stats: every ticker in `config.NIFTY_500`
  should appear in the output with a to_date of `2025-07-20`.
- `latest_to` in the stats should be `2025-07-20`.
- `earliest_from` should be `2010-01-01` (the backward walk's baseline).
- If a ticker from `config.NIFTY_500` is missing from the validate output,
  it means no transition ever added it **and** it wasn't assumed present
  at baseline — which shouldn't happen. Investigate.
