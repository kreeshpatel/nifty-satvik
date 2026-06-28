---
name: repo-maintenance
description: >
  Read before ANY git operation in this repo and whenever cleaning up branches or
  worktrees. Trigger words: "commit", "push", "branch", "worktree", "merge", "delete
  branch", "clean up", "git hygiene", "stale branches", "which branch am I on", "PR",
  "CI", "deploy", "rebase", "reset". Encodes nifty-satvik's repo geography + the
  hard-won branch/worktree hygiene rules paid for in the old monorepo.
---

# Repo & Worktree Maintenance — nifty-satvik

The git + worktree discipline for this repo. These rules were paid for in the old
`niftyquant` monorepo: accumulated worktrees (9+ at one snapshot, several with dozens
of unpushed commits), the checked-out branch flapping mid-session, and near-misses
deleting branches that still held work. Follow them so this repo stays clean.

## 0. Repo geography — confirm before any git write
- **`C:/nifty-satvik`** = THE repo (GitHub `kreeshpatel/nifty-satvik`). Work here.
- **`C:/project`** (old `niftyquant` monorepo) + **`C:/niftyquant-lh`** (superseded
  transplant) = **ARCHIVE.** Never commit/push to them.
- Confirm the remote before pushing: `git remote get-url origin` must be `nifty-satvik`.

## 1. Verify the branch before EVERY git write
Background crons/agents (and the harness) can switch the checked-out branch
mid-session — the monorepo's "main worktree flaps branches" lesson. Before any
`commit` / `push` / `add`:
```
git branch --show-current      # is it the branch you expect?
git status --short             # is the working tree what you expect?
```
**Never** `git reset --hard`, `git checkout .`, or `git clean -fd` unless you are
certain of the branch AND have inspected what you're about to discard.

## 2. Push immediately
Work isn't safe until it's on origin. After a meaningful commit:
`git push origin <branch>`. Don't accumulate unpushed commits (that's how the old
repo ended up with worktrees holding dozens of orphaned commits).

## 3. Commit style
- **Conventional Commits:** `feat: / fix: / refactor: / docs: / chore: / test: / build:`
- **Small, focused commits** — one logical change each.
- **NO `Co-Authored-By` trailers** — the git log is investor-facing.
- Quant/engine changes: state the expected backtest impact and record before/after
  paired-fold metrics in the message.

## 4. Branch hygiene — minimize, don't proliferate
- Don't create a branch you don't need. If the change fits the current branch, do it there.
- One branch per logical change: `feat/<name>`, `fix/<name>`, `refactor/<name>`, …
- `main` is the trunk; CI runs on every push/PR.

## 5. NEVER auto-delete a branch / worktree / remote ref
After a merge, do **not** auto-clean the source branch, its worktree, or its remote
ref. **Always ask the owner first** — even for a "fully merged" branch. A branch
existing is nearly free; deleting one by mistake costs hours (it may hold uncommitted
files in its worktree, unmerged sibling commits, or be the owner's parking lot for
half-finished thoughts). This applies to `git branch -d/-D`, `git push --delete`, and
`git worktree remove`.

## 6. Worktrees (only when parallel work genuinely needs them)
- Add off `main` with a fresh branch: `git worktree add <abs-path> -b <branch> main`.
- Keep the count LOW; a stale worktree with uncommitted files is the failure mode.
- Audit: `git worktree list`. Prune only with owner sign-off (§5).
- Worktrees share the object store but each has its own checked-out branch — never
  assume the CWD's branch is what you think (§1). Use absolute paths; the shell cwd
  resets between calls on this machine.

## 7. CI hygiene
- CI is lean by design (`.github/workflows/ci.yml`): ruff + `mypy --strict` + `pytest -v`,
  `OMP_NUM_THREADS=1`, **NO `--cov`** (coverage instrumentation + native libs segfault
  the Ubuntu runner — a toolchain crash, not a code bug).
- **Don't spam CI runs** — GitHub Actions minutes are a shared budget. Verify locally
  first; dispatch deliberately; watch one run rather than fire-and-retry.
- Don't add `shap` / `statsmodels` / heavy `lightgbm` — they crash the runner at import.

## 8. Before a merge to `main`
- CI green (ruff + mypy + pytest).
- **Golden master green** if the engine changed — regenerate the fixture in the SAME
  PR if the change is intentional, never leave it red.
- Update the relevant manifest/doc in the same change (manifest discipline).
- End a meaningful PR with a summary: purpose, files changed, behavior change,
  validation run, risks + rollback.

## Cross-references
- Build plan + repo layout: `BUILD_SPEC.md`
- Research discipline: `skills/backtest-rigor`, `skills/overlay-testing`
- Re-register skills after editing: `python scripts/register_skills.py`
