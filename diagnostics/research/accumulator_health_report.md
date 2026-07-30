# Accumulator Health Report — 2026-07-30

**VERDICT: ATTENTION**


## bulkblock
- exists: True
- rows: 148
- data_span: ['2026-07-28', '2026-07-28']
- sessions_expected: 1
- sessions_with_rows: 1
- gap days (0): []

## ratings
- exists: True
- rows: 87
- data_span: ['2026-07-21', '2026-07-25']
- sessions_expected: 4
- sessions_with_rows: 4
- gap days (0): []
- symbol_clean ratio by fetch day: {'2026-07-28': 0.0}

## health file
- staleness flags: {'bulkblock': False, 'ratings': False}

## idempotency probe
- probed on scratch copies; live files untouched: True
- re-fetch adds: {'bulkblock': 137, 'ratings': 5} (tolerance 5) -> FAIL

## wiring
- cron_step: OK
- cron_git_add: OK
- gitignore_whitelist: OK
