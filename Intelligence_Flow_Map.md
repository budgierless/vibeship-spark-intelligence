# Intelligence_Flow_Map.md

Generated: 2026-02-03

This file provides a high-level visual map of Spark Intelligence data flow.
For exhaustive tuneables and file interactions, see Intelligence_Flow.md.

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
    queue["lib/queue.py\n~/.spark/queue/events.jsonl"]
  end

  %% ===== Bridge Worker =====
  subgraph Bridge
    bridge_worker["bridge_worker.py"]
    bridge_cycle["lib/bridge_cycle.run_bridge_cycle"]
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
  end

  %% ===== Context + Output =====
  subgraph Output
    context_sync["lib/context_sync"]
    promoter["lib/promoter"]
    output_adapters["lib/output_adapters/*"]
    context_files["CLAUDE.md / AGENTS.md / TOOLS.md / SOUL.md / SPARK_CONTEXT.md"]
  end

  %% ===== Mind =====
  subgraph Mind
    mind_bridge["lib/mind_bridge"]
    mind_server["mind_server.py\n~/.mind/lite/memories.db"]
  end

  %% ===== Ops =====
  subgraph Ops
    dashboard["dashboard.py"]
    watchdog["spark_watchdog.py"]
    service_ctl["lib/service_control"]
  end

  %% ===== Trace Context =====
  subgraph Trace
    trace_ctx["trace_id (v1)"]
  end

  %% ===== Edges =====
  hooks_observe --> queue
  adapters --> sparkd --> queue
  scripts_emit --> queue

  queue --> bridge_worker --> bridge_cycle
  queue --> trace_ctx

  bridge_cycle --> memory_capture --> cognitive --> banks
  cognitive --> store

  bridge_cycle --> pattern_agg --> request_tracker --> distiller --> memory_gate --> eidos_store
  eidos_store --> eidos_retriever
  eidos_store --> control_plane
  trace_ctx --> pattern_agg
  trace_ctx --> eidos_store
  pattern_agg --> cognitive

  bridge_cycle --> validation_loop --> cognitive
  bridge_cycle --> prediction_loop --> outcome_log --> aha --> cognitive
  trace_ctx --> outcome_log

  bridge_cycle --> content_learner

  bridge_cycle --> chips_router --> chips_runtime --> chips_scoring --> chips_evolution
  chips_runtime --> chip_merger --> cognitive

  bridge_cycle --> context_sync --> promoter --> output_adapters --> context_files
  cognitive --> context_sync

  context_sync --> mind_bridge --> mind_server
  mind_server --> mind_bridge

  queue --> dashboard
  bridge_cycle --> dashboard
  trace_ctx --> dashboard
  service_ctl --> watchdog
```
