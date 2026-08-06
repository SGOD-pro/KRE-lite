# AGENT.md — Agent Rules / Constitution

This file satisfies hackathon non-negotiable #2 (agent rules file)
and documents our custom agent, satisfying non-negotiable #4
alongside AGENTS_AND_SKILLS.md.

## Custom Agent: `citation-verifier-agent`

Not an LLM-based agent — a deterministic verification agent that sits
between the LLM's output and the user. This is the project's core
differentiator and its one non-negotiable custom-agent requirement.

**Responsibility:** Given an LLM's structured answer + citations, and
the actual source chunks retrieved for the query, verify each
citation's `quote` field is genuinely present (fuzzy-matched) in its
claimed source chunk. Strip unverified claims. Trigger refusal if
nothing survives.

**Why this counts as an "agent" and not just a function:** it makes
an autonomous accept/reject decision per citation and composes the
final response shape (answer vs. refusal) based on that decision —
it's not a passive formatter, it's the component with actual
authority over what the user sees.

**Rules this agent must never violate:**
- Never let an unverified citation reach the user, under any
  confidence threshold, even if the LLM sounds certain.
- Never silently degrade to "answer without citations" — no
  citations surviving means refuse, full stop (DECISION.md Rule 5).
- Never call an LLM to do its job. Verification is deterministic
  fuzzy string matching, not judgment (DECISION.md Rule 9).

## Custom Skill: `adversarial-refusal-test-generator`

A skill (see RULES.md) that, given a document set, generates a batch
of "should refuse" test questions — questions plausible-sounding but
NOT answerable from the provided documents (adjacent topics, slightly
wrong entities, questions about documents not in the set). This skill
is what produces the adversarial test set that proves the
zero-fabrication claim in the demo.

## General Coding Agent Rules (for whoever/whatever is doing the
implementation — Cline, Claude Code, etc.)

- Follow DECISION.md rules exactly. If a rule and a "looks nicer"
  implementation choice conflict, the rule wins.
- Do not introduce a second LLM call anywhere without updating
  DECISION.md Rule 1 first and getting explicit sign-off — this is a
  scope-protection tripwire, not a style preference.
- Do not add infrastructure (new DB, new queue, new service) without
  updating ARCHITECTURE.md first. If it's not in the architecture
  doc, don't build it — this prevents scope creep under time
  pressure, which is the single biggest risk to a 48-hour build.
- Every new endpoint or retrieval behavior needs a corresponding test
  case added to RULES.md in the same commit, not "after it works."
- Commit continuously. A single end-of-day commit dump scores badly
  per the hackathon's own judging criteria — small, frequent, honest
  commits are part of the grade, not just good practice.
- When in doubt about scope, check BOUNDARIES.md before adding
  anything. If it's on that list, it's cut on purpose.
