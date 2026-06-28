# `results/paper_portfolio.json` schema

The paper portfolio file is the live state file consumed by:
- `src/runners/cron_runner.py` (sizing + risk-manager gates)
- `dashboard/backend/` API endpoints (portfolio display)
- Tier 5 Phase 1's `_read_paper_portfolio_total()` helper

This document is the **authoritative schema reference**. When changes
land, update this file in the same commit so future readers know what
shape to expect.

## Schema (as of 2026-04-30)

```json
{
  "cash": 1000000.0,
  "positions": {
    "INFY": {
      "entry_date": "2026-04-22",
      "entry_price": 1850.0,
      "shares": 540,
      "current_value": 1014300.0,
      "position_value": 999000.0,
      "stop": 1750.0,
      "target": 1950.0,
      "current_price": 1879.0,
      "pnl_pct": 1.57
    },
    "RELIANCE": { ... }
  },
  "total_trades": 42,
  "total_pnl": 73210.50,
  "peak_value": 1185432.10,
  "created_date": "2026-04-22",
  "last_updated": "2026-04-30T16:45:00",
  "strategy_version": "v1.4-088-cal2025q1",
  "note": "..."
}
```

## Field semantics

| Field | Type | Purpose |
|---|---|---|
| `cash` | float | Available cash, decremented on entry, incremented on exit |
| `positions` | **dict keyed by ticker** | Open positions; each value is a position dict (see below) |
| `total_trades` | int | Counter of all trades ever (open + closed) |
| `total_pnl` | float | Cumulative realized P&L since `created_date` |
| `peak_value` | float | High-water mark of total equity, used for drawdown computation |
| `created_date` | ISO date | When the paper portfolio was initialized |
| `last_updated` | ISO timestamp | When the cron last wrote to the file |
| `strategy_version` | str | Composite version stamp (model + gate + calibration) |
| `note` | str | Free-text notes for the maintainer |

## Position dict semantics

Each value in the `positions` dict has the shape:

| Field | Type | Notes |
|---|---|---|
| `entry_date` | ISO date | When the position was opened |
| `entry_price` | float | Fill price |
| `shares` | int | Number of shares held |
| `current_value` | float | `shares * current_price` (preferred for portfolio-value calc) |
| `position_value` | float | Often `shares * entry_price` (legacy field; prefer `current_value`) |
| `stop` | float | Stop-loss price |
| `target` | float | Take-profit price |
| `current_price` | float | Latest mark from yfinance |
| `pnl_pct` | float | Mark-to-market P&L percentage |

## Legacy fields (still tolerated)

The cron's read path falls back to a legacy schema where `positions`
was a list and the field name was `open_positions`:

```json
{
  "cash": 1000000,
  "open_positions": [          # OLD: list, NOT dict
    {"ticker": "INFY", ...},
  ],
  ...
}
```

`src/runners/cron_runner.py:apply_risk_manager()` reads BOTH the new
`positions` dict and the legacy `open_positions` list to support
in-flight schema migration. Once all consumers are confirmed on the
new schema, the legacy path can be removed.

## Reader contract

Consumers reading this file should:
1. Treat missing files as "empty portfolio" (cash=INITIAL_CAPITAL,
   no positions).
2. Treat missing keys as zero/empty (defensively).
3. Prefer `positions[ticker].current_value` for total-equity math;
   fall back to `position_value` if `current_value` is missing.
4. Total equity = `cash + sum(p.current_value for p in positions.values())`.

## Tier 5 Phase 1 + 1.5 changes

- **Phase 1**: cron's sizing block reads `total_equity` from this
  file (was `INITIAL_CAPITAL`, a constant).
- **Phase 1.5**: cron passes `enforce_max_positions=False` to
  RiskManager. The cap is no longer applied to the live signal-
  recommendation path. The `positions` dict is still read for
  sector-exposure and correlation gates.
