# DECISION.md — Hard Rules

Numbered so RULES.md test cases and AGENT.md can reference them
directly (e.g. "Rule 3"). These are not aspirations. If a rule is
violated, that's a bug, not a tuning knob.

## Retrieval & Generation

1. Exactly one LLM call per query. No exceptions, no retries that
   silently chain into a second call without logging it as a retry.
2. The LLM must return structured output (JSON schema /
   function-calling), never free text. Free-text parsing of
   citations is a hallucination risk in itself.
3. Every citation the LLM returns must include `page`, `section`,
   and `quote`. A citation missing any of these three fields is
   treated as failed verification automatically — no partial credit.
4. The citation verifier (deterministic code, ARCHITECTURE.md) runs
   on every response, with no bypass flag, including in dev/test
   mode. There is no "trust mode."
5. If zero citations survive verification, the API returns a
   refusal. The refusal response is a distinct, testable shape
   (`{status: "refused", reason: "no_grounded_answer"}`), not just
   an empty answer string.
6. The system never answers from the LLM's general knowledge, even
   when the LLM is confident and even when the answer is probably
   correct. If it's not in the retrieved chunks, it's not in the
   answer. This is the whole point of the project — do not weaken
   it under demo-day time pressure to make answers look "smarter."

## Ingestion

7. Every stored chunk has non-null `page_number` and
   `section_title`. No chunk is stored without both.
8. Chunk size target: small enough that a single chunk is a
   plausible, complete citation unit (roughly one paragraph to one
   subsection), not so small that it loses context, not so large
   that a citation "quote" can't be meaningfully verified against it.

## Scope Protection

9. No second LLM call anywhere in the pipeline (no "LLM judge",
   no self-critique step, no query rewriting via LLM). If verification
   quality is a problem, fix the deterministic verifier's matching
   threshold, don't add a model call.
10. No feature ships without a corresponding test in RULES.md.
    "It looked right when I tried it" is not an exit criterion.

## v1.1 Amendments (post-deploy, do not apply during v1 build)

11. Rule 1 amended for v1.1 ONLY: Q&A flow stays exactly 1 LLM call
    per query. Auditor flow = 1 LLM call PER RULE (ruleset of 5 rules
    = 5 calls, logged, not silent). Never combine multiple rules into
    1 call — mixes evidence, breaks per-rule citation trace.
12. Confidence tiers (HIGH/LOW/REFUSE) computed BEFORE any LLM call,
    via cosine sim only. REFUSE tier never reaches LLM_service.py.
    This is stricter than v1's post-hoc verify-then-strip; v1's
    verifier logic stays unchanged and still runs on HIGH/LOW tier
    output as a second, independent check — belt + suspenders, not
    replace.
13. LOW confidence answers still go thru citation_verifier.py same
    as HIGH. LOW tier only changes UI treatment + adds "partial
    match, verify" text, not the guardrail logic itself.
14. Auditor agent's per-rule Pass/Fail still requires >=1 verified
    citation to say "Pass" or "Fail" with evidence. Zero surviving
    citations for a rule = "Unable to verify" (3rd state, not
    Pass/Fail forced binary) — do not force a rule into Pass/Fail
    when no evidence found, that IS a fabrication risk.

## Explicitly Deferred (not cut forever, just not in scope for 48h)

- Multi-turn conversation memory
- Multi-document cross-referencing / multi-hop reasoning
- Confidence scoring beyond binary (verified citation exists / it
  doesn't)
- Auth, multi-tenancy, rate limiting

See BOUNDARIES.md for the full "what this is not" list and why each
item is cut.