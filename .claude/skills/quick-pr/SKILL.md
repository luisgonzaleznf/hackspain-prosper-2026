---
name: quick-pr
description: "Ship one build slice end-to-end (alias: /ship) — clean-main pre-flight, branch, implement with commit discipline, push, open a PR in the browser, then run /verify instead of waiting on CI. The ticket step is optional and skippable (no tracker needed at a hackathon). Use per slice once the shared rules are frozen, or whenever the user says \"ship this\" / \"quick-pr <task>\"."
argument-hint: "<task> [--ticket]"
---

# Ship a Slice (quick-pr / ship)

You are taking one build slice from idea to an open PR, then proving it works by **running it** — not by waiting on CI or a review bot (there is none at a hackathon). Keep it lean: the deliverable is working code on a branch with a green `/verify`, fast.

`ship` is an alias for this skill — same flow either way.

## Step 0: Set up step tracking

Create a task list with one task per step using `TaskCreate`. Don't skip this — it's easy to drop the final `/verify` hand-off, and that's the load-bearing step. Mark each task completed as soon as it's done; don't batch.

1. Parse arguments (Step 1)
2. Pre-flight check (Step 2)
3. Understand the request (Step 3)
4. Create a tracker ticket — OPTIONAL (Step 4)
5. Create git branch (Step 5)
6. Implement changes (Step 6)
7. Commit changes (Step 7)
8. Push and open PR (Step 8)
9. Open PR in browser (Step 9)
10. Run /verify (Step 10)

## Step 1: Parse arguments

`$ARGUMENTS` is the **task description**, plus an optional `--ticket` flag.

- **`--ticket` present** → do Step 4 (create a tracker ticket) if an issue tracker is wired up.
- **`--ticket` absent** (default) → **skip Step 4 entirely.** No tracker at a hackathon is the norm; don't block on it.

Strip the flag from the task text before using it in later steps.

## Step 2: Pre-flight check

Verify the working tree is clean and on the default branch (`main`):

```bash
git status --porcelain
git branch --show-current
```

- **Not on `main`:** Stop. *"You're on `<branch>`. /ship must start from `main` — switch to main and retry."* If there are also uncommitted changes, call that out explicitly (they could be lost). **Do NOT proceed.**
- **On `main` with uncommitted changes:** Stop. *"Uncommitted changes on `main` — commit or stash them before /ship."* **Do NOT proceed.**
- **On `main`, clean tree:** Pull the latest, then continue:
  ```bash
  git pull origin main
  ```

A clean start from `main` is non-negotiable: parallel slices already pushed; you want this branch rooted on their latest so `/verify` and any later `/solve-merge-conflicts` have less to reconcile.

## Step 3: Understand the request

Use the task from Step 1.

- **Clear and specific** (e.g. "add a `/health` route to app/api.py", "fix the off-by-one in lib/parse.py") → go straight to implementation.
- **Vague or complex** (e.g. "make the search better") → enter plan mode (`EnterPlanMode`), explore, design, get approval (`ExitPlanMode`), then implement.

**Capture the spec.** Write down the concrete scope you're committing to (in the ticket if you make one, else in working memory). This is the reference `/verify` uses to decide which load-bearing claims to check — and it's what keeps the slice inside its frozen file-ownership boundary so it doesn't collide with parallel work. If your slice needs to touch a *shared contract* (a type, an API shape, a data schema) that was frozen up front, stop and flag it — changing it unilaterally is how parallel builders collide.

## Step 4: Create a tracker ticket (OPTIONAL — only if `--ticket`)

**Skip this entirely unless Step 1 saw `--ticket` AND an issue tracker is actually configured.** Hackathons usually have neither.

If you are creating one: use whatever tracker the project has wired up, with a concise title, a one-line description including the Step 3 spec, assigned to the user, in an "in progress" state. Capture the ticket ID/URL for the PR body. If the tracker call fails, don't block — drop the ticket and continue.

## Step 5: Create git branch

Use a descriptive branch name (from the ticket's suggested branch if Step 4 made one, else derive from the task):

```bash
git checkout -b <slice-name>     # e.g. feat/health-route, fix/parse-off-by-one
```

Keep the slice name aligned with the frozen file-ownership split so branches stay easy to reason about when they're merged together later. (No pull needed — Step 2 already updated `main`.)

## Step 6: Implement changes

**Plan-mode path:** explore → plan → `ExitPlanMode` for approval → implement the approved plan.

**Direct path:** implement the change, follow the project's conventions in `CLAUDE.md`, and run the relevant linters/type-checks/tests on the **files you changed** (not the whole tree) as you go.

Stay inside your slice's file ownership. If you find yourself editing a file another slice owns, stop — that's a collision waiting to happen; either coordinate or note it for `/solve-merge-conflicts`.

**Trust the names. Don't narrate the code.** Before any comment, ask: would a reader lose anything they can't recover from the name, signature, types, tests, and adjacent code? If no → don't write it. Skip block-purpose headers (extract a named function instead) and PR-body-in-source cross-references (`# Mirrors slice X`, `# Chosen over <alt> because …`). Carve-out: hidden constraints, non-trivial workarounds, surprising invariants — things the code *can't* say. Docstrings are fine; keep them tight, don't restate the signature.

## Step 7: Commit changes

Commit often — small, working commits beat one giant one, especially when slices later merge.

1. Stage the **specific** files you changed. **Never `git add .`** — it sweeps in stray files and breaks the clean-checkout guarantee `/verify` relies on:
   ```bash
   git add <specific-files>
   ```

2. Conventional-commit message:
   ```bash
   git commit -m "$(cat <<'EOF'
   <type>: <concise description>

   <optional body explaining why, not what>

   Co-Authored-By: Claude Code <noreply@anthropic.com>
   EOF
   )"
   ```
   Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`.

## Step 8: Push and open PR

```bash
git push -u origin <branch-name>
```

Open the PR with a description a teammate (or future you, mid-demo) can act on:

```bash
gh pr create --title "<PR title>" --body "$(cat <<'EOF'
## Summary
<2-3 bullets: what this slice does>

## Scope
<the frozen scope from Step 3 — and the shared contracts/files this slice owns>

## Changes
<brief list of files/areas changed>

## How to verify
<the golden-path steps a human (or /verify) runs to see this slice work locally — endpoints to hit, commands to run, what good looks like>

---
Generated with [Claude Code](https://claude.ai/code) | Created with /ship
EOF
)"
```

If you made a ticket in Step 4, add a `## Ticket` line with its URL. Capture the PR URL from the output.

## Step 9: Open PR in browser

```bash
open -a "Google Chrome" "<pr-url>" || open "<pr-url>"
```

## Step 10: Run /verify (the CI replacement)

There is no CI and no review bot. **Verification is your safety net, and it works by running the code, not re-reading the diff.** Hand off to `/verify`:

```
Skill(skill: "verify")
```

Pass it the PR/branch and the Step 3 spec so it knows which load-bearing claims to check. `/verify` will:
- Run the project's linters + type-checks + tests.
- Have adversarial checker-agents actually exercise the change (call the endpoints, drive the UI) and confirm or refute each load-bearing claim with file:line evidence.
- Walk the golden demo path end-to-end on a **clean checkout** (which is why Step 7 forbade `git add .`).

If `/verify` refutes a claim, fix it (use `/debug-issue` to find the real root cause if it's not obvious), commit, push, and re-run `/verify` until green. The slice isn't shipped until `/verify` is green.

---

## Error Handling

- Any git operation fails → stop and tell the user the current branch + last successful step.
- Tracker call fails in Step 4 → drop the ticket and continue (it was optional anyway).
- `gh pr create` fails → print the manual command and stay on the branch.
- `/verify` fails to start → run the project's lint/type/test commands manually as a fallback, and tell the user `/verify` couldn't run.
