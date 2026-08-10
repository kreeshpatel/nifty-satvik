# Swing book — after-tax return (MEASUREMENT, no trial)

STCG 20%, paid out of the book each calendar year so the tax stops compounding.
Initial capital Rs 1,000,000. Reproduce: `python pipelines/diagnostics/diag_swing_after_tax.py`

| book | closed | gross CAGR | **after-tax CAGR** | wedge | gross MaxDD | after-tax MaxDD | total tax |
|---|--:|--:|--:|--:|--:|--:|--:|
| base-swing (certified, all grades) | 255 | 24.69% | **20.43%** | 4.27pp | -42.4% | -42.4% | Rs 1,664,770 |
| live config P (A-only, what trades) | 130 | 27.18% | **24.30%** | 2.88pp | -39.5% | -39.5% | Rs 1,754,584 |
