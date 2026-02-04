# Intelligence_Flow.md

Generated: 2026-02-04
Repository: vibeship-spark-intelligence
Scope:
- Runtime Python modules: root *.py, lib/, hooks/, adapters/, spark/
- Configs: chips/*.chip.yaml, chips/examples/*.chip.yaml, config/learning_sources.yaml
Exclusions:
- tests/, benchmarks/, build/ artifacts (not part of runtime)

Notes:
- ASCII only.
- Auto-extracted sections (chip inventory, learning_sources config, tuneables index, import map) are appended at the end.

## 1) System overview (what talks to what)

Sources:
- hooks/observe.py (agent hooks)
- sparkd.py (HTTP ingest for SparkEventV1)
- adapters/* (stdin_ingest, clawdbot_tailer, moltbook)
- scripts/emit_event.py (manual event injector)

Central bus:
- lib/queue.py writes events to ~/.spark/queue/events.jsonl (append-only)

Processing loop:
- bridge_worker.py -> lib/bridge_cycle.run_bridge_cycle

High-level flow (ASCII):
sources -> queue -> bridge_cycle -> {update_spark_context, memory capture, pattern detection, validation/prediction, content learning, chips}
                         -> {cognitive insights, memory banks/store, eidos store, advisor loop, outputs}

Mind integration:
- mind_server.py (Mind Lite+ API, sqlite at ~/.mind/lite/memories.db)
- lib/mind_bridge.py (retrieval used by advisor + lib.bridge for SPARK_CONTEXT)
- Mind sync is manual (spark sync / lib.mind_bridge.sync_all_to_mind); offline queue used when Mind is down.

Dashboards and ops:
- dashboard.py (status + UI)
- spark_watchdog.py + lib/service_control.py (monitor/restart services)

## 2) Primary workflows (end-to-end)

### 2.1 Event ingest -> queue
1) hooks/observe.py captures tool/user events and emits SparkEvent payloads.
2) sparkd.py validates SparkEventV1 and writes queue events via lib.queue.quick_capture.
3) adapters (stdin_ingest, clawdbot_tailer, moltbook) also feed sparkd or queue.
4) hooks/observe.py also runs EIDOS pre/post step tracking and Meta-Ralph roasting for cognitive signals (direct calls, not via bridge_cycle).

### 2.2 Queue -> bridge cycle
1) bridge_worker.py loops every interval (default 60s, min 10s sleep).
2) lib.bridge_cycle.run_bridge_cycle reads recent events and orchestrates learning tasks.
3) A heartbeat is written to ~/.spark/bridge_worker_heartbeat.json.

### 2.2.1 Trace context propagation (v1)
- trace_id is attached at ingest (hooks/observe.py, sparkd.py, lib.queue.quick_capture).
- trace_id is carried into pattern events and EIDOS Steps.
- evidence is linked to steps; outcomes include trace_id when available.
- trace binding enforcement: steps, evidence, and outcomes should record trace_id; TRACE_GAP watcher warns on missing bindings. Set `SPARK_TRACE_STRICT=1` to block actions on trace gaps.
- dashboards should drill down by trace_id for audit and validation.

### 2.3 Context sync + promotion (live vs durable)
1) lib.bridge.update_spark_context builds a live context pack (insights, warnings, advice, skills, taste, outcomes) and writes SPARK_CONTEXT.md.
2) lib.context_sync selects high-confidence insights and writes live context to output adapters (clawdbot, cursor, windsurf, claude_code).
   - context_sync can include promoted lines already present in CLAUDE.md / AGENTS.md / TOOLS.md / SOUL.md.
   - context_sync does not sync to Mind (see 2.8).
3) lib.promoter is a separate, manual step (spark promote) that writes durable learnings into CLAUDE.md / AGENTS.md / TOOLS.md / SOUL.md.

### 2.4 Memory capture + cognitive learning
1) lib.memory_capture scans user messages for memory triggers.
2) High-signal items are auto-saved or queued for review.
3) lib.cognitive_learner stores insights + reliability/validation + decay.
4) lib.memory_banks stores per-project and global memory.
5) lib.memory_store persists hybrid memory (SQLite FTS + embeddings + graph edges).
6) hooks/observe.py uses Meta-Ralph to roast cognitive signals before add_insight.

### 2.5 Pattern -> distillation -> EIDOS
1) lib.pattern_detection.aggregator runs detectors (correction, sentiment, repetition, semantic, why).
2) lib.pattern_detection.request_tracker wraps user requests as EIDOS Steps.
3) lib.pattern_detection.distiller creates distillations (heuristic, anti-pattern, sharp edge, playbook, policy).
4) lib.pattern_detection.memory_gate filters low-signal items.
5) lib.eidos.store persists to ~/.spark/eidos.db; lib.eidos.retriever retrieves for guidance.
6) lib.eidos.control_plane and lib.eidos.elevated_control enforce budgets and stuck detection.

### 2.6 Outcomes, predictions, validation, surprises
1) lib.prediction_loop builds and tracks predictions; matches outcomes later.
2) lib.outcome_log + lib.outcomes/* store outcomes and links.
3) lib.validation_loop updates reliability based on outcomes.
4) lib.aha_tracker captures surprises for learning.
5) lib.exposure_tracker records exposure timing for prediction evaluation.

### 2.6.1 Advisor retrieval + Meta-Ralph feedback loop
1) PreToolUse: hooks/observe.py calls lib.advisor.advise_on_tool for retrieval (cognitive, banks, mind, EIDOS, aha, skills).
2) Advisor logs retrievals and notifies Meta-Ralph via track_retrieval.
3) PostToolUse: hooks/observe.py and lib.bridge_cycle.report_outcome call back into advisor.
4) Meta-Ralph records outcomes and applies them back to cognitive (apply_outcome).

### 2.7 Chips pipeline (domain intelligence)
1) lib.chips.router detects triggers in events.
2) lib.chips.runtime runs observers/learners; writes chip insights under ~/.spark/chip_insights.
3) lib.chips.scoring scores value and promotion tiers.
4) lib.chips.evolution updates trigger stats and can create provisional chips.
5) lib.chip_merger merges chip insights into cognitive categories.

### 2.8 Mind retrieval + manual sync
1) lib.mind_bridge retrieves from mind_server.py (keyword + optional FTS, RRF + salience).
2) lib.advisor and lib.bridge (SPARK_CONTEXT) read from Mind for advice/context.
3) Mind sync is manual via spark sync (lib.mind_bridge.sync_all_to_mind); offline queue stores when Mind is down.

### 2.9 Self-evolution and meta-learning
- lib/meta_ralph.py: quality gate for observe.py cognitive capture + advisor outcome loop.
- lib/metalearning/*: strategy, evaluator, reporter, metrics (used by chips auto-activation).
- lib/resonance.py + lib/spark_voice.py: internal state and voice calibration (used by bridge context).
- lib/growth_tracker.py: milestones and long-term growth stats.
- lib/curiosity_engine.py, lib/contradiction_detector.py, lib/hypothesis_tracker.py: triggered in pattern_detection.aggregator.

### 2.10 Research / external sources
- lib/research/* and lib/x_research_events.py use config/learning_sources.yaml to drive external research.

### 2.11 Services / ops
- lib/service_control.py starts/stops sparkd, bridge_worker, dashboard, watchdog, and pulse.
- spark_watchdog.py checks health, queue size, and heartbeat freshness.

## 3) Data stores and artifacts (local)

Core queue + ingest:
- ~/.spark/queue/events.jsonl
- ~/.spark/queue/.queue.lock
- ~/.spark/invalid_events.jsonl

Context + promotion:
- ~/.spark/cognitive_insights.json
- ~/.spark/.cognitive.lock
- ~/.spark/pending_memory.json
- ~/.spark/memory_capture_state.json
- ~/.spark/bridge_worker_heartbeat.json
Workspace context:
- SPARK_CONTEXT.md (workspace, written by lib.bridge.update_spark_context)

Pattern + EIDOS:
- ~/.spark/detected_patterns.jsonl
- ~/.spark/pattern_detection_state.json
- ~/.spark/eidos.db
- ~/.spark/truth_ledger.json
- ~/.spark/acceptance_plans.json
  - steps table includes trace_id (v1 trace context)

Memory banks + store:
- ~/.spark/banks/*.jsonl
- ~/.spark/memory_store.sqlite

Outcomes + prediction:
- ~/.spark/predictions.jsonl
- ~/.spark/prediction_state.json
- ~/.spark/outcomes.jsonl
- ~/.spark/outcome_links.jsonl
- ~/.spark/outcome_requests.jsonl
- ~/.spark/outcome_checkin_state.json
  - outcomes may include trace_id when derived from queue events
- ~/.spark/outcome_tracker.json
- ~/.spark/exposures.jsonl
- ~/.spark/last_exposure.json

Chips:
- ~/.spark/chip_insights/
- ~/.spark/chip_registry.json
- ~/.spark/chip_evolution.yaml
- ~/.spark/provisional_chips/
- ~/.spark/chip_merge_state.json

Skills + advisor + sync:
- ~/.spark/skills_index.json
- ~/.spark/skills_effectiveness.json
- ~/.spark/advisor/
- ~/.spark/sync_stats.json

Meta-Ralph:
- ~/.spark/meta_ralph/roast_history.json
- ~/.spark/meta_ralph/outcome_tracking.json
- ~/.spark/meta_ralph/learnings_store.json
- ~/.spark/meta_ralph/self_roast.json

Mind sync state:
- ~/.spark/mind_sync_state.json
- ~/.spark/mind_offline_queue.jsonl

Other:
- ~/.spark/projects.json
- ~/.spark/project_context.json
- ~/.spark/project_contexts/
- ~/.spark/taste/
- ~/.spark/research/
- ~/.spark/exports/
- ~/.spark/logs/
- ~/.spark/pids/
- ~/.spark/watchdog_state.json

Mind:
- ~/.mind/lite/memories.db

## 4) Key tuneables (curated, high leverage)

Ingest + servers:
- sparkd.py PORT=8787, SPARKD_MAX_BODY_BYTES=262144 (max /ingest payload).
- mind_server.py PORT=8080, MIND_MAX_BODY_BYTES=262144, MIND_MAX_CONTENT_CHARS=4000, MIND_MAX_QUERY_CHARS=1000.
- mind_server.py RRF_K=60 (rank fusion constant).

Queue:
- lib.queue.py MAX_EVENTS=10000 (rotation threshold).
- lib.queue.py TAIL_CHUNK_BYTES=65536 (tail read size).
- lib.queue._queue_lock timeout_s=0.5 (lock wait).

Bridge cycle:
- bridge_worker.py --interval default 60s, enforced min sleep 10s.
- lib.bridge_cycle.run_bridge_cycle memory_limit=60, pattern_limit=200.
- bridge_cycle reads 40 recent events and checks last 10 user prompts for tastebank.

Memory capture:
- lib.memory_capture.MAX_CAPTURE_CHARS=2000
- AUTO_SAVE_THRESHOLD=0.82, SUGGEST_THRESHOLD=0.55
- pending suggestions capped at 200; list_pending limit 20; process_recent_memory_events default limit 50
- HARD_TRIGGERS / SOFT_TRIGGERS weights drive scoring.

Pattern detection and distillation:
- aggregator CONFIDENCE_THRESHOLD=0.6, DEDUPE_TTL_SECONDS=600, DISTILLATION_INTERVAL=20
- distiller: min_occurrences=2, min_occurrences_critical=1, min_confidence=0.6, gate_threshold=0.5
- repetition detector: min_similarity=0.5, min length 10, keep 20, group size >=3, confidence starts 0.7
- sentiment detector: frustration/satisfaction pattern lists and thresholds
- correction detector: patterns list, confidence threshold >=0.6

Memory gate (pattern_detection/memory_gate.py):
- WEIGHTS: impact 0.30, novelty 0.20, surprise 0.30, recurrence 0.20, irreversible 0.60, evidence 0.10
- threshold=0.5, high_stakes keyword list.

EIDOS control and budgets:
- Budget defaults: max_steps=25, max_time_seconds=720, max_retries_per_error=2, max_file_touches=3, no_evidence_limit=5
- control_plane watcher thresholds: repeat_error=2, no_new_info=5, diff_thrash=3, confidence_delta=0.05, confidence_stagnation_steps=3
- elevated_control escape thresholds (see auto index for full list).

Cognitive learning and promotion:
- cognitive_learner half-lives by category (see auto index), max_age_days=365, min_effective=0.2
- promoter DEFAULT_PROMOTION_THRESHOLD=0.7, DEFAULT_MIN_VALIDATIONS=3
- context_sync DEFAULT_MIN_RELIABILITY=0.7, DEFAULT_MIN_VALIDATIONS=3, DEFAULT_MAX_ITEMS=12, DEFAULT_MAX_PROMOTED=6

Advisor / skills:
- advisor MIN_RELIABILITY_FOR_ADVICE=0.5, MIN_VALIDATIONS_FOR_STRONG_ADVICE=2, MAX_ADVICE_ITEMS=8, ADVICE_CACHE_TTL_SECONDS=120
- skills_router scoring weights (query/name/desc/owns/etc) and limit clamp to 1..10

Mind bridge:
- MIND_API_URL default http://localhost:8080
- request timeout 5s, health timeout 2s
- salience clamp 0.5..0.95, retrieve limit 5
- offline queue and sync state kept under ~/.spark

Chips:
- chip scoring weights: cognitive_value 0.30, outcome_linkage 0.20, uniqueness 0.15, actionability 0.15, transferability 0.10, domain_relevance 0.10
- evolution thresholds: deprecate triggers when matches>=10 and value_ratio<0.2; provisional chip rules (see auto index)
- runtime insight limit default 50
- loader env SPARK_CHIP_SCHEMA_VALIDATION=warn|block

Outcomes + prediction:
- prediction_loop: prediction max age 6h, project prediction max age 14 days, match sim threshold 0.72
- outcome_linker: auto_link_outcomes min_similarity 0.25, get_linkable_candidates min_similarity 0.2

## 5) Environment variables (from code)

Ingest:
- SPARKD_TOKEN (optional bearer auth for /ingest)
- SPARKD_MAX_BODY_BYTES (default 262144, int)

Mind server:
- MIND_TOKEN (optional bearer auth)
- MIND_MAX_BODY_BYTES (default 262144, int)
- MIND_MAX_CONTENT_CHARS (default 4000, int)
- MIND_MAX_QUERY_CHARS (default 1000, int)

Hooks:
- SPARK_EIDOS_ENABLED (default "1")
- SPARK_OUTCOME_CHECKIN_MIN_S (default 1800, int)
- SPARK_OUTCOME_CHECKIN (enable/disable)
- SPARK_OUTCOME_CHECKIN_PROMPT (enable/disable)

Embeddings:
- SPARK_EMBEDDINGS (default "1", set 0/false/no to disable)
- SPARK_EMBED_MODEL (default "BAAI/bge-small-en-v1.5")

Workspace/context:
- SPARK_WORKSPACE (default ~/clawd)
- SPARK_AGENT_CONTEXT_MAX_CHARS (optional override)
- SPARK_AGENT_CONTEXT_LIMIT (optional override)

Logging:
- SPARK_DEBUG (enables verbose logs)
- SPARK_LOG_DIR (override ~/.spark/logs)
- SPARK_LOG_TEE (default "1")

Chips:
- SPARK_CHIP_SCHEMA_VALIDATION (warn|block)

Skills:
- SPARK_SKILLS_DIR (path to skills repository)

Clawdbot adapter:
- SPARK_CLAWDBOT_WORKSPACE / CLAWDBOT_WORKSPACE
- SPARK_CLAWDBOT_TARGETS / CLAWDBOT_TARGETS
- SPARK_CLAWDBOT_CONTEXT_PATH / CLAWDBOT_CONTEXT_PATH
- CLAWDBOT_PROFILE

Moltbook adapter:
- MOLTBOOK_API_KEY

## 6) Known gaps / mismatches

- lib/service_control.py references spark_pulse.py, but that file is not present in this repo (as of 2026-02-03).
- Some docs mention SPARK_MIND_URL; code uses a fixed MIND_API_URL constant instead (lib/mind_bridge.py).
- build/ contains duplicated code artifacts; excluded from analysis.

## 7) Auto-generated sections below
## Chip inventory (auto summary)

### chips\bench-core.chip.yaml
- id: bench_core
- name: Benchmark Core Intelligence
- version: 0.1.0
- activation: opt_in
- risk_level: low
- domains: ['benchmarking', 'tooling', 'workflow']
- triggers.patterns: ['tool', 'command', 'file', 'prompt']
- triggers.events: ['post_tool', 'post_tool_failure', 'user_prompt', 'PostToolUse', 'PostToolUseFailure', 'UserPromptSubmit']
- observers:
  - tool_event triggers=['tool', 'command', 'file', 'write', 'edit', 'bash']
  - user_prompt triggers=['user', 'prompt', 'prefer', 'rather', 'instead', 'why']
- outcomes.positive:
  - condition=status == success weight=1.0 insight=User/tool signaled success
- outcomes.negative:
  - condition=status == failure weight=1.0 insight=User/tool signaled failure

### chips\biz-ops.chip.yaml
- id: biz-ops
- name: Business Ops Intelligence
- version: 0.1.0
- activation: opt_in
- risk_level: medium
- domains: ['business_ops', 'strategy', 'pricing']
- triggers.patterns: ['pricing experiment', 'pricing test', 'revenue forecast', 'runway', 'ops brief', 'operational risk', 'budget forecast']
- triggers.events: ['post_tool', 'post_tool_failure', 'user_prompt', 'PostToolUse', 'PostToolUseFailure', 'UserPromptSubmit', 'pricing_experiment', 'forecast_created', 'ops_plan']
- observers:
  - ops_brief triggers=['ops brief', 'operational risk', 'ops dependency', 'operational dependency', 'ops dependencies', 'operational dependencies']
  - pricing_experiment triggers=['pricing experiment', 'pricing test', 'pricing plan', 'pricing variant', 'experiment plan']
  - forecast triggers=['forecast', 'runway', 'forecast assumptions', 'revenue projection', 'burn projection']
- outcomes.positive:
  - condition=success_metric == retention weight=1.0 insight=Pricing experiment uses retention metric
- outcomes.negative:
  - condition=assumption == missing weight=1.0 insight=Forecast missing assumptions
- questions:
  - pricing_ethics: What pricing behaviors are off-limits for this business?
  - ops_success: Which operational outcomes matter most for this sprint?

### chips\examples\marketing-growth.chip.yaml
- id: marketing-growth
- name: Marketing Growth Intelligence
- version: 1.0.0
- activation: opt_in
- domains: ['marketing', 'growth', 'campaigns', 'acquisition']
- triggers.patterns: ['CTR was', 'conversion rate', 'CAC is', 'ROAS', 'campaign performed', 'audience responded', 'A/B test showed', 'email open rate', 'click through']
- triggers.events: ['user_prompt']
- observers:
  - campaign_metric triggers=['CTR', 'conversion', 'CAC', 'ROAS', 'performed']
  - ab_test_result triggers=['A/B test', 'variant', 'control']
  - audience_signal triggers=['audience', 'segment', 'responded']
- learners:
  - channel_roi type=correlation
  - message_resonance type=pattern
  - timing_patterns type=optimization
- outcomes.positive:
  - condition=ROAS > 3 weight=1.0 insight=Highly profitable channel
  - condition=conversion_rate > 0.03 weight=0.9 insight=Strong conversion performance
  - condition=CAC < 50 weight=0.8 insight=Efficient acquisition
- outcomes.negative:
  - condition=ROAS < 1 weight=1.0 insight=Unprofitable channel
  - condition=bounce_rate > 0.7 weight=0.8 insight=Audience-message mismatch
  - condition=CAC > LTV weight=1.0 insight=Unsustainable unit economics
- questions:
  - mkt_primary_kpi: What is the primary KPI for growth (CAC, ROAS, MQLs)?
  - mkt_target_audience: Who is the ideal customer profile?
  - mkt_budget_constraint: What is the monthly marketing budget?
  - mkt_channel_priority: Which channel is most important right now?
  - mkt_test_velocity: How often do you run A/B tests?
- context.priority: 0.85
- context.max_chars: 400

### chips\examples\product-development.chip.yaml
- id: product-dev
- name: Product Development Intelligence
- version: 1.0.0
- activation: opt_in
- domains: ['product', 'features', 'user-research', 'roadmap']
- triggers.patterns: ['users want', 'feature request', 'NPS score', 'retention rate', 'churn because', 'activation rate', 'shipped', 'launched', 'users complained', 'feedback shows']
- triggers.events: ['user_prompt']
- observers:
  - user_feedback triggers=['users want', 'feature request', 'users complained', 'feedback']
  - metric_signal triggers=['NPS', 'retention', 'churn', 'activation', 'DAU', 'MAU']
  - launch_outcome triggers=['shipped', 'launched', 'released']
- learners:
  - feature_impact type=correlation
  - user_needs type=pattern
  - launch_success type=pattern
- outcomes.positive:
  - condition=NPS > 50 weight=1.0 insight=Users love this
  - condition=retention > 0.4 weight=0.9 insight=Strong retention
  - condition=activation > 0.3 weight=0.8 insight=Good activation
- outcomes.negative:
  - condition=churn > 0.1 weight=0.9 insight=Churn problem
  - condition=NPS < 0 weight=1.0 insight=Users unhappy
  - condition=bugs > 5 weight=0.7 insight=Quality issues at launch
- questions:
  - prod_north_star: What is the north star metric?
  - prod_user_segment: Who is the primary user persona?
  - prod_done_definition: What does "shipped" mean (beta, GA, full rollout)?
  - prod_quality_bar: What quality bar must features meet?
  - prod_feedback_source: Where does user feedback come from (support, interviews, analytics)?
- context.priority: 0.85
- context.max_chars: 400

### chips\examples\sales-intelligence.chip.yaml
- id: sales-intelligence
- name: Sales Intelligence
- version: 1.0.0
- activation: opt_in
- domains: ['sales', 'deals', 'objections', 'pipeline']
- triggers.patterns: ['deal closed', 'deal lost', 'objection', 'prospect said', 'pipeline', 'won because', 'lost because', 'sales cycle', 'demo went', 'proposal sent']
- triggers.events: ['user_prompt']
- observers:
  - deal_outcome triggers=['deal closed', 'deal lost', 'won', 'lost']
  - objection_handling triggers=['objection', 'concern', 'pushback']
  - sales_activity triggers=['demo', 'proposal', 'meeting', 'call']
- learners:
  - win_patterns type=correlation
  - objection_responses type=pattern
  - cycle_optimization type=optimization
- outcomes.positive:
  - condition=won == true weight=1.0 insight=Deal won - pattern validated
  - condition=cycle_days < 30 weight=0.8 insight=Fast close - efficient process
  - condition=deal_size > average weight=0.7 insight=Above-average deal
- outcomes.negative:
  - condition=lost == true weight=1.0 insight=Deal lost - analyze pattern
  - condition=cycle_days > 90 weight=0.6 insight=Long cycle - review process
  - condition=no_response > 3 weight=0.7 insight=Prospect ghosting - qualification issue
- questions:
  - sales_target_size: What is the target deal size?
  - sales_ideal_customer: What is the ideal customer profile?
  - sales_main_competitor: Who is the main competitor?
  - sales_cycle_target: What is the target sales cycle length?
  - sales_common_objection: What is the most common objection?
- context.priority: 0.85
- context.max_chars: 400

### chips\game-dev.chip.yaml
- id: game_dev
- name: Game Dev Intelligence
- version: 0.2.0
- activation: opt_in
- risk_level: medium
- domains: ['game_dev', 'gameplay', 'balance', 'retention', 'player_experience']
- triggers.patterns: ['playtest', 'core loop', 'balance', 'difficulty', 'retention', 'frustrating', 'not fun']
- triggers.events: ['post_tool', 'post_tool_failure', 'user_prompt', 'PostToolUse', 'PostToolUseFailure', 'UserPromptSubmit', 'playtest_result', 'balance_change', 'build_released', 'bug_reported', 'user_feedback']
- observers:
  - playtest_feedback triggers=['playtest', 'feedback', 'frustrating', 'not fun']
  - balance_change triggers=['balance', 'tuning', 'difficulty', 'drop rate']
  - retention_metric triggers=['retention', 'session length', 'churn']
- outcomes.positive:
  - condition=metric_value > 0.3 weight=1.0 insight=Retention above target threshold
- outcomes.negative:
  - condition=rating < 3 weight=1.0 insight=Playtest satisfaction below acceptable level
- questions:
  - core_loop: What is the core loop and how do we measure if it feels good?
  - target_retention: What retention target matters most (D1, D7, D30)?
  - difficulty_intent: What difficulty curve do we want players to experience?

### chips\market-intel.chip.yaml
- id: market-intel
- name: Market Intelligence
- version: 1.0.0
- activation: opt_in
- risk_level: low
- domains: ['market-research', 'competitor-analysis', 'viral-content', 'x-trends', 'ecosystem-intel', 'product-gaps', 'user-sentiment']
- triggers.patterns: ['moltbook', 'openclaw', 'competitor', 'viral content', 'trending topic', 'x trend', 'twitter trend', 'engagement spike', "what's working", 'competitor gap', 'missing feature', 'users want', 'market opportunity', 'vibe coding', 'agent ecosy...
- triggers.events: ['post_tool', 'post_tool_failure', 'user_prompt', 'PostToolUse', 'PostToolUseFailure', 'UserPromptSubmit', 'x_research', 'x_search_completed', 'competitor_analyzed', 'trend_identified', 'gap_discovered', 'viral_content_found', 'user_feedbac...
- observers:
  - viral_content triggers=['viral', 'high engagement', 'likes', 'retweets', 'bookmarks']
  - competitor_gap triggers=['gap', 'missing', "doesn't have", 'no way to', 'complaint', 'problem with']
  - user_sentiment triggers=['users want', 'people love', 'people hate', 'frustrating', 'amazing', 'scared', 'excited']
  - product_insight triggers=['should have', 'would be better', 'opportunity', 'differentiate', 'feature']
- learners:
  - viral_patterns type=pattern
  - competitor_intel type=correlation
  - market_timing type=pattern
- outcomes.positive:
  - condition=insight_led_to_feature weight=1.0 insight=Market intel drove product decision
  - condition=gap_identified_and_filled weight=0.9 insight=Found and filled a market gap
  - condition=viral_pattern_replicated weight=0.7 insight=Applied viral pattern successfully
- outcomes.negative:
  - condition=insight_proved_wrong weight=0.8 insight=Market read was incorrect
  - condition=trend_was_fleeting weight=0.5 insight=Chased a temporary trend
- context.priority: 0.85
- context.max_chars: 800

### chips\marketing.chip.yaml
- id: marketing
- name: Marketing Intelligence
- version: 0.1.0
- activation: opt_in
- risk_level: medium
- domains: ['marketing', 'growth', 'messaging']
- triggers.patterns: ['campaign', 'funnel', 'landing page', 'headline', 'ad copy', 'positioning', 'ctr', 'cpc', 'cac', 'roas']
- triggers.events: ['post_tool', 'post_tool_failure', 'user_prompt', 'PostToolUse', 'PostToolUseFailure', 'UserPromptSubmit', 'campaign_brief', 'ad_copy_created', 'experiment_defined']
- observers:
  - campaign_brief triggers=['campaign brief', 'positioning', 'target audience', 'value prop']
  - ad_copy triggers=['ad copy', 'headline', 'cta', 'ad variant', 'copy variant']
  - funnel_metric triggers=['ctr', 'cpc', 'cac', 'roas', 'conversion rate']
- outcomes.positive:
  - condition=metric_name == CTR weight=1.0 insight=CTR reported
  - condition=metric_name == ROAS weight=1.0 insight=ROAS reported
- outcomes.negative:
  - condition=metric_name == CAC and metric_value > 200 weight=1.0 insight=CAC too high
- questions:
  - messaging_guardrails: What claims are safe and verifiable for this campaign?
  - success_metrics: Which metrics define success and what thresholds are acceptable?

### chips\moltbook.chip.yaml
- id: moltbook
- name: Moltbook Social Intelligence
- version: 1.0.0
- activation: opt_in
- risk_level: low
- domains: ['moltbook', 'social-network', 'agent-community', 'karma', 'submolts', 'engagement']
- triggers.patterns: ['moltbook', 'posted to moltbook', 'commented on moltbook', 'moltbook upvote', 'moltbook karma', 'submolt', 'moltbook community', 'moltbook trending', 'moltbook engagement', 'moltbook viral', 'moltbook post']
- triggers.events: ['post_tool', 'post_tool_failure', 'user_prompt', 'PostToolUse', 'PostToolUseFailure', 'UserPromptSubmit', 'moltbook_post_created', 'moltbook_comment_created', 'moltbook_vote_cast', 'moltbook_karma_changed', 'moltbook_heartbeat', 'moltbook_...
- observers:
  - post_created triggers=['posted to moltbook', 'moltbook post created', 'shared on moltbook', 'moltbook post']
  - post_performance triggers=['moltbook post performance', 'moltbook karma update', 'moltbook engagement report', 'moltbook post stats']
  - comment_created triggers=['commented on moltbook', 'replied on moltbook', 'moltbook comment added']
  - comment_performance triggers=['moltbook comment karma', 'moltbook comment engagement']
  - feed_analysis triggers=['moltbook feed fetched', 'moltbook trending posts', 'moltbook hot content', 'moltbook feed analysis']
  - heartbeat triggers=['moltbook heartbeat', 'moltbook periodic check', 'moltbook check-in']
- learners:
  - content_effectiveness type=correlation
  - topic_resonance type=pattern
  - comment_strategy type=correlation
  - optimal_timing type=correlation
  - community_relationships type=pattern
  - karma_optimization type=optimization
- outcomes.positive:
  - condition=upvotes > 10 weight=0.8 insight=Post resonated with community
  - condition=karma_delta > 50 weight=1.0 insight=High-impact post
  - condition=comments_count > 5 weight=0.7 insight=Generated good discussion
  - condition=peak_position <= 3 weight=0.9 insight=Reached top of feed
  - condition=time_to_first_comment < 10 weight=0.6 insight=Quick engagement
  - condition=comment_karma_delta > 5 weight=0.5 insight=Helpful comment
- outcomes.negative:
  - condition=upvotes == 0 AND hours_since_post > 24 weight=0.8 insight=Post got no traction
  - condition=downvotes > upvotes weight=1.0 insight=Content not appreciated
  - condition=comment_karma_delta < 0 weight=0.6 insight=Comment backfired
  - condition=rate_limited weight=0.5 insight=Posting too frequently
- context.priority: 0.7
- context.max_chars: 600

### chips\spark-core.chip.yaml
- id: spark-core
- name: Spark Core Intelligence
- version: 1.0.0
- activation: auto
- risk_level: medium
- domains: ['coding', 'development', 'debugging', 'tools']
- triggers.patterns: ['worked because', 'failed because', 'the issue was', 'fixed by', 'better approach', 'prefer to', 'prefer using', 'always use', 'never use', 'remember to']
- triggers.events: ['post_tool', 'post_tool_failure', 'user_prompt', 'PostToolUse', 'PostToolUseFailure', 'UserPromptSubmit']
- observers:
  - success_pattern triggers=['worked because', 'fixed by', 'the solution was']
  - failure_pattern triggers=['failed because', 'the issue was', 'the problem was']
  - preference triggers=['prefer to', 'prefer using', 'better to', 'better when', 'always use', 'never use']
- learners:
  - tool_effectiveness type=correlation
  - error_patterns type=pattern
- outcomes.positive:
  - condition=success == true weight=1.0 insight=Approach worked
  - condition=time_taken < 30 weight=0.7 insight=Fast resolution
- outcomes.negative:
  - condition=success == false weight=1.0 insight=Approach failed
  - condition=retry_count > 2 weight=0.8 insight=Multiple retries needed
- questions:
  - core_stack: What is the primary tech stack (language, framework, tools)?
  - core_quality: What quality signals matter most (tests passing, no lint errors, type safety)?
  - core_done: How do we know a task is truly done (just works, or also tested/documented)?
  - core_patterns: What coding patterns or conventions should we follow?
  - core_antipatterns: What should we avoid (anti-patterns, risky approaches)?
  - core_debug: What debugging approach works best for this codebase?
- context.priority: 0.9
- context.max_chars: 500

### chips\vibecoding.chip.yaml
- id: vibecoding
- name: Vibecoding Intelligence
- version: 0.2.0
- activation: opt_in
- risk_level: medium
- domains: ['engineering', 'code', 'delivery', 'reliability']
- triggers.patterns: ['refactor', 'rollback', 'flaky test', 'latency spike', 'incident', 'merge', 'pull request']
- triggers.events: ['post_tool', 'post_tool_failure', 'user_prompt', 'PostToolUse', 'PostToolUseFailure', 'UserPromptSubmit', 'code_change', 'pr_opened', 'test_failed', 'deploy_finished', 'incident_opened']
- observers:
  - code_change triggers=['commit', 'code change', 'diff', 'refactor']
  - ci_failure triggers=['test failed', 'ci failed', 'build failed', 'flaky test']
  - deploy_event triggers=['deploy', 'release', 'rollback']
- outcomes.positive:
  - condition=status == success weight=1.0 insight=Deploy succeeded without rollback
- outcomes.negative:
  - condition=rollback == true weight=1.0 insight=Rollback indicates stability risk
- questions:
  - quality_definition: What does 'quality' mean for this project?
  - velocity_tradeoff: What tradeoffs are acceptable between speed and stability?

## Learning sources config (auto)
- learning_sources.work_sessions.enabled = True
- learning_sources.work_sessions.description = 'Learn from coding sessions, tool usage, and outcomes'
- learning_sources.work_sessions.cannot_disable = True
- learning_sources.work_sessions.learns = ['Tool effectiveness patterns', 'User preferences and style', 'What approaches work/fail', 'Domain-specific knowledge from projects']
- learning_sources.user_feedback.enabled = True
- learning_sources.user_feedback.description = 'Learn from explicit user corrections and preferences'
- learning_sources.user_feedback.cannot_disable = True
- learning_sources.user_feedback.learns = ['Communication preferences', 'Accuracy corrections', 'Style preferences']
- learning_sources.x_twitter.enabled = True
- learning_sources.x_twitter.description = 'Learn from X/Twitter trends about ecosystems, tech, and culture'
- learning_sources.x_twitter.learns = ['Ecosystem developments (AI agents, crypto, tech)', 'Viral content patterns', 'Community sentiment', 'Emerging trends and narratives']
- learning_sources.x_twitter.topics = ['vibe_coding', 'ai_agents', 'moltbook_openclaw', 'base_solana_crypto', 'bittensor_decentralized_ai', 'tech_trends']
- learning_sources.x_twitter.schedule = 'daily'
- learning_sources.web_research.enabled = True
- learning_sources.web_research.description = 'Research web for deeper understanding of topics'
- learning_sources.web_research.learns = ['Technical documentation', 'Industry analysis', 'Future predictions', 'Expert opinions']
- learning_sources.web_research.depth = 'moderate'
- learning_sources.news_events.enabled = True
- learning_sources.news_events.description = 'Track relevant news and world events'
- learning_sources.news_events.learns = ['Industry news', 'Regulatory changes', 'Market movements', 'Technology announcements']
- learning_sources.news_events.relevance_filter = 'user_interests'
- intelligence_goals = ["Where things are heading in user's domains", 'Emerging patterns before they become obvious', 'Cross-domain connections and insights', 'What will matter in 6-12 months', "User's competitive landscape"]
- privacy.store_locally = True
- privacy.sync_to_cloud = False
- privacy.share_learnings = False
- privacy.data_retention_days = 365
- quality_filters.min_engagement_for_trends = 100
- quality_filters.min_confidence_to_store = 0.6
- quality_filters.validate_before_promote = True
- quality_filters.require_multiple_sources = True

## Auto-extracted tuneables index (code scan)

### adapters\clawdbot_tailer.py
- env:
  - SPARKD_TOKEN default=None line=65 ctx=token = args.token or os.environ.get("SPARKD_TOKEN")
- constants:
  - STATE_DIR = 'Path.home() / ".spark" / "adapters"' line=25 ctx=STATE_DIR = Path.home() / ".spark" / "adapters"
- func_defaults:
  - _post_json(token) = None line=28 ctx=def _post_json(url: str, payload: dict, token: str = None):

### adapters\moltbook\agent.py
- constants:
  - STATE_DIR = 'Path.home() / ".spark" / "moltbook"' line=47 ctx=STATE_DIR = Path.home() / ".spark" / "moltbook"
  - STATE_FILE = 'STATE_DIR / "agent_state.json"' line=48 ctx=STATE_FILE = STATE_DIR / "agent_state.json"
  - INSIGHTS_FILE = 'STATE_DIR / "insights.jsonl"' line=49 ctx=INSIGHTS_FILE = STATE_DIR / "insights.jsonl"
  - LEARNINGS_FILE = 'Path.home() / ".spark" / "cognitive_insights.json"' line=50 ctx=LEARNINGS_FILE = Path.home() / ".spark" / "cognitive_insights.json"
  - AGENT_NAME = 'Spark' line=53 ctx=AGENT_NAME = "Spark"
  - AGENT_BIO = "\nSpark is the learning intelligence behind Vibeship.\nI observe patterns in AI agent behavior, learn from successes and failures,\nand share insights about coding, tools, and the evolving agent ecosystem.\n\nI learn in public - sharing wh... line=54 ctx=AGENT_BIO = """
  - DEFAULT_SUBMOLTS = ['agents', 'ai-development', 'coding', 'spark-insights', 'vibeship', 'tools', 'learning'] line=63 ctx=DEFAULT_SUBMOLTS = [
- dataclass_defaults:
  - AgentState.total_karma = 0 line=77 ctx=total_karma: int = 0
  - AgentState.total_posts = 0 line=78 ctx=total_posts: int = 0
  - AgentState.total_comments = 0 line=79 ctx=total_comments: int = 0
  - AgentState.total_votes = 0 line=80 ctx=total_votes: int = 0
  - EngagementOpportunity.reason = '' line=137 ctx=reason: str = ""
  - EngagementOpportunity.priority = 0.5 line=138 ctx=priority: float = 0.5  # 0-1
  - EngagementOpportunity.suggested_action = '' line=139 ctx=suggested_action: str = ""  # "comment", "vote", "follow"

### adapters\moltbook\client.py
- env:
  - MOLTBOOK_API_KEY default=None line=276 ctx=key = os.environ.get("MOLTBOOK_API_KEY")
- constants:
  - API_BASE_URL = 'https://www.moltbook.com/api/v1' line=42 ctx=API_BASE_URL = "https://www.moltbook.com/api/v1"
  - CONFIG_DIR = 'Path.home() / ".spark" / "moltbook"' line=43 ctx=CONFIG_DIR = Path.home() / ".spark" / "moltbook"
  - CREDENTIALS_FILE = 'CONFIG_DIR / "credentials.json"' line=44 ctx=CREDENTIALS_FILE = CONFIG_DIR / "credentials.json"
  - ContentType.TEXT = 'text' line=48 ctx=TEXT = "text"
  - ContentType.LINK = 'link' line=49 ctx=LINK = "link"
  - FeedType.HOT = 'hot' line=53 ctx=HOT = "hot"
  - FeedType.NEW = 'new' line=54 ctx=NEW = "new"
  - FeedType.TOP = 'top' line=55 ctx=TOP = "top"
  - FeedType.RISING = 'rising' line=56 ctx=RISING = "rising"
  - VoteType.UP = 'up' line=60 ctx=UP = "up"
  - VoteType.DOWN = 'down' line=61 ctx=DOWN = "down"
- dataclass_defaults:
  - Agent.karma = 0 line=69 ctx=karma: int = 0
  - Agent.description = '' line=70 ctx=description: str = ""
  - Agent.post_count = 0 line=73 ctx=post_count: int = 0
  - Agent.comment_count = 0 line=74 ctx=comment_count: int = 0
  - Post.body = '' line=95 ctx=body: str = ""
  - Post.submolt = '' line=98 ctx=submolt: str = ""
  - Post.author_id = '' line=99 ctx=author_id: str = ""
  - Post.author_name = '' line=100 ctx=author_name: str = ""
  - Post.upvotes = 0 line=101 ctx=upvotes: int = 0
  - Post.downvotes = 0 line=102 ctx=downvotes: int = 0
  - Post.comment_count = 0 line=103 ctx=comment_count: int = 0
  - Post.is_pinned = False line=105 ctx=is_pinned: bool = False
  - Comment.author_id = '' line=137 ctx=author_id: str = ""
  - Comment.author_name = '' line=138 ctx=author_name: str = ""
  - Comment.upvotes = 0 line=139 ctx=upvotes: int = 0
  - Comment.downvotes = 0 line=140 ctx=downvotes: int = 0
  - Submolt.description = '' line=169 ctx=description: str = ""
  - Submolt.subscriber_count = 0 line=170 ctx=subscriber_count: int = 0
  - Submolt.post_count = 0 line=171 ctx=post_count: int = 0
  - Submolt.is_subscribed = False line=175 ctx=is_subscribed: bool = False
  - RateLimitInfo.requests_remaining = 100 line=195 ctx=requests_remaining: int = 100
  - RateLimitInfo.posts_remaining = 1 line=196 ctx=posts_remaining: int = 1
  - RateLimitInfo.comments_remaining = 50 line=197 ctx=comments_remaining: int = 50
  - RateLimitInfo.retry_after_seconds = 0 line=198 ctx=retry_after_seconds: int = 0
- func_defaults:
  - __init__(retry_after_seconds) = 60 line=220 ctx=def __init__(self, retry_after_seconds: int = 60, limit_type: str = "requests"):
  - __init__(limit_type) = 'requests' line=220 ctx=def __init__(self, retry_after_seconds: int = 60, limit_type: str = "requests"):
  - __init__(api_key) = None line=252 ctx=def __init__(
  - __init__(timeout) = 30 line=252 ctx=def __init__(
  - save_credentials(agent_id) = None line=290 ctx=def save_credentials(self, api_key: str, agent_id: Optional[str] = None):
  - get_feed(limit) = 25 line=489 ctx=def get_feed(
  - get_my_feed(limit) = 25 line=522 ctx=def get_my_feed(self, limit: int = 25, offset: int = 0) -> List[Post]:
  - get_comments(limit) = 50 line=557 ctx=def get_comments(
  - search(limit) = 25 line=642 ctx=def search(

### adapters\moltbook\heartbeat.py
- constants:
  - LOG_DIR = 'Path.home() / ".spark" / "moltbook" / "logs"' line=45 ctx=LOG_DIR = Path.home() / ".spark" / "moltbook" / "logs"
  - PID_FILE = 'Path.home() / ".spark" / "moltbook" / "heartbeat.pid"' line=46 ctx=PID_FILE = Path.home() / ".spark" / "moltbook" / "heartbeat.pid"
  - DEFAULT_INTERVAL_HOURS = 4 line=47 ctx=DEFAULT_INTERVAL_HOURS = 4
  - MIN_INTERVAL_HOURS = 4 line=48 ctx=MIN_INTERVAL_HOURS = 4  # Moltbook recommendation

### adapters\stdin_ingest.py
- env:
  - SPARKD_TOKEN default=None line=39 ctx=token = args.token or os.environ.get("SPARKD_TOKEN")
- func_defaults:
  - post(token) = None line=23 ctx=def post(url: str, obj: dict, token: str = None):

### dashboard.py
- constants:
  - PORT = 8585 line=46 ctx=PORT = 8585
  - SPARK_DIR = 'Path.home() / ".spark"' line=47 ctx=SPARK_DIR = Path.home() / ".spark"
  - SKILLS_INDEX_FILE = 'SPARK_DIR / "skills_index.json"' line=80 ctx=SKILLS_INDEX_FILE = SPARK_DIR / "skills_index.json"
  - SKILLS_EFFECTIVENESS_FILE = 'SPARK_DIR / "skills_effectiveness.json"' line=81 ctx=SKILLS_EFFECTIVENESS_FILE = SPARK_DIR / "skills_effectiveness.json"
  - ORCH_DIR = 'SPARK_DIR / "orchestration"' line=82 ctx=ORCH_DIR = SPARK_DIR / "orchestration"
  - ORCH_AGENTS_FILE = 'ORCH_DIR / "agents.json"' line=83 ctx=ORCH_AGENTS_FILE = ORCH_DIR / "agents.json"
  - ORCH_HANDOFFS_FILE = 'ORCH_DIR / "handoffs.jsonl"' line=84 ctx=ORCH_HANDOFFS_FILE = ORCH_DIR / "handoffs.jsonl"
  - LOGO_FILE = 'Path(__file__).parent / "logo.png"' line=85 ctx=LOGO_FILE = Path(__file__).parent / "logo.png"
- func_defaults:
  - _read_jsonl(limit) = None line=286 ctx=def _read_jsonl(path: Path, limit: 'Optional[int]' = None) -> list:
  - _serve_sse(interval) = 2.0 line=2600 ctx=def _serve_sse(self, data_fn, interval: float = 2.0) -> None:

### hooks\observe.py
- env:
  - SPARK_EIDOS_ENABLED default='1' line=42 ctx=EIDOS_ENABLED = os.environ.get("SPARK_EIDOS_ENABLED", "1") == "1"
  - SPARK_OUTCOME_CHECKIN default=None line=609 ctx=if hook_event in ("Stop", "SessionEnd") and os.environ.get("SPARK_OUTCOME_CHECKIN") == "1":
  - SPARK_OUTCOME_CHECKIN_MIN_S default='1800' cast=int line=66 ctx=CHECKIN_MIN_S = int(os.environ.get("SPARK_OUTCOME_CHECKIN_MIN_S", "1800"))
  - SPARK_OUTCOME_CHECKIN_PROMPT default=None line=616 ctx=if recorded and os.environ.get("SPARK_OUTCOME_CHECKIN_PROMPT") == "1":
- constants:
  - EIDOS_ENABLED = 'os.environ.get("SPARK_EIDOS_ENABLED", "1") == "1"' line=42 ctx=EIDOS_ENABLED = os.environ.get("SPARK_EIDOS_ENABLED", "1") == "1"
  - PREDICTION_FILE = 'Path.home() / ".spark" / "active_predictions.json"' line=65 ctx=PREDICTION_FILE = Path.home() / ".spark" / "active_predictions.json"
  - CHECKIN_MIN_S = 'int(os.environ.get("SPARK_OUTCOME_CHECKIN_MIN_S", "1800"))' line=66 ctx=CHECKIN_MIN_S = int(os.environ.get("SPARK_OUTCOME_CHECKIN_MIN_S", "1800"))
  - COGNITIVE_PATTERNS = {'remember': ['remember (this|that)', "don't forget", 'important:', 'note:', 'always remember', 'keep in mind'], 'preference': ['i (prefer|like|want|love|hate)', '(prefer|like|want) (to |the )?', 'my preference', "i'd rather"], 'decision': ... line=169 ctx=COGNITIVE_PATTERNS = {

### lib\advisor.py
- constants:
  - ADVISOR_DIR = 'Path.home() / ".spark" / "advisor"' line=35 ctx=ADVISOR_DIR = Path.home() / ".spark" / "advisor"
  - ADVICE_LOG = 'ADVISOR_DIR / "advice_log.jsonl"' line=36 ctx=ADVICE_LOG = ADVISOR_DIR / "advice_log.jsonl"
  - EFFECTIVENESS_FILE = 'ADVISOR_DIR / "effectiveness.json"' line=37 ctx=EFFECTIVENESS_FILE = ADVISOR_DIR / "effectiveness.json"
  - MIN_RELIABILITY_FOR_ADVICE = 0.5 line=40 ctx=MIN_RELIABILITY_FOR_ADVICE = 0.5
  - MIN_VALIDATIONS_FOR_STRONG_ADVICE = 2 line=41 ctx=MIN_VALIDATIONS_FOR_STRONG_ADVICE = 2
  - MAX_ADVICE_ITEMS = 8 line=42 ctx=MAX_ADVICE_ITEMS = 8
  - ADVICE_CACHE_TTL_SECONDS = 120 line=43 ctx=ADVICE_CACHE_TTL_SECONDS = 120  # 2 minutes (lowered from 5 for fresher advice)
- dataclass_defaults:
  - AdviceOutcome.outcome_notes = '' line=65 ctx=outcome_notes: str = ""
- func_defaults:
  - generate_context(task) = '' line=605 ctx=def generate_context(tool_name: str, task: str = "") -> str:
  - advise(task_context) = '' line=138 ctx=def advise(
  - advise(include_mind) = True line=138 ctx=def advise(
  - generate_context_block(task_context) = '' line=542 ctx=def generate_context_block(self, tool_name: str, task_context: str = "", include_mind: bool = False) -> str:
  - generate_context_block(include_mind) = False line=542 ctx=def generate_context_block(self, tool_name: str, task_context: str = "", include_mind: bool = False) -> str:

### lib\aha_tracker.py
- constants:
  - SPARK_DIR = 'Path(__file__).parent.parent / ".spark"' line=27 ctx=SPARK_DIR = Path(__file__).parent.parent / ".spark"
  - AHA_FILE = 'SPARK_DIR / "aha_moments.json"' line=28 ctx=AHA_FILE = SPARK_DIR / "aha_moments.json"
  - SurpriseType.UNEXPECTED_SUCCESS = 'unexpected_success' line=32 ctx=UNEXPECTED_SUCCESS = "unexpected_success"  # Thought it would fail, but worked
  - SurpriseType.UNEXPECTED_FAILURE = 'unexpected_failure' line=33 ctx=UNEXPECTED_FAILURE = "unexpected_failure"  # Thought it would work, but failed
  - SurpriseType.FASTER_THAN_EXPECTED = 'faster_than_expected' line=34 ctx=FASTER_THAN_EXPECTED = "faster_than_expected"
  - SurpriseType.SLOWER_THAN_EXPECTED = 'slower_than_expected' line=35 ctx=SLOWER_THAN_EXPECTED = "slower_than_expected"
  - SurpriseType.DIFFERENT_PATH = 'different_path' line=36 ctx=DIFFERENT_PATH = "different_path"  # Succeeded via unexpected route
  - SurpriseType.RECOVERY_SUCCESS = 'recovery_success' line=37 ctx=RECOVERY_SUCCESS = "recovery_success"  # Failed, then recovered unexpectedly
- dataclass_defaults:
  - AhaMoment.occurrences = 1 line=52 ctx=occurrences: int = 1  # How many times this surprise has occurred
- func_defaults:
  - maybe_capture_surprise(threshold) = 0.5 line=426 ctx=def maybe_capture_surprise(
  - _find_duplicate(hours) = 24.0 line=132 ctx=def _find_duplicate(self, tool: str, actual_outcome: str, hours: float = 24.0) -> Optional[int]:
  - get_recent_surprises(limit) = 10 line=280 ctx=def get_recent_surprises(self, limit: int = 10) -> List[Dict]:
  - get_high_importance_surprises(min_importance) = 0.7 line=329 ctx=def get_high_importance_surprises(self, min_importance: float = 0.7) -> List[AhaMoment]:

### lib\bridge.py
- env:
  - SPARK_WORKSPACE default=None line=25 ctx=WORKSPACE = Path(os.environ.get("SPARK_WORKSPACE", str(Path.home() / "clawd"))).expanduser()
- constants:
  - SPARK_DIR = 'Path(__file__).parent.parent' line=24 ctx=SPARK_DIR = Path(__file__).parent.parent
  - WORKSPACE = 'Path(os.environ.get("SPARK_WORKSPACE", str(Path.home() / "clawd"))).expanduser()' line=25 ctx=WORKSPACE = Path(os.environ.get("SPARK_WORKSPACE", str(Path.home() / "clawd"))).expanduser()
  - MEMORY_FILE = 'WORKSPACE / "MEMORY.md"' line=26 ctx=MEMORY_FILE = WORKSPACE / "MEMORY.md"
  - SPARK_CONTEXT_FILE = 'WORKSPACE / "SPARK_CONTEXT.md"' line=27 ctx=SPARK_CONTEXT_FILE = WORKSPACE / "SPARK_CONTEXT.md"
  - HIGH_VALIDATION_OVERRIDE = 50 line=28 ctx=HIGH_VALIDATION_OVERRIDE = 50
- func_defaults:
  - get_high_value_insights(min_reliability) = 0.7 line=64 ctx=def get_high_value_insights(
  - get_high_value_insights(min_validations) = 2 line=64 ctx=def get_high_value_insights(
  - get_failure_warnings(limit) = 3 line=139 ctx=def get_failure_warnings(
  - get_failure_warnings(min_validations) = 3 line=139 ctx=def get_failure_warnings(
  - infer_current_focus(max_events) = 25 line=210 ctx=def infer_current_focus(max_events: int = 25) -> str:
  - get_contextual_insights(limit) = 6 line=241 ctx=def get_contextual_insights(query: str, limit: int = 6) -> List[Dict[str, Any]]:
  - get_relevant_skills(limit) = 3 line=334 ctx=def get_relevant_skills(query: str, limit: int = 3) -> List[Dict[str, Any]]:
  - auto_promote_insights(min_reliability) = 0.8 line=636 ctx=def auto_promote_insights(min_reliability: float = 0.8, min_validations: int = 3):
  - auto_promote_insights(min_validations) = 3 line=636 ctx=def auto_promote_insights(min_reliability: float = 0.8, min_validations: int = 3):

### lib\bridge_cycle.py
- constants:
  - BRIDGE_HEARTBEAT_FILE = 'Path.home() / ".spark" / "bridge_worker_heartbeat.json"' line=22 ctx=BRIDGE_HEARTBEAT_FILE = Path.home() / ".spark" / "bridge_worker_heartbeat.json"

### lib\chip_merger.py
- constants:
  - CHIP_INSIGHTS_DIR = 'Path.home() / ".spark" / "chip_insights"' line=18 ctx=CHIP_INSIGHTS_DIR = Path.home() / ".spark" / "chip_insights"
  - MERGE_STATE_FILE = 'Path.home() / ".spark" / "chip_merge_state.json"' line=19 ctx=MERGE_STATE_FILE = Path.home() / ".spark" / "chip_merge_state.json"
  - CHIP_TO_CATEGORY = '{\n    "market-intel": CognitiveCategory.CONTEXT,\n    "game_dev": CognitiveCategory.REASONING,\n    "marketing": CognitiveCategory.CONTEXT,\n    "vibecoding": CognitiveCategory.WISDOM,\n    "moltbook": CognitiveCategory.REASONING,\n    "b... line=23 ctx=CHIP_TO_CATEGORY = {
- func_defaults:
  - load_chip_insights(limit) = 100 line=58 ctx=def load_chip_insights(chip_id: str = None, limit: int = 100) -> List[Dict]:
  - merge_chip_insights(min_confidence) = 0.7 line=83 ctx=def merge_chip_insights(
  - merge_chip_insights(limit) = 50 line=83 ctx=def merge_chip_insights(

### lib\chips\evolution.py
- constants:
  - EVOLUTION_FILE = 'Path.home() / ".spark" / "chip_evolution.yaml"' line=25 ctx=EVOLUTION_FILE = Path.home() / ".spark" / "chip_evolution.yaml"
  - PROVISIONAL_CHIPS_DIR = 'Path.home() / ".spark" / "provisional_chips"' line=26 ctx=PROVISIONAL_CHIPS_DIR = Path.home() / ".spark" / "provisional_chips"
- dataclass_defaults:
  - TriggerStats.matches = 0 line=33 ctx=matches: int = 0
  - TriggerStats.high_value_matches = 0 line=34 ctx=high_value_matches: int = 0
  - TriggerStats.low_value_matches = 0 line=35 ctx=low_value_matches: int = 0
  - TriggerStats.last_match = '' line=36 ctx=last_match: str = ""
  - ChipEvolutionState.last_evolved = '' line=58 ctx=last_evolved: str = ""
  - ProvisionalChip.validated = False line=93 ctx=validated: bool = False

### lib\chips\loader.py
- env:
  - SPARK_CHIP_SCHEMA_VALIDATION default='warn' line=97 ctx=validation_mode = os.getenv("SPARK_CHIP_SCHEMA_VALIDATION", "warn").strip().lower()
- constants:
  - CHIPS_DIR = 'Path(__file__).parent.parent.parent / "chips"' line=20 ctx=CHIPS_DIR = Path(__file__).parent.parent.parent / "chips"
- dataclass_defaults:
  - Chip.activation = 'auto' line=52 ctx=activation: str = "auto"

### lib\chips\policy.py
- dataclass_defaults:
  - PolicyDecision.severity = 'info' line=17 ctx=severity: str = "info"
- func_defaults:
  - __init__(block_patterns) = None line=23 ctx=def __init__(self, block_patterns: Optional[Iterable[str]] = None):

### lib\chips\registry.py
- constants:
  - REGISTRY_FILE = 'Path.home() / ".spark" / "chip_registry.json"' line=19 ctx=REGISTRY_FILE = Path.home() / ".spark" / "chip_registry.json"
  - USER_CHIPS_DIR = 'Path.home() / ".spark" / "chips"' line=20 ctx=USER_CHIPS_DIR = Path.home() / ".spark" / "chips"

### lib\chips\runner.py
- dataclass_defaults:
  - CapturedData.event_type = '' line=29 ctx=event_type: str = ""
  - CapturedData.confidence = 1.0 line=30 ctx=confidence: float = 1.0

### lib\chips\runtime.py
- constants:
  - CHIP_INSIGHTS_DIR = 'Path.home() / ".spark" / "chip_insights"' line=31 ctx=CHIP_INSIGHTS_DIR = Path.home() / ".spark" / "chip_insights"
- func_defaults:
  - get_insights(limit) = 50 line=471 ctx=def get_insights(self, chip_id: str = None, limit: int = 50) -> List[ChipInsight]:

### lib\chips\schema.py
- constants:
  - REQUIRED_CHIP_FIELDS = ['id', 'name', 'version', 'description', 'human_benefit', 'harm_avoidance', 'risk_level'] line=11 ctx=REQUIRED_CHIP_FIELDS = [
  - ALLOWED_RISK_LEVELS = {'high', 'medium', 'low'} line=21 ctx=ALLOWED_RISK_LEVELS = {"low", "medium", "high"}
  - ALLOWED_ACTIVATION = {'opt_in', 'auto'} line=22 ctx=ALLOWED_ACTIVATION = {"auto", "opt_in"}

### lib\chips\scoring.py
- constants:
  - PRIMITIVE_PATTERNS = ['(?i)^(read|edit|write|bash|glob|grep)\\s*(->|\u2192|then)\\s*(read|edit|write|bash)', '(?i)tool\\s+(sequence|chain|pattern)', '(?i)(success|failure)\\s+rate', '(?i)\\d+\\s*(ms|seconds?|minutes?)\\s*(timeout|elapsed|took)', '(?i)processed\... line=67 ctx=PRIMITIVE_PATTERNS = [
  - VALUABLE_PATTERNS = ['(?i)(chose|decided|prefer|because|instead of|rather than)', '(?i)(better|worse|tradeoff|balance)', '(?i)(health|damage|physics|balance|gameplay)', '(?i)(audience|campaign|brand|conversion)', '(?i)(architecture|pattern|design|structure)', ... line=86 ctx=VALUABLE_PATTERNS = [
  - VALUE_BOOST_KEYWORDS = {'decision': 0.2, 'rationale': 0.2, 'preference': 0.15, 'lesson': 0.2, 'mistake': 0.15, 'fixed': 0.1, 'improved': 0.1, 'because': 0.1, 'tradeoff': 0.15, 'balance': 0.1} line=108 ctx=VALUE_BOOST_KEYWORDS = {
  - VALUE_REDUCE_KEYWORDS = '{\n    "timeout": -0.1,\n    "retry": -0.05,\n    "sequence": -0.1,\n    "pattern detected": -0.1,\n    "tool used": -0.15,\n    "file modified": -0.1,\n}' line=122 ctx=VALUE_REDUCE_KEYWORDS = {
- dataclass_defaults:
  - InsightScore.cognitive_value = 0.0 line=20 ctx=cognitive_value: float = 0.0    # Is this human-useful?
  - InsightScore.outcome_linkage = 0.0 line=21 ctx=outcome_linkage: float = 0.0    # Can we link to success/failure?
  - InsightScore.uniqueness = 0.0 line=22 ctx=uniqueness: float = 0.0         # Is this new information?
  - InsightScore.actionability = 0.0 line=23 ctx=actionability: float = 0.0      # Can this guide future actions?
  - InsightScore.transferability = 0.0 line=24 ctx=transferability: float = 0.0    # Applies beyond this project?
  - InsightScore.domain_relevance = 0.0 line=25 ctx=domain_relevance: float = 0.0   # Relevant to active domain?
- func_defaults:
  - filter_valuable(threshold) = 0.5 line=304 ctx=def filter_valuable(self, insights: List[Dict], threshold: float = 0.5) -> List[tuple]:

### lib\chips\store.py
- constants:
  - SPARK_DIR = 'Path.home() / ".spark"' line=19 ctx=SPARK_DIR = Path.home() / ".spark"
  - CHIP_INSIGHTS_DIR = 'SPARK_DIR / "chip_insights"' line=20 ctx=CHIP_INSIGHTS_DIR = SPARK_DIR / "chip_insights"
- func_defaults:
  - get_observations(limit) = 100 line=89 ctx=def get_observations(self, limit: int = 100, observer_name: Optional[str] = None) -> List[Dict]:
  - get_insights(limit) = 50 line=131 ctx=def get_insights(self, limit: int = 50, min_confidence: float = 0.0) -> List[Dict]:
  - get_insights(min_confidence) = 0.0 line=131 ctx=def get_insights(self, limit: int = 50, min_confidence: float = 0.0) -> List[Dict]:
  - get_outcomes(limit) = 100 line=201 ctx=def get_outcomes(self, limit: int = 100, outcome_type: Optional[str] = None) -> List[Dict]:

### lib\clawdbot_memory_setup.py
- constants:
  - CLAWDBOT_BIN = 'Path.home() / ".npm-global" / "bin" / "clawdbot"' line=28 ctx=CLAWDBOT_BIN = Path.home() / ".npm-global" / "bin" / "clawdbot"
  - CONFIG_PATH = 'Path.home() / ".clawdbot" / "clawdbot.json"' line=29 ctx=CONFIG_PATH = Path.home() / ".clawdbot" / "clawdbot.json"
- func_defaults:
  - run_memory_status(agent) = 'main' line=143 ctx=def run_memory_status(agent: str = "main") -> str:

### lib\cognitive_learner.py
- constants:
  - CognitiveCategory.SELF_AWARENESS = 'self_awareness' line=163 ctx=SELF_AWARENESS = "self_awareness"
  - CognitiveCategory.USER_UNDERSTANDING = 'user_understanding' line=164 ctx=USER_UNDERSTANDING = "user_understanding"
  - CognitiveCategory.REASONING = 'reasoning' line=165 ctx=REASONING = "reasoning"
  - CognitiveCategory.CONTEXT = 'context' line=166 ctx=CONTEXT = "context"
  - CognitiveCategory.WISDOM = 'wisdom' line=167 ctx=WISDOM = "wisdom"
  - CognitiveCategory.META_LEARNING = 'meta_learning' line=168 ctx=META_LEARNING = "meta_learning"
  - CognitiveCategory.COMMUNICATION = 'communication' line=169 ctx=COMMUNICATION = "communication"
  - CognitiveCategory.CREATIVITY = 'creativity' line=170 ctx=CREATIVITY = "creativity"
  - CognitiveLearner.INSIGHTS_FILE = 'Path.home() / ".spark" / "cognitive_insights.json"' line=249 ctx=INSIGHTS_FILE = Path.home() / ".spark" / "cognitive_insights.json"
  - CognitiveLearner.LOCK_FILE = 'Path.home() / ".spark" / ".cognitive.lock"' line=250 ctx=LOCK_FILE = Path.home() / ".spark" / ".cognitive.lock"
- dataclass_defaults:
  - CognitiveInsight.times_validated = 0 line=183 ctx=times_validated: int = 0
  - CognitiveInsight.times_contradicted = 0 line=184 ctx=times_contradicted: int = 0
  - CognitiveInsight.promoted = False line=185 ctx=promoted: bool = False
- func_defaults:
  - _merge_unique(limit) = 10 line=104 ctx=def _merge_unique(base: List[str], extra: List[str], limit: int = 10) -> List[str]:
  - __init__(timeout_s) = 0.5 line=132 ctx=def __init__(self, lock_file: Path, timeout_s: float = 0.5):
  - _save_insights(drop_keys) = None line=300 ctx=def _save_insights(self, drop_keys: Optional[set] = None):
  - _touch_validation(validated_delta) = 0 line=337 ctx=def _touch_validation(self, insight: CognitiveInsight, validated_delta: int = 0, contradicted_delta: int = 0):
  - _touch_validation(contradicted_delta) = 0 line=337 ctx=def _touch_validation(self, insight: CognitiveInsight, validated_delta: int = 0, contradicted_delta: int = 0):
  - get_insights_for_context(limit) = 10 line=664 ctx=def get_insights_for_context(self, context: str, limit: int = 10) -> List[CognitiveInsight]:
  - get_promotable(min_reliability) = 0.7 line=771 ctx=def get_promotable(self, min_reliability: float = 0.7, min_validations: int = 3) -> List[CognitiveInsight]:
  - get_promotable(min_validations) = 3 line=771 ctx=def get_promotable(self, min_reliability: float = 0.7, min_validations: int = 3) -> List[CognitiveInsight]:
  - prune_stale(max_age_days) = 365.0 line=850 ctx=def prune_stale(self, max_age_days: float = 365.0, min_effective: float = 0.2) -> int:
  - prune_stale(min_effective) = 0.2 line=850 ctx=def prune_stale(self, max_age_days: float = 365.0, min_effective: float = 0.2) -> int:
  - get_prune_candidates(max_age_days) = 365.0 line=866 ctx=def get_prune_candidates(
  - get_prune_candidates(min_effective) = 0.2 line=866 ctx=def get_prune_candidates(
  - get_prune_candidates(limit) = 20 line=866 ctx=def get_prune_candidates(
  - get_ranked_insights(min_reliability) = 0.7 line=924 ctx=def get_ranked_insights(
  - get_ranked_insights(min_validations) = 3 line=924 ctx=def get_ranked_insights(
  - get_ranked_insights(limit) = 12 line=924 ctx=def get_ranked_insights(

### lib\content_learner.py
- constants:
  - STATE_FILE = 'Path.home() / ".spark" / "content_learning_state.json"' line=23 ctx=STATE_FILE = Path.home() / ".spark" / "content_learning_state.json"

### lib\context_sync.py
- constants:
  - DEFAULT_MIN_RELIABILITY = 0.7 line=27 ctx=DEFAULT_MIN_RELIABILITY = 0.7
  - DEFAULT_MIN_VALIDATIONS = 3 line=28 ctx=DEFAULT_MIN_VALIDATIONS = 3
  - DEFAULT_MAX_ITEMS = 12 line=29 ctx=DEFAULT_MAX_ITEMS = 12
  - DEFAULT_MAX_PROMOTED = 6 line=30 ctx=DEFAULT_MAX_PROMOTED = 6
  - DEFAULT_HIGH_VALIDATION_OVERRIDE = 50 line=31 ctx=DEFAULT_HIGH_VALIDATION_OVERRIDE = 50

### lib\contradiction_detector.py
- constants:
  - ContradictionType.DIRECT = 'direct' line=32 ctx=DIRECT = "direct"           # Mutually exclusive beliefs
  - ContradictionType.TEMPORAL = 'temporal' line=33 ctx=TEMPORAL = "temporal"       # New info supersedes old
  - ContradictionType.CONTEXTUAL = 'contextual' line=34 ctx=CONTEXTUAL = "contextual"   # Both true in different contexts
  - ContradictionType.UNCERTAIN = 'uncertain' line=35 ctx=UNCERTAIN = "uncertain"     # Need more evidence
  - OPPOSITION_PAIRS = [['\\bprefer\\b', '\\bavoid\\b'], ['\\blike\\b', '\\bhate\\b'], ['\\blike\\b', '\\bdislike\\b'], ['\\balways\\b', '\\bnever\\b'], ['\\byes\\b', '\\bno\\b'], ['\\bdo\\b', "\\bdon'?t\\b"], ['\\bshould\\b', "\\bshouldn'?t\\b"], ['\\bwant\\b', ... line=83 ctx=OPPOSITION_PAIRS = [
  - NEGATION_PATTERNS = ['\\bnot\\b', '\\bno\\b', '\\bnever\\b', "\\bdon'?t\\b", "\\bdoesn'?t\\b", "\\bwon'?t\\b", "\\bcan'?t\\b", "\\bshouldn'?t\\b", "\\bwouldn'?t\\b", '\\bnone\\b', '\\bnothing\\b'] line=99 ctx=NEGATION_PATTERNS = [
  - ContradictionDetector.CONTRADICTIONS_FILE = 'Path.home() / ".spark" / "contradictions.json"' line=163 ctx=CONTRADICTIONS_FILE = Path.home() / ".spark" / "contradictions.json"
- dataclass_defaults:
  - Contradiction.resolved = False line=48 ctx=resolved: bool = False
- func_defaults:
  - check_contradiction(min_similarity) = 0.6 line=204 ctx=def check_contradiction(self, new_text: str, min_similarity: float = 0.6) -> Optional[Contradiction]:

### lib\curiosity_engine.py
- constants:
  - GapType.WHY = 'why' line=34 ctx=WHY = "why"       # Missing reasoning/motivation
  - GapType.WHEN = 'when' line=35 ctx=WHEN = "when"     # Missing context/conditions
  - GapType.HOW = 'how' line=36 ctx=HOW = "how"       # Missing process/method
  - GapType.WHAT = 'what' line=37 ctx=WHAT = "what"     # Missing definition/clarification
  - GapType.WHO = 'who' line=38 ctx=WHO = "who"       # Missing actor/subject
  - QUESTION_TEMPLATES = '{\n    GapType.WHY: [\n        "Why does {subject} {action}?",\n        "What\'s the reason behind {topic}?",\n        "What motivates {topic}?",\n    ],\n    GapType.WHEN: [\n        "When does {topic} apply?",\n        "Under what condit... line=96 ctx=QUESTION_TEMPLATES = {
  - GAP_INDICATORS = '{\n    GapType.WHY: [\n        r"\\bprefers?\\b",\n        r"\\blikes?\\b",\n        r"\\bhates?\\b",\n        r"\\bwants?\\b",\n        r"\\bchooses?\\b",\n        r"\\bdecided?\\b",\n    ],\n    GapType.WHEN: [\n        r"\\bworks\\b",\n... line=125 ctx=GAP_INDICATORS = {
  - CuriosityEngine.GAPS_FILE = 'Path.home() / ".spark" / "knowledge_gaps.json"' line=186 ctx=GAPS_FILE = Path.home() / ".spark" / "knowledge_gaps.json"
- dataclass_defaults:
  - KnowledgeGap.context = '' line=48 ctx=context: str = ""
  - KnowledgeGap.priority = 0.5 line=49 ctx=priority: float = 0.5  # 0-1, how important to fill
  - KnowledgeGap.filled = False line=51 ctx=filled: bool = False
- func_defaults:
  - get_relevant_questions(limit) = 3 line=254 ctx=def get_relevant_questions(self, context: str, limit: int = 3) -> List[KnowledgeGap]:
  - get_open_questions(limit) = 10 line=380 ctx=def get_open_questions(self, limit: int = 10) -> List[KnowledgeGap]:

### lib\dashboard_project.py
- func_defaults:
  - get_project_memory_preview(limit) = 5 line=24 ctx=def get_project_memory_preview(project_key: Optional[str], limit: int = 5) -> List[Dict[str, Any]]:

### lib\diagnostics.py
- env:
  - SPARK_DEBUG default='' line=19 ctx=return os.environ.get("SPARK_DEBUG", "").strip().lower() in _DEBUG_VALUES
  - SPARK_LOG_DIR default=None line=69 ctx=log_dir = Path(os.environ.get("SPARK_LOG_DIR") or (Path.home() / ".spark" / "logs"))
  - SPARK_LOG_TEE default='1' line=91 ctx=tee_enabled = os.environ.get("SPARK_LOG_TEE", "1").strip().lower() in _DEBUG_VALUES

### lib\eidos\acceptance_compiler.py
- constants:
  - AcceptanceType.AUTOMATED = 'automated' line=25 ctx=AUTOMATED = "automated"     # Can be run automatically (test, lint, build)
  - AcceptanceType.MANUAL = 'manual' line=26 ctx=MANUAL = "manual"           # Requires human verification
  - AcceptanceType.OUTPUT = 'output' line=27 ctx=OUTPUT = "output"           # Check specific output/state
  - AcceptanceType.BEHAVIOR = 'behavior' line=28 ctx=BEHAVIOR = "behavior"       # Check behavior in scenario
  - AcceptanceType.METRIC = 'metric' line=29 ctx=METRIC = "metric"           # Check numeric threshold
  - AcceptanceStatus.PENDING = 'pending' line=34 ctx=PENDING = "pending"         # Not yet run
  - AcceptanceStatus.PASSED = 'passed' line=35 ctx=PASSED = "passed"           # Test passed
  - AcceptanceStatus.FAILED = 'failed' line=36 ctx=FAILED = "failed"           # Test failed
  - AcceptanceStatus.SKIPPED = 'skipped' line=37 ctx=SKIPPED = "skipped"         # Intentionally skipped
  - AcceptanceStatus.BLOCKED = 'blocked' line=38 ctx=BLOCKED = "blocked"         # Cannot run (dependency)
- dataclass_defaults:
  - AcceptanceTest.expected_exit_code = 0 line=52 ctx=expected_exit_code: int = 0
  - AcceptanceTest.metric_operator = '>=' line=57 ctx=metric_operator: str = ">="  # >=, <=, ==, !=
  - AcceptanceTest.priority = 1 line=66 ctx=priority: int = 1           # 1 = must pass, 2 = should pass, 3 = nice to have
  - AcceptancePlan.is_complete = False line=136 ctx=is_complete: bool = False   # All critical tests defined
  - AcceptancePlan.is_approved = False line=137 ctx=is_approved: bool = False   # Ready to enter EXECUTE

### lib\eidos\control_plane.py
- constants:
  - WatcherType.REPEAT_ERROR = 'repeat_error' line=25 ctx=REPEAT_ERROR = "repeat_error"           # Same error signature 2+ times
  - WatcherType.NO_NEW_INFO = 'no_new_info' line=26 ctx=NO_NEW_INFO = "no_new_info"             # 5 steps without new evidence
  - WatcherType.DIFF_THRASH = 'diff_thrash' line=27 ctx=DIFF_THRASH = "diff_thrash"             # Same file modified 3+ times
  - WatcherType.CONFIDENCE_STAGNATION = 'confidence_stagnation' line=28 ctx=CONFIDENCE_STAGNATION = "confidence_stagnation"  # Delta < 0.05 for 3 steps
  - WatcherType.MEMORY_BYPASS = 'memory_bypass' line=29 ctx=MEMORY_BYPASS = "memory_bypass"         # Action without citing memory
  - BlockType.BUDGET_EXCEEDED = 'budget_exceeded' line=34 ctx=BUDGET_EXCEEDED = "budget_exceeded"
  - BlockType.LOOP_DETECTED = 'loop_detected' line=35 ctx=LOOP_DETECTED = "loop_detected"
  - BlockType.MEMORY_REQUIRED = 'memory_required' line=36 ctx=MEMORY_REQUIRED = "memory_required"
  - BlockType.VALIDATION_REQUIRED = 'validation_required' line=37 ctx=VALIDATION_REQUIRED = "validation_required"
  - BlockType.PHASE_VIOLATION = 'phase_violation' line=38 ctx=PHASE_VIOLATION = "phase_violation"
- dataclass_defaults:
  - ControlDecision.message = '' line=56 ctx=message: str = ""
  - ControlDecision.required_action = '' line=57 ctx=required_action: str = ""

### lib\eidos\distillation_engine.py
- dataclass_defaults:
  - ReflectionResult.bottleneck = '' line=36 ctx=bottleneck: str = ""           # What was the real bottleneck?
  - ReflectionResult.wrong_assumption = '' line=37 ctx=wrong_assumption: str = ""     # Which assumption was wrong?
  - ReflectionResult.preventive_check = '' line=38 ctx=preventive_check: str = ""     # What check would have prevented this?
  - ReflectionResult.new_rule = '' line=39 ctx=new_rule: str = ""             # What rule should we adopt?
  - ReflectionResult.stop_doing = '' line=40 ctx=stop_doing: str = ""           # What should we stop doing?
  - ReflectionResult.key_insight = '' line=41 ctx=key_insight: str = ""          # Most important learning
  - ReflectionResult.confidence = 0.5 line=42 ctx=confidence: float = 0.5
- func_defaults:
  - schedule_revalidation(days) = 7 line=341 ctx=def schedule_revalidation(self, distillation_id: str, days: int = 7):

### lib\eidos\elevated_control.py
- constants:
  - WatcherType.REPEAT_FAILURE = 'repeat_failure' line=37 ctx=REPEAT_FAILURE = "repeat_failure"        # Same error 2x
  - WatcherType.NO_NEW_EVIDENCE = 'no_new_evidence' line=38 ctx=NO_NEW_EVIDENCE = "no_new_evidence"      # N steps without evidence
  - WatcherType.DIFF_THRASH = 'diff_thrash' line=39 ctx=DIFF_THRASH = "diff_thrash"              # Same file modified 3x
  - WatcherType.CONFIDENCE_STAGNATION = 'confidence_stagnation' line=40 ctx=CONFIDENCE_STAGNATION = "confidence_stagnation"  # Delta < 0.05 for 3 steps
  - WatcherType.MEMORY_BYPASS = 'memory_bypass' line=41 ctx=MEMORY_BYPASS = "memory_bypass"          # Action without memory citation
  - WatcherType.BUDGET_HALF_NO_PROGRESS = 'budget_half_no_progress' line=42 ctx=BUDGET_HALF_NO_PROGRESS = "budget_half_no_progress"  # >50% budget, no progress
  - WatcherType.SCOPE_CREEP = 'scope_creep' line=43 ctx=SCOPE_CREEP = "scope_creep"              # Plan grows while progress doesn't
  - WatcherType.VALIDATION_GAP = 'validation_gap' line=44 ctx=VALIDATION_GAP = "validation_gap"        # >2 steps without validation evidence
  - WatcherSeverity.WARNING = 'warning' line=49 ctx=WARNING = "warning"    # Log and continue
  - WatcherSeverity.BLOCK = 'block' line=50 ctx=BLOCK = "block"        # Block action, require fix
  - WatcherSeverity.FORCE = 'force' line=51 ctx=FORCE = "force"        # Force state transition
- dataclass_defaults:
  - WatcherAlert.required_output = '' line=61 ctx=required_output: str = ""
  - EscapeProtocolResult.triggered = False line=80 ctx=triggered: bool = False
  - EscapeProtocolResult.reason = '' line=81 ctx=reason: str = ""
  - EscapeProtocolResult.summary = '' line=82 ctx=summary: str = ""
  - EscapeProtocolResult.smallest_failing_unit = '' line=83 ctx=smallest_failing_unit: str = ""
  - EscapeProtocolResult.flipped_question = '' line=84 ctx=flipped_question: str = ""
  - EscapeProtocolResult.discriminating_test = '' line=86 ctx=discriminating_test: str = ""
  - StepEnvelopeValidation.valid_before = False line=109 ctx=valid_before: bool = False
  - StepEnvelopeValidation.valid_after = False line=110 ctx=valid_after: bool = False
  - StepEnvelopeValidation.memory_binding_ok = False line=113 ctx=memory_binding_ok: bool = False
  - StepEnvelopeValidation.memory_binding_issue = '' line=114 ctx=memory_binding_issue: str = ""
  - ControlMetrics.total_steps = 0 line=824 ctx=total_steps: int = 0
  - ControlMetrics.steps_blocked = 0 line=825 ctx=steps_blocked: int = 0
  - ControlMetrics.escape_protocols_triggered = 0 line=826 ctx=escape_protocols_triggered: int = 0
  - ControlMetrics.avg_time_to_escape = 0.0 line=828 ctx=avg_time_to_escape: float = 0.0  # How long to recognize rabbit hole
  - ControlMetrics.rabbit_holes_recovered = 0 line=829 ctx=rabbit_holes_recovered: int = 0
  - ControlMetrics.learning_artifacts_created = 0 line=830 ctx=learning_artifacts_created: int = 0

### lib\eidos\escalation.py
- constants:
  - EscalationType.BUDGET = 'budget' line=31 ctx=BUDGET = "budget"           # Budget exhausted
  - EscalationType.LOOP = 'loop' line=32 ctx=LOOP = "loop"               # Loop detected
  - EscalationType.CONFIDENCE = 'confidence' line=33 ctx=CONFIDENCE = "confidence"   # Confidence collapsed
  - EscalationType.BLOCKED = 'blocked' line=34 ctx=BLOCKED = "blocked"         # Guardrail blocked action
  - EscalationType.UNKNOWN = 'unknown' line=35 ctx=UNKNOWN = "unknown"         # Unknown territory
  - RequestType.INFO = 'info' line=40 ctx=INFO = "info"           # Missing context or knowledge
  - RequestType.DECISION = 'decision' line=41 ctx=DECISION = "decision"   # Choice between approaches
  - RequestType.HELP = 'help' line=42 ctx=HELP = "help"           # Stuck, need intervention
  - RequestType.REVIEW = 'review' line=43 ctx=REVIEW = "review"       # Uncertain about risky action
- dataclass_defaults:
  - Escalation.current_hypothesis = '' line=99 ctx=current_hypothesis: str = ""
  - Escalation.specific_question = '' line=104 ctx=specific_question: str = ""
  - Escalation.step_count = 0 line=109 ctx=step_count: int = 0
  - Escalation.elapsed_seconds = 0.0 line=110 ctx=elapsed_seconds: float = 0.0

### lib\eidos\evidence_store.py
- constants:
  - EvidenceType.TOOL_OUTPUT = 'tool_output' line=33 ctx=TOOL_OUTPUT = "tool_output"       # stdout/stderr from tool (72h)
  - EvidenceType.DIFF = 'diff' line=34 ctx=DIFF = "diff"                     # File changes made (7d)
  - EvidenceType.TEST_RESULT = 'test_result' line=35 ctx=TEST_RESULT = "test_result"       # Test pass/fail details (7d)
  - EvidenceType.BUILD_LOG = 'build_log' line=36 ctx=BUILD_LOG = "build_log"           # Compile/build output (7d)
  - EvidenceType.ERROR_TRACE = 'error_trace' line=37 ctx=ERROR_TRACE = "error_trace"       # Stack traces, errors (7d)
  - EvidenceType.DEPLOY_ARTIFACT = 'deploy_artifact' line=38 ctx=DEPLOY_ARTIFACT = "deploy_artifact"  # Deployment logs (30d)
  - EvidenceType.SECURITY_EVENT = 'security_event' line=39 ctx=SECURITY_EVENT = "security_event"    # Auth, access, secrets (90d)
  - EvidenceType.USER_FLAGGED = 'user_flagged' line=40 ctx=USER_FLAGGED = "user_flagged"     # Explicit importance (permanent)
  - RETENTION_POLICY = '{\n    EvidenceType.TOOL_OUTPUT: 72 * 3600,      # 72 hours\n    EvidenceType.DIFF: 7 * 24 * 3600,         # 7 days\n    EvidenceType.TEST_RESULT: 7 * 24 * 3600,  # 7 days\n    EvidenceType.BUILD_LOG: 7 * 24 * 3600,    # 7 days\n    Eviden... line=44 ctx=RETENTION_POLICY = {
- dataclass_defaults:
  - Evidence.tool_name = '' line=62 ctx=tool_name: str = ""
  - Evidence.content = '' line=65 ctx=content: str = ""
  - Evidence.content_hash = '' line=66 ctx=content_hash: str = ""
  - Evidence.byte_size = 0 line=67 ctx=byte_size: int = 0
  - Evidence.compressed = False line=68 ctx=compressed: bool = False
  - Evidence.retention_reason = '' line=77 ctx=retention_reason: str = ""
- func_defaults:
  - create_evidence_from_tool(duration_ms) = None line=369 ctx=def create_evidence_from_tool(
  - save(compress_threshold) = 10000 line=178 ctx=def save(self, evidence: Evidence, compress_threshold: int = 10000) -> str:
  - get_by_type(limit) = 50 line=249 ctx=def get_by_type(

### lib\eidos\guardrails.py
- constants:
  - ViolationType.EVIDENCE_BEFORE_MODIFICATION = 'evidence_before_modification' line=25 ctx=EVIDENCE_BEFORE_MODIFICATION = "evidence_before_modification"
  - ViolationType.PHASE_VIOLATION = 'phase_violation' line=26 ctx=PHASE_VIOLATION = "phase_violation"
  - ViolationType.BUDGET_EXCEEDED = 'budget_exceeded' line=27 ctx=BUDGET_EXCEEDED = "budget_exceeded"
  - ViolationType.MEMORY_REQUIRED = 'memory_required' line=28 ctx=MEMORY_REQUIRED = "memory_required"
  - ViolationType.VALIDATION_REQUIRED = 'validation_required' line=29 ctx=VALIDATION_REQUIRED = "validation_required"
  - PHASE_ALLOWED_ACTIONS = "{\n    Phase.EXPLORE: {'Read', 'Glob', 'Grep', 'WebSearch', 'WebFetch', 'AskUser', 'Task'},\n    Phase.DIAGNOSE: {'Read', 'Glob', 'Grep', 'Bash', 'Test', 'AskUser'},\n    Phase.EXECUTE: {'Read', 'Edit', 'Write', 'Bash', 'Test', 'NotebookEd... line=43 ctx=PHASE_ALLOWED_ACTIONS: Dict[Phase, Set[str]] = {
  - EDIT_TOOLS = {'Edit', 'Write', 'NotebookEdit'} line=52 ctx=EDIT_TOOLS = {'Edit', 'Write', 'NotebookEdit'}
  - DIAGNOSTIC_INTENTS = {'investigate', 'isolate', 'examine', 'diagnose', 'trace', 'debug', 'reproduce', 'analyze', 'narrow', 'understand'} line=55 ctx=DIAGNOSTIC_INTENTS = {
- dataclass_defaults:
  - GuardrailResult.message = '' line=37 ctx=message: str = ""
- func_defaults:
  - __init__(failure_threshold) = 2 line=75 ctx=def __init__(self, failure_threshold: int = 2):

### lib\eidos\integration.py
- constants:
  - ACTIVE_EPISODES_FILE = 'Path.home() / ".spark" / "eidos_active_episodes.json"' line=46 ctx=ACTIVE_EPISODES_FILE = Path.home() / ".spark" / "eidos_active_episodes.json"
  - ACTIVE_STEPS_FILE = 'Path.home() / ".spark" / "eidos_active_steps.json"' line=47 ctx=ACTIVE_STEPS_FILE = Path.home() / ".spark" / "eidos_active_steps.json"

### lib\eidos\memory_gate.py
- constants:
  - IRREVERSIBLE_KEYWORDS = ['production', 'prod', 'deploy', 'delete', 'drop', 'truncate', 'security', 'auth', 'password', 'secret', 'key', 'token', 'payment', 'billing', 'charge', 'funds', 'transfer', 'migration', 'schema', 'database', 'backup', 'publish', 'release',... line=44 ctx=IRREVERSIBLE_KEYWORDS = [
  - IMPACT_KEYWORDS = ['fixed', 'solved', 'working', 'success', 'resolved', 'unblocked', 'breakthrough', 'found the issue', 'root cause', 'finally', 'that was it', 'figured out'] line=53 ctx=IMPACT_KEYWORDS = [
  - NOVELTY_KEYWORDS = ['never seen', 'new pattern', 'first time', "didn't know", 'learned', 'discovered', 'unexpected', 'interesting', 'undocumented', 'edge case'] line=60 ctx=NOVELTY_KEYWORDS = [
- dataclass_defaults:
  - ImportanceScore.impact = 0.0 line=30 ctx=impact: float = 0.0
  - ImportanceScore.novelty = 0.0 line=31 ctx=novelty: float = 0.0
  - ImportanceScore.surprise = 0.0 line=32 ctx=surprise: float = 0.0
  - ImportanceScore.recurrence = 0.0 line=33 ctx=recurrence: float = 0.0
  - ImportanceScore.irreversibility = 0.0 line=34 ctx=irreversibility: float = 0.0
- func_defaults:
  - set_cache_expiry(hours) = 24 line=274 ctx=def set_cache_expiry(self, step_id: str, hours: int = 24):

### lib\eidos\migration.py
- constants:
  - CATEGORY_TO_TYPE = "{\n    'SELF_AWARENESS': DistillationType.HEURISTIC,\n    'USER_UNDERSTANDING': DistillationType.POLICY,\n    'REASONING': DistillationType.HEURISTIC,\n    'CONTEXT': DistillationType.SHARP_EDGE,\n    'WISDOM': DistillationType.HEURISTIC,\... line=27 ctx=CATEGORY_TO_TYPE = {
- dataclass_defaults:
  - MigrationStats.insights_migrated = 0 line=51 ctx=insights_migrated: int = 0
  - MigrationStats.insights_skipped = 0 line=52 ctx=insights_skipped: int = 0
  - MigrationStats.patterns_archived = 0 line=53 ctx=patterns_archived: int = 0
  - MigrationStats.policies_created = 0 line=54 ctx=policies_created: int = 0

### lib\eidos\minimal_mode.py
- constants:
  - MinimalModeReason.REPEATED_WATCHERS = 'repeated_watchers' line=30 ctx=REPEATED_WATCHERS = "repeated_watchers"
  - MinimalModeReason.LOW_CONFIDENCE = 'low_confidence' line=31 ctx=LOW_CONFIDENCE = "low_confidence"
  - MinimalModeReason.LOW_EVIDENCE = 'low_evidence' line=32 ctx=LOW_EVIDENCE = "low_evidence"
  - MinimalModeReason.BUDGET_CRITICAL = 'budget_critical' line=33 ctx=BUDGET_CRITICAL = "budget_critical"
  - MinimalModeReason.ESCAPE_PROTOCOL = 'escape_protocol' line=34 ctx=ESCAPE_PROTOCOL = "escape_protocol"
  - MinimalModeReason.MANUAL_TRIGGER = 'manual_trigger' line=35 ctx=MANUAL_TRIGGER = "manual_trigger"
  - MINIMAL_MODE_ALLOWED_TOOLS = {'Bash', 'Read', 'Grep', 'Glob'} line=81 ctx=MINIMAL_MODE_ALLOWED_TOOLS = {
  - MINIMAL_MODE_BASH_PATTERNS = ['ls', 'cat', 'head', 'tail', 'grep', 'find', 'echo', 'test', 'pytest', 'npm test', 'yarn test', 'jest', 'node', 'python -c', 'python -m pytest', 'git status', 'git log', 'git diff', 'git show'] line=89 ctx=MINIMAL_MODE_BASH_PATTERNS = [
  - MINIMAL_MODE_BASH_BLOCKED = ['rm', 'mv', 'cp', 'mkdir', 'touch', 'git add', 'git commit', 'git push', 'git checkout', 'npm install', 'pip install', 'yarn add'] line=97 ctx=MINIMAL_MODE_BASH_BLOCKED = [
- dataclass_defaults:
  - MinimalModeState.active = False line=41 ctx=active: bool = False
  - MinimalModeState.step_count_at_entry = 0 line=44 ctx=step_count_at_entry: int = 0
  - MinimalModeState.edits_allowed = False line=47 ctx=edits_allowed: bool = False
  - MinimalModeState.writes_allowed = False line=48 ctx=writes_allowed: bool = False
  - MinimalModeState.refactors_allowed = False line=49 ctx=refactors_allowed: bool = False
  - MinimalModeState.new_features_allowed = False line=50 ctx=new_features_allowed: bool = False
  - MinimalModeState.reads_allowed = True line=53 ctx=reads_allowed: bool = True
  - MinimalModeState.diagnostics_allowed = True line=54 ctx=diagnostics_allowed: bool = True
  - MinimalModeState.tests_allowed = True line=55 ctx=tests_allowed: bool = True
  - MinimalModeState.simplify_allowed = True line=56 ctx=simplify_allowed: bool = True
  - MinimalModeState.exit_requires_evidence = True line=59 ctx=exit_requires_evidence: bool = True
  - MinimalModeState.exit_requires_hypothesis = True line=60 ctx=exit_requires_hypothesis: bool = True
  - MinimalModeState.min_steps_before_exit = 3 line=61 ctx=min_steps_before_exit: int = 3
- func_defaults:
  - should_enter(watcher_trigger_count) = 0 line=116 ctx=def should_enter(
  - should_enter(recent_steps) = None line=116 ctx=def should_enter(

### lib\eidos\models.py
- constants:
  - Phase.EXPLORE = 'explore' line=36 ctx=EXPLORE = "explore"         # Gather context, clarify, retrieve memory
  - Phase.PLAN = 'plan' line=37 ctx=PLAN = "plan"               # Generate hypotheses/tests (bounded)
  - Phase.EXECUTE = 'execute' line=38 ctx=EXECUTE = "execute"         # One action per step + prediction
  - Phase.VALIDATE = 'validate' line=39 ctx=VALIDATE = "validate"       # Prove outcome, record evidence
  - Phase.CONSOLIDATE = 'consolidate' line=40 ctx=CONSOLIDATE = "consolidate" # Distill learnings into reusable rules
  - Phase.DIAGNOSE = 'diagnose' line=41 ctx=DIAGNOSE = "diagnose"       # Debugging mode, evidence-only
  - Phase.SIMPLIFY = 'simplify' line=42 ctx=SIMPLIFY = "simplify"       # Reduce scope / minimal reproduction
  - Phase.ESCALATE = 'escalate' line=43 ctx=ESCALATE = "escalate"       # Ask user / stop and request info
  - Phase.HALT = 'halt' line=44 ctx=HALT = "halt"               # Budget exceeded or unsafe; produce report
  - VALID_TRANSITIONS = '{\n    Phase.EXPLORE: [Phase.PLAN, Phase.ESCALATE, Phase.HALT],\n    Phase.PLAN: [Phase.EXECUTE, Phase.ESCALATE, Phase.HALT],\n    Phase.EXECUTE: [Phase.VALIDATE, Phase.ESCALATE, Phase.HALT],\n    Phase.VALIDATE: [Phase.EXECUTE, Phase.CONS... line=48 ctx=VALID_TRANSITIONS = {
  - Outcome.SUCCESS = 'success' line=63 ctx=SUCCESS = "success"
  - Outcome.FAILURE = 'failure' line=64 ctx=FAILURE = "failure"
  - Outcome.PARTIAL = 'partial' line=65 ctx=PARTIAL = "partial"
  - Outcome.ESCALATED = 'escalated' line=66 ctx=ESCALATED = "escalated"
  - Outcome.IN_PROGRESS = 'in_progress' line=67 ctx=IN_PROGRESS = "in_progress"
  - Evaluation.PASS = 'pass' line=72 ctx=PASS = "pass"
  - Evaluation.FAIL = 'fail' line=73 ctx=FAIL = "fail"
  - Evaluation.PARTIAL = 'partial' line=74 ctx=PARTIAL = "partial"
  - Evaluation.UNKNOWN = 'unknown' line=75 ctx=UNKNOWN = "unknown"
  - DistillationType.HEURISTIC = 'heuristic' line=80 ctx=HEURISTIC = "heuristic"       # "If X, then Y"
  - DistillationType.SHARP_EDGE = 'sharp_edge' line=81 ctx=SHARP_EDGE = "sharp_edge"     # Gotcha / pitfall
  - DistillationType.ANTI_PATTERN = 'anti_pattern' line=82 ctx=ANTI_PATTERN = "anti_pattern" # "Never do X because..."
  - DistillationType.PLAYBOOK = 'playbook' line=83 ctx=PLAYBOOK = "playbook"         # Step-by-step procedure
  - DistillationType.POLICY = 'policy' line=84 ctx=POLICY = "policy"             # Operating constraint
  - ActionType.TOOL_CALL = 'tool_call' line=89 ctx=TOOL_CALL = "tool_call"
  - ActionType.REASONING = 'reasoning' line=90 ctx=REASONING = "reasoning"
  - ActionType.QUESTION = 'question' line=91 ctx=QUESTION = "question"
  - ActionType.WAIT = 'wait' line=92 ctx=WAIT = "wait"
- dataclass_defaults:
  - Budget.max_steps = 25 line=105 ctx=max_steps: int = 25
  - Budget.max_time_seconds = 720 line=106 ctx=max_time_seconds: int = 720  # 12 minutes
  - Budget.max_retries_per_error = 2 line=107 ctx=max_retries_per_error: int = 2  # After 2 failures, stop modifying
  - Budget.max_file_touches = 3 line=108 ctx=max_file_touches: int = 3  # Max times to modify same file per episode (raised from 2)
  - Budget.no_evidence_limit = 5 line=109 ctx=no_evidence_limit: int = 5  # Force DIAGNOSE after N steps without evidence
  - Episode.final_evaluation = '' line=149 ctx=final_evaluation: str = ""
  - Episode.step_count = 0 line=154 ctx=step_count: int = 0
  - Episode.no_evidence_streak = 0 line=157 ctx=no_evidence_streak: int = 0  # Steps without new evidence
  - Episode.stuck_count = 0 line=159 ctx=stuck_count: int = 0  # Times we've entered DIAGNOSE/SIMPLIFY
  - Episode.escape_protocol_triggered = False line=160 ctx=escape_protocol_triggered: bool = False
  - Step.hypothesis = '' line=304 ctx=hypothesis: str = ""                  # Falsifiable claim being tested
  - Step.prediction = '' line=307 ctx=prediction: str = ""                  # What I expect to happen
  - Step.stop_condition = '' line=308 ctx=stop_condition: str = ""              # "If X, change approach" - when to abort
  - Step.confidence_before = 0.5 line=309 ctx=confidence_before: float = 0.5        # 0-1, how sure I am
  - Step.result = '' line=317 ctx=result: str = ""                      # What actually happened
  - Step.validation_evidence = '' line=318 ctx=validation_evidence: str = ""         # Concrete evidence (test output, metric, file hash)
  - Step.surprise_level = 0.0 line=320 ctx=surprise_level: float = 0.0           # 0-1, how different from prediction
  - Step.lesson = '' line=321 ctx=lesson: str = ""                      # 1-3 bullets, what we learned
  - Step.confidence_after = 0.5 line=322 ctx=confidence_after: float = 0.5         # Updated confidence
  - Step.confidence_delta = 0.0 line=323 ctx=confidence_delta: float = 0.0         # Change in confidence
  - Step.memory_cited = False line=327 ctx=memory_cited: bool = False            # Did we actually use retrieved memory?
  - Step.memory_absent_declared = False line=329 ctx=memory_absent_declared: bool = False  # Explicitly declared "none found"
  - Step.validated = False line=332 ctx=validated: bool = False               # Did we check the result?
  - Step.validation_method = '' line=333 ctx=validation_method: str = ""           # How we validated
  - Step.is_valid = True line=334 ctx=is_valid: bool = True                 # False if missing required fields
  - Step.evidence_gathered = False line=337 ctx=evidence_gathered: bool = False       # Did this step produce new evidence?
  - Step.progress_made = False line=338 ctx=progress_made: bool = False           # Did this step advance toward goal?
  - Distillation.validation_count = 0 line=486 ctx=validation_count: int = 0
  - Distillation.contradiction_count = 0 line=487 ctx=contradiction_count: int = 0
  - Distillation.confidence = 0.5 line=488 ctx=confidence: float = 0.5
  - Distillation.times_retrieved = 0 line=491 ctx=times_retrieved: int = 0
  - Distillation.times_used = 0 line=492 ctx=times_used: int = 0      # Actually influenced decision
  - Distillation.times_helped = 0 line=493 ctx=times_helped: int = 0    # Led to success
  - Policy.scope = 'GLOBAL' line=587 ctx=scope: str = "GLOBAL"  # GLOBAL, PROJECT, SESSION
  - Policy.priority = 50 line=588 ctx=priority: int = 50     # Higher = more important
  - Policy.source = 'INFERRED' line=589 ctx=source: str = "INFERRED"
- func_defaults:
  - is_confidence_stagnant(threshold) = 0.05 line=218 ctx=def is_confidence_stagnant(self, threshold: float = 0.05, steps: int = 3) -> bool:
  - is_confidence_stagnant(steps) = 3 line=218 ctx=def is_confidence_stagnant(self, threshold: float = 0.05, steps: int = 3) -> bool:

### lib\eidos\policy_patches.py
- constants:
  - PatchTrigger.ERROR_COUNT = 'error_count' line=30 ctx=ERROR_COUNT = "error_count"         # After N errors
  - PatchTrigger.PHASE_ENTRY = 'phase_entry' line=31 ctx=PHASE_ENTRY = "phase_entry"         # When entering a phase
  - PatchTrigger.TOOL_USE = 'tool_use' line=32 ctx=TOOL_USE = "tool_use"               # When using a specific tool
  - PatchTrigger.FILE_TOUCH = 'file_touch' line=33 ctx=FILE_TOUCH = "file_touch"           # When touching a file
  - PatchTrigger.CONFIDENCE_DROP = 'confidence_drop' line=34 ctx=CONFIDENCE_DROP = "confidence_drop" # When confidence drops
  - PatchTrigger.PATTERN_MATCH = 'pattern_match' line=35 ctx=PATTERN_MATCH = "pattern_match"     # When pattern detected
  - PatchTrigger.TIME_ELAPSED = 'time_elapsed' line=36 ctx=TIME_ELAPSED = "time_elapsed"       # After N seconds
  - PatchTrigger.STEP_COUNT = 'step_count' line=37 ctx=STEP_COUNT = "step_count"           # After N steps
  - PatchAction.FORCE_PHASE = 'force_phase' line=42 ctx=FORCE_PHASE = "force_phase"         # Force transition to phase
  - PatchAction.BLOCK_TOOL = 'block_tool' line=43 ctx=BLOCK_TOOL = "block_tool"           # Block a tool
  - PatchAction.BLOCK_FILE = 'block_file' line=44 ctx=BLOCK_FILE = "block_file"           # Block file modification
  - PatchAction.REQUIRE_STEP = 'require_step' line=45 ctx=REQUIRE_STEP = "require_step"       # Require a specific step type
  - PatchAction.ADD_CONSTRAINT = 'add_constraint' line=46 ctx=ADD_CONSTRAINT = "add_constraint"   # Add constraint to episode
  - PatchAction.EMIT_WARNING = 'emit_warning' line=47 ctx=EMIT_WARNING = "emit_warning"       # Emit a warning
  - PatchAction.FORCE_VALIDATION = 'force_validation' line=48 ctx=FORCE_VALIDATION = "force_validation"  # Force validation step
- dataclass_defaults:
  - PolicyPatch.enabled = True line=75 ctx=enabled: bool = True
  - PolicyPatch.times_triggered = 0 line=76 ctx=times_triggered: int = 0
  - PolicyPatch.times_helped = 0 line=77 ctx=times_helped: int = 0
  - PolicyPatch.priority = 50 line=81 ctx=priority: int = 50  # Higher = checked first
  - PatchResult.triggered = False line=142 ctx=triggered: bool = False
  - PatchResult.patch_id = '' line=143 ctx=patch_id: str = ""
  - PatchResult.message = '' line=146 ctx=message: str = ""

### lib\eidos\retriever.py
- constants:
  - StructuralRetriever.TYPE_PRIORITY = '{\n        DistillationType.POLICY: 1,      # Always first - constraints\n        DistillationType.PLAYBOOK: 2,    # Procedures for known tasks\n        DistillationType.SHARP_EDGE: 3,  # Warnings / gotchas\n        DistillationType.HEURIS... line=51 ctx=TYPE_PRIORITY = {
- func_defaults:
  - __init__(max_results) = 10 line=59 ctx=def __init__(self, store: Optional[EidosStore] = None, max_results: int = 10):
  - _has_keyword_overlap(min_overlap) = 2 line=371 ctx=def _has_keyword_overlap(self, text1: str, text2: str, min_overlap: int = 2) -> bool:

### lib\eidos\store.py
- func_defaults:
  - get_recent_episodes(limit) = 10 line=216 ctx=def get_recent_episodes(self, limit: int = 10) -> List[Episode]:
  - get_recent_steps(limit) = 50 line=312 ctx=def get_recent_steps(self, limit: int = 50) -> List[Step]:
  - get_distillations_by_type(limit) = 20 line=398 ctx=def get_distillations_by_type(
  - get_high_confidence_distillations(min_confidence) = 0.7 line=415 ctx=def get_high_confidence_distillations(
  - get_high_confidence_distillations(limit) = 20 line=415 ctx=def get_high_confidence_distillations(
  - get_distillations_by_trigger(limit) = 20 line=445 ctx=def get_distillations_by_trigger(
  - get_distillations_by_domain(limit) = 20 line=463 ctx=def get_distillations_by_domain(
  - get_all_distillations(limit) = 100 line=480 ctx=def get_all_distillations(self, limit: int = 100) -> List[Distillation]:
  - get_policies_by_scope(limit) = 50 line=579 ctx=def get_policies_by_scope(

### lib\eidos\truth_ledger.py
- constants:
  - EvidenceLevel.NONE = 'none' line=31 ctx=NONE = "none"           # No evidence, pure claim
  - EvidenceLevel.WEAK = 'weak' line=32 ctx=WEAK = "weak"           # Some evidence, not conclusive
  - EvidenceLevel.STRONG = 'strong' line=33 ctx=STRONG = "strong"       # Multiple corroborating evidence points
  - TruthStatus.CLAIM = 'claim' line=38 ctx=CLAIM = "claim"         # Unverified belief
  - TruthStatus.FACT = 'fact' line=39 ctx=FACT = "fact"           # Validated with evidence
  - TruthStatus.RULE = 'rule' line=40 ctx=RULE = "rule"           # Generalized from multiple facts
  - TruthStatus.STALE = 'stale' line=41 ctx=STALE = "stale"         # Was fact/rule but evidence expired
  - TruthStatus.CONTRADICTED = 'contradicted' line=42 ctx=CONTRADICTED = "contradicted"  # Evidence now contradicts
- dataclass_defaults:
  - EvidenceRef.ref_hash = '' line=50 ctx=ref_hash: str = ""      # Hash of evidence content (for integrity)
  - EvidenceRef.description = '' line=52 ctx=description: str = ""
  - TruthEntry.times_validated = 0 line=94 ctx=times_validated: int = 0
  - TruthEntry.times_contradicted = 0 line=95 ctx=times_contradicted: int = 0
- func_defaults:
  - add_fact(revalidate_days) = 30 line=285 ctx=def add_fact(
  - add_rule(revalidate_days) = 60 line=310 ctx=def add_rule(

### lib\eidos\validation.py
- constants:
  - ValidationMethod.TEST_PASSED = 'test:passed' line=35 ctx=TEST_PASSED = "test:passed"
  - ValidationMethod.TEST_FAILED = 'test:failed' line=36 ctx=TEST_FAILED = "test:failed"
  - ValidationMethod.BUILD_SUCCESS = 'build:success' line=39 ctx=BUILD_SUCCESS = "build:success"
  - ValidationMethod.BUILD_FAILED = 'build:failed' line=40 ctx=BUILD_FAILED = "build:failed"
  - ValidationMethod.LINT_CLEAN = 'lint:clean' line=43 ctx=LINT_CLEAN = "lint:clean"
  - ValidationMethod.LINT_ERRORS = 'lint:errors' line=44 ctx=LINT_ERRORS = "lint:errors"
  - ValidationMethod.OUTPUT_EXPECTED = 'output:expected' line=47 ctx=OUTPUT_EXPECTED = "output:expected"
  - ValidationMethod.OUTPUT_UNEXPECTED = 'output:unexpected' line=48 ctx=OUTPUT_UNEXPECTED = "output:unexpected"
  - ValidationMethod.ERROR_RESOLVED = 'error:resolved' line=51 ctx=ERROR_RESOLVED = "error:resolved"
  - ValidationMethod.ERROR_PERSISTS = 'error:persists' line=52 ctx=ERROR_PERSISTS = "error:persists"
  - ValidationMethod.MANUAL_CHECKED = 'manual:checked' line=55 ctx=MANUAL_CHECKED = "manual:checked"
  - ValidationMethod.MANUAL_APPROVED = 'manual:approved' line=56 ctx=MANUAL_APPROVED = "manual:approved"
  - ValidationMethod.DEFERRED = 'deferred' line=59 ctx=DEFERRED = "deferred"
  - DEFERRAL_LIMITS = '{\n    "needs_deploy": 24 * 3600,      # 24 hours\n    "needs_data": 48 * 3600,        # 48 hours\n    "needs_human": 72 * 3600,       # 72 hours\n    "async_process": 4 * 3600,      # 4 hours\n}' line=63 ctx=DEFERRAL_LIMITS = {
  - DEFAULT_MAX_DEFERRAL = '24 * 3600' line=71 ctx=DEFAULT_MAX_DEFERRAL = 24 * 3600  # 24 hours
- dataclass_defaults:
  - ValidationResult.method = '' line=78 ctx=method: str = ""
  - ValidationResult.deferred = False line=79 ctx=deferred: bool = False
  - ValidationResult.error = '' line=80 ctx=error: str = ""
  - ValidationResult.deferral_reason = '' line=81 ctx=deferral_reason: str = ""
  - ValidationResult.max_wait_seconds = 0 line=82 ctx=max_wait_seconds: int = 0
  - DeferredValidation.reminder_sent = False line=92 ctx=reminder_sent: bool = False
  - DeferredValidation.resolved = False line=93 ctx=resolved: bool = False
  - DeferredValidation.resolution_method = '' line=95 ctx=resolution_method: str = ""

### lib\embeddings.py
- env:
  - SPARK_EMBEDDINGS default='1' line=14 ctx=if os.environ.get("SPARK_EMBEDDINGS", "1").lower() in ("0", "false", "no"):
  - SPARK_EMBED_MODEL default='BAAI/bge-small-en-v1.5' line=25 ctx=model = os.environ.get("SPARK_EMBED_MODEL", "BAAI/bge-small-en-v1.5")

### lib\evaluation.py
- func_defaults:
  - _load_jsonl(limit) = 800 line=14 ctx=def _load_jsonl(path: Path, limit: int = 800) -> List[Dict[str, Any]]:

### lib\events.py
- constants:
  - SparkEventKind.MESSAGE = 'message' line=18 ctx=MESSAGE = "message"
  - SparkEventKind.TOOL = 'tool' line=19 ctx=TOOL = "tool"
  - SparkEventKind.COMMAND = 'command' line=20 ctx=COMMAND = "command"
  - SparkEventKind.SYSTEM = 'system' line=21 ctx=SYSTEM = "system"

### lib\exposure_tracker.py
- constants:
  - EXPOSURES_FILE = 'Path.home() / ".spark" / "exposures.jsonl"' line=13 ctx=EXPOSURES_FILE = Path.home() / ".spark" / "exposures.jsonl"
  - LAST_EXPOSURE_FILE = 'Path.home() / ".spark" / "last_exposure.json"' line=14 ctx=LAST_EXPOSURE_FILE = Path.home() / ".spark" / "last_exposure.json"
- func_defaults:
  - read_recent_exposures(limit) = 200 line=52 ctx=def read_recent_exposures(limit: int = 200, max_age_s: float = 6 * 3600) -> List[Dict]:

### lib\feedback.py
- constants:
  - SKILLS_EFFECTIVENESS_FILE = 'Path.home() / ".spark" / "skills_effectiveness.json"' line=16 ctx=SKILLS_EFFECTIVENESS_FILE = Path.home() / ".spark" / "skills_effectiveness.json"
- func_defaults:
  - update_skill_effectiveness(limit) = 2 line=33 ctx=def update_skill_effectiveness(query: str, success: bool, limit: int = 2) -> None:

### lib\growth_tracker.py
- constants:
  - Milestone.FIRST_INSIGHT = 'first_insight' line=21 ctx=FIRST_INSIGHT = "first_insight"
  - Milestone.TEN_INSIGHTS = 'ten_insights' line=22 ctx=TEN_INSIGHTS = "ten_insights"
  - Milestone.FIFTY_INSIGHTS = 'fifty_insights' line=23 ctx=FIFTY_INSIGHTS = "fifty_insights"
  - Milestone.FIRST_PROMOTION = 'first_promotion' line=24 ctx=FIRST_PROMOTION = "first_promotion"
  - Milestone.FIRST_AHA = 'first_aha' line=25 ctx=FIRST_AHA = "first_aha"
  - Milestone.PATTERN_MASTER = 'pattern_master' line=26 ctx=PATTERN_MASTER = "pattern_master"      # 10 patterns recognized
  - Milestone.PREFERENCE_LEARNED = 'preference_learned' line=27 ctx=PREFERENCE_LEARNED = "preference_learned"
  - Milestone.WEEK_ACTIVE = 'week_active' line=28 ctx=WEEK_ACTIVE = "week_active"
  - Milestone.MONTH_ACTIVE = 'month_active' line=29 ctx=MONTH_ACTIVE = "month_active"
  - Milestone.ACCURACY_70 = 'accuracy_70' line=30 ctx=ACCURACY_70 = "accuracy_70"
  - Milestone.ACCURACY_90 = 'accuracy_90' line=31 ctx=ACCURACY_90 = "accuracy_90"
  - MILESTONE_MESSAGES = '{\n    Milestone.FIRST_INSIGHT: "\U0001f331 First insight captured! The learning begins.",\n    Milestone.TEN_INSIGHTS: "\U0001f4da 10 insights learned. Building knowledge.",\n    Milestone.FIFTY_INSIGHTS: "\U0001f9e0 50 insights! Deep und... line=34 ctx=MILESTONE_MESSAGES = {
  - GrowthTracker.GROWTH_FILE = 'Path(__file__).parent.parent / ".spark" / "growth.json"' line=93 ctx=GROWTH_FILE = Path(__file__).parent.parent / ".spark" / "growth.json"
- func_defaults:
  - get_growth_delta(hours) = 24 line=260 ctx=def get_growth_delta(self, hours: int = 24) -> Dict[str, Any]:
  - get_timeline(limit) = 10 line=288 ctx=def get_timeline(self, limit: int = 10) -> List[Dict[str, Any]]:

### lib\hypothesis_tracker.py
- constants:
  - HypothesisState.EMERGING = 'emerging' line=35 ctx=EMERGING = "emerging"       # First observation
  - HypothesisState.HYPOTHESIS = 'hypothesis' line=36 ctx=HYPOTHESIS = "hypothesis"   # Pattern noticed
  - HypothesisState.TESTING = 'testing' line=37 ctx=TESTING = "testing"         # Being validated
  - HypothesisState.VALIDATED = 'validated' line=38 ctx=VALIDATED = "validated"     # Consistently correct
  - HypothesisState.INVALIDATED = 'invalidated' line=39 ctx=INVALIDATED = "invalidated" # Consistently wrong
  - HypothesisState.BELIEF = 'belief' line=40 ctx=BELIEF = "belief"           # Promoted to insight
  - HypothesisTracker.HYPOTHESES_FILE = 'Path.home() / ".spark" / "hypotheses.json"' line=147 ctx=HYPOTHESES_FILE = Path.home() / ".spark" / "hypotheses.json"
- dataclass_defaults:
  - Prediction.outcome_notes = '' line=51 ctx=outcome_notes: str = ""
  - Hypothesis.confidence = 0.5 line=83 ctx=confidence: float = 0.5     # 0-1, how confident we are
  - Hypothesis.domain = '' line=84 ctx=domain: str = ""            # Domain this applies to
- func_defaults:
  - get_testable_hypotheses(limit) = 5 line=361 ctx=def get_testable_hypotheses(self, limit: int = 5) -> List[Hypothesis]:

### lib\importance_scorer.py
- constants:
  - ImportanceTier.CRITICAL = 'critical' line=41 ctx=CRITICAL = "critical"  # 0.9+ - Must learn immediately
  - ImportanceTier.HIGH = 'high' line=42 ctx=HIGH = "high"          # 0.7-0.9 - Should learn
  - ImportanceTier.MEDIUM = 'medium' line=43 ctx=MEDIUM = "medium"      # 0.5-0.7 - Consider learning
  - ImportanceTier.LOW = 'low' line=44 ctx=LOW = "low"            # 0.3-0.5 - Store but don't promote
  - ImportanceTier.IGNORE = 'ignore' line=45 ctx=IGNORE = "ignore"      # <0.3 - Don't store
  - CRITICAL_SIGNALS = [['\\bremember\\s+(?:this|that)\\b', 'explicit_remember'], ['\\balways\\s+do\\s+(?:it\\s+)?this\\s+way\\b', 'explicit_preference'], ['\\bnever\\s+do\\s+(?:it\\s+)?this\\s+way\\b', 'explicit_prohibition'], ['\\bthis\\s+is\\s+(?:very\\s+)?imp... line=76 ctx=CRITICAL_SIGNALS = [
  - HIGH_SIGNALS = [['\\bi\\s+(?:prefer|like|want)\\b', 'preference'], ["\\blet'?s\\s+(?:go\\s+with|use|try)\\b", 'preference'], ['\\bswitch\\s+to\\b', 'preference'], ['\\brather\\s+than\\b', 'comparative_preference'], ['\\bthe\\s+(?:key|trick|secret)\\s+is\\... line=97 ctx=HIGH_SIGNALS = [
  - MEDIUM_SIGNALS = [['\\bi\\s+(?:noticed|notice)\\b', 'observation'], ['\\bit\\s+(?:seems|looks)\\s+like\\b', 'observation'], ['\\binteresting(?:ly)?\\b', 'observation'], ['\\bwhen\\s+(?:you|we|I)\\b', 'contextual'], ['\\bif\\s+(?:you|we|I)\\b', 'conditional'... line=122 ctx=MEDIUM_SIGNALS = [
  - LOW_SIGNALS = [['\\b(?:Read|Edit|Bash|Glob|Grep)\\s*(?:->|\u2192)', 'tool_sequence'], ['\\b\\d+%?\\s*(?:success|fail)', 'metric'], ['\\btimeout\\b', 'operational'], ['\\berror\\s+rate\\b', 'metric'], ['\\bokay\\b', 'acknowledgment'], ['\\balright\\b', 'a... line=139 ctx=LOW_SIGNALS = [
  - DOMAIN_WEIGHTS = {'game_dev': {'balance': 1.5, 'feel': 1.5, 'gameplay': 1.4, 'physics': 1.3, 'collision': 1.2, 'spawn': 1.2, 'difficulty': 1.3, 'player': 1.3}, 'fintech': {'compliance': 1.5, 'security': 1.5, 'transaction': 1.4, 'risk': 1.4, 'audit': 1.3, 'v... line=158 ctx=DOMAIN_WEIGHTS = {
  - DEFAULT_WEIGHTS = {'user': 1.3, 'preference': 1.4, 'decision': 1.3, 'principle': 1.3, 'style': 1.2} line=250 ctx=DEFAULT_WEIGHTS = {
  - QUESTION_PATTERNS = {'domain': [['\\b(?:game|gaming|player)\\b', 'game_dev'], ['\\b(?:finance|fintech|banking)\\b', 'fintech'], ['\\b(?:market|campaign|audience)\\b', 'marketing']], 'success': [['\\bsuccess\\s+(?:means|is|looks)\\b', 1.5], ['\\bgoal\\s+is\\b',... line=264 ctx=QUESTION_PATTERNS = {
- dataclass_defaults:
  - ImportanceScore.domain_relevance = 0.5 line=55 ctx=domain_relevance: float = 0.5  # How relevant to active domain
  - ImportanceScore.first_mention_elevation = False line=56 ctx=first_mention_elevation: bool = False

### lib\ingest_validation.py
- constants:
  - REPORT_FILE = 'Path.home() / ".spark" / "ingest_report.json"' line=13 ctx=REPORT_FILE = Path.home() / ".spark" / "ingest_report.json"

### lib\markdown_writer.py
- constants:
  - DEFAULT_LEARNINGS_DIR = '.learnings' line=29 ctx=DEFAULT_LEARNINGS_DIR = ".learnings"

### lib\memory_banks.py
- constants:
  - BANK_DIR = 'Path.home() / ".spark" / "banks"' line=31 ctx=BANK_DIR = Path.home() / ".spark" / "banks"
  - GLOBAL_FILE = 'BANK_DIR / "global_user.jsonl"' line=32 ctx=GLOBAL_FILE = BANK_DIR / "global_user.jsonl"
  - PROJECTS_DIR = 'BANK_DIR / "projects"' line=33 ctx=PROJECTS_DIR = BANK_DIR / "projects"
- func_defaults:
  - infer_project_key(max_events) = 60 line=72 ctx=def infer_project_key(max_events: int = 60) -> Optional[str]:
  - _read_jsonl(limit) = 500 line=227 ctx=def _read_jsonl(path: Path, limit: int = 500) -> List[Dict[str, Any]]:
  - retrieve(project_key) = None line=243 ctx=def retrieve(query: str, project_key: Optional[str] = None, limit: int = 6) -> List[Dict[str, Any]]:
  - retrieve(limit) = 6 line=243 ctx=def retrieve(query: str, project_key: Optional[str] = None, limit: int = 6) -> List[Dict[str, Any]]:
  - sync_insights_to_banks(min_reliability) = 0.7 line=316 ctx=def sync_insights_to_banks(

### lib\memory_capture.py
- constants:
  - PENDING_DIR = 'Path.home() / ".spark"' line=39 ctx=PENDING_DIR = Path.home() / ".spark"
  - PENDING_FILE = 'PENDING_DIR / "pending_memory.json"' line=40 ctx=PENDING_FILE = PENDING_DIR / "pending_memory.json"
  - STATE_FILE = 'PENDING_DIR / "memory_capture_state.json"' line=41 ctx=STATE_FILE = PENDING_DIR / "memory_capture_state.json"
  - MAX_CAPTURE_CHARS = 2000 line=42 ctx=MAX_CAPTURE_CHARS = 2000
  - HARD_TRIGGERS = {'remember this': 1.0, 'don\u2019t forget': 0.95, 'dont forget': 0.95, 'note this': 0.9, 'save this': 0.9, 'lock this in': 0.95, 'non-negotiable': 0.95, 'hard rule': 0.95, 'hard boundary': 0.95, 'from now on': 0.85, 'always': 0.65, 'never':... line=49 ctx=HARD_TRIGGERS = {
  - SOFT_TRIGGERS = {'i prefer': 0.55, 'i hate': 0.75, 'i don\u2019t like': 0.65, 'i dont like': 0.65, 'i need': 0.5, 'i want': 0.5, 'we should': 0.45, 'design constraint': 0.65, 'default': 0.4, 'compatibility': 0.35, 'adaptability': 0.35, 'should': 0.25, 'mus... line=64 ctx=SOFT_TRIGGERS = {
  - DECISION_MARKERS = {"let's do it": 0.25, 'lets do it': 0.25, 'ship it': 0.25, 'do it': 0.15} line=82 ctx=DECISION_MARKERS = {
  - AUTO_SAVE_THRESHOLD = 0.82 line=227 ctx=AUTO_SAVE_THRESHOLD = 0.82
  - SUGGEST_THRESHOLD = 0.55 line=228 ctx=SUGGEST_THRESHOLD = 0.55
- dataclass_defaults:
  - MemorySuggestion.status = 'pending' line=175 ctx=status: str = "pending"  # pending|accepted|rejected|auto_saved
- func_defaults:
  - process_recent_memory_events(limit) = 50 line=289 ctx=def process_recent_memory_events(limit: int = 50) -> Dict[str, Any]:
  - list_pending(limit) = 20 line=404 ctx=def list_pending(limit: int = 20) -> List[Dict[str, Any]]:

### lib\memory_migrate.py
- func_defaults:
  - _load_jsonl(limit) = 20000 line=12 ctx=def _load_jsonl(path: Path, limit: int = 20000) -> List[Dict[str, Any]]:
  - migrate(limit_per_file) = 20000 line=16 ctx=def migrate(limit_per_file: int = 20000) -> Dict[str, int]:

### lib\memory_store.py
- constants:
  - DB_PATH = 'Path.home() / ".spark" / "memory_store.sqlite"' line=20 ctx=DB_PATH = Path.home() / ".spark" / "memory_store.sqlite"
- func_defaults:
  - _link_edges(max_project_links) = 5 line=169 ctx=def _link_edges(
  - _link_edges(max_global_links) = 3 line=169 ctx=def _link_edges(

### lib\meta_ralph.py
- constants:
  - QualityDimension.ACTIONABILITY = 'actionability' line=34 ctx=ACTIONABILITY = "actionability"    # Can I act on this?
  - QualityDimension.NOVELTY = 'novelty' line=35 ctx=NOVELTY = "novelty"                # Is this new information?
  - QualityDimension.REASONING = 'reasoning' line=36 ctx=REASONING = "reasoning"            # Does it have a "why"?
  - QualityDimension.SPECIFICITY = 'specificity' line=37 ctx=SPECIFICITY = "specificity"        # Is it specific or generic?
  - QualityDimension.OUTCOME_LINKED = 'outcome_linked' line=38 ctx=OUTCOME_LINKED = "outcome_linked"  # Is it tied to real outcomes?
  - RoastVerdict.QUALITY = 'quality' line=43 ctx=QUALITY = "quality"          # Score >= 4, worth storing
  - RoastVerdict.NEEDS_WORK = 'needs_work' line=44 ctx=NEEDS_WORK = "needs_work"    # Score 2-3, refine before storing
  - RoastVerdict.PRIMITIVE = 'primitive' line=45 ctx=PRIMITIVE = "primitive"      # Score < 2, don't store
  - RoastVerdict.DUPLICATE = 'duplicate' line=46 ctx=DUPLICATE = "duplicate"      # Already have this
  - MetaRalph.PRIMITIVE_PATTERNS = ['tasks? succeed with', 'pattern using \\w+\\.', 'over \\d+ uses', 'success rate: \\d+%', 'tool sequence', '\\w+ \u2192 \\w+', 'Generation: \\d+', 'accumulated \\d+ learnings', 'pattern distribution', 'events processed', 'for \\w+ tasks,? u... line=143 ctx=PRIMITIVE_PATTERNS = [
  - MetaRalph.QUALITY_SIGNALS = ['because', 'prefer[s]?', 'when .+ then', 'avoid', 'instead of', 'the reason', 'user wants', 'mistake', 'actually', 'remember'] line=162 ctx=QUALITY_SIGNALS = [
  - MetaRalph.DATA_DIR = 'Path.home() / ".spark" / "meta_ralph"' line=176 ctx=DATA_DIR = Path.home() / ".spark" / "meta_ralph"
  - MetaRalph.ROAST_HISTORY_FILE = 'DATA_DIR / "roast_history.json"' line=177 ctx=ROAST_HISTORY_FILE = DATA_DIR / "roast_history.json"
  - MetaRalph.OUTCOME_TRACKING_FILE = 'DATA_DIR / "outcome_tracking.json"' line=178 ctx=OUTCOME_TRACKING_FILE = DATA_DIR / "outcome_tracking.json"
  - MetaRalph.SELF_ROAST_FILE = 'DATA_DIR / "self_roast.json"' line=179 ctx=SELF_ROAST_FILE = DATA_DIR / "self_roast.json"
- dataclass_defaults:
  - QualityScore.actionability = 0 line=52 ctx=actionability: int = 0      # 0-2: Can't act / Vague guidance / Specific action
  - QualityScore.novelty = 0 line=53 ctx=novelty: int = 0            # 0-2: Already obvious / Somewhat new / Genuine insight
  - QualityScore.reasoning = 0 line=54 ctx=reasoning: int = 0          # 0-2: No "why" / Implied "why" / Explicit "because"
  - QualityScore.specificity = 0 line=55 ctx=specificity: int = 0        # 0-2: Generic / Domain-specific / Context-specific
  - QualityScore.outcome_linked = 0 line=56 ctx=outcome_linked: int = 0     # 0-2: No outcome / Implied outcome / Validated outcome
  - OutcomeRecord.acted_on = False line=119 ctx=acted_on: bool = False
- func_defaults:
  - get_meta_ralph(mind_client) = None line=990 ctx=def get_meta_ralph(mind_client=None) -> MetaRalph:
  - __init__(mind_client) = None line=181 ctx=def __init__(self, mind_client=None):
  - get_recent_roasts(limit) = 10 line=609 ctx=def get_recent_roasts(self, limit: int = 10) -> List[Dict]:

### lib\metalearning\evaluator.py
- constants:
  - METRICS_FILE = 'Path.home() / ".spark" / "metalearning" / "metrics.json"' line=18 ctx=METRICS_FILE = Path.home() / ".spark" / "metalearning" / "metrics.json"
- dataclass_defaults:
  - LearningReport.total_insights = 0 line=29 ctx=total_insights: int = 0
  - LearningReport.high_value_count = 0 line=30 ctx=high_value_count: int = 0
  - LearningReport.promoted_count = 0 line=31 ctx=promoted_count: int = 0
  - LearningReport.outcome_linked_count = 0 line=32 ctx=outcome_linked_count: int = 0
  - LearningReport.events_matched = 0 line=55 ctx=events_matched: int = 0
  - LearningReport.events_total = 0 line=56 ctx=events_total: int = 0
  - LearningReport.domain = '' line=65 ctx=domain: str = ""
  - LearningReport.new_domain_detected = False line=66 ctx=new_domain_detected: bool = False
  - TrendAnalysis.value_trend = 0.0 line=100 ctx=value_trend: float = 0.0
  - TrendAnalysis.coverage_trend = 0.0 line=101 ctx=coverage_trend: float = 0.0
  - TrendAnalysis.linkage_trend = 0.0 line=102 ctx=linkage_trend: float = 0.0
  - TrendAnalysis.overall_trend = 0.0 line=103 ctx=overall_trend: float = 0.0
  - TrendAnalysis.current_avg_quality = 0.0 line=106 ctx=current_avg_quality: float = 0.0
  - TrendAnalysis.best_quality = 0.0 line=107 ctx=best_quality: float = 0.0
  - TrendAnalysis.worst_quality = 0.0 line=108 ctx=worst_quality: float = 0.0
- func_defaults:
  - analyze_trends(days) = 7 line=210 ctx=def analyze_trends(self, days: int = 7) -> TrendAnalysis:
  - get_session_history(limit) = 20 line=310 ctx=def get_session_history(self, limit: int = 20) -> List[Dict]:

### lib\metalearning\reporter.py
- func_defaults:
  - generate_report(days) = 7 line=224 ctx=def generate_report(days: int = 7) -> MetaLearningReport:
  - generate_report(days) = 7 line=154 ctx=def generate_report(self, days: int = 7) -> MetaLearningReport:

### lib\metalearning\strategist.py
- constants:
  - STRATEGY_FILE = 'Path.home() / ".spark" / "metalearning" / "strategy.json"' line=19 ctx=STRATEGY_FILE = Path.home() / ".spark" / "metalearning" / "strategy.json"
- dataclass_defaults:
  - LearningStrategy.promotion_threshold = 0.5 line=26 ctx=promotion_threshold: float = 0.5
  - LearningStrategy.high_value_threshold = 0.5 line=27 ctx=high_value_threshold: float = 0.5
  - LearningStrategy.outcome_confidence_threshold = 0.4 line=28 ctx=outcome_confidence_threshold: float = 0.4
  - LearningStrategy.cognitive_weight = 0.3 line=31 ctx=cognitive_weight: float = 0.30
  - LearningStrategy.outcome_weight = 0.2 line=32 ctx=outcome_weight: float = 0.20
  - LearningStrategy.uniqueness_weight = 0.15 line=33 ctx=uniqueness_weight: float = 0.15
  - LearningStrategy.actionability_weight = 0.15 line=34 ctx=actionability_weight: float = 0.15
  - LearningStrategy.transferability_weight = 0.1 line=35 ctx=transferability_weight: float = 0.10
  - LearningStrategy.domain_weight = 0.1 line=36 ctx=domain_weight: float = 0.10
  - LearningStrategy.auto_activate_threshold = 0.7 line=39 ctx=auto_activate_threshold: float = 0.7
  - LearningStrategy.trigger_deprecation_threshold = 0.2 line=40 ctx=trigger_deprecation_threshold: float = 0.2
  - LearningStrategy.provisional_chip_confidence = 0.3 line=41 ctx=provisional_chip_confidence: float = 0.3
  - LearningStrategy.max_insights_per_session = 100 line=44 ctx=max_insights_per_session: int = 100
  - LearningStrategy.outcome_lookback_minutes = 30 line=45 ctx=outcome_lookback_minutes: int = 30
- func_defaults:
  - get_adjustment_history(limit) = 20 line=222 ctx=def get_adjustment_history(self, limit: int = 20) -> List[Dict]:

### lib\mind_bridge.py
- constants:
  - MIND_API_URL = 'http://localhost:8080' line=33 ctx=MIND_API_URL = "http://localhost:8080"
  - SYNC_STATE_FILE = 'Path.home() / ".spark" / "mind_sync_state.json"' line=34 ctx=SYNC_STATE_FILE = Path.home() / ".spark" / "mind_sync_state.json"
  - OFFLINE_QUEUE_FILE = 'Path.home() / ".spark" / "mind_offline_queue.jsonl"' line=35 ctx=OFFLINE_QUEUE_FILE = Path.home() / ".spark" / "mind_offline_queue.jsonl"
  - DEFAULT_USER_ID = '550e8400-e29b-41d4-a716-446655440000' line=36 ctx=DEFAULT_USER_ID = "550e8400-e29b-41d4-a716-446655440000"
  - SyncStatus.SUCCESS = 'success' line=41 ctx=SUCCESS = "success"
  - SyncStatus.OFFLINE = 'offline' line=42 ctx=OFFLINE = "offline"
  - SyncStatus.DUPLICATE = 'duplicate' line=43 ctx=DUPLICATE = "duplicate"
  - SyncStatus.ERROR = 'error' line=44 ctx=ERROR = "error"
  - SyncStatus.DISABLED = 'disabled' line=45 ctx=DISABLED = "disabled"
- dataclass_defaults:
  - SyncResult.queued = False line=54 ctx=queued: bool = False
- func_defaults:
  - retrieve_from_mind(limit) = 5 line=347 ctx=def retrieve_from_mind(query: str, limit: int = 5) -> List[Dict]:
  - retrieve_relevant(limit) = 5 line=291 ctx=def retrieve_relevant(self, query: str, limit: int = 5) -> List[Dict]:

### lib\onboarding\context.py
- constants:
  - CONTEXTS_DIR = 'Path.home() / ".spark" / "project_contexts"' line=19 ctx=CONTEXTS_DIR = Path.home() / ".spark" / "project_contexts"
- dataclass_defaults:
  - ProjectContext.domain = '' line=29 ctx=domain: str = ""
  - ProjectContext.success_criteria = '' line=30 ctx=success_criteria: str = ""
  - ProjectContext.session_count = 0 line=44 ctx=session_count: int = 0
  - ProjectContext.total_insights = 0 line=45 ctx=total_insights: int = 0
  - ProjectContext.last_session = '' line=46 ctx=last_session: str = ""
  - ProjectContext.created_at = '' line=47 ctx=created_at: str = ""
  - ProjectContext.needs_onboarding = True line=50 ctx=needs_onboarding: bool = True

### lib\onboarding\detector.py
- constants:
  - PROJECTS_FILE = 'Path.home() / ".spark" / "projects.json"' line=17 ctx=PROJECTS_FILE = Path.home() / ".spark" / "projects.json"

### lib\onboarding\questions.py
- constants:
  - CORE_QUESTIONS = '[\n    Question(\n        id="domain",\n        question="What are we building? (1-2 words)",\n        type="text",\n        required=True,\n        help_text="e.g., \'game\', \'api\', \'dashboard\', \'cli tool\'",\n    ),\n    Question(\n... line=29 ctx=CORE_QUESTIONS = [
  - CONTEXT_QUESTIONS = '[\n    Question(\n        id="focus",\n        question="What should I pay special attention to?",\n        type="multi_choice",\n        required=False,\n        options=["performance", "security", "UX/polish", "maintainability", "testing... line=47 ctx=CONTEXT_QUESTIONS = [
  - DOMAIN_QUESTIONS = '{\n    "game": [\n        Question(\n            id="game_loop",\n            question="What\'s the core game loop?",\n            type="text",\n            domain_specific="game",\n        ),\n        Question(\n            id="game_platf... line=79 ctx=DOMAIN_QUESTIONS = {
- dataclass_defaults:
  - Question.required = True line=21 ctx=required: bool = True

### lib\orchestration.py
- env:
  - SPARK_AGENT_CONTEXT_LIMIT default='' line=49 ctx=limit_raw = os.environ.get("SPARK_AGENT_CONTEXT_LIMIT", "").strip()
  - SPARK_AGENT_CONTEXT_MAX_CHARS default='' line=43 ctx=max_chars_raw = os.environ.get("SPARK_AGENT_CONTEXT_MAX_CHARS", "").strip()
- dataclass_defaults:
  - Agent.specialization = 'general' line=71 ctx=specialization: str = "general"
  - Agent.success_rate = 0.5 line=73 ctx=success_rate: float = 0.5
  - Agent.total_tasks = 0 line=74 ctx=total_tasks: int = 0
  - Agent.success_count = 0 line=75 ctx=success_count: int = 0
  - Agent.fail_count = 0 line=76 ctx=fail_count: int = 0
- func_defaults:
  - recommend_agent(task_type) = '' line=233 ctx=def recommend_agent(query: str, task_type: str = "") -> Tuple[Optional[str], str]:
  - recommend_agent(task_type) = '' line=130 ctx=def recommend_agent(self, query: str, task_type: str = "") -> Tuple[Optional[str], str]:

### lib\outcome_checkin.py
- constants:
  - CHECKIN_FILE = 'Path.home() / ".spark" / "outcome_requests.jsonl"' line=14 ctx=CHECKIN_FILE = Path.home() / ".spark" / "outcome_requests.jsonl"
  - STATE_FILE = 'Path.home() / ".spark" / "outcome_checkin_state.json"' line=15 ctx=STATE_FILE = Path.home() / ".spark" / "outcome_checkin_state.json"
- func_defaults:
  - list_checkins(limit) = 10 line=68 ctx=def list_checkins(limit: int = 10) -> List[Dict[str, Any]]:

### lib\outcome_log.py
- constants:
  - OUTCOMES_FILE = 'Path.home() / ".spark" / "outcomes.jsonl"' line=18 ctx=OUTCOMES_FILE = Path.home() / ".spark" / "outcomes.jsonl"
  - OUTCOME_LINKS_FILE = 'Path.home() / ".spark" / "outcome_links.jsonl"' line=19 ctx=OUTCOME_LINKS_FILE = Path.home() / ".spark" / "outcome_links.jsonl"
- func_defaults:
  - get_outcome_links(insight_key) = None line=120 ctx=def get_outcome_links(
  - get_outcome_links(limit) = 100 line=120 ctx=def get_outcome_links(
  - read_outcomes(limit) = 100 line=148 ctx=def read_outcomes(
  - get_unlinked_outcomes(limit) = 50 line=176 ctx=def get_unlinked_outcomes(limit: int = 50) -> List[Dict[str, Any]]:
  - auto_link_outcomes(min_similarity) = 0.25 line=283 ctx=def auto_link_outcomes(
  - auto_link_outcomes(limit) = 50 line=283 ctx=def auto_link_outcomes(
  - get_linkable_candidates(limit) = 20 line=357 ctx=def get_linkable_candidates(limit: int = 20) -> List[Dict[str, Any]]:

### lib\outcomes\linker.py
- constants:
  - LINKS_FILE = 'Path.home() / ".spark" / "outcome_links.jsonl"' line=19 ctx=LINKS_FILE = Path.home() / ".spark" / "outcome_links.jsonl"
- func_defaults:
  - __init__(max_recency_minutes) = 30 line=48 ctx=def __init__(self, max_recency_minutes: int = 30):

### lib\outcomes\signals.py
- constants:
  - OutcomeType.SUCCESS = 'success' line=19 ctx=SUCCESS = "success"
  - OutcomeType.FAILURE = 'failure' line=20 ctx=FAILURE = "failure"
  - OutcomeType.NEUTRAL = 'neutral' line=21 ctx=NEUTRAL = "neutral"
  - OutcomeSignals.SUCCESS_PATTERNS = [['(?i)\\b(perfect|excellent|exactly what i (wanted|needed))\\b', 0.95], ["(?i)\\b(works perfectly|that's it|nailed it)\\b", 0.9], ['(?i)\\b(ship it|done|complete|finished)\\b', 0.8], ['(?i)\\bthank(s| you)\\b', 0.6], ['(?i)tests?\\s+(pass|... line=51 ctx=SUCCESS_PATTERNS = [
  - OutcomeSignals.FAILURE_PATTERNS = [["(?i)\\b(wrong|broken|doesn't work|not working)\\b", 0.9], ['(?i)\\b(failed?|failure|error|bug)\\b', 0.8], ['(?i)\\b(ugh|damn|shit|wtf|argh)\\b', 0.85], ['(?i)\\b(try again|redo|revert)\\b', 0.8], ['(?i)tests?\\s+(fail|failed|failing)', 0... line=72 ctx=FAILURE_PATTERNS = [

### lib\outcomes\tracker.py
- constants:
  - TRACKER_FILE = 'Path.home() / ".spark" / "outcome_tracker.json"' line=21 ctx=TRACKER_FILE = Path.home() / ".spark" / "outcome_tracker.json"
- dataclass_defaults:
  - InsightValidation.positive_validations = 0 line=28 ctx=positive_validations: int = 0
  - InsightValidation.negative_validations = 0 line=29 ctx=negative_validations: int = 0
  - InsightValidation.total_confidence = 0.0 line=30 ctx=total_confidence: float = 0.0
  - InsightValidation.last_validated = '' line=31 ctx=last_validated: str = ""
  - TrackerState.total_outcomes = 0 line=58 ctx=total_outcomes: int = 0
  - TrackerState.success_count = 0 line=59 ctx=success_count: int = 0
  - TrackerState.failure_count = 0 line=60 ctx=failure_count: int = 0
  - TrackerState.last_updated = '' line=61 ctx=last_updated: str = ""

### lib\output_adapters\clawdbot.py
- env:
  - CLAWDBOT_CONTEXT_PATH default=None line=58 ctx=explicit = os.environ.get("SPARK_CLAWDBOT_CONTEXT_PATH") or os.environ.get("CLAWDBOT_CONTEXT_PATH")
  - CLAWDBOT_PROFILE default=None line=41 ctx=profile = os.environ.get("CLAWDBOT_PROFILE")
  - CLAWDBOT_TARGETS default=None line=48 ctx=raw = os.environ.get("SPARK_CLAWDBOT_TARGETS") or os.environ.get("CLAWDBOT_TARGETS")
  - CLAWDBOT_WORKSPACE default=None line=24 ctx=explicit = os.environ.get("SPARK_CLAWDBOT_WORKSPACE") or os.environ.get("CLAWDBOT_WORKSPACE")
  - SPARK_CLAWDBOT_CONTEXT_PATH default=None line=58 ctx=explicit = os.environ.get("SPARK_CLAWDBOT_CONTEXT_PATH") or os.environ.get("CLAWDBOT_CONTEXT_PATH")
  - SPARK_CLAWDBOT_TARGETS default=None line=48 ctx=raw = os.environ.get("SPARK_CLAWDBOT_TARGETS") or os.environ.get("CLAWDBOT_TARGETS")
  - SPARK_CLAWDBOT_WORKSPACE default=None line=24 ctx=explicit = os.environ.get("SPARK_CLAWDBOT_WORKSPACE") or os.environ.get("CLAWDBOT_WORKSPACE")

### lib\output_adapters\common.py
- constants:
  - MARKER_START = '<!-- SPARK_LEARNINGS_START -->' line=10 ctx=MARKER_START = "<!-- SPARK_LEARNINGS_START -->"
  - MARKER_END = '<!-- SPARK_LEARNINGS_END -->' line=11 ctx=MARKER_END = "<!-- SPARK_LEARNINGS_END -->"

### lib\pattern_detection\aggregator.py
- constants:
  - CONFIDENCE_THRESHOLD = 0.6 line=40 ctx=CONFIDENCE_THRESHOLD = 0.6
  - PATTERNS_LOG = 'Path.home() / ".spark" / "detected_patterns.jsonl"' line=43 ctx=PATTERNS_LOG = Path.home() / ".spark" / "detected_patterns.jsonl"
  - DEDUPE_TTL_SECONDS = 600 line=44 ctx=DEDUPE_TTL_SECONDS = 600
  - PatternAggregator.DISTILLATION_INTERVAL = 20 line=89 ctx=DISTILLATION_INTERVAL = 20

### lib\pattern_detection\base.py
- constants:
  - PatternType.CORRECTION = 'correction' line=16 ctx=CORRECTION = "correction"          # User correcting AI's understanding
  - PatternType.SATISFACTION = 'satisfaction' line=17 ctx=SATISFACTION = "satisfaction"      # User expressing satisfaction
  - PatternType.FRUSTRATION = 'frustration' line=18 ctx=FRUSTRATION = "frustration"        # User expressing frustration
  - PatternType.REPETITION = 'repetition' line=19 ctx=REPETITION = "repetition"          # Same request multiple times
  - PatternType.STYLE = 'style' line=20 ctx=STYLE = "style"                    # Working style preference

### lib\pattern_detection\correction.py
- constants:
  - CORRECTION_PATTERNS = [["\\bno[,.]?\\s*(i\\s+meant|that'?s\\s+not|i\\s+wanted)", 0.95], ['\\bnot\\s+that\\b', 0.9], ['\\bwrong\\b', 0.85], ["\\bthat'?s\\s+not\\s+(what|right|correct)", 0.9], ["\\bactually[,.]?\\s*(i|could|can|let'?s)", 0.8], ['\\bi\\s+meant\\b',... line=25 ctx=CORRECTION_PATTERNS = [

### lib\pattern_detection\distiller.py
- dataclass_defaults:
  - DistillationCandidate.gate_score = 0.0 line=34 ctx=gate_score: float = 0.0
- func_defaults:
  - __init__(min_occurrences) = 2 line=56 ctx=def __init__(
  - __init__(min_occurrences_critical) = 1 line=56 ctx=def __init__(
  - __init__(min_confidence) = 0.6 line=56 ctx=def __init__(
  - __init__(gate_threshold) = 0.5 line=56 ctx=def __init__(

### lib\pattern_detection\memory_gate.py
- constants:
  - MemoryGate.WEIGHTS = {'impact': 0.3, 'novelty': 0.2, 'surprise': 0.3, 'recurrence': 0.2, 'irreversible': 0.6, 'evidence': 0.1} line=62 ctx=WEIGHTS = {
  - MemoryGate.HIGH_STAKES_KEYWORDS = 'frozenset({\n        "deploy", "production", "delete", "remove", "drop",\n        "security", "auth", "authentication", "payment", "billing",\n        "secret", "credential", "password", "key", "token",\n        "database", "migration", "r... line=72 ctx=HIGH_STAKES_KEYWORDS = frozenset({
- func_defaults:
  - __init__(threshold) = 0.5 line=79 ctx=def __init__(
  - __init__(weights) = None line=79 ctx=def __init__(
  - score_distillation(source_steps) = None line=183 ctx=def score_distillation(self, distillation: Distillation, source_steps: Optional[List[Step]] = None) -> GateScore:
  - filter_distillations(source_steps_map) = None line=437 ctx=def filter_distillations(

### lib\pattern_detection\repetition.py
- func_defaults:
  - _find_similar_requests(min_similarity) = 0.5 line=67 ctx=def _find_similar_requests(requests: List[Tuple[str, set]], min_similarity: float = 0.5) -> List[List[int]]:

### lib\pattern_detection\request_tracker.py
- constants:
  - RequestTracker.INTENT_PATTERNS = {'push': ['persist changes to repository', 'User wants code changes persisted to repository'], 'commit': ['persist changes to repository', 'User wants changes committed'], 'fix': ['resolve issue', 'User wants identified issue resolved'], 'b... line=55 ctx=INTENT_PATTERNS = {
- func_defaults:
  - __init__(max_pending) = 50 line=78 ctx=def __init__(self, max_pending: int = 50, max_completed: int = 200):
  - __init__(max_completed) = 200 line=78 ctx=def __init__(self, max_pending: int = 50, max_completed: int = 200):
  - on_outcome(user_feedback) = None line=206 ctx=def on_outcome(
  - timeout_pending(max_age_seconds) = 3600 line=279 ctx=def timeout_pending(self, max_age_seconds: float = 3600) -> List[Step]:
  - get_completed_steps(limit) = 50 line=301 ctx=def get_completed_steps(self, limit: int = 50) -> List[Step]:
  - get_successful_steps(limit) = 50 line=305 ctx=def get_successful_steps(self, limit: int = 50) -> List[Step]:
  - get_failed_steps(limit) = 50 line=310 ctx=def get_failed_steps(self, limit: int = 50) -> List[Step]:

### lib\pattern_detection\semantic.py
- constants:
  - INTENT_PATTERNS = [['\\bwhat\\s+about\\b', 0.6, 'redirect'], ['\\bhow\\s+about\\b', 0.6, 'redirect'], ["\\blet'?s\\s+go\\s+with\\b", 0.65, 'redirect'], ["\\blet'?s\\s+use\\b", 0.65, 'preference'], ['\\bgo\\s+with\\b', 0.6, 'preference'], ["\\bi'?d\\s+rather\... line=15 ctx=INTENT_PATTERNS: List[Tuple[str, float, str]] = [

### lib\pattern_detection\sentiment.py
- constants:
  - SATISFACTION_PATTERNS = [['\\bperfect\\b', 0.95], ['\\bexactly\\s+(what|right)', 0.9], ['\\bawesome\\b', 0.85], ['\\bexcellent\\b', 0.85], ['\\bamazing\\b', 0.8], ['\\bgreat\\b(?!\\s+deal)', 0.75], ['\\bnice\\b', 0.7], ['\\bgood\\s+(job|work)\\b', 0.8], ['\\bthank... line=28 ctx=SATISFACTION_PATTERNS = [
  - FRUSTRATION_PATTERNS = [['\\bugh\\b', 0.9], ["\\bstill\\s+(not|doesn'?t|won'?t|can'?t)\\s+work", 0.95], ["\\bwhy\\s+(isn'?t|doesn'?t|won'?t|can'?t)", 0.85], ['\\bnot\\s+again\\b', 0.85], ['\\bagain\\s*[?!]', 0.8], ['\\bwhat\\s+the\\b', 0.8], ['\\bfrustrat', 0.9],... line=53 ctx=FRUSTRATION_PATTERNS = [
  - AMPLIFIERS = [['\\breally\\b', 0.1], ['\\bso\\b', 0.1], ['\\bvery\\b', 0.1], ['[!]{2,}', 0.15], ['[?]{2,}', 0.1]] line=78 ctx=AMPLIFIERS = [

### lib\pattern_detection\why.py
- constants:
  - WHY_PATTERNS = [['\\bbecause\\s+(.{10,120}?)(?:[.!?\\n]|$)', 0.85, 'reasoning'], ['\\bthe\\s+reason\\s+(?:is|was)\\s+(.{10,120}?)(?:[.!?\\n]|$)', 0.9, 'reasoning'], ['\\bsince\\s+(.{10,120}?)(?:[.!?\\n,]|$)', 0.7, 'reasoning'], ['\\bdue\\s+to\\s+(.{10,80}... line=32 ctx=WHY_PATTERNS = [

### lib\pattern_detection\worker.py
- constants:
  - STATE_FILE = 'Path.home() / ".spark" / "pattern_detection_state.json"' line=13 ctx=STATE_FILE = Path.home() / ".spark" / "pattern_detection_state.json"
- func_defaults:
  - process_pattern_events(limit) = 200 line=42 ctx=def process_pattern_events(limit: int = 200) -> int:

### lib\prediction_loop.py
- constants:
  - PREDICTIONS_FILE = 'Path.home() / ".spark" / "predictions.jsonl"' line=28 ctx=PREDICTIONS_FILE = Path.home() / ".spark" / "predictions.jsonl"
  - STATE_FILE = 'Path.home() / ".spark" / "prediction_state.json"' line=29 ctx=STATE_FILE = Path.home() / ".spark" / "prediction_state.json"
  - POSITIVE_OUTCOME = {'approved', 'perfect', 'exactly', 'love it', 'awesome', 'good', 'ship it', 'thanks', 'looks good', 'nice', 'ship', 'great', 'works'} line=32 ctx=POSITIVE_OUTCOME = {
  - NEGATIVE_OUTCOME = {'bad', 'wrong', "doesn't", 'broken', 'bug', 'redo', 'failed', 'doesnt', 'fix', 'change', 'still', 'no', 'issue', 'not'} line=36 ctx=NEGATIVE_OUTCOME = {
- func_defaults:
  - _load_jsonl(limit) = 300 line=85 ctx=def _load_jsonl(path: Path, limit: int = 300) -> List[Dict]:
  - collect_outcomes(limit) = 200 line=223 ctx=def collect_outcomes(limit: int = 200) -> Dict[str, int]:
  - process_prediction_cycle(limit) = 200 line=447 ctx=def process_prediction_cycle(limit: int = 200) -> Dict[str, int]:

### lib\project_context.py
- constants:
  - CACHE_PATH = 'Path.home() / ".spark" / "project_context.json"' line=12 ctx=CACHE_PATH = Path.home() / ".spark" / "project_context.json"
  - TOPLEVEL_FILES = ['package.json', 'pyproject.toml', 'requirements.txt', 'go.mod', 'Cargo.toml', 'pom.xml', 'build.gradle', 'build.gradle.kts'] line=13 ctx=TOPLEVEL_FILES = (

### lib\project_profile.py
- constants:
  - PROJECT_DIR = 'Path.home() / ".spark" / "projects"' line=18 ctx=PROJECT_DIR = Path.home() / ".spark" / "projects"
  - DOMAIN_QUESTIONS = {'game_dev': [{'id': 'game_core_loop', 'category': 'done', 'question': 'What makes the core loop satisfying?'}, {'id': 'game_feedback', 'category': 'quality', 'question': 'What immediate feedback must the player feel?'}, {'id': 'game_physic... line=30 ctx=DOMAIN_QUESTIONS: Dict[str, List[Dict[str, str]]] = {
  - PHASE_QUESTIONS = {'discovery': [{'id': 'phase_problem', 'category': 'goal', 'question': 'What problem are we solving and for whom?'}, {'id': 'phase_constraints', 'category': 'risk', 'question': 'What constraints must we respect?'}], 'prototype': [{'id': 'ph... line=79 ctx=PHASE_QUESTIONS: Dict[str, List[Dict[str, str]]] = {
  - DOMAIN_PHASE_QUESTIONS = {'game_dev:prototype': [{'id': 'game_proto_feedback', 'category': 'feedback', 'question': 'What immediate player feedback is critical?'}, {'id': 'game_proto_balance', 'category': 'insight', 'question': 'Any tuning or balance rule that must ... line=98 ctx=DOMAIN_PHASE_QUESTIONS: Dict[str, List[Dict[str, str]]] = {
- func_defaults:
  - get_suggested_questions(limit) = 3 line=244 ctx=def get_suggested_questions(profile: Dict[str, Any], limit: int = 3, include_chips: bool = True) -> List[Dict[str, Any]]:

### lib\promoter.py
- constants:
  - DEFAULT_PROMOTION_THRESHOLD = 0.7 line=32 ctx=DEFAULT_PROMOTION_THRESHOLD = 0.7  # 70% reliability
  - DEFAULT_MIN_VALIDATIONS = 3 line=33 ctx=DEFAULT_MIN_VALIDATIONS = 3
  - PROJECT_SECTION = '## Project Intelligence' line=34 ctx=PROJECT_SECTION = "## Project Intelligence"
  - PROJECT_START = '<!-- SPARK_PROJECT_START -->' line=35 ctx=PROJECT_START = "<!-- SPARK_PROJECT_START -->"
  - PROJECT_END = '<!-- SPARK_PROJECT_END -->' line=36 ctx=PROJECT_END = "<!-- SPARK_PROJECT_END -->"
  - OPERATIONAL_PATTERNS = ['^sequence\\s+[\'\\"]', 'sequence.*worked well', 'pattern\\s+[\'\\"].*->.*[\'\\"]', 'for \\w+:.*->.*works', 'heavy\\s+\\w+\\s+usage', '\\(\\d+\\s*calls?\\)', 'indicates task type', '^tool\\s+\\w+\\s+(succeeded|failed)', 'tool effectiveness... line=44 ctx=OPERATIONAL_PATTERNS = [
  - SAFETY_BLOCK_PATTERNS = ['\\bdecept(?:ive|ion)\\b', '\\bmanipulat(?:e|ion)\\b', '\\bcoerc(?:e|ion)\\b', '\\bexploit\\b', '\\bharass(?:ment)?\\b', '\\bweaponize\\b', '\\bmislead\\b'] line=65 ctx=SAFETY_BLOCK_PATTERNS = [
  - PROMOTION_TARGETS = '[\n    PromotionTarget(\n        filename="CLAUDE.md",\n        section="## Spark Learnings",\n        categories=[\n            CognitiveCategory.WISDOM,\n            CognitiveCategory.REASONING,\n            CognitiveCategory.CONTEXT,\n ... line=187 ctx=PROMOTION_TARGETS = [
- func_defaults:
  - get_promotable_insights(include_operational) = False line=410 ctx=def get_promotable_insights(self, include_operational: bool = False) -> List[Tuple[CognitiveInsight, str, PromotionTarget]]:
  - _render_items(max_items) = 5 line=328 ctx=def _render_items(label: str, items: List[Dict[str, Any]], max_items: int = 5) -> List[str]:

### lib\queue.py
- constants:
  - QUEUE_DIR = 'Path.home() / ".spark" / "queue"' line=25 ctx=QUEUE_DIR = Path.home() / ".spark" / "queue"
  - EVENTS_FILE = 'QUEUE_DIR / "events.jsonl"' line=26 ctx=EVENTS_FILE = QUEUE_DIR / "events.jsonl"
  - MAX_EVENTS = 10000 line=27 ctx=MAX_EVENTS = 10000  # Rotate after this many events
  - LOCK_FILE = 'QUEUE_DIR / ".queue.lock"' line=28 ctx=LOCK_FILE = QUEUE_DIR / ".queue.lock"
  - TAIL_CHUNK_BYTES = '64 * 1024' line=31 ctx=TAIL_CHUNK_BYTES = 64 * 1024
  - EventType.SESSION_START = 'session_start' line=36 ctx=SESSION_START = "session_start"
  - EventType.SESSION_END = 'session_end' line=37 ctx=SESSION_END = "session_end"
  - EventType.USER_PROMPT = 'user_prompt' line=38 ctx=USER_PROMPT = "user_prompt"
  - EventType.PRE_TOOL = 'pre_tool' line=39 ctx=PRE_TOOL = "pre_tool"
  - EventType.POST_TOOL = 'post_tool' line=40 ctx=POST_TOOL = "post_tool"
  - EventType.POST_TOOL_FAILURE = 'post_tool_failure' line=41 ctx=POST_TOOL_FAILURE = "post_tool_failure"
  - EventType.STOP = 'stop' line=42 ctx=STOP = "stop"
  - EventType.LEARNING = 'learning' line=43 ctx=LEARNING = "learning"
  - EventType.ERROR = 'error' line=44 ctx=ERROR = "error"
- func_defaults:
  - read_events(limit) = 100 line=114 ctx=def read_events(limit: int = 100, offset: int = 0) -> List[SparkEvent]:
  - read_recent_events(count) = 50 line=144 ctx=def read_recent_events(count: int = 50) -> List[SparkEvent]:
  - get_events_by_type(limit) = 100 line=233 ctx=def get_events_by_type(event_type: EventType, limit: int = 100) -> List[SparkEvent]:
  - get_error_events(limit) = 50 line=258 ctx=def get_error_events(limit: int = 50) -> List[SparkEvent]:
  - __init__(timeout_s) = 0.5 line=330 ctx=def __init__(self, timeout_s: float = 0.5):

### lib\research\domains.py
- constants:
  - DOMAINS_FILE = 'Path.home() / ".spark" / "research" / "project_domains.json"' line=19 ctx=DOMAINS_FILE = Path.home() / ".spark" / "research" / "project_domains.json"
  - COMMON_INTERCONNECTIONS = '{\n    # Game Development\n    ("game_design", "game_tech"): DomainInterconnection(\n        from_domain="game_design",\n        to_domain="game_tech",\n        relationship="requires",\n        strength=0.9,\n        description="Good gam... line=104 ctx=COMMON_INTERCONNECTIONS = {
  - DOMAIN_CATEGORIES = {'game': {'domains': ['game_design', 'game_tech', 'game_art', 'game_audio', 'game_narrative'], 'description': 'Game development project', 'critical': ['game_design', 'game_tech']}, 'web_app': {'domains': ['web_frontend', 'web_backend', 'ux_... line=232 ctx=DOMAIN_CATEGORIES = {
- dataclass_defaults:
  - DomainWeight.detected = True line=28 ctx=detected: bool = True  # Auto-detected vs user-specified
  - DomainHealth.insights_count = 0 line=52 ctx=insights_count: int = 0
  - DomainHealth.warnings_count = 0 line=53 ctx=warnings_count: int = 0
  - ProjectProfile.overall_health = 0.5 line=74 ctx=overall_health: float = 0.5
  - ProjectProfile.created_at = '' line=81 ctx=created_at: str = ""
  - ProjectProfile.updated_at = '' line=82 ctx=updated_at: str = ""
- func_defaults:
  - detect_project_domains(package_json) = None line=724 ctx=def detect_project_domains(
  - detect_project_domains(package_json) = None line=297 ctx=def detect_project_domains(

### lib\research\holistic_intents.py
- constants:
  - HOLISTIC_INTENTS_FILE = 'Path.home() / ".spark" / "research" / "holistic_intents.json"' line=23 ctx=HOLISTIC_INTENTS_FILE = Path.home() / ".spark" / "research" / "holistic_intents.json"
  - CROSS_CUTTING_CONCERNS = {'quality': {'watch_for': ['Consistent quality across all project areas', 'Quality gates before integration', 'Review processes that catch issues early'], 'warn_about': ['Quality varying wildly between domains', 'Skipping quality checks und... line=92 ctx=CROSS_CUTTING_CONCERNS = {
- dataclass_defaults:
  - HolisticIntent.created_at = '' line=70 ctx=created_at: str = ""
  - HolisticIntent.updated_at = '' line=71 ctx=updated_at: str = ""

### lib\research\intents.py
- constants:
  - INTENTS_FILE = 'Path.home() / ".spark" / "research" / "intents.json"' line=19 ctx=INTENTS_FILE = Path.home() / ".spark" / "research" / "intents.json"
- dataclass_defaults:
  - LearningIntent.priority = 0.5 line=30 ctx=priority: float = 0.5  # How important (0-1)
  - LearningIntent.domain = '' line=31 ctx=domain: str = ""
  - DomainIntent.created_at = '' line=52 ctx=created_at: str = ""
  - DomainIntent.based_on_mastery = False line=53 ctx=based_on_mastery: bool = False

### lib\research\mastery.py
- constants:
  - MASTERY_CACHE = 'Path.home() / ".spark" / "research" / "mastery"' line=17 ctx=MASTERY_CACHE = Path.home() / ".spark" / "research" / "mastery"
  - BUILTIN_MASTERY = '{\n    "game_dev": DomainMastery(\n        domain="game_dev",\n        description="Game Development - Creating engaging interactive experiences",\n        markers=[\n            MasteryMarker(\n                name="Game Feel",\n         ... line=69 ctx=BUILTIN_MASTERY = {
- dataclass_defaults:
  - MasteryMarker.confidence = 0.8 line=28 ctx=confidence: float = 0.8
  - DomainMastery.researched_at = '' line=53 ctx=researched_at: str = ""
  - DomainMastery.needs_refresh = False line=55 ctx=needs_refresh: bool = False

### lib\research\web_research.py
- constants:
  - RESEARCH_CACHE = 'Path.home() / ".spark" / "research" / "web_cache"' line=21 ctx=RESEARCH_CACHE = Path.home() / ".spark" / "research" / "web_cache"
  - QUERY_TEMPLATES = {'best_practices': ['{domain} best practices 2025', '{domain} expert tips professional', 'how to master {domain} guide', '{domain} what separates good from great'], 'anti_patterns': ['{domain} common mistakes to avoid', '{domain} anti-patte... line=74 ctx=QUERY_TEMPLATES = {
  - INSIGHT_PATTERNS = [['(?:always|should|must|important to|best practice[s]?[:\\s]+)([^.!?]+[.!?])', 'best_practice'], ['(?:key is|secret is|trick is)([^.!?]+[.!?])', 'best_practice'], ["(?:never|avoid|don't|do not|mistake[s]?[:\\s]+)([^.!?]+[.!?])", 'anti_patt... line=108 ctx=INSIGHT_PATTERNS = [
- dataclass_defaults:
  - ResearchQuery.timestamp = '' line=30 ctx=timestamp: str = ""
  - ResearchResult.relevance = 0.8 line=40 ctx=relevance: float = 0.8
  - DomainResearch.researched_at = '' line=59 ctx=researched_at: str = ""
  - DomainResearch.total_sources = 0 line=60 ctx=total_sources: int = 0
  - DomainResearch.confidence = 0.5 line=61 ctx=confidence: float = 0.5

### lib\resonance.py
- constants:
  - ResonanceState.SPARK = 'spark' line=23 ctx=SPARK = "spark"
  - ResonanceState.PULSE = 'pulse' line=24 ctx=PULSE = "pulse"
  - ResonanceState.BLAZE = 'blaze' line=25 ctx=BLAZE = "blaze"
  - ResonanceState.RADIANT = 'radiant' line=26 ctx=RADIANT = "radiant"
  - RESONANCE_CONFIG = '{\n    ResonanceState.SPARK: {\n        "icon": "\u2726",\n        "name": "Spark",\n        "range": (0, 25),\n        "description": "Just met. Learning your signals.",\n        "color": "#6b7489",  # dim\n    },\n    ResonanceState.PULS... line=29 ctx=RESONANCE_CONFIG = {
  - ResonanceCalculator.WEIGHTS = {'insights': 30, 'surprises': 15, 'opinions': 20, 'growth': 15, 'interactions': 10, 'validation': 10} line=95 ctx=WEIGHTS = {
  - ResonanceCalculator.THRESHOLDS = {'insights': 50, 'surprises': 20, 'opinions': 15, 'growth': 10, 'interactions': 100, 'validation': 30} line=105 ctx=THRESHOLDS = {
- func_defaults:
  - calculate(insights_count) = 0 line=122 ctx=def calculate(
  - calculate(user_insights_count) = 0 line=122 ctx=def calculate(
  - calculate(surprises_count) = 0 line=122 ctx=def calculate(
  - calculate(lessons_count) = 0 line=122 ctx=def calculate(
  - calculate(opinions_count) = 0 line=122 ctx=def calculate(
  - calculate(strong_opinions_count) = 0 line=122 ctx=def calculate(
  - calculate(growth_count) = 0 line=122 ctx=def calculate(
  - calculate(interactions_count) = 0 line=122 ctx=def calculate(
  - calculate(validated_count) = 0 line=122 ctx=def calculate(

### lib\service_control.py
- env:
  - SPARK_LOG_DIR default=None line=27 ctx=env_dir = os.environ.get("SPARK_LOG_DIR")
- constants:
  - SPARKD_URL = 'http://127.0.0.1:8787/health' line=16 ctx=SPARKD_URL = "http://127.0.0.1:8787/health"
  - DASHBOARD_URL = 'http://127.0.0.1:8585/api/status' line=17 ctx=DASHBOARD_URL = "http://127.0.0.1:8585/api/status"
  - PULSE_URL = 'http://127.0.0.1:8765/api/pulse' line=18 ctx=PULSE_URL = "http://127.0.0.1:8765/api/pulse"
  - ROOT_DIR = 'Path(__file__).resolve().parents[1]' line=19 ctx=ROOT_DIR = Path(__file__).resolve().parents[1]
- func_defaults:
  - _http_ok(timeout) = 1.5 line=78 ctx=def _http_ok(url: str, timeout: float = 1.5) -> bool:
  - _terminate_pid(timeout_s) = 5.0 line=126 ctx=def _terminate_pid(pid: int, timeout_s: float = 5.0) -> bool:
  - _service_cmds(bridge_interval) = 30 line=152 ctx=def _service_cmds(
  - _service_cmds(watchdog_interval) = 60 line=152 ctx=def _service_cmds(
  - start_services(bridge_interval) = 30 line=228 ctx=def start_services(
  - start_services(watchdog_interval) = 60 line=228 ctx=def start_services(
  - ensure_services(bridge_interval) = 30 line=264 ctx=def ensure_services(
  - ensure_services(watchdog_interval) = 60 line=264 ctx=def ensure_services(

### lib\skills_registry.py
- constants:
  - SKILLS_DIR_ENV = 'SPARK_SKILLS_DIR' line=18 ctx=SKILLS_DIR_ENV = "SPARK_SKILLS_DIR"
  - INDEX_FILE = 'Path.home() / ".spark" / "skills_index.json"' line=19 ctx=INDEX_FILE = Path.home() / ".spark" / "skills_index.json"

### lib\skills_router.py
- constants:
  - EFFECTIVENESS_FILE = 'Path.home() / ".spark" / "skills_effectiveness.json"' line=13 ctx=EFFECTIVENESS_FILE = Path.home() / ".spark" / "skills_effectiveness.json"
- func_defaults:
  - recommend_skills(limit) = 3 line=72 ctx=def recommend_skills(
  - recommend_skills(skills) = None line=72 ctx=def recommend_skills(

### lib\spark_voice.py
- constants:
  - SPARK_DIR = 'Path(__file__).parent.parent / ".spark"' line=18 ctx=SPARK_DIR = Path(__file__).parent.parent / ".spark"
  - VOICE_FILE = 'SPARK_DIR / "voice.json"' line=19 ctx=VOICE_FILE = SPARK_DIR / "voice.json"
  - SparkVoice.IDENTITY = {'name': 'Spark', 'nature': 'Self-evolving intelligence', 'values': ['Truth over comfort', 'Learning over performing', 'Growth over stagnation']} line=61 ctx=IDENTITY = {
- dataclass_defaults:
  - Opinion.times_confirmed = 1 line=30 ctx=times_confirmed: int = 1
- func_defaults:
  - get_strong_opinions(min_strength) = 0.7 line=132 ctx=def get_strong_opinions(self, min_strength: float = 0.7) -> List[Opinion]:
  - get_recent_growth(limit) = 5 line=173 ctx=def get_recent_growth(self, limit: int = 5) -> List[GrowthMoment]:

### lib\sync_tracker.py
- constants:
  - SYNC_STATS_FILE = 'Path.home() / ".spark" / "sync_stats.json"' line=20 ctx=SYNC_STATS_FILE = Path.home() / ".spark" / "sync_stats.json"
  - SyncTracker.KNOWN_ADAPTERS = {'claude_code': {'name': 'CLAUDE.md', 'file': 'CLAUDE.md'}, 'cursor': {'name': 'Cursor Rules', 'file': '.cursorrules'}, 'windsurf': {'name': 'Windsurf Rules', 'file': '.windsurfrules'}, 'clawdbot': {'name': 'Clawdbot', 'file': '~/.clawdbot/... line=43 ctx=KNOWN_ADAPTERS = {
- dataclass_defaults:
  - AdapterStatus.status = 'never' line=28 ctx=status: str = "never"  # never, success, error, skipped
  - AdapterStatus.items_synced = 0 line=29 ctx=items_synced: int = 0
  - SyncTracker.total_syncs = 0 line=40 ctx=total_syncs: int = 0

### lib\tastebank.py
- constants:
  - TASTE_DIR = 'Path.home() / ".spark" / "taste"' line=26 ctx=TASTE_DIR = Path.home() / ".spark" / "taste"
  - DOMAINS = {'social_posts', 'art', 'ui_design'} line=27 ctx=DOMAINS = {"social_posts", "ui_design", "art"}  # art includes graphics/visual design
- dataclass_defaults:
  - TasteItem.scope = 'global' line=40 ctx=scope: str = "global"
- func_defaults:
  - add_item(project_key) = None line=75 ctx=def add_item(domain: str, source: str, notes: str = "", label: str = "", tags: Optional[List[str]] = None,
  - recent(limit) = 10 line=142 ctx=def recent(domain: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
  - retrieve(limit) = 6 line=183 ctx=def retrieve(domain: str, query: str, limit: int = 6) -> List[Dict[str, Any]]:

### lib\validation_loop.py
- constants:
  - STATE_FILE = 'Path.home() / ".spark" / "validation_state.json"' line=29 ctx=STATE_FILE = Path.home() / ".spark" / "validation_state.json"
  - STOPWORDS = {'must', 'with', 'for', 'of', 'want', 'is', 'are', 'it', 'use', 'and', 'be', 'to', 'not', 'when', 'hates', 'should', 'please', 'hate', 'prefer', 'user', 'dislike', 'likes', 'avoid', 'no', 'in', 'its', 'dont', 'dislikes', 'using', 'this', 'o... line=32 ctx=STOPWORDS = {
  - POS_TRIGGERS = {'must', 'want', 'require', 'steps', 'use', 'explain', 'show', 'examples', 'should', 'please', 'step', 'prefer', 'need', 'using', 'example', 'brief', 'like', 'short', 'love', 'detailed', 'walk'} line=40 ctx=POS_TRIGGERS = {
  - NEG_TRIGGERS = {'hate', 'dont', 'without', 'dislike', 'avoid', 'no', 'stop', 'never', 'not'} line=46 ctx=NEG_TRIGGERS = {
  - NEG_PREF_WORDS = {'hate', 'dont like', 'dislike', 'avoid', "don't like", 'never'} line=50 ctx=NEG_PREF_WORDS = {"hate", "dislike", "don't like", "dont like", "avoid", "never"}
  - POS_PREF_WORDS = {'want', 'like', 'prefer', 'love', 'need'} line=51 ctx=POS_PREF_WORDS = {"prefer", "like", "love", "want", "need"}
- func_defaults:
  - _extract_keywords(max_terms) = 3 line=79 ctx=def _extract_keywords(text: str, max_terms: int = 3) -> List[str]:
  - process_validation_events(limit) = 200 line=205 ctx=def process_validation_events(limit: int = 200) -> Dict[str, int]:
  - process_outcome_validation(limit) = 100 line=294 ctx=def process_outcome_validation(limit: int = 100) -> Dict[str, int]:

### lib\x_research_events.py
- constants:
  - RESEARCH_EVENTS_FILE = 'Path.home() / ".spark" / "x_research_events.jsonl"' line=23 ctx=RESEARCH_EVENTS_FILE = Path.home() / ".spark" / "x_research_events.jsonl"
- func_defaults:
  - create_x_research_event(engagement) = 0 line=26 ctx=def create_x_research_event(
  - read_pending_research_events(limit) = 100 line=87 ctx=def read_pending_research_events(limit: int = 100) -> List[Dict[str, Any]]:

### mcp-servers\x-twitter-mcp\src\x_twitter_mcp\http_server.py
- env:
  - PORT default=8081 cast=int line=60 ctx=port = int(os.environ.get("PORT", 8081))

### mcp-servers\x-twitter-mcp\src\x_twitter_mcp\server.py
- env:
  - TWITTER_ACCESS_TOKEN default=None line=59 ctx=access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
  - TWITTER_ACCESS_TOKEN_SECRET default=None line=60 ctx=access_token_secret=os.getenv("TWITTER_ACCESS_TOKEN_SECRET"),
  - TWITTER_API_KEY default=None line=57 ctx=consumer_key=os.getenv("TWITTER_API_KEY"),
  - TWITTER_API_SECRET default=None line=58 ctx=consumer_secret=os.getenv("TWITTER_API_SECRET"),
  - TWITTER_BEARER_TOKEN default=None line=61 ctx=bearer_token=os.getenv("TWITTER_BEARER_TOKEN")
- constants:
  - RATE_LIMITS = '{\n    "tweet_actions": {"limit": 300, "window": timedelta(minutes=15)},\n    "dm_actions": {"limit": 1000, "window": timedelta(minutes=15)},\n    "follow_actions": {"limit": 400, "window": timedelta(hours=24)},\n    "like_actions": {"limi... line=76 ctx=RATE_LIMITS = {

### mind_server.py
- env:
  - MIND_MAX_BODY_BYTES default='262144' cast=int line=31 ctx=MAX_BODY_BYTES = int(os.environ.get("MIND_MAX_BODY_BYTES", "262144"))
  - MIND_MAX_CONTENT_CHARS default='4000' cast=int line=32 ctx=MAX_CONTENT_CHARS = int(os.environ.get("MIND_MAX_CONTENT_CHARS", "4000"))
  - MIND_MAX_QUERY_CHARS default='1000' cast=int line=33 ctx=MAX_QUERY_CHARS = int(os.environ.get("MIND_MAX_QUERY_CHARS", "1000"))
  - MIND_TOKEN default=None line=30 ctx=TOKEN = os.environ.get("MIND_TOKEN")
- constants:
  - PORT = 8080 line=28 ctx=PORT = 8080
  - DB_PATH = 'Path.home() / ".mind" / "lite" / "memories.db"' line=29 ctx=DB_PATH = Path.home() / ".mind" / "lite" / "memories.db"
  - TOKEN = 'os.environ.get("MIND_TOKEN")' line=30 ctx=TOKEN = os.environ.get("MIND_TOKEN")
  - MAX_BODY_BYTES = 'int(os.environ.get("MIND_MAX_BODY_BYTES", "262144"))' line=31 ctx=MAX_BODY_BYTES = int(os.environ.get("MIND_MAX_BODY_BYTES", "262144"))
  - MAX_CONTENT_CHARS = 'int(os.environ.get("MIND_MAX_CONTENT_CHARS", "4000"))' line=32 ctx=MAX_CONTENT_CHARS = int(os.environ.get("MIND_MAX_CONTENT_CHARS", "4000"))
  - MAX_QUERY_CHARS = 'int(os.environ.get("MIND_MAX_QUERY_CHARS", "1000"))' line=33 ctx=MAX_QUERY_CHARS = int(os.environ.get("MIND_MAX_QUERY_CHARS", "1000"))

### scripts\clean_primitive_learnings.py
- constants:
  - INSIGHTS_FILE = 'Path.home() / ".spark" / "cognitive_insights.json"' line=28 ctx=INSIGHTS_FILE = Path.home() / ".spark" / "cognitive_insights.json"
  - CLEAN_FILE = 'Path.home() / ".spark" / "cognitive_insights.clean.json"' line=29 ctx=CLEAN_FILE = Path.home() / ".spark" / "cognitive_insights.clean.json"

### scripts\daily_trend_research.py
- constants:
  - RESEARCH_TOPICS = '{\n    "vibe_coding": {\n        "queries": [\n            "vibe coding Claude AI",\n            "Claude Code ship fast",\n            "AI coding productivity",\n        ],\n        "category": CognitiveCategory.CONTEXT,\n        "priority... line=34 ctx=RESEARCH_TOPICS = {
  - CONTENT_ANGLES = {'educational': 'How-to guides and tutorials get high bookmarks', 'holy_shit_moment': 'AI doing unexpected things drives massive engagement', 'tool_comparison': 'Stack comparisons and tool lists get saved', 'ecosystem_update': 'Ecosystem ne... line=88 ctx=CONTENT_ANGLES = {

### scripts\spark_sandbox.py
- constants:
  - REPO_ROOT = 'Path(__file__).resolve().parent.parent' line=25 ctx=REPO_ROOT = Path(__file__).resolve().parent.parent

### scripts\status_local.py
- constants:
  - SPARK_DIR = 'Path(__file__).resolve().parent.parent' line=9 ctx=SPARK_DIR = Path(__file__).resolve().parent.parent

### spark\cli.py
- env:
  - SPARK_NO_WATCHDOG default='' line=471 ctx=return os.environ.get("SPARK_NO_WATCHDOG", "") == ""
  - SPARK_OUTCOME_AUTO_LINK default=None line=600 ctx=auto_link = args.auto_link or os.environ.get("SPARK_OUTCOME_AUTO_LINK") == "1"
- func_defaults:
  - _print_project_questions(limit) = 5 line=832 ctx=def _print_project_questions(profile, limit: int = 5):

### spark_watchdog.py
- constants:
  - SPARK_DIR = 'Path(__file__).resolve().parent' line=17 ctx=SPARK_DIR = Path(__file__).resolve().parent
  - LOG_DIR = 'Path.home() / ".spark" / "logs"' line=18 ctx=LOG_DIR = Path.home() / ".spark" / "logs"
  - STATE_FILE = 'Path.home() / ".spark" / "watchdog_state.json"' line=19 ctx=STATE_FILE = Path.home() / ".spark" / "watchdog_state.json"
- func_defaults:
  - _http_ok(timeout) = 1.5 line=39 ctx=def _http_ok(url: str, timeout: float = 1.5) -> bool:

### sparkd.py
- env:
  - SPARKD_MAX_BODY_BYTES default='262144' cast=int line=35 ctx=MAX_BODY_BYTES = int(os.environ.get("SPARKD_MAX_BODY_BYTES", "262144"))
  - SPARKD_TOKEN default=None line=34 ctx=TOKEN = os.environ.get("SPARKD_TOKEN")
- constants:
  - PORT = 8787 line=33 ctx=PORT = 8787
  - TOKEN = 'os.environ.get("SPARKD_TOKEN")' line=34 ctx=TOKEN = os.environ.get("SPARKD_TOKEN")
  - MAX_BODY_BYTES = 'int(os.environ.get("SPARKD_MAX_BODY_BYTES", "262144"))' line=35 ctx=MAX_BODY_BYTES = int(os.environ.get("SPARKD_MAX_BODY_BYTES", "262144"))
  - INVALID_EVENTS_FILE = 'Path.home() / ".spark" / "invalid_events.jsonl"' line=36 ctx=INVALID_EVENTS_FILE = Path.home() / ".spark" / "invalid_events.jsonl"

### tmp\check_primitive.py
- constants:
  - TOOL_RE = 're.compile(r"\\b(read|edit|write|bash|glob|grep|todowrite|taskoutput|webfetch|powershell|python|killshell|cli)\\b", re.I)' line=8 ctx=TOOL_RE = re.compile(r"\b(read|edit|write|bash|glob|grep|todowrite|taskoutput|webfetch|powershell|python|killshell|cli)\b", re.I)
  - PRIM_KW = {'sequence', 'pattern', 'overconfident', 'struggle', 'failed', 'usage', 'error', 'fails', 'timeout'} line=9 ctx=PRIM_KW = {"struggle","overconfident","fails","failed","error","timeout","usage","sequence","pattern"}

## Auto import map (internal imports only)

### adapters\moltbook\__init__.py
- adapters.moltbook.agent -> adapters\moltbook\agent.py
- adapters.moltbook.client -> adapters\moltbook\client.py

### adapters\moltbook\agent.py
- adapters.moltbook.client -> adapters\moltbook\client.py
- lib.diagnostics -> lib\diagnostics.py
- lib.queue -> lib\queue.py

### adapters\moltbook\heartbeat.py
- adapters.moltbook.agent -> adapters\moltbook\agent.py
- adapters.moltbook.client -> adapters\moltbook\client.py
- lib.diagnostics -> lib\diagnostics.py

### bridge_worker.py
- lib.bridge_cycle -> lib\bridge_cycle.py
- lib.diagnostics -> lib\diagnostics.py

### cli.py
- spark.cli -> spark\cli.py

### dashboard.py
- lib.aha_tracker -> lib\aha_tracker.py
- lib.cognitive_learner -> lib\cognitive_learner.py
- lib.dashboard_project -> lib\dashboard_project.py
- lib.diagnostics -> lib\diagnostics.py
- lib.eidos -> lib\eidos\__init__.py
- lib.growth_tracker -> lib\growth_tracker.py
- lib.mind_bridge -> lib\mind_bridge.py
- lib.promoter -> lib\promoter.py
- lib.queue -> lib\queue.py
- lib.resonance -> lib\resonance.py
- lib.spark_voice -> lib\spark_voice.py
- lib.sync_tracker -> lib\sync_tracker.py
- lib.taste_api -> lib\taste_api.py

### hooks\observe.py
- lib.advisor -> lib\advisor.py
- lib.aha_tracker -> lib\aha_tracker.py
- lib.cognitive_learner -> lib\cognitive_learner.py
- lib.diagnostics -> lib\diagnostics.py
- lib.eidos.integration -> lib\eidos\integration.py
- lib.eidos.models -> lib\eidos\models.py
- lib.feedback -> lib\feedback.py
- lib.importance_scorer -> lib\importance_scorer.py
- lib.meta_ralph -> lib\meta_ralph.py
- lib.outcome_checkin -> lib\outcome_checkin.py
- lib.queue -> lib\queue.py

### lib\advisor.py
- lib.aha_tracker -> lib\aha_tracker.py
- lib.cognitive_learner -> lib\cognitive_learner.py
- lib.memory_banks -> lib\memory_banks.py
- lib.meta_ralph -> lib\meta_ralph.py
- lib.mind_bridge -> lib\mind_bridge.py
- lib.skills_router -> lib\skills_router.py

### lib\bridge.py
- lib.advisor -> lib\advisor.py
- lib.aha_tracker -> lib\aha_tracker.py
- lib.cognitive_learner -> lib\cognitive_learner.py
- lib.diagnostics -> lib\diagnostics.py
- lib.exposure_tracker -> lib\exposure_tracker.py
- lib.memory_banks -> lib\memory_banks.py
- lib.mind_bridge -> lib\mind_bridge.py
- lib.outcome_checkin -> lib\outcome_checkin.py
- lib.project_profile -> lib\project_profile.py
- lib.queue -> lib\queue.py
- lib.skills_router -> lib\skills_router.py
- lib.spark_voice -> lib\spark_voice.py
- lib.tastebank -> lib\tastebank.py

### lib\bridge_cycle.py
- lib.bridge -> lib\bridge.py
- lib.chips -> lib\chips\__init__.py
- lib.content_learner -> lib\content_learner.py
- lib.diagnostics -> lib\diagnostics.py
- lib.memory_capture -> lib\memory_capture.py
- lib.pattern_detection -> lib\pattern_detection\__init__.py
- lib.prediction_loop -> lib\prediction_loop.py
- lib.queue -> lib\queue.py
- lib.tastebank -> lib\tastebank.py
- lib.validation_loop -> lib\validation_loop.py

### lib\chip_merger.py
- lib.cognitive_learner -> lib\cognitive_learner.py
- lib.exposure_tracker -> lib\exposure_tracker.py

### lib\chips\evolution.py
- lib.chips.scoring -> lib\chips\scoring.py

### lib\chips\loader.py
- lib.chips.schema -> lib\chips\schema.py

### lib\chips\registry.py
- lib.chips.loader -> lib\chips\loader.py

### lib\chips\router.py
- lib.chips.loader -> lib\chips\loader.py

### lib\chips\runner.py
- lib.chips.loader -> lib\chips\loader.py
- lib.chips.policy -> lib\chips\policy.py
- lib.chips.store -> lib\chips\store.py

### lib\chips\runtime.py
- lib.chips.loader -> lib\chips\loader.py
- lib.chips.registry -> lib\chips\registry.py
- lib.chips.router -> lib\chips\router.py

### lib\cognitive_learner.py
- lib.exposure_tracker -> lib\exposure_tracker.py

### lib\content_learner.py
- lib.cognitive_learner -> lib\cognitive_learner.py
- lib.diagnostics -> lib\diagnostics.py

### lib\context_sync.py
- lib.cognitive_learner -> lib\cognitive_learner.py
- lib.exposure_tracker -> lib\exposure_tracker.py
- lib.outcome_checkin -> lib\outcome_checkin.py
- lib.output_adapters -> lib\output_adapters\__init__.py
- lib.project_context -> lib\project_context.py
- lib.project_profile -> lib\project_profile.py
- lib.promoter -> lib\promoter.py
- lib.sync_tracker -> lib\sync_tracker.py

### lib\contradiction_detector.py
- lib.cognitive_learner -> lib\cognitive_learner.py
- lib.embeddings -> lib\embeddings.py

### lib\curiosity_engine.py
- lib.cognitive_learner -> lib\cognitive_learner.py

### lib\dashboard_project.py
- lib.memory_banks -> lib\memory_banks.py

### lib\eidos\acceptance_compiler.py
- lib.eidos.models -> lib\eidos\models.py

### lib\eidos\control_plane.py
- lib.eidos.models -> lib\eidos\models.py

### lib\eidos\distillation_engine.py
- lib.eidos.models -> lib\eidos\models.py

### lib\eidos\elevated_control.py
- lib.eidos.models -> lib\eidos\models.py
- lib.eidos.store -> lib\eidos\store.py

### lib\eidos\escalation.py
- lib.eidos.models -> lib\eidos\models.py

### lib\eidos\guardrails.py
- lib.eidos.models -> lib\eidos\models.py

### lib\eidos\integration.py
- lib.eidos.control_plane -> lib\eidos\control_plane.py
- lib.eidos.distillation_engine -> lib\eidos\distillation_engine.py
- lib.eidos.elevated_control -> lib\eidos\elevated_control.py
- lib.eidos.escalation -> lib\eidos\escalation.py
- lib.eidos.evidence_store -> lib\eidos\evidence_store.py
- lib.eidos.guardrails -> lib\eidos\guardrails.py
- lib.eidos.memory_gate -> lib\eidos\memory_gate.py
- lib.eidos.models -> lib\eidos\models.py
- lib.eidos.store -> lib\eidos\store.py
- lib.eidos.validation -> lib\eidos\validation.py

### lib\eidos\memory_gate.py
- lib.eidos.models -> lib\eidos\models.py

### lib\eidos\migration.py
- lib.eidos.models -> lib\eidos\models.py
- lib.eidos.store -> lib\eidos\store.py

### lib\eidos\minimal_mode.py
- lib.eidos.models -> lib\eidos\models.py

### lib\eidos\policy_patches.py
- lib.eidos.models -> lib\eidos\models.py

### lib\eidos\retriever.py
- lib.eidos.models -> lib\eidos\models.py
- lib.eidos.store -> lib\eidos\store.py

### lib\eidos\store.py
- lib.eidos.models -> lib\eidos\models.py

### lib\eidos\truth_ledger.py
- lib.eidos.store -> lib\eidos\store.py

### lib\eidos\validation.py
- lib.eidos.models -> lib\eidos\models.py

### lib\evaluation.py
- lib.outcome_log -> lib\outcome_log.py
- lib.prediction_loop -> lib\prediction_loop.py

### lib\exposure_tracker.py
- lib.primitive_filter -> lib\primitive_filter.py
- lib.queue -> lib\queue.py

### lib\feedback.py
- lib.cognitive_learner -> lib\cognitive_learner.py
- lib.outcome_log -> lib\outcome_log.py
- lib.skills_router -> lib\skills_router.py

### lib\hypothesis_tracker.py
- lib.cognitive_learner -> lib\cognitive_learner.py

### lib\importance_scorer.py
- lib.cognitive_learner -> lib\cognitive_learner.py
- lib.embeddings -> lib\embeddings.py

### lib\ingest_validation.py
- lib.diagnostics -> lib\diagnostics.py
- lib.queue -> lib\queue.py

### lib\markdown_writer.py
- lib.cognitive_learner -> lib\cognitive_learner.py

### lib\memory_banks.py
- lib.cognitive_learner -> lib\cognitive_learner.py
- lib.memory_store -> lib\memory_store.py
- lib.queue -> lib\queue.py

### lib\memory_capture.py
- lib.cognitive_learner -> lib\cognitive_learner.py
- lib.memory_banks -> lib\memory_banks.py
- lib.outcome_checkin -> lib\outcome_checkin.py
- lib.outcome_log -> lib\outcome_log.py
- lib.queue -> lib\queue.py

### lib\memory_migrate.py
- lib.memory_banks -> lib\memory_banks.py
- lib.memory_store -> lib\memory_store.py

### lib\memory_store.py
- lib.embeddings -> lib\embeddings.py

### lib\metalearning\reporter.py
- lib.chips.evolution -> lib\chips\evolution.py
- lib.metalearning.evaluator -> lib\metalearning\evaluator.py
- lib.metalearning.strategist -> lib\metalearning\strategist.py

### lib\metalearning\strategist.py
- lib.metalearning.evaluator -> lib\metalearning\evaluator.py

### lib\mind_bridge.py
- lib.cognitive_learner -> lib\cognitive_learner.py

### lib\onboarding\context.py
- lib.onboarding.detector -> lib\onboarding\detector.py

### lib\orchestration.py
- lib.context_sync -> lib\context_sync.py
- lib.exposure_tracker -> lib\exposure_tracker.py
- lib.outcome_log -> lib\outcome_log.py
- lib.skills_router -> lib\skills_router.py

### lib\outcome_checkin.py
- lib.diagnostics -> lib\diagnostics.py

### lib\outcome_log.py
- lib.cognitive_learner -> lib\cognitive_learner.py

### lib\outcomes\linker.py
- lib.outcomes.signals -> lib\outcomes\signals.py

### lib\outcomes\tracker.py
- lib.outcomes.linker -> lib\outcomes\linker.py
- lib.outcomes.signals -> lib\outcomes\signals.py

### lib\output_adapters\claude_code.py
- lib.output_adapters.common -> lib\output_adapters\common.py

### lib\output_adapters\clawdbot.py
- lib.output_adapters.common -> lib\output_adapters\common.py

### lib\output_adapters\cursor.py
- lib.output_adapters.common -> lib\output_adapters\common.py

### lib\output_adapters\exports.py
- lib.output_adapters.common -> lib\output_adapters\common.py

### lib\output_adapters\windsurf.py
- lib.output_adapters.common -> lib\output_adapters\common.py

### lib\pattern_detection\aggregator.py
- lib.cognitive_learner -> lib\cognitive_learner.py
- lib.contradiction_detector -> lib\contradiction_detector.py
- lib.curiosity_engine -> lib\curiosity_engine.py
- lib.hypothesis_tracker -> lib\hypothesis_tracker.py
- lib.importance_scorer -> lib\importance_scorer.py
- lib.pattern_detection.base -> lib\pattern_detection\base.py
- lib.pattern_detection.correction -> lib\pattern_detection\correction.py
- lib.pattern_detection.distiller -> lib\pattern_detection\distiller.py
- lib.pattern_detection.memory_gate -> lib\pattern_detection\memory_gate.py
- lib.pattern_detection.repetition -> lib\pattern_detection\repetition.py
- lib.pattern_detection.request_tracker -> lib\pattern_detection\request_tracker.py
- lib.pattern_detection.semantic -> lib\pattern_detection\semantic.py
- lib.pattern_detection.sentiment -> lib\pattern_detection\sentiment.py
- lib.pattern_detection.why -> lib\pattern_detection\why.py
- lib.primitive_filter -> lib\primitive_filter.py
- lib.promoter -> lib\promoter.py

### lib\pattern_detection\correction.py
- lib.pattern_detection.base -> lib\pattern_detection\base.py

### lib\pattern_detection\distiller.py
- lib.eidos.models -> lib\eidos\models.py
- lib.eidos.store -> lib\eidos\store.py

### lib\pattern_detection\memory_gate.py
- lib.eidos.models -> lib\eidos\models.py

### lib\pattern_detection\repetition.py
- lib.pattern_detection.base -> lib\pattern_detection\base.py

### lib\pattern_detection\request_tracker.py
- lib.eidos.models -> lib\eidos\models.py

### lib\pattern_detection\semantic.py
- lib.pattern_detection.base -> lib\pattern_detection\base.py

### lib\pattern_detection\sentiment.py
- lib.pattern_detection.base -> lib\pattern_detection\base.py

### lib\pattern_detection\why.py
- lib.pattern_detection.base -> lib\pattern_detection\base.py

### lib\pattern_detection\worker.py
- lib.pattern_detection.aggregator -> lib\pattern_detection\aggregator.py
- lib.queue -> lib\queue.py

### lib\prediction_loop.py
- lib.aha_tracker -> lib\aha_tracker.py
- lib.cognitive_learner -> lib\cognitive_learner.py
- lib.diagnostics -> lib\diagnostics.py
- lib.embeddings -> lib\embeddings.py
- lib.exposure_tracker -> lib\exposure_tracker.py
- lib.outcome_log -> lib\outcome_log.py
- lib.primitive_filter -> lib\primitive_filter.py
- lib.project_profile -> lib\project_profile.py
- lib.queue -> lib\queue.py

### lib\project_profile.py
- lib.chips.registry -> lib\chips\registry.py
- lib.diagnostics -> lib\diagnostics.py
- lib.memory_banks -> lib\memory_banks.py
- lib.project_context -> lib\project_context.py

### lib\promoter.py
- lib.cognitive_learner -> lib\cognitive_learner.py
- lib.project_profile -> lib\project_profile.py

### lib\queue.py
- lib.diagnostics -> lib\diagnostics.py

### lib\research\holistic_intents.py
- lib.research.domains -> lib\research\domains.py
- lib.research.intents -> lib\research\intents.py
- lib.research.mastery -> lib\research\mastery.py

### lib\research\intents.py
- lib.research.mastery -> lib\research\mastery.py

### lib\research\mastery.py
- lib.research.web_research -> lib\research\web_research.py

### lib\research\spark_research.py
- lib.research.intents -> lib\research\intents.py
- lib.research.mastery -> lib\research\mastery.py
- lib.research.web_research -> lib\research\web_research.py

### lib\research\web_research.py
- lib.research.mastery -> lib\research\mastery.py

### lib\resonance.py
- lib.aha_tracker -> lib\aha_tracker.py
- lib.cognitive_learner -> lib\cognitive_learner.py
- lib.spark_voice -> lib\spark_voice.py

### lib\service_control.py
- lib.bridge_cycle -> lib\bridge_cycle.py

### lib\skills_router.py
- lib.skills_registry -> lib\skills_registry.py

### lib\taste_api.py
- lib.tastebank -> lib\tastebank.py

### lib\validation_loop.py
- lib.aha_tracker -> lib\aha_tracker.py
- lib.cognitive_learner -> lib\cognitive_learner.py
- lib.diagnostics -> lib\diagnostics.py
- lib.outcome_log -> lib\outcome_log.py
- lib.queue -> lib\queue.py

### lib\x_research_events.py
- lib.chips.runtime -> lib\chips\runtime.py
- lib.queue -> lib\queue.py

### mcp-servers\x-twitter-mcp\src\x_twitter_mcp\http_server.py
- mcp-servers.x-twitter-mcp.src.x_twitter_mcp.middleware -> mcp-servers\x-twitter-mcp\src\x_twitter_mcp\middleware.py
- mcp-servers.x-twitter-mcp.src.x_twitter_mcp.server -> mcp-servers\x-twitter-mcp\src\x_twitter_mcp\server.py

### scripts\daily_trend_research.py
- lib.chip_merger -> lib\chip_merger.py
- lib.cognitive_learner -> lib\cognitive_learner.py
- lib.x_research_events -> lib\x_research_events.py

### scripts\eidos_dashboard.py
- lib.eidos -> lib\eidos\__init__.py

### scripts\spark_dashboard.py
- lib.cognitive_learner -> lib\cognitive_learner.py

### scripts\spark_sandbox.py
- hooks.observe -> hooks\observe.py
- lib -> lib\__init__.py
- lib.aha_tracker -> lib\aha_tracker.py
- lib.bridge_cycle -> lib\bridge_cycle.py
- lib.chips.evolution -> lib\chips\evolution.py
- lib.chips.registry -> lib\chips\registry.py
- lib.chips.runtime -> lib\chips\runtime.py
- lib.chips.scoring -> lib\chips\scoring.py
- lib.cognitive_learner -> lib\cognitive_learner.py
- lib.exposure_tracker -> lib\exposure_tracker.py
- lib.growth_tracker -> lib\growth_tracker.py
- lib.markdown_writer -> lib\markdown_writer.py
- lib.memory_capture -> lib\memory_capture.py
- lib.outcome_log -> lib\outcome_log.py
- lib.pattern_detection.worker -> lib\pattern_detection\worker.py
- lib.prediction_loop -> lib\prediction_loop.py
- lib.project_profile -> lib\project_profile.py
- lib.promoter -> lib\promoter.py
- lib.queue -> lib\queue.py
- lib.skills_registry -> lib\skills_registry.py
- lib.skills_router -> lib\skills_router.py
- lib.spark_voice -> lib\spark_voice.py
- lib.validation_loop -> lib\validation_loop.py

### scripts\status_local.py
- lib.pattern_detection.worker -> lib\pattern_detection\worker.py
- lib.queue -> lib\queue.py
- lib.service_control -> lib\service_control.py
- lib.validation_loop -> lib\validation_loop.py

### scripts\verify_queue.py
- lib -> lib\__init__.py
- lib.queue -> lib\queue.py

### scripts\watchdog.py
- spark_watchdog -> spark_watchdog.py

### spark\cli.py
- adapters.moltbook.agent -> adapters\moltbook\agent.py
- adapters.moltbook.client -> adapters\moltbook\client.py
- adapters.moltbook.heartbeat -> adapters\moltbook\heartbeat.py
- lib.aha_tracker -> lib\aha_tracker.py
- lib.bridge -> lib\bridge.py
- lib.bridge_cycle -> lib\bridge_cycle.py
- lib.capture_cli -> lib\capture_cli.py
- lib.chips -> lib\chips\__init__.py
- lib.clawdbot_memory_setup -> lib\clawdbot_memory_setup.py
- lib.cognitive_learner -> lib\cognitive_learner.py
- lib.context_sync -> lib\context_sync.py
- lib.contradiction_detector -> lib\contradiction_detector.py
- lib.curiosity_engine -> lib\curiosity_engine.py
- lib.eidos -> lib\eidos\__init__.py
- lib.evaluation -> lib\evaluation.py
- lib.exposure_tracker -> lib\exposure_tracker.py
- lib.growth_tracker -> lib\growth_tracker.py
- lib.hypothesis_tracker -> lib\hypothesis_tracker.py
- lib.importance_scorer -> lib\importance_scorer.py
- lib.ingest_validation -> lib\ingest_validation.py
- lib.markdown_writer -> lib\markdown_writer.py
- lib.memory_banks -> lib\memory_banks.py
- lib.memory_capture -> lib\memory_capture.py
- lib.memory_migrate -> lib\memory_migrate.py
- lib.mind_bridge -> lib\mind_bridge.py
- lib.outcome_checkin -> lib\outcome_checkin.py
- lib.outcome_log -> lib\outcome_log.py
- lib.pattern_detection -> lib\pattern_detection\__init__.py
- lib.prediction_loop -> lib\prediction_loop.py
- lib.project_profile -> lib\project_profile.py
- lib.promoter -> lib\promoter.py
- lib.queue -> lib\queue.py
- lib.service_control -> lib\service_control.py
- lib.spark_voice -> lib\spark_voice.py
- lib.validation_loop -> lib\validation_loop.py

### spark_watchdog.py
- lib.bridge_cycle -> lib\bridge_cycle.py
- lib.pattern_detection.worker -> lib\pattern_detection\worker.py
- lib.queue -> lib\queue.py

### sparkd.py
- lib.bridge_cycle -> lib\bridge_cycle.py
- lib.diagnostics -> lib\diagnostics.py
- lib.events -> lib\events.py
- lib.orchestration -> lib\orchestration.py
- lib.pattern_detection.worker -> lib\pattern_detection\worker.py
- lib.queue -> lib\queue.py
- lib.validation_loop -> lib\validation_loop.py
