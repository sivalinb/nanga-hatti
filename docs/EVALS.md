# What the evaluation checks

The repository includes 50 authored workflow fixtures and 20 retrieval queries. All contribution text is fictional. The workflow fixtures cover normal contributions, aliases, ambiguous/missing town names, absent consent, private records, absent sharing permission, rejection, malicious quoted instructions, timeouts, unsupported IDs, duplicate IDs and repeated source searches. Fault providers are explicitly simulated; the LangGraph execution, checkpoints and storage are real.

Each case checks task correctness, the review gate, verbatim memory preservation, source-reference validity, clarification, visibility, bounded searches and consent enforcement. The task score verifies the expected final status and town selection. The source-reference score verifies membership in retrieved evidence and uniqueness, not semantic relevance or historical truth. A private save and an appropriate clarification are scored according to the case's expected behavior.

The retrieval queries have expected fact IDs from the small source collection. Recall@3 measures the fraction of expected IDs retrieved in the first three positions. MRR@3 uses the rank of the first correct ID. These queries were written against this corpus; this is not a held-out, community-authored language benchmark. The fixture dataset is an engineering regression suite, not evidence of broad real-world accuracy.

```sh
python -m pytest -q
python -m nanga.cli eval
python -m nanga.cli eval --live --cases 8 --upload-braintrust
```

Live evaluation uses eight ordinary fictional cases from the same versioned fixtures, actual provider calls, actual usage, and the full review/save workflow. The report's `live_execution_rate` requires a live result with model calls; authored fallback cannot pass as live execution. Uploading to Braintrust creates an experiment from the recorded results with redacted inputs and stage evidence. Trace and experiment links require the owner's account permissions.

Reports: [authored suite](../evals/reports/latest.json), [live suite](../evals/reports/live.json), [live trace evidence](../evals/reports/live-traces.json).

During implementation, traces exposed a schema mismatch: the model sometimes included an action field in a composition response, and composition fields in a planning response. The strict validator rejected those extra fields. The recorded [prompt-v1 mixed-mode run](../evals/reports/schema-v1-mixed.json) is retained. Prompt v2 gives each task its own instructions and exact JSON schema, then was evaluated again on the same cases. This is an example of observability informing a repair and evals checking it.

Before collecting real stories, add contributor-reviewed cases that cover differing accounts, meaningful context selection, local place names and community access practices. Fluent speakers must assess Badaga language and cultural interpretation. Repeat stochastic cases and report sample counts when comparing models. No existing score measures pronunciation, cultural authority, community adoption or intergenerational learning.

Official references: [evaluating agents](https://www.braintrust.dev/docs/best-practices/agents), [evaluation cycle](https://www.braintrust.dev/docs/evaluate).
