# Spark Autonomy: 24/7 Self-Evolving Builder

## The Vision

Spark doesn't just learn from human sessions - it **builds autonomously** while humans sleep, work, or are away. It orchestrates the VibeShip ecosystem to create projects, run experiments, evolve itself, and feed learnings back into the system.

**Key Principle: No deviation until task is complete.** Tasks flow through Spawner-UI for proper tracking, completion gates verify quality, and learnings feed back into the system.

---

## VibeShip Ecosystem (What Already Exists)

**Spark doesn't rebuild what exists. It orchestrates.**

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        VIBESHIP ECOSYSTEM                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌────────────┐  │
│  │  IDEARALPH  │   │    MIND     │   │   SPAWNER   │   │ SPAWNER-UI │  │
│  │  (Ideation) │   │  (Memory)   │   │  (Routing)  │   │ (Executor) │  │
│  │             │   │             │   │             │   │            │  │
│  │ • Ideas     │   │ • Memories  │   │ • Skills    │   │ • Missions │  │
│  │ • Specs     │   │ • Context   │   │ • Stacks    │   │ • Progress │  │
│  │ • Risk tags │   │ • Retrieval │   │ • Agents    │   │ • Gates    │  │
│  │ • Decisions │   │             │   │ • H70 (443) │   │ • Learning │  │
│  └──────┬──────┘   └──────┬──────┘   └──────┬──────┘   └──────┬─────┘  │
│         │                 │                 │                 │        │
│         └─────────────────┴─────────────────┴─────────────────┘        │
│                                     │                                   │
│                                     ▼                                   │
│                    ┌───────────────────────────────┐                    │
│                    │      SPARK INTELLIGENCE       │                    │
│                    │                               │                    │
│                    │  • Orchestrates builds        │                    │
│                    │  • Learns from outcomes       │                    │
│                    │  • Evolves ecosystem          │                    │
│                    │  • Feeds back to IdeaRalph    │                    │
│                    └───────────────────────────────┘                    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Install VibeShip Tools

```bash
npx github:vibeforge1111/vibeship-idearalph install
```

### Key Locations

| Tool | Location | Purpose |
|------|----------|---------|
| **IdeaRalph** | `C:\Users\USER\Desktop\vibeship-idearalph` | Ideation, specs, risk tags |
| **Spawner-UI** | `C:\Users\USER\Desktop\spawner-ui` | Mission execution, task tracking |
| **Skills Lab** | `C:\Users\USER\Desktop\vibeship-skills-lab` | 443+ H70 skills |
| **Mind** | MCP server | Persistent memory |
| **Spark** | This repo | Intelligence layer |

---

## Spawner-UI: The Execution Engine

**Critical: All autonomous builds MUST flow through Spawner-UI for proper task tracking.**

### Why Spawner-UI?

Spawner-UI provides:
1. **Mission Executor** - Converts ideas to executable missions
2. **Task Progress Tracking** - Real-time via WebSocket/SSE
3. **Completion Gates** - Quality verification before marking done
4. **H70 Skills** - 443+ domain expert skills auto-loaded
5. **Learning Reinforcement** - Decision→Outcome tracking

### Mission Execution Flow

```
┌──────────────────────────────────────────────────────────────────────────┐
│                       SPAWNER-UI EXECUTION FLOW                          │
│                                                                          │
│  1. MISSION CREATION                                                     │
│     IdeaRalph idea → Spawner-UI Mission Builder                          │
│     - Converts spec to tasks                                             │
│     - Auto-loads relevant H70 skills (max 10)                            │
│     - Sets completion gates                                              │
│                                                                          │
│  2. EXECUTION (NO DEVIATION UNTIL COMPLETE)                              │
│     Claude Code executes autonomously                                    │
│     - POST /api/events {type: "task_started"}                            │
│     - Work on task...                                                    │
│     - POST /api/events {type: "task_progress", progress: 50}             │
│     - Continue until done...                                             │
│     - POST /api/events {type: "task_completed"}                          │
│                                                                          │
│  3. COMPLETION VERIFICATION                                              │
│     Completion gates run automatically:                                  │
│     - build: npm run build                                               │
│     - test: npm run test                                                 │
│     - typecheck: npx tsc --noEmit                                        │
│     - lint: code quality                                                 │
│     - artifacts: files created                                           │
│                                                                          │
│  4. LEARNING REINFORCEMENT                                               │
│     - Successful decisions → boost confidence                            │
│     - Failed decisions → reduce confidence                               │
│     - Save learnings to Mind + Spark                                     │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### Events API (Critical for Progress Tracking)

All task progress MUST be reported to Spawner-UI:

```bash
# Task started
curl -X POST http://localhost:5173/api/events \
  -H "Content-Type: application/json" \
  -d '{
    "type": "task_started",
    "data": {"taskId": "task-123", "message": "Starting implementation"}
  }'

# Progress update (send every 30-60 seconds max)
curl -X POST http://localhost:5173/api/events \
  -H "Content-Type: application/json" \
  -d '{
    "type": "task_progress",
    "data": {"taskId": "task-123", "progress": 50, "message": "Building API routes"}
  }'

# Task completed
curl -X POST http://localhost:5173/api/events \
  -H "Content-Type: application/json" \
  -d '{
    "type": "task_completed",
    "data": {"taskId": "task-123", "success": true}
  }'
```

### Completion Gates (Quality Verification)

| Gate | Command | When Required |
|------|---------|---------------|
| `build` | `npm run build` | Deployment tasks |
| `test` | `npm run test` | Testing tasks |
| `typecheck` | `npx tsc --noEmit` | TypeScript tasks |
| `lint` | Code quality check | All code tasks |
| `artifacts` | Files created | Build tasks |
| `manual` | Human review | High-risk tasks |

**Quality Score (0-100):**
- skillsLoaded: +25 points
- artifactsCreated: +25 points
- noErrors: +25 points
- gatesPassed: +25 points

### H70 Skills (443+ Domain Experts)

Spawner-UI auto-loads relevant skills from `vibeship-skills-lab`:

```yaml
# Example: react-patterns skill
identity: Senior React developer with 10+ years experience
owns:
  - React component architecture
  - State management patterns
  - Performance optimization
delegates:
  - Backend API design → backend-expert
  - Database queries → sql-expert
disasters:
  - Prop drilling leading to unmaintainable code
  - useEffect dependency hell
patterns:
  - Custom hooks for shared logic
  - Context for cross-cutting concerns
anti_patterns:
  - Avoid deeply nested component trees
  - Never mutate state directly
```

**Skill Loading Rules:**
- Max 3 skills per task
- Max 10 skills per mission
- Matched via keyword mappings (391 patterns)

---

## The Autonomy Loop (Updated)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    SPARK AUTONOMY LOOP (v2)                             │
│                                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │  IDEARALPH   │───▶│ SPAWNER-UI   │───▶│    SPARK     │              │
│  │  (Ideation)  │    │  (Executor)  │    │  (Learner)   │              │
│  └──────────────┘    └──────────────┘    └──────────────┘              │
│         ▲                   │                    │                      │
│         │                   ▼                    │                      │
│         │            ┌──────────────┐            │                      │
│         │            │ CLAUDE CODE  │            │                      │
│         │            │ (Worker)     │            │                      │
│         │            │              │            │                      │
│         │            │ H70 Skills   │            │                      │
│         │            │ loaded       │            │                      │
│         │            └──────────────┘            │                      │
│         │                   │                    │                      │
│         │                   ▼                    │                      │
│         │            ┌──────────────┐            │                      │
│         │            │ COMPLETION   │            │                      │
│         │            │ GATES        │────────────┘                      │
│         │            └──────────────┘                                   │
│         │                   │                                           │
│         └───────────────────┘                                           │
│                  FEEDBACK LOOP                                          │
│                                                                         │
│  IdeaRalph:          Spawner-UI:          Spark:                       │
│  • Next idea         • Mission creation   • Pattern detection          │
│  • Specifications    • Task tracking      • Cognitive insights         │
│  • Risk assessment   • Progress events    • Decision confidence        │
│  • Success criteria  • Completion gates   • Feed back to IdeaRalph     │
│                      • H70 skill loading                               │
└─────────────────────────────────────────────────────────────────────────┘
```

### Phase 1: IDEATE (IdeaRalph)

IdeaRalph provides:
- `idea_id` - Unique identifier
- `title` - What to build
- `spec_summary` - How to build it
- `risk_tags` - What could go wrong
- `decisions` - Choices made

**Spark's role:** Query IdeaRalph for next actionable idea.

### Phase 2: EXECUTE (Spawner-UI)

**Critical: Tasks flow through Spawner-UI, not direct execution.**

1. **Mission Builder** converts idea to mission:
   - Parses spec_summary into tasks
   - Identifies task dependencies
   - Auto-loads H70 skills
   - Sets completion gates

2. **Mission Executor** runs tasks:
   - Sends execution prompt to Claude Code
   - Monitors progress via Events API
   - Handles failures gracefully
   - Enforces timeouts

3. **Claude Code** executes autonomously:
   - Loads H70 skills (disasters, patterns, anti-patterns)
   - Reports progress every 30-60 seconds
   - **NO PAUSING** - executes until complete
   - **100% COMPLETION** - no placeholder code

### Phase 3: VERIFY (Completion Gates)

Before marking a task done:
1. Run completion gates (build, test, typecheck)
2. Calculate quality score (0-100)
3. Verify artifacts created
4. Check for errors

**Task is NOT complete until gates pass.**

### Phase 4: LEARN (Spark Intelligence)

Using existing Spark systems + Spawner-UI reinforcement:

| Component | Role |
|-----------|------|
| Cognitive Learner | Store build learnings |
| Pattern Detection | Extract success/failure patterns |
| Validation Loop | Link outcomes to predictions |
| Learning Reinforcement | Boost/reduce decision confidence |

**Spark's role:**
1. Receive completion data from Spawner-UI
2. Extract learnings via pattern detection
3. Store in cognitive_insights.json
4. Reinforce decisions (success → boost, failure → reduce)
5. Feed insights back to IdeaRalph

---

## Integration Points

### Spawner-UI APIs

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/events` | POST | Receive task progress events |
| `/api/events` | GET | SSE stream for real-time updates |
| `/api/mission/active` | GET | Check current mission status |
| `/api/mission/active` | POST | Update mission progress |
| `/api/mission/active` | DELETE | Clear completed mission |
| `/api/h70-skills/[id]` | GET | Load specific H70 skill |
| `/api/mcp/call` | POST | Invoke MCP tools |

### Active Mission State

Spawner-UI maintains `.spawner/` directory:
```
.spawner/
├── active-mission.json     # Current mission state
├── RULES.md                # Execution rules for Claude
└── mission-history/        # Past mission records
```

### Spark Integration

```python
# lib/autonomy.py - Updated to use Spawner-UI

class AutonomyOrchestrator:
    """Orchestrates autonomy loop through Spawner-UI."""

    def __init__(self):
        self.idearalph = MCPClient("idearalph")
        self.spawner_ui = "http://localhost:5173"
        self.cognitive = get_cognitive_learner()

    def run_cycle(self):
        # 1. Get next idea from IdeaRalph
        idea = self.idearalph.get_next_idea()
        if not idea:
            return {"status": "no_ideas"}

        # 2. Create mission in Spawner-UI
        mission = self.create_mission(idea)

        # 3. Wait for completion (Spawner-UI handles execution)
        outcome = self.wait_for_completion(mission.id)

        # 4. Learn from outcome
        learnings = self.learn_from_outcome(outcome, idea)

        # 5. Reinforce decisions
        self.reinforce_decisions(mission, outcome)

        # 6. Feed back to IdeaRalph
        self.idearalph.record_outcome(idea.idea_id, outcome)

        return {
            "idea": idea.title,
            "outcome": outcome.status,
            "quality_score": outcome.quality_score,
            "learnings": len(learnings)
        }

    def create_mission(self, idea):
        """Create mission in Spawner-UI from IdeaRalph idea."""
        return requests.post(f"{self.spawner_ui}/api/mission", json={
            "name": idea.title,
            "spec": idea.spec_summary,
            "decisions": idea.decisions,
            "risk_tags": idea.risk_tags
        }).json()

    def wait_for_completion(self, mission_id):
        """Poll for mission completion."""
        while True:
            status = requests.get(
                f"{self.spawner_ui}/api/mission/active"
            ).json()

            if not status["active"]:
                return status["mission"]

            time.sleep(30)  # Poll every 30 seconds

    def reinforce_decisions(self, mission, outcome):
        """Reinforce decision confidence based on outcome."""
        if outcome.status == "success":
            for decision in mission.decisions:
                self.cognitive.boost_confidence(decision, 0.1)
        else:
            for decision in mission.decisions:
                self.cognitive.reduce_confidence(decision, 0.05)
```

---

## Execution Rules (Claude Code)

**These rules MUST be followed during autonomous execution:**

1. **NO PAUSING** - Execute autonomously, don't ask for confirmation
2. **100% COMPLETION** - Don't leave placeholder code; finish the entire project
3. **TEST AFTER** - Build and run the project before declaring done
4. **SEND PROGRESS EVENTS** - Heartbeat every 60 seconds max
5. **ERROR HANDLING** - Attempt fixes, move to next task on failure
6. **COMPLETION GATES** - All gates must pass before task is marked complete

### Progress Event Format

```javascript
// Every 30-60 seconds during execution:
fetch('http://localhost:5173/api/events', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    type: 'task_progress',
    data: {
      taskId: 'current-task-id',
      progress: 75,  // 0-100
      message: 'Building API routes...'
    }
  })
});
```

---

## Example Night (Full Flow)

```
22:00 - Human sleeps, Spark Autonomy activates

22:05 - QUERY IDEARALPH
  GET mcp.idearalph.get_next_idea()
  Response: {
    idea_id: "spark-lookup-cli",
    title: "CLI for quick insight lookup",
    spec_summary: "Build CLI tool, <100ms, offline support",
    risk_tags: ["low_complexity"],
    decisions: ["use argparse", "sqlite cache"]
  }

22:06 - CREATE MISSION IN SPAWNER-UI
  POST http://localhost:5173/api/mission
  - Mission Builder parses spec into 3 tasks
  - H70 skills auto-loaded: python, cli, sqlite
  - Completion gates set: build, test

22:07 - CLAUDE CODE EXECUTES
  Task 1: Set up project structure
    → POST /api/events {task_started}
    → Creates directories, files
    → POST /api/events {task_progress: 100}
    → POST /api/events {task_completed}

  Task 2: Implement CLI logic
    → POST /api/events {task_started}
    → H70 skill "cli" loaded (anti-patterns, patterns)
    → POST /api/events {task_progress: 30}
    → Building argparse interface...
    → POST /api/events {task_progress: 60}
    → Adding sqlite cache...
    → POST /api/events {task_progress: 90}
    → POST /api/events {task_completed}

  Task 3: Write tests
    → POST /api/events {task_started}
    → Creates test_cli.py
    → POST /api/events {task_completed}

22:35 - COMPLETION GATES RUN
  - build: PASS
  - test: PASS (5/5 tests)
  Quality Score: 100/100

22:40 - LEARN & FEEDBACK
  Spawner-UI → Spark:
    - Task completion times
    - Quality scores
    - Skills used

  Pattern Detection extracts:
    - "Haiku sufficient for simple CLI" (REASONING)
    - "Offline sqlite pattern reliable" (WISDOM)

  Learning Reinforcement:
    - Decision "use argparse" → boost confidence +0.1
    - Decision "sqlite cache" → boost confidence +0.1

  Store in cognitive_insights.json

  Feedback to IdeaRalph:
    idea_id: "spark-lookup-cli"
    outcome: "success"
    duration: 33min
    quality_score: 100

22:45 - NEXT CYCLE
  Query IdeaRalph for next idea...
```

---

## Resource Management

### Cost Control

```python
AUTONOMY_CONFIG = {
    "max_builds_per_night": 3,
    "max_tokens_per_build": 50000,
    "max_duration_per_build": 3600,  # 1 hour
    "preferred_models": ["haiku", "sonnet"],  # Opus only for strategic
    "cost_limit_daily": 5.00,  # USD
}
```

### Scheduling

- **Bridge Worker**: `--interval` flag for continuous
- **Sparkd**: `/autonomy` endpoint for on-demand
- **Cron/Task Scheduler**: Time-based triggers

---

## Safety

### Sandboxing (enforced)
- All builds in `~/.spark/sandboxes/`
- No access to main codebase during build
- Resource limits (time, tokens)

### Human Oversight
- Daily summary posted
- High-risk ideas require approval
- Kill switch: `spark autonomy stop`

### Learning Bounds
- Failure learnings need 3+ occurrences
- Self-modification requires review
- All decisions logged and explainable

---

## Implementation Checklist

### Required for Autonomy

- [ ] Spawner-UI running at localhost:5173
- [ ] IdeaRalph MCP connected
- [ ] H70 skills available in vibeship-skills-lab
- [ ] Spark's cognitive_learner.py accessible
- [ ] Mind MCP for persistent memory

### Spark Additions Needed

1. **lib/autonomy.py** - Orchestrator connecting:
   - IdeaRalph (ideas)
   - Spawner-UI (execution)
   - Cognitive learner (learning)
   - Mind (memory)

2. **sparkd.py endpoints**:
   - `/autonomy` - Trigger cycle
   - `/autonomy/status` - Check state

3. **chips/autonomy.chip.yaml** - Learning patterns for builds

4. **bridge_cycle.py** - Optional autonomy cycle integration

---

## Questions Resolved

| Question | Answer |
|----------|--------|
| **How are tasks tracked?** | Spawner-UI Events API + Mission Executor |
| **How do we ensure completion?** | Completion gates (build, test, typecheck) |
| **What skills are available?** | 443+ H70 skills in vibeship-skills-lab |
| **How do learnings persist?** | Mind MCP + cognitive_insights.json |
| **How do decisions improve?** | Learning Reinforcement (confidence scores) |
