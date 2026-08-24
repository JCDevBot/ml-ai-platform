# Generative evaluation

The generative evaluation layer supports LLM, RAG, tool-using agent, and routing/graph candidates without requiring a model-provider SDK in the core package.

## Candidate execution boundary

`GenerativeCandidate` is a minimal protocol: an adapter receives a labeled `GenerativeCase` and returns a recorded `GenerativeOutput`. Provider-backed execution belongs in optional adapters or consumer packages. The core evaluator only consumes recorded outcomes.

This keeps paid APIs, credentials, and provider-specific request objects out of the base package and allows deterministic fake candidates in CI.

## Deterministic evidence

`evaluate_generative` can calculate the following metrics when labels/evidence are present:

- `task_accuracy` — exact labeled task outcome accuracy;
- `structured_output_validity` — fraction of outputs satisfying the consumer's structure/schema check;
- `tool_selection_accuracy` — expected versus selected tool;
- `retrieval_recall` and `retrieval_precision` — against labeled relevant document IDs;
- `unsupported_claim_rate` — claims not present in the case's labeled supported-claim set;
- `mean_latency_ms` — recorded latency metadata;
- `total_cost_units` — provider-neutral recorded cost units.

These metrics carry `metadata.evidence_type = deterministic` and can be used by the same comparison and promotion policy mechanics as classical ML metrics.

Consumers remain responsible for defining meaningful labels, structure validators, claim extraction, retrieval identifiers, and any conversion from provider billing into `cost_units`.

## Judge-model evidence

`JudgeResult` is optional subjective evidence. A judge result must include:

- `judge_id`;
- `config_hash`;
- source score scale;
- case ID and score.

Aggregated judge metrics are emitted with:

```text
evidence_type = judge_model
authoritative_ground_truth = false
judge_id = ...
judge_config_hash = ...
```

Results from different judge identities, configurations, or score scales cannot be silently aggregated into one metric.

Judge output may inform analysis or a deliberately configured policy, but the platform never relabels it as deterministic ground truth.

## Incident-triage proof

`examples/incident_triage/` contains a provider-free fixture comparing:

- an `fixture:llm-prompt` baseline;
- a `fixture:tool-agent` challenger.

The fixture includes severity labels, expected tools, relevant runbook IDs, supported factual claims, latency/cost metadata, and a fake judge with explicit provenance.

The challenger improves labeled task accuracy, structured validity, tool selection, and unsupported-claim rate while increasing total cost. Reusable `comparison_findings` therefore produce both improvement findings and a cost regression finding.

The same `ChampionLifecycle` used for classical ML then applies deterministic gates for task accuracy, structured validity, tool accuracy, and unsupported claims. The challenger passes those gates and becomes champion. Judge score is persisted in the evaluation run but is not used as authoritative ground truth in the fixture's promotion policy.

## Provider adapters

No OpenAI, Anthropic, Bedrock, Vertex, LangChain, LangGraph, or other provider/framework dependency is required by this feature. Future integrations should be optional extras or consumer-side adapters that translate their outputs into `GenerativeOutput` and, where desired, `JudgeResult`.
