# DATA BUG — the swing path never applies the CA cleaner (19 unadjusted splits)

**Found 2026-07-16 by the owner**, from the #1 "worst trade" on a TradingView review list: our CGCL entry
printed **763.65** where TradingView showed **~190**. Ratio 763.65/194.66 = **3.92 ≈ 4x**, and the trade's
`mae_pct` was **−75.01%** — exactly 1 − 1/4. It was never a loss; it was a **1:4 split**.

## Root cause

`scripts/run_bhanushali_path1.corrected_universe()` returns **raw** OHLCV:

```python
def corrected_universe():
    ohlcv = dict(load_ohlcv_cache(OHLCV_CACHE))   # RAW pickle load
    ...                                            # backfill + alias materialisation
    return ohlcv                                   # <- never cleaned
```

It never calls `clean_ohlcv_for_features` / `clean_ohlcv_dict`, so the repo's `_CORP_ACTION_MOVE = 0.50`
back-adjustment, bad-tick removal, zero-volume and holiday-phantom drops **never run on the swing path**.

**Architectural gap:** the cleaner is referenced ONLY from `nq/data/features.py`, `nq/data/ohlcv.py`,
`nq/engine/panel.py` — the **momentum / long-horizon** path. The **swing book (the LIVE model) has never
had CA cleaning.** The demerger reference (`data/corporate_actions_demergers.csv`) covers only **4
tickers**, and would not help anyway since the cleaner is not invoked.

**The live cron shares the defect:** `run_bhanushali_cron._refresh_ohlcv` uses
`load_ohlcv_cache` + `download_ohlcv`/`merge_ohlcv` with no cleaning step.

## Scope — 19 unadjusted splits

Scanning all 788 names for <−45% single-session moves: **24 events / 22 tickers** → 4 are genuine
demergers (correctly left), 1 is a reverting bad tick, **19 are almost certainly unadjusted splits**:

PATANJALI −94.9% · RNAVAL −94.0% · GPIL −79.5% · NIITLTD −76.1% · SHANKARA −75.5% · **CGCL −74.8%** ·
MOTILALOFS −74.6% · HSIL −73.7% · INFIBEAM −70.8% · THYROCARE −67.6% (x2) · ALLCARGO −64.9% · ABREL
−55.4% · STAR −54.0% · J&KBANK −53.8% · …

The backfill manifest **explicitly names** INFIBEAM splits and HSIL 2019 — the repo knew; the cleaner just
never ran here.

## Impact — small on the backtest, REAL on the live book

| | |
|---|---|
| substrate trades corrupted (open across a split) | **5 of 4,321 = 0.12%** |
| their share of total R | **−0.8%** (sumR −14.9 of 1,868.6) |
| **live touch setup** | **2 of 1,720**; meanR **+0.331 → +0.339** (delta +0.008) |

Corrupted trades: CGCL −17.325R · GPIL −3.807R · MOTILALOFS −1.320R · INDIAMART +3.393R · THYROCARE
+4.166R. **The headline (Sharpe 1.004 / 171 tr) is materially unaffected** — 19 splits over 10 years
across 788 names rarely coincide with an open position.

**But three real costs:**
1. **LIVE HAZARD (~2 split events/year).** When a split hits a held name the cron sees a −75% crash →
   prints a **fake SELL card**, and the stored stop is on the pre-split scale. The broker adjusts real
   shares so actual P&L is fine — **the signal shown is wrong.**
2. **Suppressed signals.** Post-split the 44w SMA / slope / RS stay corrupted for ~44 weeks, muting
   genuine signals on that name (unquantified opportunity cost).
3. **Polluted forensics.** The #1 "worst trade" handed to the owner for chart review (CGCL −17.32R) was
   pure artifact. Any loser-forensic that ranks by R will surface these first.

## The fix, and why it is owner-gated

Apply `clean_ohlcv_dict` inside `corrected_universe()` **and** in the cron's `_refresh_ohlcv`, and extend
`corporate_actions_demergers.csv` so genuine demergers are still left alone (HSIL 2019 is described as a
demerger in the backfill manifest but is absent from the reference — classify before cleaning, or a real
demerger gets fabricated into a soaring trend: the VEDL bug).

**Cost:** it changes the data ⇒ **re-anchors the determinism guard (1.1319 / 255)** and every pinned assert
(`build_substrate.py`, `build_trade_packets.py`, …). Small in magnitude (+0.008R) but it is a
**pin-re-anchor = quarterly-review/governance class** per CLAUDE.md. **Not a session action.**

## Immediate no-regret action taken

Regenerate the TradingView review lists **excluding** trades that span an unadjusted split, so the owner's
chart analysis is not spent on stock splits.
