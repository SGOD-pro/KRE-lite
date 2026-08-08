# BOUNDARIES.md — What This Is Not (Read This Before Adding Anything)

Every item below was deliberately cut. If you find yourself building
one of these at hour 30 because "it would make the demo better,"
stop and re-read PROJECT.md's one-sentence pitch first. None of these
make the core claim ("cited or silent") stronger — they make the
system bigger and the deadline riskier.

## Not building: cloud deployment for Round 1

Per the hackathon's own submission requirements, "working code" means
demonstrable — `docker-compose up`, a demo video, or screenshots. It
does NOT require a live public URL. Do not spend hackathon hours
solving Lambda packaging, RDS provisioning, or container-image size
limits. That entire class of problem (which cost real time on the
KRE project) is explicitly out of scope here. If hours remain after
Phase 4 exits clean, a 10-minute Railway/Render deploy is a fine
stretch goal — never a Phase 1-4 dependency.

## Not building: OKF, PageIndex, knowledge graph

These are KRE concepts. This project is a different, smaller system
built for a different constraint (48 hours, not 50 days). BM25 +
vector + LLM + citation verification is the entire retrieval
pipeline. Do not port typed-property extraction, structural scoring,
or graph traversal into this repo. If a teammate suggests "we already
have OKF code, let's just use it" — the answer is no, because it
brings the dual-provider matrix, the RDS+ElastiCache dependency, and
the multi-Lambda packaging problem with it.

## Not building: dual dev/prod provider routing

One embedding path (AWS Bedrock Titan Text Embeddings v2, via boto3 API
call). One LLM provider (AWS Bedrock Nova Pro via Converse API, with
OpenRouter as a documented fallback if rate-limited — not a live dual-path,
just a config value you can flip). No environment-specific model matrix.

## Not building: a second LLM call anywhere

No LLM-as-judge, no query rewriting, no self-critique, no
multi-agent handoff. DECISION.md Rule 1 and Rule 9. The citation
verifier is deterministic code specifically so it doesn't become a
second hallucination surface.

## Not building: auth, multi-tenancy, rate limiting

Single-session local demo tool. No login, no user accounts, no API
keys issued to end users.

## Not building: multi-turn conversation / chat memory

Each question is independent. No conversation history influences
retrieval or generation. This keeps the citation verifier's job
simple (verify against this query's retrieved chunks, not an
accumulated context window).

## Not building: clustering, priority queues, approval workflows

Those belong to the Track A concept this team considered and
deprioritized. Nothing from that direction (KMeans clustering, SQS,
swipe-to-approve UI) belongs in this repo. If the team pivots back to
Track A, that's a different doc set, not an addition to this one.

## The one thing that IS allowed to grow if time remains

The adversarial test set (RULES.md). More adversarial questions,
more categories, is the one form of "scope creep" that directly
strengthens the core claim instead of diluting it. If Phase 4 exits
early, spend the remaining time here first, before touching UI
polish or deployment.
