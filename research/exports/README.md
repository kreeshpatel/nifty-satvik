# research/exports — derived artifacts

Outputs of committed code over pinned inputs. Most are small and committed; a few are large and
deliberately **not** committed because they are byte-deterministic and therefore regenerable.

## Not committed (git-ignored) — regenerate on demand

| artifact | size | regeneration command |
|---|---|---|
| `ohlcv_corrected_long.{csv,parquet}` | ~100 MB + ~48 MB | `python scripts/export_ohlcv_corrected_long.py` |

**`ohlcv_corrected_long.{csv,parquet}`** — long-format dump of the corrected universe (814 tickers,
1,594,575 rows, `[ticker, Date, Open, High, Low, Close, Volume]`, 4-decimal precision), built from
the pinned `data/ohlcv.pkl` (`f8625a8f…`, release `dataset-pin-20260701`) plus
`data/ohlcv_backfill.pkl` (`9ebbe448…`, release `dataset-pin-20260729`) via the committed
`corrected_universe()`.

Classified **derived, not mortal** — no vendor is involved in regenerating it, so it is not pinned
to a release. Verified 2026-07-30: the previously-untracked working copies reproduced exactly from
the builder — identical shape, tickers and dates, and numerically identical once the 4dp rounding is
applied (max abs diff 5.0e-05 pre-rounding, `allclose` after). The CSV is also within a rounding
error of GitHub's 100 MB hard file limit, which is an independent reason not to commit it.

Fetch and `sha256sum` the pinned inputs before regenerating — local `data/` is not evidence
(see `diagnostics/research/review_2026Q4/01_reanchor.md` §PROVENANCE).
