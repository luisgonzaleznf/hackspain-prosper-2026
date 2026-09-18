---
name: solve-merge-conflicts
description: Resolve merge conflicts between parallel hackathon branches — load the branch, merge the base in, resolve every conflict by SYNTHESIZING both sides' intent, regenerate generated files, commit, push, then hand off to /verify. Use when parallel build slices clash, when the user says "solve merge conflicts on PR #N" / "fix conflicts on this branch", or pastes a PR/branch with the same intent.
argument-hint: "[pr-number-or-url-or-branch]"
---

# Solve Merge Conflicts

You are resolving merge conflicts caused by parallel build slices touching nearby code. The flow is: load the branch → merge the base (usually `main`) in → resolve each conflict with deep reasoning → regenerate any generated files → commit → push → hand off to `/verify`.

Conflict resolution is the only judgement-heavy step. Take it seriously: each conflict is two builders touching the same lines for different reasons, and "pick HEAD" / "pick origin/main" is almost never the right answer. The whole point of freezing shared rules up front was so slices wouldn't collide — when they do anyway, the resolution must honor *both* slices' intent, because both shipped real work.

## Step 0: Set up step tracking

Create a task list with one task per step using `TaskCreate`. Mark each completed as soon as it's done — don't batch.

1. Resolve target branch (Step 1)
2. Pre-flight check (Step 2)
3. Check out the branch (Step 3)
4. Merge the base branch (Step 4)
5. Resolve conflicts (Step 5)
6. Regenerate generated files (Step 6)
7. Lint touched files (Step 7)
8. Commit and push (Step 8)
9. Hand off to /verify (Step 9)
10. Summary (Step 10)

## Step 1: Resolve the target

Dispatch on the form of `$ARGUMENTS`:

- **Bare number** (matches `^\d+$`) → it's a PR: `gh pr view <n> --json number,headRefName,baseRefName,url,state,mergeable,mergeStateStatus`
- **Full GitHub URL** → `gh pr view "<url>" --json number,headRefName,baseRefName,url,state,mergeable,mergeStateStatus`
- **Branch name** (anything else non-empty) → `gh pr list --head "<branch>" --json number,headRefName,baseRefName,url,state,mergeable,mergeStateStatus --jq '.[0]'`; if no PR exists, treat the literal branch name as the head and `main` (or whatever `git symbolic-ref refs/remotes/origin/HEAD` resolves to) as the base — you can resolve conflicts on a branch that has no PR yet.
- **Empty** → resolve from the current branch: `gh pr view --json number,headRefName,baseRefName,url,state,mergeable,mergeStateStatus`. If the current branch has no PR, just use the current branch as head and `main` as base.

Capture: **head ref**, **base ref** (typically `main`), **PR number/URL** if one exists, **mergeStateStatus** if available.

If a PR is closed or merged, stop and tell the user — there's nothing to merge into.

## Step 2: Pre-flight check

```bash
git status --porcelain
git branch --show-current
```

- **Dirty working tree** touching files the merge will rewrite → stop and ask. Never stash silently.
- **Dirty working tree** with unrelated changes → warn, continue only if the user confirms.
- **On a different branch** → fine, Step 3 switches you.

## Step 3: Check out the branch

```bash
gh pr checkout <N>   # if a PR exists
# OR, no PR:
git fetch origin && git checkout <head-ref> && git pull
```

`gh pr checkout` may report "your branch is behind origin/<head> by N commits" — fast-forward with `git pull` so any commits a parallel worker pushed since you last fetched are included.

If a PR exists, sanity-check mergeability (GitHub's snapshot can be stale — always trust `git merge` over the API):

- `CLEAN` / `BLOCKED` (no conflicts) → no merge needed; skip to Step 9.
- `BEHIND` → base moved but no content conflicts; the merge in Step 4 succeeds cleanly.
- `DIRTY` → real content conflicts; expect Step 5 to do work.
- `UNKNOWN` → not computed yet; proceed and let `git merge` tell the truth.

## Step 4: Merge the base branch

```bash
git fetch origin <base-ref>
git merge origin/<base-ref> --no-edit
```

Three outcomes:

1. **"Already up to date."** Base is already merged in. Skip to Step 9.
2. **Merge succeeds, no conflicts.** A merge commit was created. Skip to Step 7 (lint anything touched), then Step 8.
3. **"Automatic merge failed; fix conflicts and then commit the result."** Continue to Step 5.

**Don't be fooled by an existing merge commit.** If the branch already has a `Merge branch 'main' into ...` commit but `git log HEAD..origin/<base>` is non-empty, the base has moved further since — you still need to merge again.

## Step 5: Resolve conflicts (think hard on each one)

### 5a. Triage the conflict set

```bash
git status
```

For every "both modified" file, classify the conflict before editing. Different types want different strategies:

| Type | Pattern | Strategy |
|---|---|---|
| **Import conflict** | `<<<<<<<` inside a contiguous `import` / `from x import y` block | Keep **both** imports. Reflow to match the file's existing import style and ordering. |
| **Constant / enum / config additions** | Both sides appended new entries to the same list / enum / dict / `.env.example` / config block | Keep **both**, preserve the file's existing ordering (alphabetical, grouped, or by-domain — match what's there). |
| **Route / endpoint additions** | Both slices registered a new FastAPI route, handler, or schema near each other | Keep **both**. Verify the path/operation IDs don't collide and that any shared router prefix stays consistent. |
| **Test additions** | Both sides added tests near each other | Keep **both**. Verify fixture/factory names don't collide and any shared `setUp`/`conftest` stays consistent. |
| **Logic edit on shared lines** | Both sides modified the same statement / branch / signature | Read 10+ lines of context on each side. Use `git log -p` (5b) to see each side's **intent**. Synthesize a result that preserves both — do **not** "pick a side." |
| **Generated / lockfile** | `package-lock.json`, `uv.lock`, `openapi.json`, build artifacts, snapshots | Resolve by **regenerating**, not hand-editing. See Step 6. |
| **Dependency manifest** | Both sides added deps to `pyproject.toml` / `package.json` | Keep **both** dependency lines (preserve ordering), then regenerate the lockfile in Step 6. |

### 5b. Resolve content conflicts (think hard on each one)

For each non-generated conflicted file:

1. Read the file at the conflict location with surrounding context.
2. Understand each side's intent — look at the actual diffs:
   ```bash
   git log -p HEAD..origin/<base-ref> -- <file>     # what the base did
   git log -p origin/<base-ref>..HEAD -- <file>     # what this branch/slice did
   ```
3. **Think hard:** what behavior does each side want? Is there an ordering? A precondition? A new abstraction or shared contract (a type, an API shape, a schema field) one side introduced that the other side's edit should now flow through? Synthesize, don't pick. If a conflict reveals the two slices diverged on a *frozen* shared contract, the synthesis must converge them back onto a single contract — that's the actual bug, not the textual conflict.
4. Edit the file. Remove all three markers (`<<<<<<<`, `=======`, `>>>>>>>`). Use the `Edit` tool, not in-place `sed`.
5. After editing every conflict in the file, verify no markers remain:
   ```bash
   grep -n '<<<<<<<\|=======\|>>>>>>>' <file>
   ```
   The `=======` regex also matches valid `===` separators in docstrings/markdown — eyeball the matches before declaring victory.

## Step 6: Regenerate generated files

Generated files cannot be hand-resolved correctly. After resolving the *source* conflicts they derive from, regenerate them:

- **Lockfiles** (`uv.lock`, `package-lock.json`, `yarn.lock`) — take the base's version, then re-resolve from the merged manifest:
  ```bash
  # Python (uv)
  git checkout --theirs uv.lock && uv lock && git add uv.lock
  # Node
  git checkout --theirs package-lock.json && npm install && git add package-lock.json
  ```
- **Generated API schema** (`openapi.json` / `openapi.yaml`) — regenerate from the merged routes/models rather than hand-merging, then `git add` it. Use whatever generator the project defines (e.g. a `scripts/` exporter or a FastAPI `app.openapi()` dump).
- **Snapshot / golden files** — after resolving the source that drives them, re-run the snapshot update the project provides (commonly `pytest --snapshot-update` or an `UPDATE_SNAPSHOTS=1` env flag) and `git add` the result.

If the project has no generator for a "generated" file, fall back to synthesizing it by hand per Step 5b — but say so in the summary.

## Step 7: Lint touched files

Lint **only** the files you touched — never the whole tree. Use the project's checks:

```bash
# Python
uv run ruff check <files> --fix && uv run ruff format <files> && uv run mypy <files>
# Node/TS, if present
npm run lint
```

If a check reports a real issue, your synthesis in Step 5b was incomplete — go back and reconsider, don't paper over it with `# noqa` / `eslint-disable`.

## Step 8: Commit and push

**If you came from Step 5 (conflict-resolution path):** the merge is still in progress with resolved files staged/modified.

```bash
git add <resolved-files>
git status              # confirm "All conflicts fixed but you are still merging."
git commit --no-edit    # accept git's default merge commit message
git push
```

**If you came directly from Step 4 outcome 2 (clean merge):** `git merge` already created the merge commit. Nothing to commit — just push.

```bash
git status   # clean tree on top of the new merge commit
git push
```

**Don't `--amend` the merge commit.** If something went wrong, `git merge --abort` (only valid on the conflict-resolution path while merging) and restart from Step 4. If a pre-commit hook fails on the merge commit, fix the underlying issue, stage the fix, and add a **new** commit on top — do not amend.

## Step 9: Hand off to /verify

A merge resolution must be verified by **running the code**, never by re-reading the diff — the conflict may have textually resolved while leaving the two slices semantically inconsistent (a frozen contract drifted, a route shadowed, a fixture collided). Hand off to `/verify`:

```
Skill(skill: "verify")
```

`/verify` will run the linters + type-checks + tests, have adversarial checker-agents actually exercise the affected endpoints/UI to confirm both slices' behavior survived the merge, and walk the golden demo path on a clean checkout. Pass it the head branch and a one-line note on what you synthesized so it knows where to probe hardest.

## Step 10: Summary

Report to the user, in 4–6 lines:

- Branch (and PR number/URL if one exists).
- Number of conflicted files and a one-phrase description per type (e.g., *"1 import conflict in app/api.py — kept both imports"*, *"package-lock.json regenerated"*, *"converged both slices onto the frozen Task schema in lib/types.py"*).
- Merge commit SHA.
- The `/verify` outcome (what it confirmed/refuted, with file:line evidence).
- Confirmation the branch is pushed.

Don't dump the diff — the merge commit captures it.

## Gotchas

- **GitHub's `mergeStateStatus: DIRTY` can lie clean.** A previous merge commit may already be on the branch but the base has moved since. Always `git fetch origin <base>` and check `git log HEAD..origin/<base>` before deciding there's nothing to do.
- **`git checkout --ours` / `--theirs` discards real work.** Use them ONLY on generated/lockfiles you regenerate immediately after — never on hand-written source.
- **Don't amend a merge commit.** If you need a do-over, `git merge --abort` and start over.
- **A clean textual resolution is not a correct one.** Two slices can both compile and still disagree on a shared contract. That's exactly why Step 9 verifies by running, not reading.
- **Lockfile conflicts are almost always "take base, re-resolve".** Hand-merging hash blocks breaks the resolver.
- **Don't skip /verify.** A merge that "looks fine" but breaks the golden demo path is the worst possible failure at a hackathon — it surfaces live, on camera.
