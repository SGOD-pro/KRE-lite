# PROMPTS.md — Copy-Paste Prompts for Each Session

Use these with Cline, Roo Code, Claude Code, or whatever agent you're
driving. Paste as-is, fill in the [BRACKETS]. Every prompt tells the
agent to read the doc set first — that's not filler, it's how the
agent stays inside DECISION.md and BOUNDARIES.md instead of drifting.

---

## PROMPT 0 — First Session, Phase 0 Setup

```
Read, in this order: PROJECT.md, ARCHITECTURE.md, DECISION.md,
BOUNDARIES.md, PHASES.md (Phase 0 section only for now), MEMORY.md.

You are starting Phase 0 of this build. Do exactly what Phase 0 in
PHASES.md specifies — nothing more. In particular:

- Scaffold the repo structure matching the module map in
  ARCHITECTURE.md.
- Set up docker-compose with a FastAPI hello-world app and a /health
  endpoint.
- Set up the GitHub Actions workflow file (see ci-cd/workflow.yml if
  provided, otherwise a minimal one that installs deps and runs
  `pytest --collect-only` so it's green from commit one).
- Do NOT write ingestion, retrieval, or generation code yet — that's
  Phase 1+.
- Do NOT add any dependency, service, or infrastructure not listed
  in ARCHITECTURE.md's tech stack. If you think something's missing,
  say so and ask before adding it — don't just add it.

Before you finish this session, update MEMORY.md: check off Phase 0
items as they're actually done (not before), log any decisions you
made, and write a one-to-two-sentence "next session should start by"
note.

Commit frequently and with clear messages as you go — do not do one
giant end-of-session commit.
```

---

## PROMPT 1 — Phase 1, Ingestion + Retrieval

```
Read MEMORY.md first to see current state. Then read PHASES.md
(Phase 1 section) and ARCHITECTURE.md's module map for ingest/ and
query/ retrieval pieces.

Build Phase 1 exactly as specified:
- chunker.py: split the demo document set by page + heading. Every
  chunk MUST have non-null page_number and section_title
  (DECISION.md Rule 7) — if you can't reliably detect headings in a
  given PDF, fall back to "Untitled section, page N", never null.
- embed_service.py: BGE-small-en-v1.5 via ONNX, running locally, no
  external API call for this step.
- store.py: Chroma (or sqlite-vec if you hit friction with Chroma —
  log that decision in MEMORY.md if you switch).
- bm25_retriever.py and vector_retriever.py per the retrieval flow
  in ARCHITECTURE.md.
- POST /ingest per API.md's contract exactly — including the error
  cases (400 unsupported type, 422 unparseable/no-text-extracted).

Do not build the LLM call or citation verifier yet — that's Phase 2.

Write the tests listed under "Ingestion Tests" and "Retrieval Sanity
Tests" in RULES.md as you build, not after. Run them before
declaring Phase 1 done.

Update MEMORY.md before ending: phase checklist, decisions, test
status, known issues, next-session note.
```

---

## PROMPT 2 — Phase 2, Generation + Citation Verifier (the core of
## the whole project — take this one slowly)

```
Read MEMORY.md first. Then re-read ARCHITECTURE.md's "Citation
Verifier — Design Detail" section and DECISION.md rules 1-6 and 9
carefully — this phase is what makes the entire product's claim
true or false. Do not rush it to get to the frontend sooner.

Build, in this order:
1. llm_service.py — single call, forces structured JSON output per
   the schema in API.md's "Internal Contract" section. Use NVIDIA
   Build (build.nvidia.com) as the provider; if it's rate-limited or
   unavailable, fall back to OpenRouter — this should be a config
   value, not two separate code paths.
2. citation_verifier.py — deterministic fuzzy-match verification,
   exactly as described in ARCHITECTURE.md. This is NOT an LLM call.
   Write its unit tests FIRST (RULES.md "Citation Verifier — Unit
   Tests" section) using hand-crafted fake LLM outputs, before wiring
   it into the full pipeline — that way you know the verifier itself
   is correct before you're debugging it inside a live pipeline.
3. planner.py — wires retrieve -> generate -> verify -> respond.
4. POST /query per API.md's contract, including the exact refusal
   response shape.

Then: use the adversarial-refusal-test-generator skill (AGENT.md) to
produce 15-20 adversarial "should refuse" questions against the demo
document set, covering all four categories in RULES.md (adjacent-but-
absent, wrong entity swap, out-of-corpus, leading questions). Run the
full pipeline against them. Target: 100% refuse correctly. If it's
not 100%, that's a blocking bug — tell me the failure cases
specifically, don't just report a percentage and move on.

Only attempt rerank_service.py (NVIDIA Build rerank) after all of the
above is solid AND you have hours to spare before hour 22 of the
overall build (see PHASES.md). If you're past that point, skip it and
log the decision in MEMORY.md.

Update MEMORY.md before ending: phase checklist, decisions, the
adversarial test set pass rate specifically (not just "tests
passing"), known issues, next-session note.
```

---

## PROMPT 3 — Phase 3, Frontend

```
Read MEMORY.md first. Then read UI-UX.md in full and API.md's
response shapes (answered vs. refused).

Build the two-pane interface exactly as specified in UI-UX.md's
component list — do not add components not on that list (check
UI-UX.md's "Explicitly Cut From UI Scope" section before adding
anything you think would be nice).

Key requirement: the refusal state must look distinctly different
from an error state and different from an answer state — it's a
correct behavior, not a failure, and the UI should communicate that
at a glance.

Write the Playwright smoke tests from RULES.md's "End-to-End" section
(see also playwright/citation-flow.spec.ts if already scaffolded).

Update MEMORY.md before ending.
```

---

## PROMPT 4 — Phase 4, Polish + Validation (see PROMPT-VALIDATE below
## for the full end-of-build check)

```
Read MEMORY.md first. Confirm Phase 1-3 checklist items are actually
checked off with passing tests, not just "looked right."

Do PHASES.md's Phase 4 deliverables: README with one-command setup,
demo script, AGENTS_AND_SKILLS.md finalized, CI green on the actual
final commit.

Then run the full validation prompt (PROMPT-VALIDATE below) before
declaring the build done.
```

---

## PROMPT-RESUME — Use This Any Time You're Starting a New Session
## Mid-Build (use instead of 0-4 above once you're not sure exactly
## where you left off)

```
Read MEMORY.md in full before doing anything else. Based on its
"Current Status," "Phase Checklist," and "Next Session Should Start
By" sections, tell me in one paragraph: what phase we're actually in,
what's the very next concrete task, and whether any "Known Issues" in
MEMORY.md are blocking that task. Wait for my confirmation before
writing any code.
```

---

## PROMPT-VALIDATE — End-of-Build Validation Against RULES.md,
## PHASES.md, and BOUNDARIES.md

```
Read RULES.md, PHASES.md, and BOUNDARIES.md in full. Then do the
following, in order, and report results for each explicitly — don't
summarize, list every item:

1. Run the full test suite (pytest + Playwright). Report pass/fail
   per test file, not just an aggregate.
2. Specifically report the adversarial "should refuse" set pass rate
   as a fraction (e.g. "18/18"), not a percentage rounded off. If
   it's not 100%, list the exact questions that failed and what the
   system answered instead of refusing.
3. Go through PHASES.md phase by phase and confirm each phase's exit
   criteria are actually met, citing the specific test or manual
   check that proves it. Do not mark a phase's exit criteria "met"
   without pointing to evidence.
4. Go through BOUNDARIES.md line by line and confirm nothing on that
   list snuck into the repo during the build (check for: cloud
   deploy config beyond an optional documented stretch step, any
   OKF/PageIndex/graph code, any second LLM call, auth/multi-tenancy
   code, multi-turn memory, clustering/queue/approval-workflow code
   left over from an earlier track discussion).
5. Confirm all five hackathon non-negotiables are present in the
   repo: architecture doc, agent rules file (AGENT.md), working code
   that runs via docker-compose, a documented custom agent + skill
   (AGENTS_AND_SKILLS.md), a green CI/CD pipeline on the latest
   commit.

Update MEMORY.md's "Test Status" section with the final numbers from
this validation pass. If anything failed, do not fix it silently as
part of this same prompt — report it first, then I'll tell you
whether to fix it now or note it as a known limitation for the demo.
```
