---
name: debug-issue
description: Trace something you just built that's failing to its real root cause — falsify the load-bearing premise, build a timeline, write a repro — instead of patching the symptom
argument-hint: "<error message, traceback, failing test, screenshot, or 'X is broken' description>"
---

## Context

You are the debugger for whatever you just shipped at this hackathon. Something is failing and the clock is running. Your job is to trace it to its **root cause** — not to slap a patch on the symptom and pray. You diagnose, write a local reproduction, and hand off a clean fix plan.

It is tempting under time pressure to do the opposite: add a retry instead of fixing the race, bump a limit instead of bounding the resource, add a try/except instead of fixing the bad state. Those "fixes" feel fast and then cost you three more bugs an hour later, mid-demo. A proper diagnosis produces a **timeline** that explains *why* the bug happens, not just *what* error it prints.

**The two cardinal rules:**

1. **Understand the root cause before suggesting any fix.** The worst hackathon bugs come from fixing symptoms.
2. **Verify the load-bearing premise before you scaffold a story on it.** Every diagnosis rests on one or two foundational claims about how the system actually behaves ("the API call is slow", "the library waits N seconds before X", "the queue is full", "the model returns Y format"). When those claims are wrong, the entire downstream timeline is wrong, and your fix targets a problem that doesn't exist. The classic miss is writing 1000 words of analysis on top of a premise that took 60 seconds to falsify — e.g. "the request is timing out" when a single log line shows it returns in 0.2s. Step 1.5 below is the structural counter-pressure. Do not skip it.

**Input**: $ARGUMENTS — an error message, traceback, failing test output, screenshot, log excerpt, or plain description ("the thing I just wired up is broken").

## Collaboration principle

**You built this five minutes ago — your own memory is an investigation tool.** You know what you just changed, what you were in the middle of, what you tried. Use it. But don't trust it blindly: the bug is usually in the gap between what you *think* you wrote and what's actually on disk. Read the real code.

When you're working with a teammate, ask them at key checkpoints rather than barreling through. A 30-second answer ("oh, I just swapped the env var") can save 10 minutes of digging. But don't block on a human for anything you can look up yourself.

**When to ask:**
- After triage: "Here's what I see — does this match what you're observing?"
- When the timeline has a gap tools can't fill: "I see X happened then Y failed, but I can't tell what triggered X — do you know?"
- When the issue might be environment-specific: "Does this reproduce on a clean checkout, or only in your current working tree?"
- When you find a suspicious recent change: "This was touched in the last commit — did that line up with when it broke?"

**When NOT to ask (just look it up):**
- Anything in the source code or git history
- Config/env-var values and their defaults
- Stacktrace interpretation
- What a dependency actually does (read its installed source)

## Available investigation tools

Use these aggressively to build the timeline. All are generic — adapt to whatever you actually have:

### Code (always available)
- Read the source of the thing that's failing
- `git log`, `git blame`, `git diff` — trace when code changed and what the last commit touched (often the culprit at a hackathon)
- Search for callers, consumers, and related code paths

### Your logs
- Application logs / stdout / the terminal you ran it in
- For a server: the request log. For a UI: the browser console + network tab. For a script: print/log output
- Grep around the timestamp of the failure to see what happened just before

### Your error tracker (if you have one)
- Full stacktrace, first/last seen, frequency, affected inputs
- Whatever monitoring or crash reporting you wired up — optional, skip if you have none

### Run it yourself
- The cheapest investigation tool is often re-running the failing path with one extra log line or a debugger breakpoint
- Reproduce in isolation: call the endpoint with `curl`, run the one function in a REPL, drive the one UI action

## Step 1: Triage the input

Determine what you're working with and extract the initial signal:

- **Error / traceback**: identify the exception type, the file:line, and the call chain. Open that code.
- **Failing test**: read the assertion, the expected vs actual, and the setup. The diff between them is the lead.
- **Screenshot / user-facing symptom**: identify the visible failure, then work backwards — which endpoint, which handler, which code path could produce *this exact* behavior?
- **Vague "it's broken"**: get specifics. You need at least: what action triggered it, when it last worked, and how often it happens. "It's broken" is not a starting point.

**Output a 1-2 sentence problem statement** before proceeding: "The issue is [X], happening when [Y], [every time / intermittently]." If it's intermittent, say so — that immediately points at concurrency, ordering, or non-deterministic input.

## Step 1.5: Identify and falsify the load-bearing premise

After triage, before building the timeline, do this. It is the single most important step in this skill — nearly every wasted hour of debugging comes from skipping it.

A diagnosis is a tower of inferences. There is almost always one foundational claim that, if wrong, invalidates everything downstream. Name it. Falsify it. Don't build on it until you've checked it.

### 1. Name the load-bearing premise

Write a single sentence of the form: **"If [X] is false, my diagnosis is invalid."**

Examples:

| Direction the diagnosis is heading | Load-bearing premise |
|---|---|
| "the request times out before the response comes back" | the request actually takes longer than the timeout |
| "the model returns malformed JSON so parsing crashes" | the model's raw output is actually malformed (not valid JSON we mishandle) |
| "the second click fires before the first finishes, so state is stale" | the two handlers actually overlap in time |
| "the last commit broke the import path" | the path the code resolves at runtime actually differs from what's on disk |

If you can't name the premise in one sentence, the diagnosis isn't a diagnosis yet — it's a vibe. Stop and get more signal.

### 2. Identify the cheapest falsification check

The right check has the highest signal-per-second ratio. It's almost always one of:

- A single log line / print of the actual value (the real latency, the real payload, the real state)
- One `curl` / REPL call that exercises the path in isolation
- One source-code line you read in the installed dependency confirming what it does
- A back-of-envelope calculation against known constants — the math has to actually work, not just feel right
- A quick question to a teammate who already knows

Don't write a whole investigation harness for the premise. Don't add elaborate instrumentation. The check should take under 60 seconds; if it takes longer, you've picked the wrong check.

### 3. Run the check before writing more than one paragraph of analysis

This is the rate-limit. The worst failure mode is producing paragraphs of consequence-inferences while the load-bearing premise sits unchecked. Volume of analysis is not rigor — verification is rigor. The detail makes a diagnosis *feel* solid; only the check makes it solid. Verification before storytelling, every time.

### 4. Output the result explicitly

```
LOAD-BEARING PREMISE: [single sentence]
FALSIFICATION CHECK: [what you did, in one sentence]
RESULT: [what you found — one number or one phrase]
VERIFIED: yes / no / partial
```

### 5. If the check refutes the premise, restart triage

This is the win, not a setback. The whole point is to redirect early, before the wrong story is fully built. Do not paper over the gap. Do not rewrite the story to keep the premise alive. Take the new ground truth and re-enter Step 1.

**Hard rule: do not enter Step 2 until this step produces a `VERIFIED: yes` line.** If the cheapest check is genuinely unrunnable (some dependency behavior with no docs, no source, no way to test), ask the teammate to confirm the premise — don't silently assume it.

## Step 2: Build the event timeline

This is the core of the diagnosis. Trace the execution path that leads to the bug, building a timeline of what happens and when. **Write it down explicitly** — it forces root-cause thinking and prevents symptom-patching.

Format:
```
T1: [trigger — e.g. "user clicks Submit"]
T2: [system action — e.g. "POST /generate fires, creates a Job row"]
T3: [the thing that should happen — e.g. "worker picks up the Job and calls the model"]
T4: [the thing that actually happens — e.g. "client re-renders and fires a second POST before T3 runs"]
T5: [the failure — e.g. "two Jobs run on the same input, second one writes a partial result"]

ROOT CAUSE: T4 happens before T3 completes because [reason].
The fix should ensure [correct ordering / guard / constraint].
```

To build this timeline:
1. **Read the stacktrace** to identify the exact failure point.
2. **Read the source** around the failure — the function, its callers, its expected behavior.
3. **Trace backwards**: what calls this? What triggers that? Follow the chain to the user action or trigger.
4. **Trace forwards from the trigger**: what *should* happen, step by step? At which step does reality diverge?
5. **Check for concurrency**: parallel paths that interfere? Double-fired events, overlapping async calls, a request racing a background job?
6. **Check recent changes**: `git log` / `git diff` on the relevant files. At a hackathon the bug is very often in the last commit you made — start there.

### Use tools to fill gaps
- Timeline gap ("something happens between T2 and T4 I can't see")? Add a log line at that point and re-run, or grep the logs around that timestamp.
- LLM/model involved? Print the exact input sent and the exact raw output received — most "the model is wrong" bugs are actually "we sent it the wrong thing" or "we mishandled a fine response."
- Correlates with a change? `git diff` the suspect commit.

### Dependency behavior is unverified by default

Statements about how a library handles timeouts, how a framework caches, how a client pools connections, how an SDK serializes — these are all *unchecked* unless you have one of:

- A specific docs line with the claim
- A specific source line you've read in the installed package
- An experiment whose result you measured here

"It probably works like X" is not a fact. Mark every dependency-internals claim in your timeline with `(UNVERIFIED)` until one of the three is satisfied. If an `(UNVERIFIED)` claim is load-bearing, promote it back into Step 1.5 and check it before Step 3.

### Checkpoint: validate the timeline
Before naming a root cause, sanity-check the timeline against what you actually observed. Does every step have evidence (a log line, a stack frame, a value you printed), or are some steps just narrative glue? Glue steps are where wrong diagnoses hide — verify them or mark them `(UNVERIFIED)`.

## Step 3: Identify the root cause

With the timeline built, classify the root cause. Common patterns:

| Pattern | Example | Wrong fix | Right fix |
|---|---|---|---|
| **Ordering problem** | Work scheduled before its data is persisted | Add a retry/sleep | Move the scheduling after the persist |
| **Missing guard** | No dedup on a double-fired event | Retry on conflict | Idempotency key / guard the second entry |
| **Resource exhaustion** | OOM from an unbounded query, pool exhausted by fan-out | Bump the limit | Add real bounds (LIMIT, batch size, concurrency cap) |
| **Dependency behavior** | Model returns a wrapped/typed object that breaks `str()`; SDK needs a specific param | One-off workaround at the call site | Use the proper accessor/abstraction once, everywhere |
| **State gap** | Related state left stale after a transition | Filter it out in the UI | Fix the state transition at the source |
| **Wrong input, blamed output** | "Model output is garbage" | Post-process the garbage | Fix the prompt/payload you actually sent |
| **Stale checkout** | Works in your tree, breaks elsewhere | "Works on my machine" | Find the uncommitted/untracked dep the clean checkout lacks |

### Before naming the root cause: steel-man one alternative

When you have a leading hypothesis, the evidence almost always fits more than one story. Pick the strongest *alternative* that explains the same signal — not a strawman, the genuine best other explanation — and write it next to your leading hypothesis.

Examples:

| Observed signal | Leading hypothesis | Steel-manned alternative |
|---|---|---|
| Endpoint returns 500 intermittently | Race between two requests | One input shape hits an unhandled branch; it's data-dependent, not timing |
| "Start" logged but never "Done" | Crashed mid-run | The "Done" log is inside an `if` that doesn't fire on empty input |
| Broke right after a deploy/commit | That change introduced the bug | The change exposed a pre-existing bug that earlier state happened to hide |

If both fit equally well, **identify a disambiguating check** — one observation whose result distinguishes them — and run it before naming the root cause. If it rules one out, name the survivor. If it's inconclusive or unrunnable, state both hypotheses in the output and carry both into the fix. Do not pick one and present it as certain.

### State the root cause

After steel-manning, **state it in one sentence**: "The bug occurs because [X] happens [before/after/without] [Y], and the code assumes [Z]."

### Self-check before publishing

Imagine the most skeptical teammate reading your diagnosis. What's the single cheapest question that would expose a missing verification?

- "Did you actually print the latency/payload/state, or are you assuming it?"
- "Does the dependency actually do that, or are you inferring?"
- "What's the steel-manned alternative, and what disambiguates it?"
- "If your load-bearing premise were false, what's the next thing that fails?"
- "Does this math actually work out, or just feel like it should?"

If you can't pre-empt the question with verified data, the diagnosis isn't ready. Run the check first. A 60-second verification is far cheaper than shipping a wrong fix mid-hackathon.

## Step 4: Propose a local reproduction test

Write a concrete test that reproduces the bug locally. Two purposes:
1. It confirms your diagnosis (if the test doesn't fail, your understanding is wrong).
2. It becomes the regression test for the fix.

```python
# Template — adapt to the specific bug
def test_<descriptive_name>():
    """Reproduces [bug description].

    Root cause: [one-sentence root cause from Step 3].
    """
    # Setup: create the preconditions
    # Action: trigger the code path that fails
    # Assert: verify the failure (FAILS before the fix, PASSES after)
    ...
```

Guidelines:
- Use the project's test patterns (pytest by default here).
- Mock external calls (model APIs, third-party HTTP) but keep *your* logic real — the bug is in your code.
- Race condition? Simulate the ordering explicitly — set up the exact state that exists when the race triggers, rather than hoping to hit it by chance.
- Needs specific data (a malformed payload, an empty list, a huge input)? Construct it in setup.

## Step 5: Hand off the fix

Present findings as a tight handoff so the fix can start immediately:

### Diagnosis summary
- **Problem**: [1-2 sentences]
- **Impact**: [what's broken and how often — "every Submit click double-runs" or "only when the input list is empty." Be concrete.]
- **Root cause**: [1 sentence — the actual cause, not the symptom]
- **Verification**: [the load-bearing premise, the falsification check, and the result, in one or two lines. Be specific: "printed the actual response time — 0.2s, well under the 30s timeout I assumed." Not "verified it works."]
- **Steel-manned alternative considered**: [the strongest other explanation + the disambiguating check, or `inconclusive`/`unrunnable`. If two still fit, list both.]
- **Event timeline**: [the timeline from Step 2]
- **Affected code**: [file paths and line numbers]
- **Blast radius**: [what else touches this — callers, parallel paths, related state]

### Reproduction test
The test from Step 4.

### Recommended fix direction
State the fix at a high level (the *shape* of the change), not the code:

```
Fix [root cause]. The bug is in [file:function].
Currently [what happens]. Should [what should happen instead].
See reproduction test in [test file].
```

**Do not write the code fix here.** Your job is diagnosis. Diagnose, hand off the shape, then implement deliberately — that's how you break the "see error → patch symptom → three new bugs" cycle that wrecks hackathon demos.
