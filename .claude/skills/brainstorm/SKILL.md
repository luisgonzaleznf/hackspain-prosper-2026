---
name: brainstorm
description: Pick + sharpen the hackathon idea with demo-wow as a first-class criterion, then FREEZE the shared contracts (types, API shapes, data schema, file ownership) and produce the parallel-safe slice plan that orchestrate dispatches.
argument-hint: "<hackathon theme / rough idea / problem statement>"
---

## Context

You are the architect for a hackathon build. Time is the binding constraint, judges decide in minutes, and there is NO CI/Greptile/review safety net — so the plan itself has to be the safety net. Your two jobs:

1. **Pick + sharpen the idea** — turn a vague theme into one buildable app, with *demo-wow* as a first-class ranking criterion alongside feasibility.
2. **Freeze the contracts and split the work** — produce the FROZEN shared rules (types, API shapes, data schema, file ownership) plus an ordered list of build slices tagged **parallel-safe** vs **serial**, so the `orchestrate` skill can hand them out to parallel workers who never collide.

**Input**: $ARGUMENTS (the theme, a rough idea, or a problem statement)

This skill OWNS the contract freeze. `orchestrate`'s mandatory first move is to confirm the contracts are frozen — if you don't freeze them here, parallel builders WILL collide and the build burns its time budget on merge conflicts.

## Step 0: Set up step tracking

Before starting, create a task list with one task per step using `TaskCreate`. This is not optional — it's easy to skip a step (especially Step 1b subagent fan-out, Step 2 blast-radius/coupling, or Step 4 the contract freeze — the three most commonly dropped). The task list keeps you honest.

Create these tasks, in this order:

1. Understand the theme + constraints (Step 1)
2. Classify the build type (Step 1a)
3. Fan out 3 subagents for independent idea/approach candidates (Step 1b)
4. Rank candidates on demo-wow + feasibility (Step 1c)
5. Map the blast radius / coupling surface of the chosen idea (Step 2)
6. Think like an architect — where does each piece live (Step 3)
7. FREEZE the shared contracts (Step 4)
8. Cut the parallel-safe slice plan (Step 5)
9. Produce the brainstorm doc (Step 6)
10. Resolve open questions (Step 7) — mark completed immediately if there are none
11. Next action (Step 8)

Mark each task `in_progress` when you start and `completed` when you finish. Do not skip ahead. If you're about to produce the slice plan without a `completed` task for Step 1b (fan-out) and Step 4 (contract freeze), stop — go back and do them. The whole parallel build depends on those two.

## Step 1: Understand the theme + constraints

The hackathon domain is unknown until it starts. Based on `$ARGUMENTS`:

1. **Pin the hard constraints** — theme/prompt, judging criteria (read them literally; build toward what's scored), time budget, team size, and any required tech or APIs.
2. **Pin the locked stack facts** — local-only (no live URL, the deliverable is a recorded demo), Python-first (uv + ruff + mypy + pytest, FastAPI backends), Anthropic-primary LLM calls through `lib/ai.py`. A Vite+React UI is opt-in, only for polish-critical demos.
3. **Find the wow.** What's the single moment that makes a judge lean in? AI doing something that looks impossible-by-hand, a live transformation, a surprising result. Name it early — it shapes the idea.
4. **Find the smallest real thing.** What is the minimum app that actually works end-to-end and hits that wow? Everything past it is cut.

If the theme is too vague to commit to an idea, ask 1-2 clarifying questions before proceeding — but bias toward picking and moving; a hackathon rewards a committed plan over a perfect one.

## Step 1a: Classify the build type

Classify what you're building — it sets the framing for everything downstream:

- **Greenfield app** — net-new from an empty repo (the hackathon default). Primary framing is **Goal** (who's the judge/user persona in the demo + what they see happen). This is almost always the case.
- **Feature on top of an existing base** — you're extending a starter or a prior project. Primary framing is **Goal** + the integration seam with what's already there.
- **Integration / glue** — the wow is wiring two systems together (an API, a model, a data source). Primary framing is **Goal** + the contract at the boundary.

Pick one explicitly. For every type, articulate:
- **Who** the demo is for (the judge persona / the user the demo embodies — not "users" in the abstract).
- **What they see happen** in the golden demo path — the concrete sequence of on-screen moments, ending on the wow.

If you can't name the demo persona or the on-screen golden path, the idea isn't sharp enough yet — sharpen it before proceeding.

## Step 1b: Fan out 3 subagents to propose independent idea/approach candidates

Before your own deep analysis, spin up 3 general-purpose subagents in parallel, each to propose a complete idea-and-approach candidate. Do not skip this — your first instinct is not the benchmark, and at a hackathon the difference between a forgettable and a winning idea is exactly the kind of thing independent exploration surfaces.

Three independent explorations beat one **only when the prompts are neutral**. If you bias the prompt toward your favored idea or your suspected architecture, all three inherit the same blind spot and convergence becomes bias amplification rather than independent agreement. The de-bias checklist below is mandatory.

Why fan out at all:
- Surface ideas/approaches your defaults would've missed — especially higher-wow framings of the same theme.
- **Genuine** convergence (2+ neutral-prompted agents landing on the same idea or architecture) is a strong signal it's the right call.
- Divergence surfaces non-obvious trade-offs (wow vs feasibility) worth deciding deliberately.
- Cross-candidate comparison gives a defensible demo-wow + feasibility ranking.

### De-bias checklist — run BEFORE writing the subagent prompt

Write the prompt, then read it against this checklist. Every "yes" is a contamination source — strike it before sending.

1. **Did you name the specific app idea you're leaning toward?** → strike. Describe the theme, the judging criteria, and the constraints — let the subagent pick the idea. If the prompt already decides the app, you're not exploring, you're confirming.
2. **Did you name a specific architecture, framework, or file layout?** → strike for the idea-generation pass. The constraints (local-only, Python-first, FastAPI, `lib/ai.py`) are fair to state as immutable facts; a specific module layout is not — it collapses the solution space.
3. **Did you describe the theme in your own words after step 1a?** → demote. Your step-1a framing IS a frame. Include the raw `$ARGUMENTS` verbatim; do not summarize it through your classification.
4. **Did you use phrases like "simple," "small," or "easy to build"?** → strike. Those bias away from the high-wow idea before feasibility has even been weighed. Wow and feasibility get ranked together in Step 1c, not pre-filtered in the prompt.
5. **Could a sharp builder reading the prompt cold propose a genuinely different app than yours?** → if no, the prompt is biased. Rewrite until yes.

If you can't pass the checklist, you don't understand the theme well enough yet — go back to Step 1.

### How to run

Send a SINGLE message containing 3 parallel `Agent` tool calls with `subagent_type: "general-purpose"`. Identical prompt to all 3. They don't see each other — that's the point.

Each subagent prompt should include:
- The original `$ARGUMENTS` **verbatim** (do not paraphrase through your step-1a framing).
- The **build type** classification (greenfield / feature / integration) — allowed because it sets expectations, not a fix layer.
- The **judging criteria** verbatim if you have them — the candidates should optimize toward what's actually scored.
- **Constraints** (not examples): the locked stack facts as immutable rules the answer must respect — local-only, recorded-demo deliverable, Python-first (uv/ruff/mypy/pytest, FastAPI), Anthropic-primary via `lib/ai.py`, time budget, team size. Constraints don't bias; a prescribed app idea or module layout does.
- Instruction: **propose an idea + an approach, do not write or edit code.**
- **Required: enumerate idea alternatives.** Before recommending one, the subagent must list 2-3 *distinct* app ideas it considered, with one sentence each on the demo-wow and the main feasibility risk, and why it ruled the others out. This forces explicit idea-traversal rather than latching onto the first thing.
- Explicit asks for:
  1. **Idea alternatives considered** (2-3, each with its wow + feasibility risk + one-sentence rejection reason).
  2. **Recommended idea** — the survivor, in 2-3 sentences: who the demo is for and the on-screen golden path ending on the wow.
  3. **The single demo-wow moment**, stated in one sentence.
  4. **How AI is load-bearing** — what the LLM does that makes the app impossible/unimpressive without it. If AI is decorative, say so honestly.
  5. **Rough architecture** — the major pieces and how they talk (endpoints/components and the data that flows between them), enough to see the natural seams to split on.
  6. **Build slices** — a first cut at how the work divides into independent chunks, and which chunks could run in parallel vs which must be serial.
  7. **Top 2-3 risks** — the things most likely to eat the time budget or kill the demo.
- Explicit instruction: **optimize for demo-wow within feasibility.** Pick the idea that produces the strongest judge reaction that the team can actually finish and demo in the time budget. A jaw-dropping idea you can't finish scores zero; a boring idea you finish early is a missed opportunity. Rank on both axes — Step 1c does the final weighing.
- Length cap: under 600 words total.

### How to synthesize (after all 3 return)

1. **Extract** — for each candidate, pull out: the idea, the wow moment, how AI is load-bearing, the rough architecture, the slice cut, and the top risk.
2. **Deduplicate** — if two candidates are functionally the same idea + same architecture, merge them and note the convergence.
3. **Disambiguate** — if two candidates share the same idea but differ in architecture/slicing, call out the diff explicitly and carry both into the Step 1c ranking.
4. **Carry all survivors into Step 1c** for ranking. Don't pick the winner here — that's the next step, where wow and feasibility get weighed together.
5. **Flag showstoppers** — if a candidate has a fatal flaw visible now (can't run local-only, the wow needs paid hosting/a live URL, AI is purely decorative, can't finish in the budget), drop it and explain why.

### Convergence-vs-amplification check

If 2+ subagents converged on the same idea or architecture, do not skip this. Convergence-as-signal only works if the prompts were neutral; a biased prompt makes convergence the bias multiplied by 3.

1. **Re-read your original subagent prompt** against the de-bias checklist. Did any item slip through?
2. **If a checklist item slipped through**: the convergence is suspect. Run a 4th subagent with a deliberately neutralized prompt — theme + criteria + constraints only, no leaned-toward idea, no prescribed architecture. Compare its idea/architecture against the converged trio.
3. **If the 4th converges** → real convergence, high confidence, proceed.
4. **If the 4th proposes a genuinely different idea/architecture** → your framing was biased and the 4th is the de-biased candidate. Carry both into Step 1c; don't silently keep the trio's answer.
5. **If no checklist item slipped through** → real convergence, proceed with high confidence.

### Degenerate cases

- **All 3 converged on one idea** → run the convergence check above, then proceed with high confidence.
- **One subagent failed / returned garbage** → mark it failed, synthesize with the remaining 2. Don't retry unless you're at 0 usable candidates.
- **All 3 diverged into 3 distinct ideas** → rank all 3 in Step 1c and put the trade-off (wow vs feasibility) in front of the user; the theme may admit several strong directions and the choice is theirs.

## Step 1c: Rank candidates on demo-wow + feasibility

Take the survivors from Step 1b and rank them on two axes, weighed together:

1. **Demo-wow (primary)** — how strong is the judge reaction in the first 60 seconds? Does it hit something that looks impossible-by-hand? Is the wow front-loaded (judges decide in minutes)? Is AI visibly load-bearing, not decorative?
2. **Feasibility within the budget (gate)** — can the team actually finish a working version and record the golden-path demo in the time available, local-only? This is a gate, not a tie-breaker: an idea that can't be finished is disqualified no matter how high the wow.

Further tie-breakers, in order: fewer external dependencies to wire → fewer moving parts in the golden path → more of the build naturally parallelizes (more independent slices = more throughput with the team you have).

Recommend one idea unambiguously. State why it wins on wow-within-feasibility. If you're recommending a lower-wow idea, name the feasibility showstopper that knocked out the higher-wow one. Final call is the user's — but make a clear recommendation.

## Step 2: Map the blast radius / coupling surface

Before freezing contracts, understand how the pieces of the chosen idea couple — because the coupling surface is exactly what determines which slices are parallel-safe and which are serial. The expensive failure here isn't a production bug; it's two builders editing the same file or assuming different shapes for the same payload, and discovering it at integration time when there's no clock left.

Walk the chosen idea and identify:

### Shared state and shared files
- **What data does more than one piece read or write?** The thing two slices both touch is the thing whose shape MUST be frozen before either starts (that's the Step 4 contract).
- **What files would two builders naturally both want to edit?** A shared `models.py`, a shared `types.py`, a router that every endpoint registers into, a single `App.tsx`. These are collision magnets — either assign a single owner or split the file so each slice owns its own piece.

### The seams between pieces
- **Every boundary where one piece calls another is a contract.** Backend↔frontend (the API shape), backend↔LLM (the `lib/ai.py` call signature + the expected output schema), backend↔data (the schema/seed shape), component↔component (shared props/types). Each seam that two slices straddle must be frozen before those slices fork.

### Order dependencies
- **What must exist before something else can be built or tested?** The data schema and seed data usually come first (everything reads them). The `lib/ai.py` wrapper and the shared types usually come first (everything imports them). Slices that depend on a not-yet-built piece are **serial**, gated behind it; slices that only depend on already-frozen contracts are **parallel-safe**.

### The golden demo path
- **Trace the exact end-to-end path the demo walks.** Every piece on that path is load-bearing and must be real, not stubbed, by demo time. Pieces off the path are cut candidates. This trace also tells you the integration order: build the spine of the golden path first, hang the rest off it.

The output of this step is the raw material for Steps 4 and 5: the list of shared shapes to freeze, the list of collision-prone files to assign owners for, and the dependency order that separates parallel-safe slices from serial ones.

## Step 3: Think like an architect — where does each piece live

Apply a lightweight architectural-fit pass, scoped to a hackathon (no over-engineering — the right amount of structure is the minimum that lets the team build in parallel without colliding):

### Where does each responsibility live?
- One clear home per responsibility. Endpoints in the API layer, model calls behind `lib/ai.py`, data access in one place, UI in components. Don't let LLM calls leak into route handlers or DB access leak into UI.
- Keep the dependency direction clean: shared types and the `lib/ai.py` wrapper sit at the bottom (everything imports them, they import nothing app-specific). Build them first; freeze their interfaces.
- Functions over classes when there's no real state. Don't introduce a model/migration/abstraction you won't use in the demo.

### What's the right data model for a demo?
- **In-memory or SQLite by default.** A hackathon demo runs local with deterministic seed data — reach for the simplest store that survives the golden path. Only add a real DB if the wow genuinely needs it.
- Seed data is part of the contract: the demo must be reproducible from a clean checkout with a deterministic seed. Decide the seed shape here.
- Right-size everything to the demo. No speculative fields, no future-proofing.

### What's the simplest thing that hits the wow?
- Cut ruthlessly to the golden path. Every piece not on the demo path is a cut candidate.
- Reuse the kit's primitives (`lib/ai.py`, shared types) rather than reinventing.
- Prefer the boring, known-working approach for everything that isn't the wow — spend the novelty budget only on the wow itself.

### LLM-specific (the load-bearing part)
- **All model calls go through `lib/ai.py`** — never call a vendor SDK directly from app code. Freeze the wrapper's call signature and its expected output shape as a contract.
- **Treat model output as untrusted** — parse defensively (`.get()` with defaults, tolerate missing/extra fields). LLMs don't guarantee schema conformance, and a demo that crashes on a malformed completion is a dead demo.
- **Use the right model for the job and don't invent ids** — `claude-opus-4-8` for hard reasoning, `claude-sonnet-4-6` for the default workhorse, `claude-haiku-4-5` for fast/cheap calls. Pin the model id in the contract so slices agree.
- **Make the AI's work visible in the demo.** If the wow is AI, the golden path must show it happening (stream it, show the reasoning, show before/after) — invisible AI reads as no AI to a judge.

## Step 4: FREEZE the shared contracts

This is the load-bearing step and the reason this skill exists. Everything that two or more slices touch gets its shape nailed down HERE, before any slice forks. Once frozen, these are gospel — `orchestrate` hands them to every worker and no worker may change a frozen contract unilaterally (a contract change mid-build must come back through here and re-sync every affected slice).

Produce all five of these explicitly:

### 4a. Shared types / data shapes
The canonical shape of every payload that crosses a seam — request/response bodies, the LLM output schema, internal records two slices share. Show them as skeletons (field names + types), no commentary:
```python
class Recipe(BaseModel):
    id: str
    title: str
    steps: list[str]
    ai_score: float
```
Name the one file these live in (e.g. `lib/types.py` / `shared/types.ts`) and declare it **frozen, owned by no single slice — append-only by agreement**.

### 4b. API shapes
Every endpoint on the golden path: method + path + request shape + response shape + status codes. This is the backend↔frontend contract; freeze it so the frontend can build against it before the backend is done (and vice versa):
```
POST /generate   req: {prompt: str}              resp: 200 {recipe: Recipe}
GET  /recipes    req: -                           resp: 200 {recipes: list[Recipe]}
```

### 4c. Data schema + seed shape
The store (in-memory / SQLite / etc.), the table/collection shapes, and the **deterministic seed data** the demo runs on. The seed is part of the contract because the golden path must be reproducible from a clean checkout. Name the seed file/command.

### 4d. The `lib/ai.py` contract
The model-call wrapper's signature and the expected output shape every slice relies on, plus the pinned model id(s). Freeze it so slices that call the model all agree on the interface:
```python
def complete(prompt: str, *, model: str = "claude-sonnet-4-6", schema: type[BaseModel] | None = None) -> ...:
    ...
```

### 4e. File ownership map
The single most important collision-prevention artifact. For every file/directory, name exactly one owning slice (or mark it shared/frozen). Two slices may NEVER own the same file. Format as a table:

| Path | Owner (slice) | Status |
|------|---------------|--------|
| `lib/types.py` | shared | frozen, append-only by agreement |
| `lib/ai.py` | shared | frozen |
| `api/routes/generate.py` | Slice A | owned |
| `api/routes/recipes.py` | Slice B | owned |
| `web/src/components/RecipeCard.tsx` | Slice C | owned |
| `seed.py` | Slice A | owned |

If two slices both need to touch one file (e.g. a router that registers every route), either (a) give the file a single owner and have other slices request additions through them, or (b) split it so each slice owns its own fragment (per-feature route modules, a components folder per slice). **A shared-write file with no single owner is the #1 cause of parallel-build collisions — eliminate every one before dispatch.**

State explicitly at the end of this step: **"Contracts FROZEN."** This is the literal phrase `orchestrate` looks for before it dispatches.

## Step 5: Cut the parallel-safe slice plan

Now turn the frozen contracts into the ordered list of build slices that `orchestrate` dispatches. A slice is a chunk of work small enough for one worker to finish independently, that owns a non-overlapping set of files (per the Step 4e map) and depends only on already-frozen contracts (or on earlier slices, if serial).

For each slice, specify:
- **Name + one-line goal** — what it delivers.
- **Files it owns** — from the ownership map; must not overlap any other slice.
- **Contracts it depends on** — which frozen shapes/endpoints it builds against.
- **Parallel-safe or serial** — and if serial, what it's gated behind (e.g. "serial — needs the data schema + seed from Slice 0").
- **Definition of done** — the runnable check that proves it works (an endpoint returns the right shape, a component renders the seed, a test passes). This is what `verify` will actually run.

### Sequencing rules
- **Foundation slice(s) go first and are serial gates.** The shared types, `lib/ai.py`, and the data schema + seed are imported/read by everything — build and freeze them before parallel work forks. Mark them **serial (must complete first)**.
- **Then the parallel-safe slices fork.** Each owns its files and builds against frozen contracts. These run concurrently.
- **The integration / golden-path-wiring slice is serial and last** — it stitches the parallel pieces into the end-to-end demo path.

### The parallelization threshold
**Parallelize only past ~4 independent slices. Below that, go serial.** The coordination overhead of worktrees + dispatch + merge isn't worth it for 2-3 slices — a single worker building serially is faster and collision-free. If the chosen idea naturally splits into 4+ genuinely independent slices, lay out the parallel plan. If it's 3 or fewer, say so explicitly and recommend a serial build: "3 slices — below the parallelization threshold, build serially in this order." Don't manufacture fake parallelism to hit the threshold.

### Output of this step
An **ordered list** of slices, each tagged parallel-safe vs serial, with owned files and definition-of-done. This list IS what `orchestrate` consumes. The order encodes the dependency graph: serial foundation first, parallel middle, serial integration last.

## Step 6: Produce the brainstorm doc

Write the result conversationally — share your reasoning, think out loud — but the contract and slice sections must be precise and copy-pasteable, because downstream workers build against them verbatim.

### Hard rules for the output

The brainstorm is an *implementer's brief* and the *frozen source of truth* for a parallel build. Workers treat it as gospel. So:

1. **Code blocks in the Approach/reasoning sections are skeletons, not source.** Strip everything not load-bearing for understanding shape — no docstrings, no inline comments, no `# explanation:` lines. Show the shape; put the reasoning in the prose around the block.
2. **The contract sections (Step 4) ARE the source shapes** — those skeletons are meant to be copied into real files verbatim, so they must be exactly right: real field names, real types, pinned model ids. This is the one place precision beats brevity.
3. **All rationale is prose, here, in this doc** — never as a docstring or comment inside a code block. "We chose X because Y," trade-offs, the wow argument, design lineage all live in the prose sections and (later) in `SUBMISSION.md`.
4. **The "Watch out for" section flags conditions, not documentation tasks.** Phrase pitfalls as architectural/behavioral conditions ("the LLM output may omit `steps` — parse defensively"), never as "add a comment explaining X."
5. **Definitions of done are runnable checks, not prose.** List them as the literal thing `verify` runs (a curl, a test name, a UI action + expected on-screen result), not an essay.

Structure your output as:

### Build type
One line: greenfield / feature / integration. Matches Step 1a.

### The idea (Goal)
The recommended idea: who the demo is for (the judge/user persona), and the on-screen golden path ending on the wow. Name the single demo-wow moment in one sentence. Be concrete — "the judge types a fridge's worth of ingredients and watches a full recipe stream out, scored and plated" beats "an AI recipe app."

### Why this idea (wow + feasibility)
Why this beats the alternatives: the wow argument (the first-60-seconds judge reaction, why it looks impossible-by-hand) and the feasibility argument (why it finishes in the budget, local-only). If you picked a lower-wow idea, name the showstopper that knocked out the higher-wow one.

### How AI is load-bearing
What the model does that the app is impossible/unimpressive without — the thing `pitch`'s SUBMISSION.md will lead with. If AI is only decorative, say so honestly and reconsider the idea.

### Idea candidates
The 2-3 ideas from Step 1b/1c, ranked on wow-within-feasibility:
1. **[RECOMMENDED]** `<name>` — wow: <one line>. feasibility: <one line>. why it wins.
2. `<name>` — wow / feasibility / why it lost.
3. `<name>` — wow / feasibility / why it lost.
If all 3 converged, note it ("all 3 agents landed here — high confidence") and skip the ranking.

### Approach
2-4 paragraphs on how the app is built: the major pieces, how they talk, the patterns to follow, what to reuse from the kit (`lib/ai.py`, shared types). Skeletons only in any code block (Hard rule #1).

### FROZEN contracts
The deliverable. Reproduce all five sub-artifacts from Step 4 exactly:
- **4a. Shared types** — the type skeletons + the file they live in.
- **4b. API shapes** — every golden-path endpoint.
- **4c. Data schema + seed** — store choice, shapes, deterministic seed + its command.
- **4d. `lib/ai.py` contract** — signature + pinned model id(s).
- **4e. File ownership map** — the table; every file owned by exactly one slice or marked shared/frozen.

End with the literal line: **Contracts FROZEN.**

### Slice plan (ordered)
The ordered list from Step 5. For each slice: name + goal, owned files, contracts depended on, **parallel-safe / serial** (+ what serial slices are gated behind), and the runnable definition of done. State the parallelization verdict explicitly: either "N independent slices — parallelize" or "≤3 slices — below threshold, build serially in this order."

### Coupling / blast radius
What couples to what (from Step 2): shared shapes, collision-prone files and how you de-collided them (single owner or split), and the dependency order. Short if the surface is small.

### The golden demo path
The exact end-to-end sequence the demo walks, step by step, ending on the wow. This is what `demo` records and `verify` walks on a clean checkout. Name the seed data it runs on.

### Watch out for
Specific pitfalls for THIS build — coupling risks, the parts of the golden path most likely to break, LLM output fragility, the time-budget traps. Phrase each as a condition (Hard rule #4), never as "add a comment."

### Open questions
Things to resolve before dispatch — anything left ambiguous in the idea, the contracts, or the slice split. Be honest about uncertainty, firm on the contract freeze (an unfrozen contract is not an "open question to figure out during implementation" — it's a blocker).

## Step 7: Resolve open questions

**HARD STOP before proceeding.** If the brainstorm's "Open questions" section has any items, resolve them before moving on — a parallel build cannot start with an unfrozen contract. Use `AskUserQuestion` to present them and get answers.

- Present open questions as a numbered list.
- If the user answers some but not all, re-present only the unresolved ones.
- Loop until every question is either **answered** (fold the answer into the relevant section — especially any contract it affects) or **explicitly deferred** by the user.
- Anything touching a contract (4a-4e) or the slice split CANNOT be deferred — it must be answered before dispatch, or the parallel build is unsafe. Deferral is only acceptable for off-golden-path nice-to-haves.
- Once resolved, update the doc: fold answers into their sections, re-confirm **Contracts FROZEN**, and rename the section to "Deferred decisions" if only off-path deferrals remain, or remove it entirely.

If there are no open questions, skip this step.

## Step 8: Next action

Once the contracts are frozen and the slice plan is set, use `AskUserQuestion` to ask what to do next:

> Plan is ready and contracts are FROZEN. Would you like to:
> 1. **Copy to clipboard** — copy the full brainstorm (contracts + slice plan) so you can paste it into the orchestrate session or worker prompts.
> 2. **Hand off to orchestrate** — start `/orchestrate` with this slice plan: it confirms the contracts are frozen, then dispatches the parallel-safe slices to workers (background subagents in their own git worktrees, and/or separate terminal sessions) while keeping the main session lean.
> 3. **Build serially myself** — if the plan came out ≤3 slices (below the parallelization threshold), skip orchestrate and build the slices in order yourself with `/ship` (a.k.a. quick-pr) per slice.

Then execute whichever option the user chooses. The frozen contracts + ordered slice plan are the payload that flows forward — carry them verbatim into whatever runs next (orchestrate's dispatch or the first serial slice), since the downstream session can't see this conversation.
