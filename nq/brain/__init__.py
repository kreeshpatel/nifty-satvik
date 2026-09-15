"""Satvik Brain — the research and analysis layer that learns from the web, from books, and from the
book's own trades (plan: `docs/brain/` once written; approved 2026-09-15).

The rule every module here obeys: **the Brain works the cheap side of research — read, extract,
confront, measure, log forward — and never decides what is traded.** Nothing in this package is
imported by the engine, the paper book, or any production cron that places a signal, so the golden
master (`tests/test_stage2_golden.py`) cannot move because of it.

Why the rule exists, in one breath: the live book closes about one trade a week, so an outcome-driven
learner fits noise; every rule the system could adopt on its own is an uncounted trial; and a language
model's training data contains market outcomes, so any historical "learning" it does is partly recall.
Three independent research sweeps (this repo, practitioners on the web, peer-reviewed studies) agree.

Two standing constraints on every reader:

* The 0125 informed-judge log is SEALED until its first review read. Read repository artifacts through
  :func:`nq.brain.io.read_json`, which refuses it.
* A number the Brain reports carries its sample size and is reproducible from committed inputs — the
  attribution tests reproduce the figures quoted to the owner from an immutable archive snapshot.
"""
