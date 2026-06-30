# Data & Artifacts — where everything lives (the filing map)

> The single source of truth for: where data comes from, what runs where (local / CI / cloud),
> which files are committed vs regenerated, and where future-improvement work + records go. Read
> this before adding a new data source, output, or experiment so things land in the right place.

---

## 1. Data sources & flows

| Stream | Source | Cadence | Runs where | Output |
|---|---|---|---|---|
| **Live signals** | yfinance, **incremental** (download recent N days → merge) | daily post-close | GitHub Actions cron — **NOT BUILT YET** (only the scan core `nq/runner/scan.py` exists; the incremental downloader + `cron-scanner.yml` are a Stage-3/live port) | `results/ohlcv_cache_lh.json` → `results/signals_today.json` |
| **Canonical backtest** | yfinance, full/corrected universe (or the pinned snapshot) | manual dispatch | GitHub Actions `cpcv-research.yml` (cloud) | `data/ohlcv.pkl` (cache, gitignored) → `results/cpcv_long.json` (uploaded artifact) |
| **Fundamentals (PIT D/E)** | Screener.in scrape — **one-time, cached, NOT a cron** | on demand | local or cloud (`scripts/scrape_screener.py`) | merged into `data/fundamentals_pit_screener.pkl` (committed) |
| **Index membership** | Wayback NSE snapshots (`reconstruct_membership` — old-repo script, not yet ported) | when NSE reconstitutes (~biannual) | manual | `data/nifty500_membership.csv` (committed) |

**Kite is deliberately OFF the price/backtest path** (`skills/kite-execution` §0): yfinance only, for
reproducibility. Kite is reserved for live order placement / cross-check, gated on credentials.

## 2. Local vs CI vs cloud — what data each uses

- **Local** — the carried fixtures (committed) for hermetic dev/tests; a degenerate ~20-name OHLCV
  cache is for smoke ONLY (inadmissible — never quote its numbers).
- **CI** (`.github/workflows/ci.yml`) — runs the hermetic test suite on **committed fixtures only,
  zero download** (golden fixture, fundamentals pkl, membership). Lean + segfault-proof.
- **Cloud** (`.github/workflows/cpcv-research.yml`) — the ONLY admissible-headline runs: downloads
  the universe from yfinance, produces `cpcv_long.json` as an artifact.

**Reproducibility caveat (load-bearing):** yfinance history **drifts run-to-run** (observed CAGR
14.2 → 15.6 → 16.25 on identical commands). A headline number is only reproducible against a
**pinned OHLCV snapshot** (see §4 baseline_v1 pin_status). This is *why* baseline_v0's 26.1% can't
be byte-reproduced — its vintage is gone; the faithful pipeline on current data gives ~15.5%
(`research/baseline_v1.json`).

## 3. Folder filing map (committed vs gitignored)

| Path | Contents | Committed? | Written by |
|---|---|---|---|
| `nq/` | the code package (data / engine / strategy / validation / runner) | ✅ | us |
| `config.py` | universe, costs, thresholds, holidays, sectors, `load_frozen_cfg` | ✅ | us (carried) |
| `models/long_horizon/config.json` | the frozen cfg (source of truth) | ✅ | carried |
| `data/` (corrections) | membership, fundamentals_pit_screener.pkl, corporate_actions_demergers.csv, nse_circulars/, sector_intelligence.pkl, macro_data.pkl, problem_sector_map.json, nifty500_official_*.csv | ✅ via `!` exceptions | carried + scrape |
| `data/ohlcv.pkl`, `data/features.pkl`, `data/_screener_cache/`, `data/*.log` | regenerable caches / scrape scratch (64 MB OHLCV — too big for git) | ❌ gitignored | runs |
| `results/` | run outputs: signals_today.json, cpcv_long.json (artifact), portfolio_history.csv, paper_*, kill_*, cron_health.json | live-cron files whitelisted; **0 tracked today** | runs / cron |
| `research/` | empirical anchors: `baseline_v0.json`, `baseline_v1.json`, `overlay_registry.md`, `findings/` | ✅ | us, per result |
| `diagnostics/research/` | governance: `n_trials.json` (=79), `HOLDOUT.md`, `preregistry/` | ✅ | us, per experiment |
| `docs/` | plans + decisions (ROADMAP, STAGE_A_PLAN, this file, protocols) | ✅ | us |
| `tests/` (+ `fixtures/`) | tests + the golden fixture `lh_golden_panel.csv` | ✅ | us |
| `skills/` | the binding methodology | ✅ | carried |
| `.claude/.../memory/` | cross-session facts (`MEMORY.md` index + files) | (outside repo) | the assistant |

## 4. The future-improvement workspace (the "revisit forever" OS)

Every model improvement after Stage A goes through this — **pre-register → run on cloud → record
verdict**, so we never re-run a dead lever and significance math stays honest:

- **`nq/research/`** — overlay/conviction research code (factor screens, the factor lab) —
  *the deferred Stage-C folder.*
- **`diagnostics/research/preregistry/`** — **one file per experiment, written BEFORE the run**
  (hypothesis, single primary metric, decision rule, which holdout, bump `n_trials.json`).
- **`research/overlay_registry.md`** + **`research/findings/`** — the verdict ledger
  (PROMOTE-CANDIDATE / UNDERPOWERED / KILL) + the §11 KILL log.
- Harness: `nq/runner/research.evaluate_overlay` (paired ΔSharpe CI + DSR). Governing skills:
  `research-log`, `overlay-testing`, `backtest-rigor`, `leakage-audit`, `data-quality`.

**Revisit recipe:** memory → `docs/ROADMAP.md` → `research/overlay_registry.md` + `findings/` →
pre-register a trial → cloud run → record verdict + bump `n_trials`.

## 4a. Dataset pin — how baseline_v1 becomes byte-reproducible

yfinance drifts run-to-run, so a headline is only reproducible against a **fixed OHLCV snapshot**.
The snapshot is identified by the **sha256 of its exact pickle bytes** — a pinned run loads that
blob (a GitHub release asset, since 64 MB > git limit) instead of hitting yfinance, so the input
is byte-identical and (with the pinned deps) the baseline is byte-reproducible.

Plumbing (wired, code-complete): `nq.data.ohlcv.file_sha256` + `run_cpcv --pinned-release <tag>`
(fetches the asset via `gh`) + `--expect-sha256 <hex>` (aborts on mismatch; defaults to the pin
recorded in `research/baseline_v1.json`). Every run records `pin.ohlcv_sha256` in `cpcv_long.json`.

**Mint-the-pin recipe (one cloud action, then it's permanent):**
1. Trigger `cpcv-research.yml` with `mode=corrected`, `pin_tag` **blank** (fresh yfinance) — this
   produces the canonical `data/ohlcv.pkl` and uploads it as the `cpcv-research-corrected` artifact.
   Note `pin.ohlcv_sha256` printed in the run / `cpcv_long.json`.
2. Download that artifact, create a release (e.g. `gh release create dataset-pin-YYYYMMDD ohlcv.pkl`),
   so the snapshot lives as a release asset.
3. Write `ohlcv_sha256` + `release_tag` into `research/baseline_v1.json` `pin` block; flip status.
4. Verify: re-trigger with `pin_tag=dataset-pin-YYYYMMDD` → it fetches the asset, the sha256 gate
   passes, and the baseline reproduces byte-for-byte. From then on every quote is pinned.

## 5. Known gaps / TODO (so they're not lost)
- **Dataset pin (A2 half-2):** plumbing is wired (§4a); the remaining step is the **mint cloud
  action** — produce the snapshot, promote it to a release asset, and fill `pin.ohlcv_sha256` in
  `baseline_v1.json`. Until minted, headline numbers drift ~1-2pp.
- **Live cron not built:** the incremental yfinance downloader + `cron-scanner.yml` (live signals).
- **`.gitignore` is being de-crufted** from the old monorepo (dashboard/v1/AI whitelist entries
  removed); keep it to only what the LH rebuild emits.
- **after-tax (STCG 20%)** not yet computed by the cloud run.
- **membership refresh** (`reconstruct_membership`) not yet ported.
