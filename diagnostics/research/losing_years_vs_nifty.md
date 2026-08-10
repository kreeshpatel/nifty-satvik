# Do the book's losing years coincide with the index's? (MEASUREMENT, no trial)

Tests the stated premise for accepting losing years — *"nifty will be negative in that year and we have to overlook something"*.

| year | **NIFTY 500 TRI** | NIFTY-50 (px) | base-swing (certified) (after tax) | live config P (what trades) (after tax) | 0001 cross-sectional momentum (after tax) |
|---|--:|--:|--:|--:|--:|
| 2017 | **+6.96%** | +28.75% | +31.76% | +50.57% | +0.00% |
| 2018 | **-2.14%** | +3.15% | +9.51% | -18.02% | -9.57% |
| 2019 | **+8.97%** | +12.02% | +25.88% | +29.58% | +7.85% |
| 2020 | **+17.89%** | +14.90% | +5.66% | +104.48% | +51.74% |
| 2021 | **+31.60%** | +24.12% | +32.45% | +41.63% | +82.70% |
| 2022 | **+4.25%** | +4.33% | +27.24% | -2.76% | -4.45% |
| 2023 | **+26.91%** | +20.03% | +58.71% | +36.42% | +48.72% |
| 2024 | **+16.24%** | +8.80% | +3.25% | +16.19% | +35.10% |
| 2025 | **+7.76%** | +10.51% | -16.22% | -15.97% | -8.11% |
| 2026 *(partial)* | **-3.20%** | -8.66% | +31.32% | +31.24% | +2.13% |

**NIFTY 500 TRI losing years:** [2018, 2026]  (2017 is a PARTIAL TRI year — series starts 2017-09-14)

- **base-swing (certified)** — losing years [2025]; of those, **0** coincide with a TRI decline and **1** occurred while the index ROSE ([2025]).
- **live config P (what trades)** — losing years [2018, 2022, 2025]; of those, **1** coincide with a TRI decline and **2** occurred while the index ROSE ([2022, 2025]).
- **0001 cross-sectional momentum** — losing years [2018, 2022, 2025]; of those, **1** coincide with a TRI decline and **2** occurred while the index ROSE ([2022, 2025]).

## Reading

Against the benchmark of record the premise **partly holds**. 2018 — the book's worst year — was a genuine market decline (TRI −2.14%), so one of the three losing years is the market-wide kind the owner said they would overlook. The other two, 2022 and 2025, are not: the index rose and this book did not.

That split is the expected shape. Momentum and swing books do not lose money in bear markets so much as in **reversals** — the Daniel-Moskowitz result that crashes cluster in panic-and-rebound states rather than in declines. 2025 in particular was a midcap reversal inside a rising large-cap year, which is this family's worst regime.

Reproduce: `python pipelines/diagnostics/diag_losing_years_vs_nifty.py`
