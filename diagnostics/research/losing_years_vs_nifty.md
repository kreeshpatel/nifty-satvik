# Do the book's losing years coincide with the index's? (MEASUREMENT, no trial)

Tests the stated premise for accepting losing years — *"nifty will be negative in that year and we have to overlook something"*.

| year | NIFTY-50 | base-swing (certified) (after tax) | live config P (what trades) (after tax) | 0001 cross-sectional momentum (after tax) |
|---|--:|--:|--:|--:|
| 2017 | +28.75% | +31.76% | +50.57% | +0.00% |
| 2018 | +3.15% | +9.51% | -18.02% | -9.57% |
| 2019 | +12.02% | +25.88% | +29.58% | +7.85% |
| 2020 | +14.90% | +5.66% | +104.48% | +51.74% |
| 2021 | +24.12% | +32.45% | +41.63% | +82.70% |
| 2022 | +4.33% | +27.24% | -2.76% | -4.45% |
| 2023 | +20.03% | +58.71% | +36.42% | +48.72% |
| 2024 | +8.80% | +3.25% | +16.19% | +35.10% |
| 2025 | +10.51% | -16.22% | -15.97% | -8.11% |
| 2026 *(partial)* | -8.66% | +31.32% | +31.24% | +2.13% |

**NIFTY-50 losing years:** [2026]

- **base-swing (certified)** — losing years [2025]; of those, **0** coincide with a Nifty decline and **1** occurred while the index ROSE ([2025]).
- **live config P (what trades)** — losing years [2018, 2022, 2025]; of those, **0** coincide with a Nifty decline and **3** occurred while the index ROSE ([2018, 2022, 2025]).
- **0001 cross-sectional momentum** — losing years [2018, 2022, 2025]; of those, **0** coincide with a Nifty decline and **3** occurred while the index ROSE ([2018, 2022, 2025]).

## Reading

Momentum and swing books do not lose money in bear markets — they lose it in **reversals**, which is the Daniel-Moskowitz result (crashes cluster in panic-and-rebound states, not in declines). So the premise does not hold on this record: the losing years are years the index made money and this book did not. That is a harder thing to sit through than a market-wide decline, and it is the risk `docs/DESTINATION.md` §6 asks the owner to accept consciously.

Reproduce: `python pipelines/diagnostics/diag_losing_years_vs_nifty.py`
