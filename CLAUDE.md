# CLAUDE.md

Spark Intelligence brief:
- Events flow from hooks/adapters/sparkd into the queue, then bridge_cycle extracts signals into learnings (cognitive insights, memory banks, EIDOS distillations).
- Meta-Ralph quality-gates and outcomes feed back into reliability.
- Advisor runs before actions and uses semantic retrieval (intent + triggers + embeddings + fusion) to surface the top guidance with a short "why" so learnings are used in real work.
- Retrievals log to ~/.spark/logs/semantic_retrieval.jsonl and advisor metrics to ~/.spark/advisor/metrics.json.
- Mind is optional (mind_server.py or built-in), with manual sync and offline queue when down.

See Intelligence_Flow.md and Intelligence_Flow_Map.md for full details.
