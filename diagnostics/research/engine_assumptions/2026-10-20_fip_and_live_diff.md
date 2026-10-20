# Engine assumptions, 2026-10-20 — FIP as a seat key (exploratory) and the live-vs-replay decision diff (measurement)

Source: `research/scout/2026-10-20.md` top-3 items 1 and 2. Process tier: **0 (item 1, EXPLORE)** and **1 (item 2, MEASURE)**
per `docs/PROCESS_TIERS.md`. No pre-registration, no screen row, no `n_trials` change. Standing counts, read from the
ledgers on this branch: **screens 23** (`diagnostics/research/label_screen_ledger.md`, last row 0150), **n_trials 2**
(`diagnostics/research/n_trials.json`), sealed opens 3 (held by `tests/test_standing_counts.py`, which passed).
Scripts: `pipelines/diagnostics/diag_fip_seat_key.py`, `pipelines/diagnostics/diag_live_decision_diff.py`.
Outputs: `fip_seat_key.json`, `live_decision_diff.json` (this directory).

## Item 1 — information discreteness (FIP) as a within-week seat key. EXPLORATORY.

**Method.** The 0150 Part-1 substrate, re-run unchanged: uncapped, all grades, live configuration with PIT membership
(`load_membership()`), every price series cut at 2024-06-30 before the engine sees it (asserted; last bar 2024-06-28).
The substrate reproduces 0150 exactly: n = 1,367 filled trades, 238 ISO weeks, CRS rank IC −0.004. For each trade, over the 63
sessions strictly before the entry session (PIT): `ID = sign(formation return) × (%negative days − %positive days)`; the
seat score is `−ID` (smoother = better, per Da–Gurun–Warachka). Week-clustered bootstrap, 5,000 draws, seed 20261020.
"Top 5 vs rest" is computed over the weeks that have both groups (80 weeks), pooled, as in 0150.

| score | set | within-week rank IC (95% CI) | mean R top-5 minus rest (95% CI) | top-5 / rest mean R |
|---|---|---|---|---|
| **−ID (FIP)** | all | +0.004 [−0.070, +0.078] | **−0.481** [−1.398, +0.203] | +1.135 / +1.616 |
| | 2019-21 | −0.020 [−0.130, +0.090] | −1.179 [−3.896, +0.293] | +0.797 / +1.976 |
| | 2022-24H1 | +0.024 [−0.073, +0.122] | −0.036 [−0.670, +0.571] | +1.412 / +1.448 |
| CRS (live key, same set) | all | −0.005 [−0.082, +0.075] | +0.078 [−0.958, +0.892] | +1.452 / +1.375 |
| | 2019-21 | +0.050 [−0.065, +0.165] | −1.412 [−3.933, +0.276] | +0.685 / +2.097 |
| | 2022-24H1 | −0.052 [−0.159, +0.055] | **+1.043** [+0.183, +2.021] | +2.080 / +1.037 |
| −ext (closer to the 44w line) | all | −0.045 [−0.126, +0.033] | +0.427 [−0.421, +1.471] | +1.650 / +1.224 |

**Reading.** FIP is not distinguishable from noise as a seat key: IC +0.004, CI straddles zero by ±0.07, and the
top-5-smoothest group earned *less* than the rest (point estimate −0.48R, CI includes zero). Both sub-periods give an
IC within ±0.025 of zero. It does no better than CRS (IC −0.005), whose own "edge" flips sign between sub-periods (−1.41 then
+1.04) — a reminder that the top-5-vs-rest gap on ~40 weeks per sub-period is a very wide instrument (CI half-widths of 0.6–2.7R).
Nothing here clears a bar for an activation bound; and because the reading is null, Law II (a ranker is not a rescue) and Law I
wall #3 do not need to be invoked to refuse it. For completeness: Law I wall #3 (path-shape `path_eff` flipped sign on the
sealed set) is why even a train-only positive here would have counted as weak; the result is not positive.

**Is FIP just extension?** No — it is orthogonal. Spearman(ID, ext over the 44w SMA): pooled −0.014, mean within-week −0.028
(−0.019/−0.063 in 2019-21, −0.012/+0.003 in 2022-24H1). Spearman(ID, CRS): −0.007. So FIP is a genuinely separate
feature source from the thing program-laws says is the engine (ext itself orders R only weakly here: Spearman(ext, R) −0.014).
Within near-line trades (ext < 5%, n = 321) the FIP IC is −0.079 (40 weeks); within ext ≥ 5% (n = 1,046) −0.018 — both
the wrong sign if anything, both inside noise.

**Caveats.** `ext` is my own PIT reconstruction (entry price over the mean of the last 44 weekly closes completed before the
entry week; weeks are Friday closes of the cut series), not the engine's internal `sma_sig`; the engine ledger does not carry it.
No 1-month skip in the formation window. Nine (score × set) looks are reported, so no p-values are quoted; none of
the intervals excludes zero except CRS in 2022-24H1 on the edge statistic, which is the *incumbent* key. Ties in `−ID` are broken
by `rank(method="first")`. This is a scratch count on the 0150 substrate, not a replay with FIP as the fill order: the lab has no
rank-override key, so portfolio effects (seat competition, cash) are not measured.

**Cheapest test that would change the answer.** If anyone still wants FIP: add `ID` as a logged column in the signal-quality
forward-wall collector (zero trials, nothing acted on) and read it at the wall. Not recommended ahead of the 0150 seat-waste fix.

## Item 2 — live-vs-replay decision diff. MEASUREMENT.

### What could not be checked, and why (stated first)

1. **A same-week engine replay for any published week is not possible offline.** The pinned price cache
   (`data/ohlcv.pkl`, `data/ohlcv_backfill.pkl`) ends **2026-06-29**; every Saturday archive is dated ≥ 2026-07-24 (first archive
   in `results/archive/`). There is no local price for any live week, so (a) "recompute levels from local data for dates the local
   data covers" covers **zero** published cards.
2. **The 44-week lookback of any live signal lies mostly inside the sealed 2024-07-01..2026-06-30 window**, which this work may
   not read. So I read **no price series at all** in item 2. `data/raw_close_reference.parquet` (raw probes) ends 2026-06-24 and
   was not opened. The adjusted-vs-raw comparison is therefore analytic, built from the exchange adjustment factors the 2026Q3
   foundation audit already measured (`layer2_passA.parquet`, `corpactions_raw.parquet`), `data/corporate_actions_post_harvest.csv`
   and `KNOWN_SEAMS` — metadata, not prices.
3. **The corporate-action census ends 2026-07-01** (post-harvest addendum adds HEG 2026-09-07 only). Splits, bonuses and
   dividends with ex-dates in the live window (up to 16 weeks of the latest snapshot's lookback) are invisible to it. I added a
   close-to-close break detector on the published record (|week-over-week close ratio − 1| > 25% for held names) to partly cover that.
4. The raw-vs-adjusted SMA/extension shifts are **flat-price estimates**, not measurements. Also: Kite's own charts normally
   back-adjust splits/bonuses for display; the "unadjusted" case describes a user computing levels from raw prices or from an
   indicator over a mixed series. Treat it as an upper bound on what a raw-price user would see.

### A. Published levels recomputed from published fields, and cross-snapshot consistency

19 snapshots (15 base + 4 reruns), 465 card rows, 90 distinct cards, 61 FRESH rows.

| check | result |
|---|---|
| target = entry + 2 × (entry − stop) (±5 paise) | **0 / 465 mismatches** |
| stop = max(signal-week low, entry − 10%) (FRESH cards) | **0 mismatches** |
| `ext_pct_over_sma44` = entry / SMA44 − 1 (SMA from the runner tranche) | **0 mismatches** (tol 0.06pp) |
| FRESH card above its ext cap without the "would skip" flag | **0** |
| rerun snapshots vs the snapshot they re-ran: levels/grade changed | **0** in all 4; 2026-08-14 rerun added 2 cards (CCL, NATIONALUM) absent from the original |
| held position's entry/stop/target restated between consecutive snapshots | **11 restatements across 10 positions**; all but one are −0.1% to −1.3% entry moves (modeled fill re-based, e.g. CUB 212.00 → 210.03, SIEMENS 3651 → 3633.15, SAIL −1.29%); **HEG −62.6%** (650.00 → 242.95, stop 585.00 → 218.66) on 2026-09-11 → 2026-09-15 |
| FRESH published entry vs the modeled fill the following Mon–Thu (32 matched) | mean slip +0.38%, range −3.07% to +4.19%; mean risk-per-share 5.82% (published) → 6.08% (fill); 1 fill above the card's `no_chase_above` (POWERINDIA, 31,172.5 → 32,480, +4.19%, risk 4.90% → 8.73% because the stop stays anchored to the signal-week low); 0 outside the buy band |
| stop distance across all cards | median 6.25%, range 1.52% – 10.91% |

Worst cases: **HEG** — the demerger (ex 2026-09-07) was applied retroactively to a held position's published entry and stop
(card 650.00/585.00/780.00 → 242.95/218.66/291.54). A user who took the modeled HEG fill (650.00, stop 585.00) and placed a stop order at 585 on
raw prices would have been stopped through by the demerger-day cliff (close 728.25 → 237.20 across 2026-09-04 → 2026-09-11); the
card now shows entry 242.95 / stop 218.66. The
close-break detector fires only for HEG (ratio 0.326). `corporate_action_reviews.csv` carries no HEG review row and its
post-harvest row is `LEFT_UNADJUSTED_AS_INTENDED`; the published-level restatement shows the record and the engine's adjusted
history do not agree with each other on how the position is carried. **POWERINDIA** — a modeled fill 4.19% above the published
entry and past `no_chase_above`, nearly doubling per-share risk, is within the engine's own rules but is a different trade from the card.

### B. Corporate-action exposure inside the 44-week lookback

Per distinct (ticker, signal) — FRESH cards: **16 of 36 (44%)** have ≥1 census event in their lookback; held positions: **27 of 53
(51%)**. By kind (distinct signals touched, a signal can have several): dividends 40, splits 6, bonus 1, demerger 1.
No FRESH card had an event inside its own signal week (0), so **entry, stop and target themselves are unaffected for a raw-price
user** (they derive from the signal-week bar and the entry price). One held position had an event after its fill (HEG demerger).
Non-dividend events touching any published or held name: ANGELONE split (ex 2026-02-26), MCX split (2026-01-02), NUVAMA split
(2025-12-26), CUB bonus (2026-06-12), HEG demerger (2026-09-07) — five names. **No `KNOWN_SEAMS` name (TRENT, CONCOR, ...) appears
on any published card or held position**, so the accepted seam exposure did not reach the book in this window.
Cap-flip test (does the ext-cap decision change if SMA44 is computed on raw closes): **0 flips** — the raw SMA sits above the
adjusted one, so raw extension reads lower, never higher; a raw-price user would not have been shown a fresh signal that the
engine capped out.

Where a raw-price user *would* see a different number is the SMA44 line and therefore the **runner exit ("weekly close below the
44-week SMA")** and the extension. Largest estimated distortions of SMA44(raw)/SMA44(adjusted), FRESH cards:

| ticker | snapshot | event(s) in lookback | SMA44 raw / adj | ext adj → raw est. |
|---|---|---|---|---|
| ANGELONE | 2026-09-11 | split ×10 ex 2026-02-26 | 4.11 | +7.7% → −73.8% |
| MCX | 2026-08-14 | split ×5 ex 2026-01-02 | 2.00 | +16.8% → −41.6% |
| NUVAMA | 2026-10-01 | split ×5 ex 2025-12-26 | 1.37 | +12.0% → −18.3% |

All other FRESH cards shift by ≤ 1.2pp (dividends only). Held-name SMA distortions follow the same events (CUB bonus 1:3 ex
2026-06-12, ratio 1.28, snapshot 2026-07-24).
Per-row exposure (events, factors, SMA ratios) is in `live_decision_diff.json` under `exposure_rows`.

**Practical reading.** For the money-bearing levels printed on the card — entry, stop, target — the adjusted history and the
unadjusted Kite price agree in every checked case, because they are recent-bar quantities. The gap is confined to long-lookback
quantities (SMA44 runner line, extension, CRS rank) on the few names with a split/bonus in the last 44 weeks (4 of the names
seen in this window), plus the
retroactive restatement that follows a corporate action *during* a hold (HEG). The card already prints the SMA level in rupees, which
is the right defence; a user who re-derives it from raw weekly closes would get a materially different line on ANGELONE/MCX/NUVAMA-type names.

**What would close the remaining gap.** (i) When the live price cache is reachable, replay each Saturday through
`nq.lab.runs.replay` and diff the full signal set/grade/levels (the parity test covers lab↔cron only). (ii) Extend the corporate-action
census past 2026-07-01 so live-window ex-dates are no longer invisible. (iii) Persist the published CRS rank on ACTIVE cards so held
positions can be diffed too. None of these is done here.
