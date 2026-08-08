# AGENTS_AND_SKILLS.md — Custom Agent & Skill Documentation

## 1. System Overview

**KRE-lite** is a zero-hallucination Document Question-Answering system designed to enforce total factual ground truth.

Traditional RAG systems silently fabricate answers when documents lack information. KRE-lite implements an invariant-enforcing agentic architecture: **Every factual claim must be backed by a verified verbatim citation quote, or the system strictly refuses to answer.**

---

## 2. Custom Agent: `citation-verifier-agent`

### Specification
- **Agent Type**: Deterministic Post-Generation Guardrail Agent
- **Location**: `backend/app/query/citation_verifier.py`
- **Verification Paradigm**: Multi-stage fuzzy string matching & token n-gram overlap ($\ge 90\%$) against raw stored document chunks. Zero secondary LLM calls.

### Decision Logic & Authority
1. **Quote Existence Check**: Extracts all cited quotes from the structured LLM output and validates their character and token overlap against the exact retrieved chunks in storage.
2. **Entity & Negation Check**: Detects ungrounded number swaps, date mismatches, and entity hallucination.
3. **Filtering & Synthesis (3-State Machine)**:
   - Strips ungrounded claims and invalid citations.
   - If at least one verified citation survives and no false premise is detected, returns status `answered` with page and section anchors.
   - If a verified citation numerically contradicts the user's stated premise (`contains_claim=True`), returns status `corrected` with the grounded refutation (DECISION.md Rule 15).
   - If zero verified citations survive, overrides the LLM and outputs status `refused` (`reason: no_grounded_answer`).

---

## 3. Custom Skill: `adversarial-refusal-test-generator`

### Specification
- **Skill Type**: Automated Adversarial Stress Testing & Guardrail Verification
- **Location**: `backend/tests/unit/test_adversarial_refusal.py` & `backend/benchmark_evaluation.py`

### Question Generation Categories:
1. **Adjacent-but-Absent**: Facts plausible within the domain but completely missing from the ingested corpus.
2. **Wrong-Entity & Number Swap**: Genuine facts where metrics, parameters, or entity names are subtly altered.
3. **Out-of-Corpus**: High-confidence external trivia and current affairs.
4. **Leading False Premises**: Trap questions with false presuppositions.

---

## 4. Architectural Rules & Invariants
- **Rule 1 (Single LLM Call)**: Only one LLM call per query. Verification is strictly deterministic.
- **Rule 2 (Structured Output)**: Responses adhere to standard schema contracts.
- **Rule 4 & 9 (Cited or Silent)**: No unverified claims reach the client. Refusal is an active security state, not an error.
