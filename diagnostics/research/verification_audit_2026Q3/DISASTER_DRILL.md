# Clean-clone disaster drill — 2026-07-31

**Verification class. Counts frozen: screens 14 · sealed opens 1 · n_trials 138.**
Fresh directory. **Nothing copied from the working tree** — `git clone` + GitHub releases only.
Doubles as mechanical replication for **A1** (baseline_v1), **A2** (corrected anchor), **A3** (swing
record + goldens).

## Total reconstruction time: **4 min 37 s** (277 s)

| step | elapsed |
|---|---:|
| full `git clone` | 15 s |
| `dataset-pin-20260701` (ohlcv.pkl, 64 MB) | 40 s |
| `dataset-pin-20260729` (backfill + banked, 59 MB) | 13 s |
| sha verify + artifact inventory + install attempt | 20 s |
| golden masters (22 tests) | 12 s |
| full suite (218 tests) | 71 s |
| A2 corrected-anchor table | 106 s |

**That is the program's actual disaster-recovery cost on a warm network.** It is genuinely fast —
but the drill's value is the four gaps below, not the clock.

## What reconstructed cleanly

- **`ohlcv.pkl` sha256 = `f8625a8f…` — matches the pin documented in CLAUDE.md exactly.** The
  dataset pin is real and verifiable, not a claim.
- **Golden masters: 22 passed** (`test_r94_golden`, `test_stage1_golden`, `test_stage2_golden`).
- **Full suite: 218 passed** — identical to the working tree.
- **A2 corrected-anchor table reproduces**, and with it **A3's headline: swing corrected
  Sharpe 1.132, MaxDD −42.4%** — exact against the published record. The pinned-vs-corrected trade
  diff regenerates too (111 corrected-only / 96 pinned-only trades).

## Gaps — the drill's actual output

### G1 — a fresh clone **does not install** on current Python

```
ERROR: Package 'nifty-satvik' requires a different Python: 3.13.5 not in '<3.13,>=3.12'
```

`pyproject.toml` pins `>=3.12,<3.13`; the machine runs 3.13.5. **`pip install -e ".[dev]"` — the
documented setup step, and the one CI runs — fails outright.**

**Why the program still works anyway:** every script does `sys.path.insert(0, ROOT)`, so imports
resolve without the package being installed. Verified: `import config, nq.validation.metrics`
succeeds. **CI is currently unaffected** (the workflow pins `python-version: "3.12"`).

**So this is a latent blocker, not an active one** — it bites a human or a recovery operator on a
current interpreter, and it will bite CI the day the pin is bumped. Recommend widening the ceiling
or documenting the required interpreter in the recovery path.

### G2 — `research/substrate/trades.parquet` is in **neither git nor either release**

The Stage-1 uncapped substrate (4,321 trades) underpins the **band census (A5)**, **0126's hug
screen** and **0127's activation bound**. It is rebuildable via `scripts/build_substrate.py`, but
that rebuild was **not exercised** here, so "recoverable" is asserted rather than demonstrated.

### G3 — `data/fundamentals_pit_depth.pkl` is in neither git nor either release

Consumed by the value/quality layer. Same class as G2, without a named rebuilder.

### G4 — **A1 cannot be mechanically replicated: baseline_v1 has no producer script**

`research/baseline_v1.json` carries the anchors (Sharpe 0.667 / CAGR 15.46% / MaxDD −46.26% /
1,279 trades) and attributes them to a plan document, but **no committed script regenerates them.**
A repo-wide search finds only *consumers* of the file.

**This is the same defect class as the 0115 blend gap the audit found in session 2 and remedied in
session 3** — a headline number whose producer is absent. It is more serious here, because
**baseline_v1 is the pinned anchor of record** for the momentum book.

**A1 status: IRREPRODUCIBLE.** Not wrong — unverifiable. Recommend the same remedy that worked for
0115: commit the producer, name every parameter it needs, and have the binder cite the reproducible
figure.

## Minor divergence, recorded

A2 reports swing corrected **CAGR 25.21%** against the published **24.7%**, while **Sharpe (1.132)
and MaxDD (−42.4%) match exactly.** A 0.5 pp CAGR gap at identical Sharpe and drawdown points at a
window-end or compounding-convention difference, not a return difference. **Flagged, not corrected.**

## Verdict

**The program survives a total loss of the working tree in under five minutes — for everything that
has a producer.** Three artifacts (G2, G3) and one headline (G4) do not, and G1 means the documented
install path is broken on a current interpreter. None of this moves a standing verdict; all of it is
recovery risk that was invisible before the drill.
