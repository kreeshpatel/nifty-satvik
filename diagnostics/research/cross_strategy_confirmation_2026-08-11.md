# Strategy agreement is not confirmation — the overlap is the crowded name

**MEASUREMENT, DESCRIPTIVE. Zero trials. Zero screen-ledger rows** — reads the committed 0001 book
and the swing 0094 record, never the banked label dataset. Standing counts: read from
`diagnostics/research/n_trials.json` and `label_screen_ledger.md`.

Prompted by the owner: run the two books side by side, and check whether names both strategies pick
are better trades ("better confirmation").

Reproduce: run `pipelines/research/run_0001_xsec_momentum.run(band)` for the momentum holdings and
`run_bhanushali_weekly_rank.backtest` for the swing ledger, both on `corrected_universe()`; correlate
daily returns and split swing R by whether momentum held the name at swing entry.

## 1. The two books correlate at 0.669 — too high to diversify

| | Sharpe |
|---|--:|
| swing (0094) | 1.13 |
| 0001 momentum | 1.13 |
| 50/50 blend | 1.24 |

Daily-return correlation **0.669** over 2,347 common days. The blend Sharpe rises to 1.24 — a real
but modest +0.11, the smoothing of idiosyncratic noise. It is **not** regime diversification: both
are long-only Indian-equity momentum and draw down in the same years (2018, 2022), so in a bad year
both are down together. Finding 0115 killed a sleeve at a *lower* correlation (0.57–0.64); 0.669 is
above that bar.

## 2. Cross-strategy agreement runs the wrong way

| swing trades | meanR | win% | N |
|---|--:|--:|--:|
| **also held by momentum at entry** | **+0.354** | 56% | 39 |
| swing only | **+0.504** | 60% | 216 |

Names both books picked did **worse**, not better. Agreement is not a confirmation signal. (N=39 is
small; read as "no confirmation benefit," with a lean to mild-negative rather than a certified kill.)

## Mechanism — one factor, two costumes

Both effects have the same cause. When a weekly-touch book and a monthly-momentum book hold the same
name, it is a well-known, heavily-trended, **crowded** stock — the extended name. The swing book's
edge lives in the fresh names momentum has not already caught; the overlap is the extended crowd,
which every measurement this session has shown is not the better population. And because both books
are the same underlying factor (relative strength / momentum), they co-move in the drawdown years,
which is why the correlation is high and the diversification illusory.

This is 0115's lesson from a new angle: sleeve diversification keeps failing on this programme
because every candidate has been a momentum variant. Real diversification needs a **different
factor** (mean-reversion, low-vol, or a different timeframe), not a second momentum book.

## Consequence

- **0001 remains a good book on its own** — Sharpe 1.13, shallower drawdown than swing, passes its
  pre-registered gate. It deserves its own forward record.
- It does **not** serve as a diversifier or a confirmer of the swing book. Running both is a modest
  smoothing play, not risk reduction, and "both books agree" is not a higher-conviction filter.
- The "strategy-agreement as confirmation" idea is closed with a receipt.

## Caveats

- Descriptive; committed artifacts, not banked labels. No trial, no screen.
- N=39 overlap is thin — the negative is directional, not certified.
- Both books are the corrected-universe research runs, not the live paper books; the live A-only
  swing book is a subset (top-5 CRS) and would overlap momentum even more, if anything.
