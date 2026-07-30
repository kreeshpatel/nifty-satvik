# §3 Forward-wall audit

**Pre-committed criteria (forward/prereg.md, verbatim):**
> "**All three books begin in PAPER (Phase A).** The base transitions to small real capital only in
> Phase B, and only via a dated §10 amendment once the repo's **pre-committed paper gate is met**
> (`skills/portfolio-simulation`: **≥ 30 closed trades AND ~2 months** of paper)."
> "Thresholds are the backtest's own rolling-12-month distribution"
> "Red is a *review* trigger, not an auto-halt"

**Machinery:** `scripts/audit_forward_wall.py` — fixture-tested 5/5 (tamper detection, halt breach,
gate counts, sleeve completeness, config drift). **The live wall logs were NOT read during the build**
(no-peeking held); September runs it against the live logs for the first time.

**EVIDENCE (September fills):**
- [ ] chain verification result (live)
- [ ] paper-gate counts per book
- [ ] halt events + sleeve completeness
- [ ] config-drift result vs prereg.md frozen keys
