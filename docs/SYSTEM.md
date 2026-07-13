# nifty-satvik — Live System of Record

*The single authoritative map of the live weekly-swing product pipeline: every cron, every file,
every hop from market data to a user's dashboard — plus a tracked fault register and the operating
invariants that keep it honest. If it runs on a schedule or renders on the dashboard, it is described
here. Built 2026-07-13 from a full `/debug` + `/leakage-audit` sweep (three parallel audits).*

Rule: **do not add a cron, results file, or dashboard read without adding it here.** Scattered,
undocumented moving parts are how the silent-push-drop bug hid for a week.

---

## 1. The pipeline (end to end)

```
market data (yfinance .NS, ^NSEI)                Kite Connect (owner dev app + per-user)
        │                                                     │
        ▼                                          ┌──────────┴───────────┐
  GitHub Actions crons  ── write ──► results/*.json│  owner token          per-user token
        │                                          │  (quotes/LTP/hist)    (holdings/orders)
        ▼                                          └──────────┬───────────┘
  results/*_weekly.* committed to main ── read ──► FastAPI backend (Fly.io) ◄── per-user join
        │                                                     │
        ▼ (Vercel auto-deploy)                                ▼
  React dashboard  ◄────────── /api/signals?model=weekly ─────┘
```

**Decision cadence is weekly; the book only changes after Friday's close.** Everything else (the
daily monitor, the intraday shadow, the per-user join) is presentation/observation on top of the
frozen weekly signal.

---

## 2. Cron registry

| Workflow | Schedule (IST) | Status | Script | Writes | Push |
|---|---|---|---|---|---|
| `cron-bhanushali-scanner` | Sat 18:00 | **ACTIVE** | `run_bhanushali_cron.py` + `bhanushali_review_scorecard.py` | `signals_today_weekly.json`, `signals_history_weekly.json`, `signal_analytics_weekly.json`, `paper_portfolio_weekly.json`, `portfolio_history_weekly.csv`, `weekly_review_scorecard.json` | **SAFE** (retry+exit1) |
| `cron-bhanushali-monitor` | Mon–Fri 16:15 | **ACTIVE** | `run_bhanushali_monitor.py` | `weekly_monitor.json` | **SAFE** (fixed 2026-07-13) |
| `cron-intraday-scan` | Mon–Fri 14:30 | **ACTIVE** | `run_intraday_scan.py` | `results/intraday_scan/*.json` | **SAFE** (fixed 2026-07-13) |
| `cron-kite-refresh` | Mon–Fri 06:15 | **ACTIVE** (inert w/o secrets) | `dashboard/backend/refresh_kite_session.py` | — (owner Kite token → DB) | N/A (no commit) |
| `cron-scanner` (momentum) | — | **SUSPENDED** 2026-07-06 | `run_paper_cron.py` | `paper_*.json`, `signals_today.json`, … | FRAGILE (dormant) |

**The push contract (mandatory for any committing cron).** The OHLCV download leaves unstaged cache
changes, so a plain `git pull --rebase` aborts and `... || echo "nothing to push"` returns exit 0 —
a green run that published nothing. Every committing cron MUST use:
```bash
if git commit -m "…"; then
  for i in 1 2 3; do
    git pull --rebase --autostash origin main && git push origin main && exit 0
    sleep 5
  done
  echo "::error::committed but could not push"; exit 1     # RED run, not a silent drop
else echo "no change"; fi
```

---

## 3. Results-file registry (source → dashboard)

| File | Written by | Read by | Freshness rule |
|---|---|---|---|
| `signals_today_weekly.json` | scanner (Sat) | `get_signals(weekly)` | `generated_at` age >48h ⇒ `cron_health=STALE` |
| `signals_history_weekly.json` | scanner (Sat) | history view; **should feed held-position exit guidance** (see F5) | — |
| `signal_analytics_weekly.json` | scanner (Sat) | scorecard, history | — |
| `paper_portfolio_weekly.json` | scanner (Sat) | scorecard, portfolio badge | inception-gated (empty until first post-inception trade) |
| `weekly_review_scorecard.json` | scanner scorecard step (Sat) | `ReviewCard` (admin) | refreshes only when the scanner push succeeds |
| `weekly_monitor.json` | monitor (weekday) | `_overlay_weekly_monitor` → live price + event chips | daily; absent ⇒ overlay is a silent no-op |
| `results/intraday_scan/*.json` | intraday (weekday) | shadow stats (research) | daily |

Backend read path: `_read_json_with_fallback` — **GitHub-API-first** for `results/*` (the cron pushes
there; Fly's local disk is a stale deploy snapshot), local fallback on GH outage
(`signals.py:135-174`).

---

## 4. Backend → dashboard (per-user vs shared)

- **Shared** (same for everyone): the weekly signal cards, the CRS-rank, the scorecard, and all
  **market data** (quote/LTP/historical) — served with the **owner's single Kite dev-app token**
  (`kite.py`: `/quote` :655, `/quote/ltp` :675, `/historical` :751).
- **Per-user** (each viewer's own): **account data** — holdings/positions/orders — served with the
  **user's own token** (`kite.py`: `/holdings` :413, `/orders` :433); and the per-user augmentation
  `_augment_signals_for_user` (`signals.py`) which joins the shared signals against that user's
  `nq_orders` + Kite holdings to stamp `actionability` + `user_position`. The owner/per-user token
  split was audited **clean** — no mix-up.
- **Held vs buy** (frontend `SignalsV3.jsx` `deriveAction` :124): a card is a *held* position if the
  viewer holds it in Kite, or has `held_qty>0` in `nq_positions`, or it is an `ACTIVE` card with an
  `nq_position_id`. Otherwise it is a *buy candidate*.

---

## 5. Integrity verdict (leakage-audit)

**The live weekly signal path is leakage-clean and `live == backtest` by construction.** Verified:
- All features trailing-only (44-wk SMA, 13-wk slope, quality-green, 44-wk touch, CRS/`crs_dist`);
  grep swept every `run_bhanushali_*.py` — **zero** `.shift(-k)`, centered windows, or `[i+1:]`
  (`run_bhanushali_weekly_rank.py:66-78`).
- Entry uses only the **next** week's actual open against the **prior** week's band (`:176-177`);
  exits decided at the weekly close, filled at the next open (`:125-127,150-162`) — no same-bar peek.
- The live cron calls the **same** `prep_weekly_rank` + `backtest` as the 0094 run of record
  (`run_bhanushali_cron.py:313-315`); params are shared module constants — the live path cannot
  diverge.
- Survivorship is correct-by-design: backtest uses the corrected universe, the live book uses
  survivor-only live data because a forward book only trades currently-listed names (documented
  `run_bhanushali_cron.py:307-309`). PIT index-membership masking applied on cards and fills.

The **math is sound**; the faults below are all operational/plumbing, not signal correctness.

---

## 6. Fault register

Status: ✅ fixed · 🔧 open (fix specified) · 👁 watch. Severity P0 (silent data loss / money-risk) →
P2 (cosmetic/robustness).

| ID | Sev | Fault | Root cause | Status |
|----|-----|-------|-----------|--------|
| **F1** | P0 | Weekly scanner computed fresh state (07-11: 18 signals, 3 holds) but never published it | fragile `pull --rebase && push \|\| echo` swallowed the push (exit 0) | ✅ fixed `35e422d` |
| **F2** | P0 | `cron-bhanushali-monitor` never publishes — `weekly_monitor.json` has never been committed | same fragile push | ✅ fixed `2026-07-13` |
| **F3** | P0 | `cron-intraday-scan` never publishes — `results/intraday_scan/` never committed; survival stats never accrued | same fragile push | ✅ fixed `2026-07-13` |
| **F4** | P1 | Live dashboard shows the stale/expired 2026-07-03 board; forward record has a hole at its first data point | downstream of F1 (07-11 run dropped) | 🔧 re-run scanner to publish current week |
| **F5** | P1 | **Weekly held positions get no exit guidance** — a user whose weekly trade hits its stop is never told to sell | `nq_positions.py:56` hardcodes the momentum `signals_history.json`; the weekly book writes `signals_history_weekly.json` | 🔧 make history-index model-aware (union both files) |
| **F6** | P1 | **A bought weekly card vanishes from the holder's board next Saturday** | join-key drift: orders keyed by setup-Friday `signal_date`; held/history cards keyed by fill `entry_date` (`run_bhanushali_cron.py:125` vs `:154`; `signals.py:285`) | 🔧 align the join key (see §7) |
| **F7** | P1 | Live `last_signal` has no weekly-completeness guard | `run_bhanushali_weekly_rank.py:89-93` reads `weeks[-1]` unconditionally; an off-cadence run surfaces a partial-bar card | 🔧 guard: suppress unless `weeks[-1]` ends on the latest completed Friday |
| **F8** | P2 | Stale weekly file not surfaced on the Research page | frontend never reads `cron_health` (`SignalsV3.jsx`) | 🔧 render a "data stale / scan failed" banner |
| **F9** | P2 | Day counter mixes calendar days with a 65-**trading**-day horizon (reads near-exit ~4 weeks early) | `dayOf` calendar days (`SignalsV3.jsx:170`) vs `hold=65` trading days | 🔧 show "week N of 13" |
| **F10** | P2 | `status_for_user` classified on raw qty while returned `held_qty` is FIFO-capped | `nq_positions.py:297-309` | 👁 stacked same-ticker positions only |
| **F11** | P2 | Weekly cards carry no `actionability`; rely on the `buy_window_until` fallback | cron doesn't stamp it | 👁 works today; brittle if a run omits `buy_window_until` |
| **F12** | P2 | Naming drift: workflows/scripts are `bhanushali_*` but every output + model id is `*_weekly`; orphan `.pyc`; 12+ research variants beside the one live script | the weekly→bhanushali rename (#30) was partial | 👁 pick one convention, delete orphans |

---

## 7. Fix plan for the open money-risk faults (F5 + F6, entangled)

F5 and F6 both break **held-position tracking for real users** and must be fixed together — fixing the
history file alone won't help because the held/history record and the user's order are keyed
differently. The coherent fix:
1. **One canonical `signal_id` across the lifecycle.** Choose the **setup-Friday `signal_date`** as
   the stable key (it's what the FRESH card and the user's order already record) and carry it
   unchanged onto the held/ACTIVE card and the history record (add a `signal_date` = setup-Friday
   field there, distinct from `entry_date`). Then `run_bhanushali_cron.py:125/154`, the order in
   `useOrderPlacement.js:44`, and the augmentation key in `signals.py:285` all agree.
2. **Model-aware history index.** `_get_history_index` reads **both** `signals_history.json` and
   `signals_history_weekly.json` (union by id) so weekly exits resolve.
3. Verify with a scripted scenario (user buys a weekly signal Mon → held card + sell-guidance both
   resolve the following Sat) before deploy. Requires a **fly deploy** (backend change).

---

## 8. Operating invariants

- **Every committing cron uses the §2 push contract.** No bare `|| echo "nothing to push"`.
- **Register it here** before adding a cron / results file / dashboard read.
- **`results/*` is read GitHub-first** by the backend; committing to `main` is how live data updates
  (no fly deploy needed for data). Backend *code* changes need a fly deploy; frontend auto-deploys via
  Vercel.
- **Weekly decision cadence is frozen** — the daily monitor/intraday jobs observe and re-price; they
  never change the signal, the paper book, or the wall.
- **The forward wall + the Oct-1 review are the only certifiers** (`forward/prereg.md`); the
  scorecard tile surfaces readiness but decides nothing between quarterly dates.
- **Health check:** `cron_health` goes STALE at >48h; a green cron run must now mean a real publish
  (F1–F3 fixed) — a push failure is a RED run.
