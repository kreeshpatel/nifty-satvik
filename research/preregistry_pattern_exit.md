# PRE-REG — 40%@2R / 40% blow-off PATTERN tranche / 20% runner-to-44wSMA

*Frozen 2026-07-16 BEFORE the run (R4/R11). n_trials 128->129.*

Owner: *"40 percent at 2R and 40 percent at pattern and 20 at runner and sell below 44SMA"*.
`scaled_exit(tp1_r=2.0, tp1_frac=0.40, tp2_frac=0.0, pattern_frac=0.40, pattern_arm_r=2.5,
runner_sma_buffer=0.0)`. The 40% pattern tranche books on the BLOW-OFF exhaustion bar (new high closing
in its lower third once MFE>=2.5R) — the one pattern with validated exit value; the zoo ENTRY detectors
(VCP/flag/etc) are IC~0 here (0079), so they are NOT used. 20% runs to a weekly close below the 44w SMA.

New engine: a partial "part" pending books a mid-position fraction at next Monday open, keeping the
runner open. Golden byte-identical verified (1.1319/255). K=1 arm on the LIVE book (A-only + discipline).

Gate: 2022-26 slice vs LIVE 1.04; promote dSharpe>=+0.10 & DD not worse. Report full/17-21/22-26 Sharpe,
CAGR, DD, trades, win, maxR, R>=3, exit mix. Skeptical prior: 60% runner is >LIVE's 50%, but blended max
~7R << LIVE 16.7R, and the 20% at-SMA runner bleeds (70/30 lesson) though less. Likely between B (1.03)
and LIVE (1.04), no promote. KILL/UNDERPOWERED first-class; nothing ships in-sample.
