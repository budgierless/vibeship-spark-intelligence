# Spark Neural Dashboard

Social intelligence dashboard showing Spark's learning journey on X in real time.

**URL**: http://localhost:8770

## Starting the Dashboard

```bash
python dashboard/social_intel/app.py
```

Output:
```
==================================================
  SPARK NEURAL - Social Intelligence Dashboard
  http://localhost:8770
==================================================
```

## Sections

The dashboard is a single-page app with live polling every 30 seconds.

### 1. Hero Section

Top-level stats:
- Total insights (cognitive + all chips)
- Patterns cataloged
- Social interactions tracked

### 2. Learning Flow (The Pipeline)

Visualizes: `OBSERVE -> FILTER -> LEARN -> VALIDATE -> ADVISE`
- Shows counts at each stage
- Confidence distribution (high/medium/low)
- Category breakdown

### 3. Research Topics

Live from the research engine:
- All tracked topics with tier, category, min_likes threshold
- Hit rate and trend (rising/stable/declining/paused)
- Active/skipped status per session
- Discovered topics (from research self-evolution)

### 4. Social Patterns

Built from real research data:
- **Emotional triggers**: Ranked by observation count + avg engagement
- **Content strategies**: From LLM analysis (strategies with counts + avg engagement)
- **Engagement hooks**: From LLM analysis
- **Writing patterns**: Structural elements detected
- **Questions vs statements**: Which drives more engagement

### 5. Voice System

Current personality configuration:
- Tone defaults per context (reply/quote/post)
- Earned principles from conversation intelligence

### 6. Research Engine

Research findings:
- Session count, tweets analyzed, insights stored
- **Intelligence panel** (if LLM data available):
  - Content strategies from phi4-mini
  - Engagement hooks ranked by frequency
  - Actionable lessons extracted
- **High performers**: Top tweets with analysis
- **Watched accounts**: From watchlist
- **Research intents**: Auto-generated goals

### 7. Live Evolution

Real-time self-improvement tracking:
- **Stats**: Total evolutions, replies tracked, hits, hit rate, patterns adopted
- **Voice weights**: Trigger weight bars (boosted green, reduced orange)
- **Strategy weights**: Content strategy preferences
- **Timeline**: Chronological evolution events with confidence scores

### 8. Intelligence Funnel (NEW)

Visual filter/distillation pipeline showing how intelligence flows from raw data to influence:
- **Meta cards**: Active triggers, active strategies, MetaRalph filter rate, global avg likes
- **Funnel visualization**: 6-stage funnel (tweets analyzed -> high performers -> LLM analyzed -> evolution events -> high confidence -> passed MetaRalph) with counts, filter descriptions, and filter rates
- **Trigger performance**: Bar chart of all triggers with avg likes, observation count, and current weight
- **Strategy performance**: Bar chart of top strategies with avg likes and weight status
- Polls every 60 seconds (every 2nd poll cycle)

### 9. System Health & Gap Diagnosis

Real-time diagnosis of all Spark Intelligence subsystems:
- **Overall health badge**: healthy / good / improving / needs_attention / critical
- **Core integration status**: Which Spark systems are connected (CognitiveLearner, MetaRalph, Advisor, EIDOS)
- **Per-system health cards**: Key metrics for Cognitive, Advisor, EIDOS, MetaRalph, Evolution, Research
- **Gap cards**: Identified weaknesses with severity, description, metric progress bar, and recommendation
- Polls every 90 seconds (every 3rd poll cycle to reduce load)

### 10. Growth Timeline

Milestones + current stats:
- Days active, posts, replies, conversations
- Research sessions, tweets analyzed
- Accounts watched, users discovered

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/status` | GET | Health check |
| `/api/overview` | GET | Hero stats (insights, users, topics) |
| `/api/learning-flow` | GET | Pipeline stages + confidence distribution |
| `/api/topics` | GET | Research topics with performance |
| `/api/social-patterns` | GET | Triggers, strategies, hooks, patterns |
| `/api/conversations` | GET | Voice/conversation stats |
| `/api/research` | GET | Research findings + LLM intelligence |
| `/api/evolution` | GET | Evolution tracking (weights, timeline) |
| `/api/filter-funnel` | GET | Filter/distillation funnel (stages, trigger/strategy perf) |
| `/api/gaps` | GET | System gap diagnosis (health, gaps, recommendations) |
| `/api/growth` | GET | Growth milestones + current stats |

## How Data Flows to Dashboard

```
~/.spark/cognitive_insights.json   --> /api/overview, /api/learning-flow, /api/gaps
~/.spark/chip_insights/*.jsonl     --> /api/overview, /api/social-patterns, /api/research
~/.spark/x_research_state.json    --> /api/topics, /api/research, /api/growth, /api/gaps
~/.spark/x_watchlist.json         --> /api/research, /api/growth
~/.spark/x_evolution_state.json   --> /api/evolution, /api/gaps
~/.spark/x_evolution_log.jsonl    --> /api/evolution (timeline), /api/filter-funnel
~/.spark/advisor/effectiveness.json --> /api/gaps
~/.spark/eidos.db                  --> /api/gaps (distillation health)
~/.spark/tuneables.json            --> /api/gaps (auto-tuner status)
```

All data is read-only from the dashboard. No writes.

## Customization

### Changing poll interval

In `index.html`:
```javascript
const POLL_INTERVAL = 30000; // 30 seconds (change this)
```

### Adding new sections

1. Add API endpoint in `app.py`
2. Add HTML section in `index.html`
3. Add JS fetch function
4. Wire into `DOMContentLoaded` and `pollLiveData`

## Files

| File | Purpose |
|------|---------|
| `dashboard/social_intel/app.py` | FastAPI backend (10 endpoints) |
| `dashboard/social_intel/index.html` | Frontend SPA (2,000+ lines) |
