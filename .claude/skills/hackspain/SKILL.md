---
name: hackspain
description: "Drive the HackSpain 2026 participant platform through the `hackspain` CLI: team status, linking the public repo, track registration, stack, milestones, the feed, posting updates, the AI-usage watcher, and the final project submission. Use when the user mentions HackSpain, the dashboard, the feed, milestones, linking the repo, 'submit the project', 'post an update', or asks where the team stands on the platform."
argument-hint: "[what to do on HackSpain, e.g. 'status', 'link repo', 'draft submission', 'post <text>']"
---

# HackSpain CLI

The `hackspain` CLI is the terminal client for the HackSpain 2026 dashboard (https://hackspain.app). It uses the same account and data as the dashboard: team, tracks, submission, feed and watcher. Its reference page is https://hackspain.app/cli.

**Input:** $ARGUMENTS. With no argument, run the status check in Step 1 and report where the team stands.

## Our setup (as of Fri 18 Sep 2026; re-check live with Step 1)

| Thing | Value |
|---|---|
| Team | `refugia2`, 4 members; Luis is the owner |
| Track | `prosper-ai` (already registered) |
| Repo to link | `https://github.com/luisgonzaleznf/hackspain-prosper-2026`, the **public** mirror. Never link `hackspain-prosper-2026-private`: the platform requires a public repo. |
| Submissions | not open yet (`submissionsOpen: false`) |

The feed and stack detection only see pushes to the **linked public repo**. Work in the private repo does not show up until someone runs `git push public main` from a clone that has the `public` remote.

## Rules for agents

1. **Always pass `--json`** (as `hackspain --json <cmd>`). It prints exactly one JSON object `{"ok": bool, "data": …}` on stdout, turns off all prompts, and sends everything else to stderr. Parse it; don't scrape the human-readable tables.
2. **Never run anything interactive.** Bare `hackspain` opens a menu and `hackspain watch` is a full-screen TUI. Both need a real terminal. Tell the user to run them in their own terminal instead.
3. **Login is the user's job.** `hackspain auth login` opens a browser to approve the device. On exit code `3`, ask the user to run `! hackspain auth login`.
4. **Confirm before anything outward-facing.** Show the exact command and wait for a clear yes before running any command in the "Changes things" table below. Read-only commands can run freely.
5. **There is only ONE submission, and agents never make it.** A final `submit` (anything without `--draft`) freezes the project for good, and `--json` skips the CLI's own confirmation. A repo hook (`.claude/hooks/guard_hackspain_submit.py`, wired in `.claude/settings.json`) blocks every agent-run `hackspain … submit` that lacks `--draft`.
   - Don't try to route around the hook: no aliases, variables, scripts or the dashboard's submit button in the browser.
   - Your job ends at a correct draft. Hand off by showing the draft and asking the user to run the final `hackspain submit` themselves.

## Step 1: Status check (read-only)

```sh
hackspain --json auth status     # logged in? gate.state should be "ready"
hackspain --json team show       # members, repoUrls, techStack (includes the join code; don't paste it anywhere public)
hackspain --json track list      # which tracks we're in; submissionsOpen
hackspain --json project show    # our project / draft, if any
hackspain --json milestone list  # milestones recorded so far
```

Summarize for the user in plain words: logged in yes/no, repo linked yes/no, stack set yes/no, track entered, whether submissions are open, and which milestones are recorded.

## Command reference

### Read-only (safe to run)

| Command | What it does |
|---|---|
| `auth status` | Check the session |
| `profile` | Name, diet, travel, phone, notifications, GitHub, X |
| `team show` / `team list` | Our team / all teams (with tracks and repos) |
| `track list` | Tracks, which ones we've entered, and `submissionsOpen` |
| `project show` / `project list` | Our project / all projects |
| `stack show` | Our declared or detected stack |
| `perk list` | Partner perks catalogue (perks are claimed on the dashboard, not here). The output includes redeemable credit codes, so never paste it into the repo or the feed. |
| `milestone list [--all]` | Our milestones (or everyone's) |
| `feed [-n 20] [--no-images] [--before <cursor or ISO date>]` | Everyone's posts plus pushes and PRs from every team's repo |
| `telemetry stats` | What the watcher has recorded on this machine |
| `open [page]` | Open the dashboard (feed, teams, tracks, perks, profile) in the browser, already signed in. `--print` prints the link instead, but that link carries a session token (`hs-token=`): never paste, commit or post it. |

### Changes things (confirm with the user first)

| Command | Effect |
|---|---|
| `team repo <url…> [-y]` | Link the public GitHub repo(s). The stack is then detected from them (`-y` accepts the detection). `--clear` unlinks. |
| `stack detect [-y]` / `stack set <tech…>` | Detect the stack from the linked repo, or replace it by hand |
| `track register/unregister <slug…>` / `track move <from> <to>` | Change which tracks the project enters |
| `milestone add firstCommit\|firstBuild\|firstDemo\|custom [--label …] [--at ISO]` | Record a team milestone. `custom` requires `--label`. |
| `post "text" [--image file]` | **Public** post to the feed: 500 characters max; jpg, png, webp or gif image up to 5 MB |
| `submit --draft …` | Save a draft; everything stays editable |
| `submit …` (no `--draft`) | **Final, one-shot submission. It freezes the project. Agents never run it: the hook blocks it and the user runs it.** |
| `profile edit …`, `profile notify on\|off`, `profile phone`, `profile github`, `profile x` | Edit the user's own profile |
| `team code --regenerate` | Invalidate the current join code |
| `team leave` / `team transfer [member]` / `team dissolve` | Leave the team / hand it over / delete it. **Almost never what we want; the owner cannot leave.** |
| `update` | Download the latest CLI release and replace the binary |

## Recipes

**Link the repo.** Only after the public mirror has real content pushed:
```sh
hackspain --json team repo https://github.com/luisgonzaleznf/hackspain-prosper-2026 -y
```

**Record milestones** at the real moments, with the user's OK:
- `firstBuild`: when the agent first answers a call end to end.
- `firstDemo`: after the first scored run or the first recorded demo.
- `custom --label "…"`: for other wins, such as a checkpoint lead or all practice cases passing.

**Submission.** `--json` turns off prompts, so pass every field as a flag:

| Flag | What to pass |
|---|---|
| `--name` | Project name, taken from `SUBMISSION.md` |
| `--description` | What it does, at least 10 characters, taken from `SUBMISSION.md` |
| `--repo` | The public repo URL |
| `--video` | A YouTube, Loom or MP4 link to the demo video. Ask the user for it; there is no local upload. |
| `--demo` | Optional. A live URL, only if we have one. |
| `--track` | `prosper-ai`. Repeatable. |
| `--perk` | Optional. A perk id from `perk list`. Repeatable. |

Save a draft first:
```sh
hackspain --json submit --draft --name "…" --description "…" \
  --repo https://github.com/luisgonzaleznf/hackspain-prosper-2026 \
  --video "<url>" --track prosper-ai
```
Check the draft with `hackspain --json project show`, show it to the user, and stop there. **The final submit is the user's to run.** They run `hackspain submit` in their own terminal, where the CLI walks through the form and asks for a final confirmation. Do this only once the whole team agrees it's the final version.

**Post an update.** Draft the text, show it to the user, and post only after they approve. Keep it under 500 characters.

## The watcher

`hackspain watch` is meant to stay open in its own terminal all weekend, so the user should start it themselves.
- **What it shows:** the feed and messages from the organizers.
- **What it reports:** AI-harness usage (Claude Code, Codex, Gemini CLI and others) for the whole hackathon window, including time it wasn't running, and nothing from outside that window.
- **What it never sends:** prompts or full file paths.
- **Keys:** `q` quit, `p` pause, `↑↓` scroll the feed, `g` back to live.
- **Useful flags:** `--plain` (line-by-line output), `--once` (scan once and exit), `--no-upload` (keep everything local).

Check what it has recorded with `hackspain telemetry stats`.

## Exit codes

| Code | Meaning | Next step |
|---|---|---|
| 0 | OK | — |
| 1 | Server or generic error | Retry once, then report the stderr |
| 2 | Usage error (bad flags, or input missing in non-interactive mode) | Fix the flags; with `--json`, every required field must be a flag |
| 3 | No session or session expired | User runs `! hackspain auth login` |
| 4 | Not eligible yet (no application, not accepted, onboarding incomplete, or the hackathon isn't running) | Report the gate message; outside the hackathon window only `profile`, `perk list` and `open` work |
| 5 | Backend unreachable | Check the network and retry |
| 130 | Interrupted (Ctrl+C) | — |

## Install / update

The CLI is a self-contained binary (currently at `~/.local/bin/hackspain`, v0.5.1).
- **Update:** `hackspain update` (ask the user first).
- **Fresh install on macOS or Linux:** `curl -fsSL https://hackspain.com/install.sh | sh`. This downloads and runs a script, so ask the user before running it.
- **Windows:** download `hackspain-windows-x64.exe` from the releases page and rename it to `hackspain.exe`.
