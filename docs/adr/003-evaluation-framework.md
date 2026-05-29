# ADR 003 — Evaluation framework: automated LLM-as-judge with human calibration

Date: 2026-05-28

Context
-------
We must evaluate generated answers for faithfulness, relevance, and retrieval quality at scale to support fine-tuning and monitoring. Pure human annotation is costly, slow, and hard to scale. Recent work uses LLMs as automated judges (entailment/cross-encoders or instruction-tuned LLMs) to score outputs rapidly. We need a defensible evaluation pipeline that balances speed, cost, and reliability.

Decision
--------
Adopt a hybrid evaluation strategy: primarily automated LLM-as-judge evaluation for continual scoring and fast feedback, with a human-in-the-loop calibration and audit process. Automated scores are used for monitoring, filtering candidate fine-tuning examples, and triggering alerts; humans validate samples and outcomes before promoting models or datasets.

Why:
- Scale: automated judges enable scoring millions of examples over time at a fraction of human cost.
- Speed: supports near-real-time feedback loops (e.g., eligibility for fine-tuning, drift detection).
- Consistency: a well-configured model provides reproducible scoring and fewer annotator disagreements.

Consequences
------------
Benefits:
- Faster iteration for fine-tuning and model selection.
- Cost-effective continuous evaluation and richer telemetry for monitoring.

Primary failure modes:
1. Judge hallucination/bias — the automated judge may itself hallucinate, miss contradictions, or prefer fluent but ungrounded answers.
2. Overfitting to the judge — models fine-tuned using judge-selected examples can learn to optimize for the judge rather than true user value.
3. Domain drift — judge performance degrades on niche domains without calibration data.
4. Adversarial examples — prompt injections or cleverly phrased responses that fool the judge.

Detection and mitigations:
- Calibration set: maintain a human-labeled gold set (stratified by domain and difficulty). Regularly (daily/weekly) compute judge vs human agreement (e.g., Cohen's kappa) and alert if it drops below a threshold.
- Ensembles & cross-checks: use multiple automatic signals (entailment model + semantic overlap + token-overlap heuristics) and combine them; require consensus or flag for human review when signals disagree.
- Conservative selection for training: only accept examples for fine-tuning when the automated faithfulness score is high AND an optional sampled human review passes OR when multiple automated checks agree.
- Periodic human audits: sample generated responses (both high and low scores) for manual review; surface systematic failure patterns.
- Rejects & fallback: if judge confidence is low or signals conflict, send to human annotation or exclude from training datasets.

Operational notes
-----------------
- Track judge metrics over time (agreement with humans, false positive/negative rates).
- Log all inputs to the judge with provenance to enable rollback of training data if judge drift is detected.
- Use strict PII detectors before any automated scoring or usage in training.

Consequences for model lifecycle
--------------------------------
- Automated judging accelerates dataset curation and enables frequent small fine-tuning cycles, but raises the risk of judge-induced bias. The human calibration loop and ensemble checks are mandatory gatekeepers before promoting models into production.

Status: Adopt automated LLM-as-judge as primary evaluation path, with enforced human calibration and audit processes.
