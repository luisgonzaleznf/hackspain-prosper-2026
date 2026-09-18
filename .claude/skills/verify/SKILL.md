---
name: verify
description: The CI replacement, run LOCALLY. Three layers in order — (1) FAST deterministic ruff + mypy + pytest on the whole tree, (2) PROVE-IT adversarial checker-agents that ACTUALLY RUN the code (call the endpoint, hit the function, drive the UI) and return confirmed/refuted with file:line evidence for every load-bearing claim, (3) GOLDEN-PATH e2e on a CLEAN checkout. Outputs a go/no-go verdict + ranked fix list. Use before integrating a slice or before the demo. Never let a builder re-read its own diff and call it verified.
argument-hint: "[--fast] [path]"
disable-model-invocation: true
---

# Verify Skill — the local CI / review replacement

There is no CI here. No Greptile, no remote checks, no second pair of human eyes. This skill **is** the safety net, and it runs entirely on your laptop.

Its one non-negotiable belief: **you verify by RUNNING the code, never by re-reading the diff.** A builder who just wrote a slice is the worst possible judge of whether it works — they will read their own intention back into the code. So this skill spawns **independent checker-agents** that have not seen the builder's reasoning, hand each one a single load-bearing claim, and make it **execute the real thing** (call the endpoint, invoke the function, drive the UI) and come back with `confirmed` / `refuted` and **file:line + captured output** as evidence.

Three layers, **in order**, each gates the next:

1. **FAST (deterministic).** `ruff` + `mypy` + `pytest` on the whole tree. Must be green. Cheap, runs always, catches the dumb stuff before you spend agent budget.
2. **PROVE-IT (adversarial).** A `Workflow` fan-out of one checker-agent per load-bearing claim. Each agent runs the code and confirms or refutes. This is the heart of the skill.
3. **GOLDEN-PATH (e2e).** Boot the app on a **CLEAN checkout** (fresh `uv sync`, zero uncommitted state) and walk the exact demo path end to end.

**Output:** a single **GO / NO-GO** verdict plus a **ranked fix list**.

It is **dial-able**:
- **`--fast`** → run Layer 1 only. Use constantly while building (every few commits). Seconds, not minutes.
- **default (no flag)** → all three layers. Run this **before integrating a slice** into the shared branch and **before recording the demo**. This is the full adversarial pass.

`[path]` optionally scopes Layers 1 and 2 to a subtree (e.g. one slice's directory). Layer 3 always runs the whole golden path — the demo doesn't care about your slice boundaries.

Track the layers with `TaskCreate` / `TaskUpdate`. Mark each done as you finish it — don't batch.

---

## Layer 0 — Parse args + locate the contracts

From `$ARGUMENTS`:
- **`--fast`**: present iff the literal flag appears. If present, you run **only Layer 1** and stop.
- **`[path]`**: first non-flag positional. Scopes Layers 1 + 2. Defaults to repo root.

Then locate the two things every later layer needs. Do **not** invent them:

- **The frozen contracts** — the shared rules `/brainstorm` froze before parallelizing (types, API shapes, data schema, file ownership). Look for `CONTRACTS.md`, `docs/contracts*`, or a "Shared Rules" / "Contracts" section in `CLAUDE.md` / the brainstorm notes. These tell you what each claim is *supposed* to satisfy. If you cannot find them, say so loudly at the top of the report — you are verifying against intention you had to guess, which is weaker.
- **The golden demo path** — the exact click-path / call-sequence the demo walks, plus its deterministic seed. Look for it in `CLAUDE.md`, `SUBMISSION.md`, a `/demo` script, or the brainstorm output. If absent, Layer 3 cannot run; flag it and stop before Layer 3.

Create the task list:

1. Parse args + locate contracts (mark done immediately)
2. **Layer 1 — FAST**: ruff + mypy + pytest, whole tree (or `[path]`)
3. *(stop here if `--fast`)*
4. **Layer 2 — PROVE-IT**: extract load-bearing claims, fan out checker-agents that RUN them
5. **Layer 3 — GOLDEN-PATH**: clean checkout, fresh `uv sync`, walk the demo
6. Verdict + ranked fix list

---

## Layer 1 — FAST (deterministic, always)

Run, in this order, scoped to `[path]` if given else the whole tree:

```bash
uv run ruff check .          # lint
uv run ruff format --check . # formatting (don't auto-fix here — just report drift)
uv run mypy .                # types
uv run pytest -q             # the whole suite
```

Rules:
- **Whole tree, not just the diff.** A green slice that broke a sibling slice is the exact failure this layer exists to catch. (Scope to `[path]` only when the user explicitly asked to.)
- **Green means zero errors and zero failures.** A skipped test is not a pass — note skips in the report.
- **If anything is red, STOP.** Do not proceed to Layer 2. A red tree means the deterministic floor is broken; agent-level verification of a broken floor is wasted budget. Emit a NO-GO now with the failing checks as the top of the fix list.
- If a `pyproject.toml` / lockfile is missing or `uv` isn't set up, that itself is a NO-GO finding (the clean-checkout layer would fail anyway).

If the project has a JS/Vite UI slice (the polish recipe, not the default), also run its checks where present: `npm run -s lint`, `npm run -s typecheck`, `npm run -s test` (or the `package.json` equivalents). Skip silently if there's no UI.

**If `--fast`:** report Layer 1 results as the verdict and stop. Green → "GO (fast lane — Layers 2 + 3 NOT run)". Red → NO-GO with the failures ranked.

---

## Layer 2 — PROVE-IT (adversarial, run-the-code)

This is where re-reading a diff is forbidden and running it is mandatory.

### 2a. Extract the load-bearing claims

A **load-bearing claim** is a statement that, if false, breaks the demo or a contract. Pull them from, in priority order: the slice's commit messages / PR body, the frozen contracts (every API shape and data-schema guarantee is a claim), and the golden demo path (every step is a claim: "the endpoint returns X", "the function handles empty input", "the UI shows Y after click Z").

Write each as a falsifiable, **executable** assertion. Good claims name a thing to run and an observable result:
- "`POST /summarize` with a 2-line body returns 200 and JSON `{summary: str}` in < 5s" → call it.
- "`extract_entities('')` returns `[]`, not a crash" → invoke it.
- "clicking **Generate** with the seed renders a non-empty result card" → drive the UI.

Drop anything you can't make executable (pure styling taste, future TODOs). Keep it tight — aim for the handful of claims the demo actually rests on, not an exhaustive audit. Below ~4 real claims, you can run them inline; at/above ~4, fan out.

### 2b. Fan out one checker-agent per claim (Workflow)

Launch a `Workflow` with one independent verifier agent per claim, in parallel. Each agent gets ONLY its claim and the repo path — **not** the builder's diff or reasoning (that's the point: it must reach the verdict by execution, not by trusting the author). Each agent **runs the real code** and returns a structured verdict with file:line + captured output.

```javascript
export const meta = {
  name: 'verify-claims',
  description: 'Adversarially verify each load-bearing claim by RUNNING the real code',
  phases: [{ title: 'Prove' }],
}

const VERDICT_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    claim_id: { type: 'string' },
    headline: { type: 'string' },
    verdict: { type: 'string', enum: ['confirmed', 'refuted', 'partially-confirmed', 'inconclusive'] },
    how_i_ran_it: { type: 'string', description: 'the exact command / call / UI steps executed' },
    evidence: { type: 'string', description: 'file:line refs + the ACTUAL captured output (status code, return value, rendered text, error trace)' },
    corrected_statement: { type: 'string', description: 'the true statement after running it' },
    severity: { type: 'string', enum: ['Blocker', 'Bug', 'Design', 'Minor', 'Nit', 'None'] },
    fix: { type: 'string', description: 'concrete fix if refuted/partial, else empty' },
  },
  required: ['claim_id', 'verdict', 'how_i_ran_it', 'evidence', 'corrected_statement', 'severity', 'fix'],
}

const REPO = '<absolute repo path>'
const PREAMBLE = `You are an adversarial checker. Verify ONE claim about the code at ${REPO} by ACTUALLY RUNNING IT — never by reading the diff and reasoning about it. You have NOT seen the author's intent; do not trust it.

HOW TO RUN, by claim type:
- backend endpoint: boot it (\`uv run uvicorn <app>:app --port <free>\` or the project's run command), then hit it with \`curl\`/httpx. Quote the real status + body.
- pure function / module: \`uv run python -c "..."\` importing and calling it with the claim's inputs. Quote the real return value or traceback.
- UI behavior: drive it via claude-in-chrome (navigate, click, read the rendered DOM). Quote what actually rendered.
- Use a deterministic seed if the golden path defines one. Use the .env / test config the project ships; never invent secrets.

Be adversarial: try the empty input, the boundary, the unhappy path the claim glosses over. If it crashes, hangs (>10s), leaks a secret into output/logs, or returns the wrong shape — that's REFUTED, report it with the captured evidence. A claim is 'confirmed' ONLY if you observed the asserted result with your own execution.

CLAIM:
`

phase('Prove')
const CLAIMS = [ /* { id, prompt } per 2a claim */ ]
const results = await parallel(CLAIMS.map((c) => () =>
  agent(PREAMBLE + c.prompt, { label: `prove:${c.id}`, phase: 'Prove', schema: VERDICT_SCHEMA })
    .then((v) => ({ ...v, claim_id: v?.claim_id || c.id }))))
return { verdicts: results.filter(Boolean) }
```

Hard rules for this layer:
- **A `confirmed` is only valid if the agent's `evidence` contains real captured output** (a status code, a return value, rendered text, a traceback) — not a paraphrase of the code. If an agent returns `confirmed` with no execution evidence, treat it as `inconclusive` and re-run it with a sharper "you must run it" instruction.
- **`inconclusive` counts against GO**, same as refuted, until resolved. "I couldn't run it" is not a pass.
- Don't spawn workflows anywhere else in this skill. This is the one fan-out.

### 2c. The footgun sweep (generic, de-framework'd)

Each checker-agent, while it has the file open to run the claim, also eyeballs the **load-bearing code path it just executed** for these generic footguns. This is the transferable core of a hard-nosed senior review, with all framework specifics stripped. Flag any it sees (with file:line), mapped to severity:

- **Unhandled errors / swallowed exceptions** — broad `except:` that catches and continues (or returns `None`) so a failure silently becomes wrong data. Refuted-adjacent: it hides the very bug you're hunting. **Blocker** if on the demo path.
- **Missing `await`** — a coroutine called without `await` (returns a coroutine object, never runs). Classic silent no-op. **Bug.**
- **Secret leakage** — API keys / tokens hard-coded, printed, logged, or returned in a response/error body. Check that keys come from env, not literals. **Blocker.**
- **Blocking I/O on the hot path** — a sync `requests`/`time.sleep`/disk call inside an async handler, or any external call **without a `timeout=`** (it can hang the demo forever). **Bug.**
- **Unbounded loop / unbounded growth** — `while True` with no break/timeout, pagination with no cap, retry with no max, an LLM/agent loop with no step limit. **Bug** (it'll hang the demo).
- **N+1 / per-iteration external calls** — an API/DB/LLM call **inside** a loop that could be batched or hoisted. Slow demos die on stage. **Design**, **Bug** if it makes a demo step exceed a few seconds.
- **Bad error handling at the boundary** — endpoint/handler returns a 200 with an error payload, or a raw 500 stacktrace, instead of a clean status. **Design.**
- **Mutable/shared state across requests** — module-level mutable default or cache that bleeds between calls and makes the demo non-deterministic. **Bug.**

This sweep is advisory unless an item sits **on the golden demo path** — then it's a Blocker, because it will fail live in front of judges.

### 2d. Aggregate

Collect the verdicts. The fix list seeds from every `refuted` / `partially-confirmed` / `inconclusive` claim and every footgun, each carrying its file:line evidence and severity. State refutations plainly — a refuted claim the builder "knew" was true is exactly the catch that justifies this layer.

---

## Layer 3 — GOLDEN-PATH e2e (clean checkout)

The demo is the deliverable, so the last gate is: **does the exact demo path work from a clean slate?** Not your working tree — a fresh checkout with nothing uncommitted, because the demo runs from a clean checkout and uncommitted state is the #1 way a demo dies ("works on my machine").

1. **Refuse if the tree is dirty.** `git status --porcelain` must be empty. If not, NO-GO with "uncommitted state — commit or stash before verifying the golden path" at the top. Demoing uncommitted work is banned; so is verifying it.
2. **Clean checkout into a temp dir.** `git worktree add /tmp/verify-clean <current-branch-or-HEAD>` (or clone to a temp dir). Everything below runs **there**, never in your working copy.
3. **Fresh deps from the lockfile.** In the clean dir: `uv sync` (and `npm ci` if there's a UI slice). A failure here is a NO-GO — it means a dep isn't pinned and the demo machine won't boot.
4. **Boot with the deterministic seed.** Start the app the way the demo does (the `/demo` boot command or the project's documented run command), loading the seed data the golden path expects. Confirm it comes up clean (health check / first page renders, no tracebacks in the log).
5. **Walk the exact golden path, end to end.** Backend-only → the documented `curl`/script sequence. UI → drive it with claude-in-chrome exactly as the demo will (same clicks, same inputs, same order). **Observe the real result at every step** — capture the status/output/rendered screen. Any step that errors, hangs, or shows the wrong thing is a NO-GO with that step at the top of the fix list.
6. **Tear down** the temp worktree/dir (`git worktree remove --force /tmp/verify-clean`) so nothing leaks into the next run.

If Layer 0 couldn't find a golden path, skip this layer and downgrade the verdict to **GO-WITH-CAVEAT** at most (you proved the pieces but not the whole walk), and put "define + verify the golden demo path" as the #1 fix.

---

## Verdict + ranked fix list

End with exactly one verdict and a ranked list.

**Verdict (pick one):**
- **GO** — Layer 1 green, every load-bearing claim `confirmed` with execution evidence, no on-path footgun, golden path walked clean on a fresh checkout. Safe to integrate / record the demo.
- **GO-WITH-CAVEAT** — the demo path works, but there are non-blocking findings (off-path footguns, `Minor`/`Design` items), or Layer 3 couldn't fully run (no golden path defined). Name every caveat.
- **NO-GO** — any of: Layer 1 red, any `refuted`/`inconclusive` load-bearing claim, an on-path footgun, dirty tree, failed `uv sync`, or a golden-path step that errored. The demo is not safe yet.

**Ranked fix list** — ordered by severity then demo-path proximity (on-path beats off-path at equal severity):

| # | Severity | Finding | Evidence (file:line + captured output) | Fix |
|---|---|---|---|---|
| 1 | Blocker | … | … | … |

Severity ladder: **Blocker** (breaks the demo / leaks a secret) → **Bug** (wrong behavior, off the immediate demo path) → **Design** (works but fragile / slow) → **Minor** → **Nit**.

Then one plain-English line a tired builder can act on at 3am: the single most important thing to fix before this slice is safe.

---

## Operating rules (the posture, encoded)

- **Verify by running, never by re-reading.** If a layer's evidence is a description of the code instead of its captured output, that layer didn't run — redo it. This is the whole reason the skill exists.
- **The builder never grades their own homework.** Layer 2's checker-agents are independent and intent-blind on purpose. Don't let the slice author's "it works" substitute for execution.
- **Deterministic floor first.** Never spend agent budget on Layer 2 while Layer 1 is red.
- **Clean checkout or it doesn't count.** The demo runs from clean; so does the final gate. Uncommitted state is a NO-GO, full stop.
- **Dial it to the moment.** `--fast` while building (constantly, cheap); full three-layer pass before integrating a slice and before recording. Below ~4 claims, run Layer 2 inline; at/above, fan out.
- **Refute plainly.** When you refute a claim — the builder's or your own earlier read — say so and show the captured evidence. That transparency is the product.

## Writing style

Sound human. No em dashes, no padding, no praise. Write for a builder with zero context who needs to act in the next two minutes. Be specific: "`/summarize` returned 500 — `KeyError: 'text'` at `app/routes.py:41`, the handler reads `body['text']` but the contract says `body['content']`" beats "the endpoint has an issue." Lead with the verdict; the fix list is the payload.
