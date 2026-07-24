# ADR 004 — Model routing: cost/latency/capability/domain routing matrix

Date: 2026-05-28

Context
-------
NeuroFlow must route generation requests to an appropriate LLM. Requirements: control cost, meet latency SLAs, use domain-specialized models when available, enable experiments (fine-tuned models), and failover on model errors. Models available (examples):

- Tier A — High-capability models (e.g., GPT-4-class, large proprietary models): high cost, high capability, longer latency
- Tier B — General-purpose medium models (e.g., GPT-4o/GPT-4o-mini, smaller hosted models): balanced cost and latency
- Tier C — Low-cost fast models (e.g., GPT-3.5-class, small open models): low cost, low latency, lower capability
- Fine-tuned models — per-domain fine-tuned variants of tiers above

Decision
--------
Use a rule-based routing service with a configurable routing matrix and dynamic runtime signals. Routing inputs:

- Query type (instruction, summarization, question-answering, code, math)
- Domain tags (medical, legal, financial, internal docs)
- Cost sensitivity / user tier (free vs paid vs admin)
- Latency requirement (interactive vs batch)
- Model health signals (latency, error rate, quota)
- Experiment flags (A/B, canary)

Rules (examples):

- If query.domain in {medical, legal, financial} AND user_tier != free => prefer Fine-tuned Tier A (if available) else Tier A
- If latency_required == interactive AND max_latency_ms <= 200 => prefer Tier C or Tier B-mini (cheaper low-latency)
- If user_tier == free => prefer Tier C, unless query is flagged as high-risk domain (then return a limited answer or require upgrade)
- If model_health[preferred] degraded (error rate > 2% or p95 latency > SLA) => failover to next available tier and mark for retries
- For batch jobs or long-running fine-tune candidates => queue to Tier A (offline) or batch LLM farm

Routing matrix (illustrative)

| Query type / criteria         | Tier A (high-cap) | Tier B (balanced) | Tier C (cheap/fast) | Fine-tuned |
|-------------------------------|-------------------:|------------------:|--------------------:|-----------:|
| Short FAQ / lookup (interactive)| Low priority        | Medium (default)  | High (default)      | Low        |
| Complex synthesis / long form  | High (default)      | Medium            | Low                 | High (if domain matches)
| Code generation / evaluation   | High                | Medium (fast variant)| Low               | Medium     |
| Legal / medical question (sensitive)| High (must)    | Low               | Deny/require upgrade | High (if tuned)
| Cost-sensitive user / free tier| Deny / throttle     | Low               | High                | Deny       |

Consequences
------------
Pros:
- Predictable, auditable routing decisions expressed as rules and a matrix.
- Easy to add experiment flags or new model endpoints (canary / rollout).
- Supports cost controls and latency SLAs by design.

Cons / trade-offs:
- Rule-based systems require maintenance and can grow complex with many exceptions.
- Hard thresholds may cause oscillation if not smoothed (e.g., rapid health flips).

Operational notes & implementation spec (Task 38)
-----------------------------------------------
- Implement a `ModelRouter` microservice that takes QueryPayload + runtime signals and returns `model_id` and `routing_reason`.
- Persist routing decisions (request -> model_id) for auditing and evaluation.
- Expose an admin UI/API to edit routing matrix and set experiment percentages.
- Health checks: collect model latency/error metrics; apply exponential smoothing and circuit-breaker rules.
- Metrics to track: routing distribution, per-model latency and error rate, cost per request, success rate of fallbacks.

Migration / evolution
--------------------
- Start with conservative rules and expand with telemetry-driven adjustments.
- Add ML-based routing (meta-controller) later if rule complexity grows; keep rule overrides for safety.

Status: Proposed and added as ADR; Task 38 will implement the routing service and matrix.
