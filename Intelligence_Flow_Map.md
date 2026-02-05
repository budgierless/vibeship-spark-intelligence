# Intelligence_Flow_Map.md

Generated: 2026-02-05

This file provides a high-level visual map of Spark Intelligence data flow.
For exhaustive tuneables and file interactions, see Intelligence_Flow.md.

Brief overview:
Spark Intelligence captures events (hooks/adapters/sparkd) into a queue, runs a bridge cycle to extract signals, and turns them into learnings (cognitive insights, memory bank entries, EIDOS distillations). Queue consumption uses a logical head pointer with overflow spillover to reduce rewrite contention. Bridge-cycle persistence is batched so cognitive/meta stores flush once per cycle instead of per event. Meta-Ralph quality-gates what is stored, outcomes feed back into reliability, and Advisor/Context Sync surface those learnings before actions. When semantic retrieval is enabled, Advisor extracts intent from the current task, matches triggers, runs embedding search over stored insights, fuses scores (similarity + recency + outcome), and returns the top guidance with "why" so learnings are actually used during real work. This map shows the systems and data stores; Intelligence_Flow.md covers exact configs, tuneables, and file-level interactions.

```mermaid
flowchart LR
  %% ===== Sources =====
  subgraph Sources
    hooks_observe["hooks/observe.py"]
    sparkd["sparkd.py /ingest"]
    adapters["adapters/*"]
    scripts_emit["scripts/emit_event.py"]
  end

  %% ===== Queue =====
  subgraph Queue
    queue["lib/queue.py\n~/.spark/queue/events.jsonl\n+ events.overflow.jsonl\n+ state.json (head_bytes)"]
  end

  %% ===== Bridge Worker =====
  subgraph Bridge
    bridge_worker["bridge_worker.py"]
    bridge_cycle["lib/bridge_cycle.run_bridge_cycle"]
    update_context["lib/bridge.update_spark_context"]
  end

  %% ===== Core Learning Loops =====
  subgraph Learning
    memory_capture["lib/memory_capture"]
    cognitive["lib/cognitive_learner"]
    banks["lib/memory_banks"]
    store["lib/memory_store"]

    pattern_agg["lib/pattern_detection.aggregator"]
    request_tracker["request_tracker"]
    distiller["distiller"]
    memory_gate["memory_gate"]
    eidos_store["lib/eidos/store"]
    eidos_retriever["lib/eidos/retriever"]
    control_plane["lib/eidos/control_plane"]

    validation_loop["lib/validation_loop"]
    prediction_loop["lib/prediction_loop"]
    outcome_log["lib/outcome_log"]
    aha["lib/aha_tracker"]

    content_learner["lib/content_learner"]

    chips_router["lib/chips/router"]
    chips_runtime["lib/chips/runtime"]
    chips_scoring["lib/chips/scoring"]
    chips_evolution["lib/chips/evolution"]
    chip_merger["lib/chip_merger"]

    contradictions["lib/contradiction_detector"]
    curiosity["lib/curiosity_engine"]
    hypotheses["lib/hypothesis_tracker"]
  end

  %% ===== Advisor =====
  subgraph Advisor
    advisor["lib/advisor"]
    skills_router["lib/skills_router"]
  end

  %% ===== Semantic Retrieval =====
  subgraph Semantic
    semantic_retriever["lib/semantic_retriever"]
    semantic_index["~/.spark/semantic/insights_vec.sqlite"]
    embeddings["lib/embeddings"]
    semantic_logs["~/.spark/logs/semantic_retrieval.jsonl"]
    advisor_metrics["~/.spark/advisor/metrics.json"]
  end

  %% ===== Meta-Ralph =====
  subgraph MetaRalph
    meta_ralph["lib/meta_ralph"]
  end

  %% ===== Context + Output =====
  subgraph Output
    spark_context["SPARK_CONTEXT.md"]
    context_sync["lib/context_sync"]
    output_adapters["lib/output_adapters/*"]
    context_files["CLAUDE.md / AGENTS.md / TOOLS.md / SOUL.md"]
    promoter["lib/promoter (manual/CLI)"]
  end

  %% ===== Mind =====
  subgraph Mind
    mind_bridge["lib/mind_bridge"]
    mind_server["mind_server.py\n~/.mind/lite/memories.db"]
  end

  %% ===== Ops =====
  subgraph Ops
    dashboard["dashboard.py"]
    meta_ralph_dashboard["meta_ralph_dashboard.py"]
    pulse_dashboard["vibeship-spark-pulse/app.py\n(service_control target)"]
    watchdog["spark_watchdog.py"]
    service_ctl["lib/service_control"]
  end

  %% ===== Trace Context =====
  subgraph Trace
    trace_ctx["trace_id (v1)"]
  end

  %% ===== EIDOS Hook Integration =====
  subgraph EidosHooks
    eidos_integration["lib/eidos.integration (hooks)"]
  end

  %% ===== Edges =====
  hooks_observe --> queue
  adapters --> sparkd --> queue
  scripts_emit --> queue

  queue --> bridge_worker --> bridge_cycle
  queue --> trace_ctx

  bridge_cycle --> update_context --> spark_context

  bridge_cycle --> memory_capture --> cognitive
  memory_capture --> banks
  cognitive --> store

  bridge_cycle --> pattern_agg --> request_tracker --> distiller --> memory_gate --> eidos_store
  eidos_store --> eidos_retriever
  eidos_store --> control_plane
  trace_ctx --> pattern_agg
  trace_ctx --> eidos_store
  pattern_agg --> cognitive

  pattern_agg --> contradictions
  pattern_agg --> curiosity
  pattern_agg --> hypotheses

  bridge_cycle --> validation_loop --> cognitive
  bridge_cycle --> prediction_loop --> outcome_log --> aha --> cognitive
  trace_ctx --> outcome_log

  bridge_cycle --> content_learner --> cognitive

  bridge_cycle --> chips_router --> chips_runtime --> chips_scoring --> chips_evolution
  chips_runtime --> chip_merger --> cognitive

  bridge_cycle --> context_sync --> output_adapters --> context_files
  context_files --> context_sync
  promoter --> context_files

  hooks_observe --> advisor
  bridge_cycle --> advisor
  update_context --> advisor
  advisor --> skills_router
  advisor --> cognitive
  advisor --> banks
  advisor --> eidos_retriever
  advisor --> aha
  advisor --> mind_bridge
  advisor --> meta_ralph
  advisor --> semantic_retriever
  advisor --> advisor_metrics
  semantic_retriever --> semantic_index
  semantic_retriever --> embeddings
  semantic_retriever --> semantic_logs
  hooks_observe --> meta_ralph
  meta_ralph --> cognitive

  update_context --> mind_bridge
  mind_bridge --> mind_server
  mind_server --> mind_bridge
  cognitive -.-> mind_bridge

  hooks_observe --> eidos_integration --> eidos_store
  eidos_integration --> control_plane
  trace_ctx --> eidos_integration

  queue --> dashboard
  bridge_cycle --> dashboard
  trace_ctx --> dashboard
  meta_ralph --> meta_ralph_dashboard
  service_ctl --> pulse_dashboard
  service_ctl --> watchdog
```
