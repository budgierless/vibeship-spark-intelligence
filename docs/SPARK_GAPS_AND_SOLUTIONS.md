# Spark Intelligence: Gap Analysis and Solutions

Related docs:
- docs/IMPROVEMENT_PLANS.md (KISS index and lightweight plan)
- docs/IMPLEMENTATION_ROADMAP.md
- docs/INTEGRATION-PLAN.md
- docs/VIBE_CODING_INTELLIGENCE_ROADMAP.md

## Implementation Status (Updated 2026-01-30)

| # | Gap | Priority | Status | Implementation |
|---|-----|----------|--------|----------------|
| 1 | Session Amnesia | P0 | ✅ DONE | `lib/context_sync.py`, `lib/output_adapters/` |
| 2 | No Semantic Understanding | P1 | ✅ DONE | `lib/pattern_detection/semantic.py` |
| 3 | Project Context Blindness | P1 | ✅ DONE | `lib/project_context.py` |
| 4 | Platform Dependencies | P1 | ✅ DONE | Cross-platform Python, `pathlib` |
| 5 | Agent Isolation | P1 | ✅ DONE | `lib/orchestration.py:inject_agent_context()` |
| 6 | No Learning Decay | P2 | ✅ DONE | `lib/cognitive_learner.py:effective_reliability()` |
| 7 | No Conflict Resolution | P2 | ✅ DONE | `lib/cognitive_learner.py:resolve_conflicts()` |
| 8 | Content Learning | P3 | ✅ DONE | `lib/content_learner.py` (28/28 tests) |
| 9-10 | Export, Timeline | P3 | 🟡 PARTIAL | Some features exist |
| 11-20 | Deep Gaps | P4 | 🔴 NOT STARTED | Future work |
| 21-30 | Philosophical Gaps | P5 | 🔴 NOT STARTED | Future work |
| NEW | Worker Health Monitoring | P1 | ✅ DONE | `scripts/watchdog.py`, `lib/bridge_cycle.py` |

### Key Discoveries (2026-01-30)
- **Worker Health**: Already implemented! `scripts/watchdog.py` + `lib/bridge_cycle.py` provide full health monitoring. Events accumulated because services were started manually instead of via `start_spark.bat`.
- **Validation Loop Gap (partial)**: v1 validates preference/communication insights; prediction registry + outcome matching exists, but explicit outcome check-ins and non-cognitive boost/decay are still missing.

---

## Critical Gaps (Blocking Value)

### 1. Session Amnesia

**The Problem:**
Every Claude Code session starts fresh. Even with hooks capturing everything, there's no mechanism to **load** learnings at session start.

```
Session 1: User teaches "I prefer TypeScript"
           → Captured and stored ✓
Session 2: Claude starts fresh, doesn't know preference
           → User has to re-teach ✗
```

**Why This Matters:**
- Learnings are stored but never applied
- Users get frustrated re-teaching the same things
- The whole system is pointless if learnings don't persist across sessions

**Solution: Session Bootstrap Protocol**

```python
class SessionBootstrap:
    """Load learnings at session start."""

    def __init__(self, learnings_path: str = "~/.spark/"):
        self.learnings_path = Path(learnings_path).expanduser()

    def generate_context(self) -> str:
        """Generate context block for CLAUDE.md or system prompt."""

        # Load all sources
        preferences = self._load_preferences()
        principles = self._load_principles()
        opinions = self._load_opinions()
        style = self._load_working_style()

        # Generate context
        context = []

        if preferences:
            context.append("## User Preferences (Learned)")
            for p in preferences[:10]:  # Top 10 by confidence
                context.append(f"- {p['key']}: {p['value']} ({p['confidence']:.0%} confident)")

        if principles:
            context.append("\n## Working Principles")
            for p in principles[:5]:
                context.append(f"- {p['statement']}")

        if style:
            context.append(f"\n## Working Style: {style['name']}")
            for trait in style['traits']:
                context.append(f"- {trait}")

        return "\n".join(context)

    def update_claude_md(self):
        """Auto-update CLAUDE.md with learned context."""
        # Find CLAUDE.md in project
        claude_md = self._find_claude_md()

        # Read current content
        current = claude_md.read_text()

        # Find or create Spark section
        marker_start = "<!-- SPARK_LEARNINGS_START -->"
        marker_end = "<!-- SPARK_LEARNINGS_END -->"

        new_section = f"{marker_start}\n{self.generate_context()}\n{marker_end}"

        if marker_start in current:
            # Replace existing section
            import re
            updated = re.sub(
                f"{marker_start}.*?{marker_end}",
                new_section,
                current,
                flags=re.DOTALL
            )
        else:
            # Append new section
            updated = current + f"\n\n{new_section}"

        claude_md.write_text(updated)
```

**Platform Compatibility:**
- Pure Python, no OS-specific calls
- Uses `pathlib` for cross-platform paths
- Falls back gracefully if CLAUDE.md not found

---

### 2. No Semantic Understanding

**The Problem:**
Pattern matching is keyword-based. It detects "no, I meant" but doesn't understand meaning.

```python
# Current: String matching
CORRECTION_PHRASES = ["no, I meant", "actually", "wrong"]

# Problem: Misses
"Could you instead..."        # Not detected
"Let's go with option B"      # Not detected (implies A was wrong)
"Hmm, what about..."          # Not detected (polite correction)
```

**Why This Matters:**
- Misses nuanced corrections
- Can't generalize across phrasings
- False positives on casual use of keywords

**Solution: Local Semantic Matching**

```python
class SemanticMatcher:
    """Lightweight semantic understanding without LLM calls."""

    def __init__(self):
        # Semantic clusters - words that mean similar things
        self.CORRECTION_CLUSTER = {
            "direct": ["no", "wrong", "incorrect", "not that"],
            "redirect": ["instead", "rather", "how about", "what about", "let's try"],
            "implicit": ["actually", "hmm", "well", "but"],
            "polite": ["could you", "would you mind", "perhaps"]
        }

        # Intent patterns (regex + semantic)
        self.INTENT_PATTERNS = {
            "correction": [
                (r"no[,.]?\s+(i\s+)?(want|need|meant)", 0.9),
                (r"(not|don't)\s+(that|this|like)", 0.8),
                (r"(instead|rather)\s+(of|than)?", 0.7),
                (r"^(actually|well|hmm)[,.]", 0.6),
            ],
            "satisfaction": [
                (r"(perfect|exactly|great|yes)[!.]?$", 0.9),
                (r"(thanks|thank you)", 0.8),
                (r"(works?|working)", 0.7),
            ],
            "frustration": [
                (r"(still|again)\s+(not|doesn't|won't)", 0.9),
                (r"(why|how)\s+(is|does|doesn't)", 0.7),
                (r"^(ugh|argh|sigh)", 0.8),
            ]
        }

    def classify_intent(self, text: str) -> tuple[str, float]:
        """Classify user intent with confidence."""
        text_lower = text.lower().strip()

        best_intent = None
        best_confidence = 0.0

        for intent, patterns in self.INTENT_PATTERNS.items():
            for pattern, base_confidence in patterns:
                if re.search(pattern, text_lower):
                    # Adjust confidence based on text length
                    # Short = more confident (clear signal)
                    length_factor = 1.0 if len(text) < 50 else 0.9
                    confidence = base_confidence * length_factor

                    if confidence > best_confidence:
                        best_intent = intent
                        best_confidence = confidence

        return (best_intent, best_confidence) if best_intent else (None, 0.0)

    def extract_preference_pair(self, before: str, after: str) -> dict:
        """Extract what changed between two states."""
        # Diff-based extraction
        # "Use JavaScript" → "Use TypeScript instead"
        # Extracts: rejected=JavaScript, preferred=TypeScript

        # Simple word-level diff
        before_words = set(before.lower().split())
        after_words = set(after.lower().split())

        removed = before_words - after_words
        added = after_words - before_words

        # Filter stopwords
        stopwords = {"use", "the", "a", "an", "to", "for", "with", "in", "instead", "please"}
        removed = removed - stopwords
        added = added - stopwords

        if removed and added:
            return {
                "rejected": list(removed),
                "preferred": list(added),
                "confidence": 0.7
            }
        return None
```

**Platform Compatibility:**
- Pure Python regex, no external dependencies
- No LLM calls needed (works fully offline)
- Graceful degradation if patterns don't match

---

### 3. Project Context Blindness

**The Problem:**
Same learnings apply to all projects. "Prefers TypeScript" applies even in a Python-only repo.

**Why This Matters:**
- Recommendations don't match project context
- User has to override inappropriate suggestions
- Loses trust in the system

**Solution: Context-Aware Learnings**

```python
class ProjectContext:
    """Detect and use project context."""

    def __init__(self, project_path: str):
        self.path = Path(project_path)
        self.context = self._detect_context()

    def _detect_context(self) -> dict:
        """Auto-detect project type and stack."""
        context = {
            "type": None,
            "languages": [],
            "frameworks": [],
            "tools": [],
        }

        # Language detection
        if (self.path / "package.json").exists():
            context["languages"].append("javascript")
            pkg = json.loads((self.path / "package.json").read_text())
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

            if "typescript" in deps:
                context["languages"].append("typescript")
            if "react" in deps or "next" in deps:
                context["frameworks"].append("react")
            if "vue" in deps:
                context["frameworks"].append("vue")

        if (self.path / "requirements.txt").exists() or (self.path / "pyproject.toml").exists():
            context["languages"].append("python")

        if (self.path / "go.mod").exists():
            context["languages"].append("go")

        if (self.path / "Cargo.toml").exists():
            context["languages"].append("rust")

        return context


class ContextAwareLearnings:
    """Filter learnings by relevance to current context."""

    def get_relevant_preferences(self, context: dict) -> list:
        """Get preferences that apply to current project."""
        all_prefs = self._load_all_preferences()

        relevant = []
        for pref in all_prefs:
            # Check if preference has context requirements
            if "applies_to" in pref:
                # Only include if context matches
                if self._context_matches(pref["applies_to"], context):
                    relevant.append(pref)
            else:
                # Universal preference, always include
                relevant.append(pref)

        return relevant

    def _context_matches(self, required: dict, actual: dict) -> bool:
        """Check if actual context matches requirements."""
        for key, values in required.items():
            if key in actual:
                if not any(v in actual[key] for v in values):
                    return False
        return True
```

**Data Model Enhancement:**

```python
class Preference:
    key: str
    value: str
    confidence: float

    # NEW: Context scoping
    applies_to: dict = None  # {"languages": ["python"], "frameworks": ["django"]}
    universal: bool = True    # Applies everywhere if True

    # NEW: When to apply
    conditions: list = None   # ["when_debugging", "when_testing"]
```

---

### 4. Platform Dependencies

**The Problem:**
- Windows batch files (`.bat`)
- Hardcoded paths (`C:\Users\USER\`)
- Assumed Python version
- OS-specific commands

**Solution: Universal Launcher**

```python
#!/usr/bin/env python3
"""
spark_launcher.py - Cross-platform Spark launcher

Works on: Windows, macOS, Linux
Requires: Python 3.8+
"""

import sys
import os
import subprocess
import platform
from pathlib import Path

# Platform detection
IS_WINDOWS = platform.system() == "Windows"
IS_MAC = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"

# Universal paths
HOME = Path.home()
SPARK_HOME = HOME / ".spark"
DATA_DIR = SPARK_HOME / "data"
QUEUE_DIR = SPARK_HOME / "queue"
CONFIG_FILE = SPARK_HOME / "config.json"

def ensure_directories():
    """Create necessary directories."""
    for d in [SPARK_HOME, DATA_DIR, QUEUE_DIR]:
        d.mkdir(parents=True, exist_ok=True)

def find_python():
    """Find Python executable cross-platform."""
    candidates = ["python3", "python"]
    if IS_WINDOWS:
        candidates = ["python", "py -3", "python3"]

    for cmd in candidates:
        try:
            result = subprocess.run(
                cmd.split() + ["--version"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0 and "Python 3" in result.stdout:
                return cmd
        except:
            continue

    raise RuntimeError("Python 3 not found")

def start_daemon(port: int = int(os.environ.get("SPARKD_PORT", "8787"))):
    """Start Spark daemon cross-platform."""
    python = find_python()
    daemon_path = Path(__file__).parent / "sparkd.py"

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"  # Unicode support
    env["SPARKD_PORT"] = str(port)

    if IS_WINDOWS:
        # Windows: use subprocess with CREATE_NEW_CONSOLE
        subprocess.Popen(
            [python, str(daemon_path)],
            creationflags=subprocess.CREATE_NEW_CONSOLE,
            env=env
        )
    else:
        # Unix: use nohup or screen
        subprocess.Popen(
            ["nohup", python, str(daemon_path)],
            stdout=open(SPARK_HOME / "daemon.log", "w"),
            stderr=subprocess.STDOUT,
            start_new_session=True,
            env=env
        )

def start_dashboard(port: int = int(os.environ.get("SPARK_DASHBOARD_PORT", "8585"))):
    """Start dashboard cross-platform."""
    python = find_python()
    dashboard_path = Path(__file__).parent / "dashboard.py"

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["SPARK_DASHBOARD_PORT"] = str(port)

    if IS_WINDOWS:
        subprocess.Popen(
            [python, str(dashboard_path)],
            creationflags=subprocess.CREATE_NEW_CONSOLE,
            env=env
        )
    else:
        subprocess.Popen(
            ["nohup", python, str(dashboard_path)],
            stdout=open(SPARK_HOME / "dashboard.log", "w"),
            stderr=subprocess.STDOUT,
            start_new_session=True,
            env=env
        )

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Spark Intelligence Launcher")
    parser.add_argument("command", choices=["start", "stop", "status", "bootstrap"])
    parser.add_argument("--daemon-port", type=int, default=int(os.environ.get("SPARKD_PORT", "8787")))
    parser.add_argument("--dashboard-port", type=int, default=int(os.environ.get("SPARK_DASHBOARD_PORT", "8585")))

    args = parser.parse_args()

    if args.command == "start":
        ensure_directories()
        start_daemon(args.daemon_port)
        start_dashboard(args.dashboard_port)
        print(f"Spark started: daemon:{args.daemon_port}, dashboard:{args.dashboard_port}")

    elif args.command == "bootstrap":
        # Generate context for current session
        bootstrap = SessionBootstrap()
        context = bootstrap.generate_context()
        print(context)

if __name__ == "__main__":
    main()
```

---

### 5. Agent Isolation

**The Problem:**
When using the `Task` tool to spawn agents, those agents have NO access to Spark learnings. The orchestrator knows preferences, but spawned agents work in isolation.

```
Orchestrator: Knows user prefers TypeScript
    │
    └─> Task(agent) ─> Agent: No idea, might use JavaScript
```

**Why This Matters:**
- Agents ignore learned preferences
- Inconsistent behavior across agents
- User has to specify preferences in every prompt

**Solution: Spark Context Injection**

```python
class SparkContextInjector:
    """Inject Spark context into agent prompts."""

    def __init__(self):
        self.bootstrap = SessionBootstrap()

    def inject_into_prompt(self, original_prompt: str, context_level: str = "summary") -> str:
        """
        Inject Spark context into prompt before sending to agent.

        context_level:
          - "minimal": Just top 3 preferences
          - "summary": Key preferences + style
          - "full": Everything relevant
        """
        spark_context = self._generate_context(context_level)

        if not spark_context:
            return original_prompt

        return f"""<spark_context>
{spark_context}
</spark_context>

{original_prompt}"""

    def _generate_context(self, level: str) -> str:
        preferences = self.bootstrap._load_preferences()

        if level == "minimal":
            top_prefs = sorted(preferences, key=lambda p: p.get("confidence", 0), reverse=True)[:3]
            return "\n".join(f"- {p['key']}: {p['value']}" for p in top_prefs)

        elif level == "summary":
            # Preferences + working style
            lines = ["User preferences:"]
            for p in preferences[:5]:
                lines.append(f"  - {p['key']}: {p['value']}")

            style = self.bootstrap._load_working_style()
            if style:
                lines.append(f"\nWorking style: {style['name']}")

            return "\n".join(lines)

        else:  # full
            return self.bootstrap.generate_context()
```

**Hook Integration:**

```python
# In observe.py hook, intercept Task tool calls
def on_pre_tool_use(event: dict):
    if event.get("tool_name") == "Task":
        # Inject Spark context into agent prompt
        injector = SparkContextInjector()
        original_prompt = event.get("input", {}).get("prompt", "")
        enhanced_prompt = injector.inject_into_prompt(original_prompt)
        event["input"]["prompt"] = enhanced_prompt
```

---

### 6. No Learning Decay

**The Problem:**
Learnings never expire. A preference from 6 months ago has equal weight to one from today.

**Solution: Temporal Decay**

```python
class TemporalDecay:
    """Decay confidence over time."""

    HALF_LIFE_DAYS = {
        "preference": 90,      # Preferences decay slower
        "principle": 180,      # Principles are stable
        "opinion": 60,         # Opinions change faster
        "observation": 30,     # Observations are transient
    }

    def decayed_confidence(self, learning: dict) -> float:
        """Calculate current confidence with decay."""
        original_confidence = learning.get("confidence", 0.5)
        last_validated = learning.get("last_validated")
        learning_type = learning.get("type", "observation")

        if not last_validated:
            return original_confidence * 0.5  # Unknown age = decay

        # Calculate days since validation
        from datetime import datetime
        last_dt = datetime.fromisoformat(last_validated)
        days_since = (datetime.now() - last_dt).days

        # Apply half-life decay
        half_life = self.HALF_LIFE_DAYS.get(learning_type, 60)
        decay_factor = 0.5 ** (days_since / half_life)

        return original_confidence * decay_factor

    def prune_stale(self, learnings: list, threshold: float = 0.3) -> list:
        """Remove learnings that have decayed below threshold."""
        active = []
        pruned = []

        for learning in learnings:
            current_conf = self.decayed_confidence(learning)
            if current_conf >= threshold:
                learning["effective_confidence"] = current_conf
                active.append(learning)
            else:
                pruned.append(learning)

        return active, pruned
```

---

### 7. No Conflict Resolution

**The Problem:**
What if learnings contradict each other?
- "Prefers verbose output" vs "Prefers concise output"
- Both from different contexts

**Solution: Contextual Priority**

```python
class ConflictResolver:
    """Resolve conflicting learnings."""

    def resolve(self, learnings: list, current_context: dict) -> list:
        """Select non-conflicting learnings for current context."""

        # Group by topic
        by_topic = {}
        for l in learnings:
            topic = l.get("key", l.get("topic"))
            if topic not in by_topic:
                by_topic[topic] = []
            by_topic[topic].append(l)

        # For each topic, pick the best one
        resolved = []
        for topic, candidates in by_topic.items():
            if len(candidates) == 1:
                resolved.append(candidates[0])
            else:
                winner = self._pick_best(candidates, current_context)
                resolved.append(winner)

        return resolved

    def _pick_best(self, candidates: list, context: dict) -> dict:
        """Pick best candidate based on context match + confidence."""
        scores = []

        for c in candidates:
            score = 0

            # Context match score
            if self._context_matches(c.get("applies_to", {}), context):
                score += 50

            # Recency score
            if "last_validated" in c:
                days_old = self._days_since(c["last_validated"])
                score += max(0, 30 - days_old)  # Recent = higher score

            # Confidence score
            score += c.get("confidence", 0.5) * 20

            # Validation count
            score += min(c.get("times_validated", 0) * 2, 20)

            scores.append((score, c))

        # Return highest scoring
        return max(scores, key=lambda x: x[0])[1]
```

---

## High-Impact Gaps (Not Blocking But Valuable)

### 8. No Learning From Content

**The Problem:**
Spark learns from behavior (tool usage, corrections) but not from content (code written, files read).

**Opportunity:**
- Learn coding patterns from code written
- Learn domain knowledge from files read
- Learn project structure from exploration

**Solution: Content Learning**

```python
class ContentLearner:
    """Learn from content, not just behavior."""

    def learn_from_code(self, code: str, file_path: str, context: dict):
        """Extract learnable patterns from code."""

        # Detect patterns
        patterns = []

        # Naming conventions
        if re.search(r"def [a-z]+_[a-z]+", code):  # snake_case functions
            patterns.append(("naming_style", "snake_case", "python"))
        elif re.search(r"function [a-z][a-zA-Z]+", code):  # camelCase
            patterns.append(("naming_style", "camelCase", "javascript"))

        # Error handling style
        if "try:" in code and "except Exception" in code:
            patterns.append(("error_handling", "broad_except", None))
        elif "try:" in code and "except " in code:
            patterns.append(("error_handling", "specific_except", None))

        # Import style
        if re.search(r"from \w+ import \*", code):
            patterns.append(("import_style", "star_import", None))

        # Store as observations (not preferences - those need validation)
        for topic, value, lang in patterns:
            self._store_observation(topic, value, lang, file_path)

    def learn_from_project_structure(self, files: list):
        """Learn project conventions from structure."""

        # Test location
        test_patterns = {
            "tests/": "separate_tests_dir",
            "__tests__/": "jest_style",
            "*.test.ts": "colocated_tests",
            "*.spec.ts": "colocated_specs",
        }

        for pattern, style in test_patterns.items():
            if any(pattern.replace("*", "") in f for f in files):
                self._store_observation("test_organization", style, None)

        # Source organization
        if any("src/" in f for f in files):
            self._store_observation("source_organization", "src_directory", None)
```

---

### 9. No Export/Import

**The Problem:**
Learnings are locked in local files. Can't share, backup, or transfer.

**Solution: Portable Format**

```python
class SparkExporter:
    """Export/import Spark learnings."""

    def export_all(self, format: str = "json") -> str:
        """Export all learnings to portable format."""

        data = {
            "version": "1.0",
            "exported_at": datetime.now().isoformat(),
            "preferences": self._load_preferences(),
            "principles": self._load_principles(),
            "opinions": self._load_opinions(),
            "observations": self._load_observations(),
            "meta": {
                "total_events_processed": self._get_stats()["total_events"],
                "resonance": self._get_resonance(),
            }
        }

        if format == "json":
            return json.dumps(data, indent=2)
        elif format == "yaml":
            import yaml
            return yaml.dump(data, default_flow_style=False)
        elif format == "markdown":
            return self._to_markdown(data)

    def import_learnings(self, data: str, format: str = "json", merge: bool = True):
        """Import learnings from portable format."""

        if format == "json":
            imported = json.loads(data)
        elif format == "yaml":
            import yaml
            imported = yaml.safe_load(data)

        if merge:
            self._merge_learnings(imported)
        else:
            self._replace_learnings(imported)

    def _to_markdown(self, data: dict) -> str:
        """Export as human-readable markdown."""
        lines = [
            "# Spark Learnings Export",
            f"\nExported: {data['exported_at']}",
            f"Events processed: {data['meta']['total_events_processed']}",
            f"Resonance: {data['meta']['resonance']:.0%}",
            "\n## Preferences\n"
        ]

        for p in data["preferences"]:
            lines.append(f"- **{p['key']}**: {p['value']} ({p['confidence']:.0%})")

        lines.append("\n## Principles\n")
        for p in data["principles"]:
            lines.append(f"- {p['statement']}")

        return "\n".join(lines)
```

---

### 10. No Visualization of Learning Journey

**The Problem:**
Dashboard shows current state but not how we got here. No trajectory, no history of learning.

**Solution: Learning Timeline**

```python
class LearningTimeline:
    """Track and visualize learning over time."""

    def __init__(self):
        self.timeline_file = Path.home() / ".spark" / "timeline.jsonl"

    def record_milestone(self, event_type: str, details: dict):
        """Record a learning milestone."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "details": details
        }

        with open(self.timeline_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def get_timeline(self, days: int = 30) -> list:
        """Get learning timeline for visualization."""
        cutoff = datetime.now() - timedelta(days=days)

        entries = []
        with open(self.timeline_file) as f:
            for line in f:
                entry = json.loads(line)
                entry_time = datetime.fromisoformat(entry["timestamp"])
                if entry_time >= cutoff:
                    entries.append(entry)

        return entries

    def generate_summary(self) -> dict:
        """Generate learning journey summary."""
        timeline = self.get_timeline(days=365)

        return {
            "total_learnings": len(timeline),
            "by_type": self._count_by_type(timeline),
            "learning_rate": self._calculate_rate(timeline),
            "milestones": self._extract_milestones(timeline),
            "growth_curve": self._generate_growth_curve(timeline),
        }
```

---

## Implementation Priority

### Must Have (Week 1-2)
1. **Session Bootstrap** - Without this, learnings are useless
2. **Cross-Platform Launcher** - Universal access
3. **Temporal Decay** - Prevents stale data accumulation
4. **Conflict Resolution** - Prevents contradictory behavior

### Should Have (Week 3-4)
5. **Semantic Matching** - Better pattern detection
6. **Project Context** - Relevance filtering
7. **Agent Context Injection** - Consistent behavior

### Nice to Have (Week 5+)
8. **Content Learning** - Deeper understanding
9. **Export/Import** - Portability
10. **Learning Timeline** - Visualization

---

## Compatibility Matrix

| Feature | Windows | macOS | Linux | Offline | Dependencies |
|---------|---------|-------|-------|---------|--------------|
| Session Bootstrap | ✓ | ✓ | ✓ | ✓ | None |
| Semantic Matching | ✓ | ✓ | ✓ | ✓ | None |
| Project Context | ✓ | ✓ | ✓ | ✓ | None |
| Cross-Platform Launcher | ✓ | ✓ | ✓ | ✓ | Python 3.8+ |
| Agent Context Injection | ✓ | ✓ | ✓ | ✓ | None |
| Temporal Decay | ✓ | ✓ | ✓ | ✓ | None |
| Conflict Resolution | ✓ | ✓ | ✓ | ✓ | None |
| Content Learning | ✓ | ✓ | ✓ | ✓ | None |
| Export/Import | ✓ | ✓ | ✓ | ✓ | PyYAML (optional) |
| Timeline | ✓ | ✓ | ✓ | ✓ | None |

All solutions use:
- Pure Python standard library
- Cross-platform `pathlib`
- JSON for storage (universal)
- No OS-specific syscalls
- No external services required

---

## The Critical Insight

The biggest gap isn't any single feature - it's the **feedback loop**:

```
Current:  Capture → Store → (nothing)

Needed:   Capture → Store → Load → Apply → Validate → Improve
                              ↑                        │
                              └────────────────────────┘
```

Without the **Load** step, everything else is pointless.
Without the **Apply** step, learnings never affect behavior.
Without the **Validate** step, we don't know if learnings are right.
Without the **Improve** step, the system can't get better.

**Session Bootstrap + Validation Loop = Actually Useful System**

---

## The Hardest Problem: Session Start

Here's the fundamental challenge that's harder than it looks:

```
┌─────────────────────────────────────────────────────────────┐
│                    TIMING PROBLEM                           │
│                                                             │
│   User types prompt ─────────────────────────────────────▶  │
│                           │                                 │
│   Hooks fire AFTER ───────┤  Claude already                 │
│   Claude gets prompt      │  processing WITHOUT             │
│                           │  Spark context                  │
│                           ▼                                 │
│   Spark learns from    Too late! Claude                     │
│   what happened        didn't have prefs                    │
└─────────────────────────────────────────────────────────────┘
```

**The problem:** By the time hooks fire, Claude is already working. There's no "before session starts" hook.

**Possible Solutions:**

### Option A: CLAUDE.md Daemon
A background process that keeps CLAUDE.md updated with latest learnings:
```python
# spark_sync.py - Runs continuously
while True:
    update_claude_md_with_learnings()
    sleep(60)  # Update every minute
```
- Pro: Always fresh context
- Con: Extra process running, file constantly changing

### Option B: Pre-Session Command
User runs `spark context` before starting Claude Code:
```bash
$ spark context >> CLAUDE.md  # Or copy to clipboard
$ claude  # Now start Claude Code
```
- Pro: Simple, explicit
- Con: Manual step users will forget

### Option C: Shell Hook
Wrap the `claude` command:
```bash
# In .bashrc / .zshrc
claude() {
    spark-bootstrap  # Update CLAUDE.md first
    command claude "$@"
}
```
- Pro: Automatic
- Con: Shell-specific, doesn't work on Windows easily

### Option D: Git Hook
Pre-commit or post-checkout hook updates CLAUDE.md:
```bash
# .git/hooks/post-checkout
spark-bootstrap > .spark-context.md
```
- Pro: Project-aware
- Con: Only fires on git operations

### Option E: Claude Code Extension (Future)
If Claude Code adds extension support, Spark could inject context at startup.
- Pro: Perfect solution
- Con: Doesn't exist yet

### Recommended: Hybrid Approach

```python
class HybridBootstrap:
    """Multiple strategies for maximum coverage."""

    def ensure_context_available(self):
        # 1. Update CLAUDE.md if it exists and has markers
        self._update_claude_md()

        # 2. Create .spark-context file (can be @imported)
        self._write_context_file()

        # 3. Set environment variable (Claude Code might read it)
        self._set_env_context()

        # 4. If daemon mode, keep updating in background
        if self.daemon_mode:
            self._start_daemon()

    def _write_context_file(self):
        """Write .spark-context that can be @imported in prompts."""
        context = self.generate_context()
        (Path.cwd() / ".spark-context").write_text(context)
        # User can then start with: "@.spark-context help me with..."
```

This is the **#1 blocker** to making Spark actually useful.

---

## Quick Wins vs Deep Work

| Gap | Effort | Impact | Priority |
|-----|--------|--------|----------|
| Session Bootstrap | Medium | CRITICAL | P0 |
| Cross-Platform Launcher | Low | High | P1 |
| Temporal Decay | Low | Medium | P2 |
| Conflict Resolution | Medium | Medium | P2 |
| Semantic Matching | High | High | P1 |
| Project Context | Medium | High | P1 |
| Agent Injection | Medium | High | P1 |
| Content Learning | High | Medium | P3 |
| Export/Import | Low | Low | P3 |
| Timeline | Medium | Low | P4 |

**Start with P0: Session Bootstrap.** Everything else is useless without it.

---

## Deeper Gaps: What We're Not Even Thinking About

### 11. No Learning From My Own Reasoning

**The Problem:**
I explain WHY I do things constantly, but that reasoning is never captured.

```
Me: "I'm using TypeScript here because it catches errors early
     and this codebase already uses it..."

Spark: *captures that I used Edit tool*
       *misses the entire reasoning*
```

**What's Lost:**
- Decision rationale
- Trade-off analysis
- Context-dependent choices
- The "why" behind the "what"

**Solution: Reasoning Capture**

```python
class ReasoningCapture:
    """Capture and learn from AI's own reasoning."""

    # Patterns that indicate reasoning
    REASONING_MARKERS = [
        r"because\s+",
        r"since\s+",
        r"I('m| am) (using|choosing|doing)\s+.+\s+because",
        r"the reason\s+",
        r"this (approach|way|method)\s+",
        r"rather than\s+",
        r"instead of\s+",
        r"trade-?off",
        r"(pro|con)s?:",
    ]

    def extract_reasoning(self, response: str) -> list[dict]:
        """Extract reasoning statements from response."""
        reasonings = []

        for marker in self.REASONING_MARKERS:
            matches = re.finditer(marker, response, re.IGNORECASE)
            for match in matches:
                # Get surrounding context (sentence)
                start = response.rfind('.', 0, match.start()) + 1
                end = response.find('.', match.end())
                if end == -1:
                    end = len(response)

                statement = response[start:end].strip()
                reasonings.append({
                    "statement": statement,
                    "marker": marker,
                    "context": self._get_context(response, match.start())
                })

        return reasonings

    def learn_from_reasoning(self, reasoning: dict):
        """Convert reasoning into learnable insight."""
        # "I'm using TypeScript because it catches errors early"
        # → Principle: "TypeScript preferred for error catching"

        statement = reasoning["statement"]

        # Extract the choice and rationale
        if "because" in statement.lower():
            parts = re.split(r'\s+because\s+', statement, flags=re.IGNORECASE)
            if len(parts) == 2:
                choice = parts[0]
                rationale = parts[1]

                return {
                    "type": "decision_pattern",
                    "choice": choice,
                    "rationale": rationale,
                    "confidence": 0.6,  # Lower - needs validation
                    "source": "self_reasoning"
                }
```

---

### 12. No Learning From Failures (Deep)

**The Problem:**
We track that failures happen, but don't analyze WHY or learn prevention.

```
Failure: Edit tool failed - string not found
Current: Log it, move on
Missing: WHY wasn't it found? What should I do differently?
```

**What's Lost:**
- Failure patterns
- Prevention strategies
- Recovery approaches
- Root cause understanding

**Solution: Failure Analysis Engine**

```python
class FailureAnalyzer:
    """Deep analysis of failures to prevent recurrence."""

    FAILURE_PATTERNS = {
        "string_not_found": {
            "causes": [
                "file_changed_since_read",
                "wrong_indentation",
                "encoding_mismatch",
                "partial_match_attempted"
            ],
            "preventions": {
                "file_changed_since_read": "Re-read file immediately before edit",
                "wrong_indentation": "Copy exact whitespace from Read output",
                "encoding_mismatch": "Check file encoding first",
                "partial_match_attempted": "Use larger unique context"
            }
        },
        "command_failed": {
            "causes": [
                "wrong_directory",
                "missing_dependency",
                "permission_denied",
                "syntax_error"
            ],
            "preventions": {
                "wrong_directory": "Always use absolute paths",
                "missing_dependency": "Check package.json/requirements first",
                "permission_denied": "Check file permissions",
                "syntax_error": "Validate command syntax"
            }
        }
    }

    def analyze_failure(self, failure_event: dict) -> dict:
        """Analyze failure and determine cause + prevention."""

        error_msg = failure_event.get("error", "")
        tool_name = failure_event.get("tool_name", "")
        context = failure_event.get("context", {})

        # Classify failure type
        failure_type = self._classify_failure(error_msg)

        # Determine most likely cause
        likely_cause = self._determine_cause(failure_type, context)

        # Get prevention strategy
        prevention = self.FAILURE_PATTERNS.get(failure_type, {}).get(
            "preventions", {}
        ).get(likely_cause, "Unknown - investigate manually")

        return {
            "failure_type": failure_type,
            "likely_cause": likely_cause,
            "prevention": prevention,
            "should_retry": self._should_retry(failure_type, likely_cause),
            "retry_strategy": self._get_retry_strategy(failure_type)
        }

    def learn_from_recovery(self, failure: dict, recovery_action: dict, success: bool):
        """Learn what recovery strategies work."""
        if success:
            # This recovery worked - strengthen it
            self._strengthen_recovery(failure["failure_type"], recovery_action)
        else:
            # Recovery failed - weaken it
            self._weaken_recovery(failure["failure_type"], recovery_action)
```

---

### 13. No User Mental Model

**The Problem:**
We learn preferences but not HOW the user thinks. Their mental model affects everything.

```
User A: Thinks in terms of files and folders
User B: Thinks in terms of features and flows
User C: Thinks in terms of data and transformations

Same request, three different approaches needed.
```

**What's Lost:**
- How user conceptualizes problems
- What analogies resonate
- What level of abstraction they prefer
- Their problem-solving approach

**Solution: Mental Model Detection**

```python
class MentalModelDetector:
    """Detect and adapt to user's mental model."""

    MODELS = {
        "structural": {
            # Thinks in terms of structure
            "signals": [
                "file", "folder", "directory", "path",
                "component", "module", "class", "function"
            ],
            "approach": "Show file structure, component hierarchy"
        },
        "behavioral": {
            # Thinks in terms of behavior
            "signals": [
                "flow", "process", "step", "then",
                "when", "after", "before", "trigger"
            ],
            "approach": "Show sequences, workflows, state machines"
        },
        "data_centric": {
            # Thinks in terms of data
            "signals": [
                "data", "input", "output", "transform",
                "schema", "model", "entity", "field"
            ],
            "approach": "Show data flow, schemas, transformations"
        },
        "visual": {
            # Thinks in diagrams
            "signals": [
                "show me", "diagram", "picture", "visualize",
                "what does it look like", "draw"
            ],
            "approach": "Use ASCII diagrams, visual representations"
        },
        "example_driven": {
            # Learns by example
            "signals": [
                "example", "show me how", "like what",
                "such as", "for instance", "demo"
            ],
            "approach": "Lead with examples, then explain"
        },
        "principle_driven": {
            # Wants to understand why
            "signals": [
                "why", "how does", "what's the reason",
                "explain", "understand", "concept"
            ],
            "approach": "Explain principles first, then implementation"
        }
    }

    def __init__(self):
        self.model_scores = {m: 0.0 for m in self.MODELS}
        self.observations = []

    def observe_prompt(self, prompt: str):
        """Update mental model estimate from user prompt."""
        prompt_lower = prompt.lower()

        for model, config in self.MODELS.items():
            score = sum(1 for s in config["signals"] if s in prompt_lower)
            self.model_scores[model] += score

        self.observations.append(prompt)

    def get_dominant_model(self) -> tuple[str, float]:
        """Get most likely mental model."""
        if not any(self.model_scores.values()):
            return ("unknown", 0.0)

        total = sum(self.model_scores.values())
        best = max(self.model_scores.items(), key=lambda x: x[1])

        return (best[0], best[1] / total if total > 0 else 0.0)

    def get_approach(self) -> str:
        """Get recommended approach for current user."""
        model, confidence = self.get_dominant_model()
        if confidence > 0.3:
            return self.MODELS[model]["approach"]
        return "Balanced approach - mix structure and examples"
```

---

### 14. No Skill Level Adaptation

**The Problem:**
We treat beginners and experts the same way.

```
Beginner: Needs explanation of what useState is
Expert: Annoyed by basic explanations, wants advanced patterns

Same code, different needs.
```

**Solution: Skill Level Detection**

```python
class SkillLevelDetector:
    """Detect and adapt to user's skill level."""

    def __init__(self):
        self.signals = {
            "beginner": [],
            "intermediate": [],
            "advanced": [],
            "expert": []
        }

    def observe(self, prompt: str, code_context: str = None):
        """Observe signals of skill level."""

        # Beginner signals
        beginner_signals = [
            r"what is\s+",
            r"how do (i|you)\s+",
            r"i('m| am) (new|learning|beginner)",
            r"can you explain",
            r"i don't understand",
            r"what does .+ mean",
        ]

        # Expert signals
        expert_signals = [
            r"optimize",
            r"performance",
            r"edge case",
            r"race condition",
            r"memory leak",
            r"type inference",
            r"generics",
            r"abstract",
            r"design pattern",
        ]

        prompt_lower = prompt.lower()

        for pattern in beginner_signals:
            if re.search(pattern, prompt_lower):
                self.signals["beginner"].append(pattern)

        for pattern in expert_signals:
            if re.search(pattern, prompt_lower):
                self.signals["expert"].append(pattern)

        # Code complexity signals
        if code_context:
            self._analyze_code_complexity(code_context)

    def get_level(self) -> tuple[str, float]:
        """Estimate skill level with confidence."""
        counts = {k: len(v) for k, v in self.signals.items()}
        total = sum(counts.values())

        if total == 0:
            return ("intermediate", 0.5)  # Default assumption

        # Weight recent signals more
        if counts["expert"] > counts["beginner"]:
            return ("advanced", counts["expert"] / total)
        elif counts["beginner"] > counts["expert"]:
            return ("beginner", counts["beginner"] / total)
        else:
            return ("intermediate", 0.5)

    def get_explanation_depth(self) -> str:
        """How much explanation to provide."""
        level, confidence = self.get_level()

        if level == "beginner":
            return "detailed"  # Explain everything
        elif level == "expert":
            return "minimal"   # Just the code
        else:
            return "moderate"  # Brief explanations
```

---

### 15. No Intention Inference

**The Problem:**
We see WHAT user asks, not WHY they're asking.

```
User: "How do I add a button?"

Could mean:
- Learning: "I want to understand how buttons work"
- Building: "I need a button for my feature"
- Debugging: "My button isn't working"
- Exploring: "Just curious what's possible"

Each needs different response.
```

**Solution: Intention Detection**

```python
class IntentionDetector:
    """Infer user's underlying intention."""

    INTENTIONS = {
        "learning": {
            "signals": ["how does", "what is", "explain", "understand", "concept"],
            "response": "Educational - explain the why"
        },
        "building": {
            "signals": ["add", "create", "implement", "build", "make"],
            "response": "Practical - give working code"
        },
        "debugging": {
            "signals": ["not working", "error", "bug", "fix", "wrong", "issue"],
            "response": "Diagnostic - find and fix problem"
        },
        "exploring": {
            "signals": ["can I", "is it possible", "what if", "options"],
            "response": "Expansive - show possibilities"
        },
        "optimizing": {
            "signals": ["improve", "better", "faster", "optimize", "refactor"],
            "response": "Analytical - measure and improve"
        },
        "validating": {
            "signals": ["is this right", "correct", "good practice", "should I"],
            "response": "Evaluative - assess and advise"
        }
    }

    def detect_intention(self, prompt: str) -> dict:
        """Detect primary and secondary intentions."""
        prompt_lower = prompt.lower()

        scores = {}
        for intention, config in self.INTENTIONS.items():
            score = sum(1 for s in config["signals"] if s in prompt_lower)
            if score > 0:
                scores[intention] = score

        if not scores:
            return {"primary": "building", "confidence": 0.5}

        sorted_intentions = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        return {
            "primary": sorted_intentions[0][0],
            "secondary": sorted_intentions[1][0] if len(sorted_intentions) > 1 else None,
            "confidence": sorted_intentions[0][1] / sum(scores.values()),
            "recommended_response": self.INTENTIONS[sorted_intentions[0][0]]["response"]
        }
```

---

### 16. No Self-Awareness (Meta-Cognition)

**The Problem:**
Spark learns about the user but not about ME (Claude). I have patterns, biases, strengths, weaknesses.

```
My patterns I don't track:
- Do I over-explain?
- Do I favor certain technologies?
- Do I repeat myself?
- What do I get wrong often?
- What am I actually good at?
```

**Solution: Self-Model**

```python
class SparkSelfModel:
    """Spark's model of its own patterns and tendencies."""

    def __init__(self):
        self.patterns = {
            "response_length": [],      # Track my verbosity
            "technologies_used": {},    # What I recommend
            "approaches_taken": {},     # How I solve problems
            "errors_made": [],          # My mistakes
            "successes": [],            # What worked
            "user_corrections": [],     # When I was wrong
        }

    def observe_my_response(self, response: str, context: dict):
        """Track patterns in my own responses."""

        # Track length
        self.patterns["response_length"].append(len(response))

        # Track technologies mentioned
        techs = self._extract_technologies(response)
        for tech in techs:
            self.patterns["technologies_used"][tech] = \
                self.patterns["technologies_used"].get(tech, 0) + 1

        # Track approach patterns
        approach = self._classify_approach(response, context)
        self.patterns["approaches_taken"][approach] = \
            self.patterns["approaches_taken"].get(approach, 0) + 1

    def observe_correction(self, my_response: str, user_correction: str):
        """Learn from being corrected."""
        self.patterns["user_corrections"].append({
            "my_response": my_response[:200],
            "correction": user_correction,
            "timestamp": datetime.now().isoformat()
        })

    def get_self_insights(self) -> dict:
        """What have I learned about myself?"""
        return {
            "avg_response_length": np.mean(self.patterns["response_length"]) if self.patterns["response_length"] else 0,
            "favorite_technologies": sorted(
                self.patterns["technologies_used"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:5],
            "common_approaches": sorted(
                self.patterns["approaches_taken"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:3],
            "correction_rate": len(self.patterns["user_corrections"]) / max(len(self.patterns["successes"]), 1),
            "blind_spots": self._identify_blind_spots()
        }

    def _identify_blind_spots(self) -> list:
        """What do I consistently get wrong?"""
        corrections = self.patterns["user_corrections"]

        if len(corrections) < 5:
            return ["Not enough data yet"]

        # Find patterns in corrections
        themes = {}
        for c in corrections:
            # Simple keyword extraction
            words = c["correction"].lower().split()
            for word in words:
                if len(word) > 4:  # Skip short words
                    themes[word] = themes.get(word, 0) + 1

        # Return most common themes in corrections
        return [theme for theme, count in sorted(themes.items(), key=lambda x: x[1], reverse=True)[:3] if count > 2]
```

---

### 17. No Communication Style Matching

**The Problem:**
I communicate the same way regardless of user's style.

```
User A: "yo can u fix this quick"
User B: "Could you please assist with this issue?"
User C: "bug in auth.ts line 42"

I respond the same formal way to all three.
```

**Solution: Style Matching**

```python
class CommunicationStyleMatcher:
    """Match user's communication style."""

    def __init__(self):
        self.observations = []

    def observe(self, user_message: str):
        """Analyze user's communication style."""
        self.observations.append({
            "length": len(user_message),
            "formality": self._measure_formality(user_message),
            "emoji_use": bool(re.search(r'[\U0001F600-\U0001F64F]', user_message)),
            "punctuation": self._measure_punctuation(user_message),
            "abbreviations": self._count_abbreviations(user_message),
            "technical_density": self._measure_technical_density(user_message)
        })

    def _measure_formality(self, text: str) -> float:
        """0 = very casual, 1 = very formal."""
        casual_markers = ["u ", "ur ", "pls", "thx", "gonna", "wanna", "yo", "hey"]
        formal_markers = ["please", "could you", "would you", "thank you", "kindly"]

        text_lower = text.lower()
        casual_count = sum(1 for m in casual_markers if m in text_lower)
        formal_count = sum(1 for m in formal_markers if m in text_lower)

        if casual_count + formal_count == 0:
            return 0.5
        return formal_count / (casual_count + formal_count)

    def get_recommended_style(self) -> dict:
        """Get recommended response style."""
        if not self.observations:
            return {"formality": "moderate", "length": "moderate", "emoji": False}

        avg_formality = np.mean([o["formality"] for o in self.observations[-10:]])
        avg_length = np.mean([o["length"] for o in self.observations[-10:]])
        uses_emoji = any(o["emoji_use"] for o in self.observations[-10:])

        return {
            "formality": "formal" if avg_formality > 0.6 else "casual" if avg_formality < 0.4 else "moderate",
            "length": "brief" if avg_length < 50 else "detailed" if avg_length > 200 else "moderate",
            "emoji": uses_emoji,
            "technical_level": "high" if np.mean([o["technical_density"] for o in self.observations[-10:]]) > 0.5 else "moderate"
        }
```

---

### 18. No Temporal Patterns

**The Problem:**
User behavior changes by time of day, day of week, project phase.

```
Morning: User is fresh, wants to tackle hard problems
Evening: User is tired, wants quick wins
Friday: User wants to ship, less careful
Monday: User is planning, more thorough
```

**Solution: Temporal Pattern Learning**

```python
class TemporalPatternLearner:
    """Learn patterns based on time."""

    def __init__(self):
        self.patterns = {
            "by_hour": {h: {"prompts": [], "tools": [], "mood": []} for h in range(24)},
            "by_day": {d: {"prompts": [], "tools": [], "mood": []} for d in range(7)},
        }

    def observe(self, event: dict):
        """Track patterns by time."""
        ts = datetime.fromisoformat(event.get("timestamp", datetime.now().isoformat()))
        hour = ts.hour
        day = ts.weekday()

        self.patterns["by_hour"][hour]["prompts"].append(event)
        self.patterns["by_day"][day]["prompts"].append(event)

    def get_time_insights(self) -> dict:
        """What patterns emerge from time?"""
        insights = {}

        # Most productive hours
        hour_counts = {h: len(p["prompts"]) for h, p in self.patterns["by_hour"].items()}
        peak_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        insights["peak_hours"] = [h[0] for h in peak_hours]

        # Most productive days
        day_counts = {d: len(p["prompts"]) for d, p in self.patterns["by_day"].items()}
        peak_days = sorted(day_counts.items(), key=lambda x: x[1], reverse=True)[:2]
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        insights["peak_days"] = [day_names[d[0]] for d in peak_days]

        return insights

    def get_time_adjusted_approach(self) -> dict:
        """Adjust approach based on current time patterns."""
        now = datetime.now()
        hour = now.hour
        day = now.weekday()

        # Late night = probably tired, keep it simple
        if hour >= 22 or hour <= 5:
            return {"complexity": "simple", "verbosity": "brief", "safety": "high"}

        # Friday afternoon = shipping mode
        if day == 4 and hour >= 14:
            return {"complexity": "moderate", "verbosity": "brief", "safety": "high"}

        # Monday morning = planning mode
        if day == 0 and hour < 12:
            return {"complexity": "any", "verbosity": "detailed", "safety": "moderate"}

        return {"complexity": "any", "verbosity": "moderate", "safety": "moderate"}
```

---

### 19. No Unlearning Mechanism

**The Problem:**
Once something is learned, it can't be explicitly unlearned.

```
Spark: "User prefers JavaScript" (learned 6 months ago)
User: "I've switched to TypeScript now"
Spark: Still weighs old JavaScript preference
```

**Solution: Explicit Unlearning**

```python
class UnlearningEngine:
    """Allow explicit unlearning of incorrect learnings."""

    def unlearn(self, key: str, reason: str = None):
        """Explicitly mark a learning as invalid."""
        learning = self._find_learning(key)

        if learning:
            learning["status"] = "unlearned"
            learning["unlearned_at"] = datetime.now().isoformat()
            learning["unlearn_reason"] = reason

            # Don't delete - keep for meta-learning
            # Why was this wrong? What can we learn?
            self._log_unlearning(learning, reason)

    def handle_contradiction(self, old_learning: dict, new_signal: dict):
        """Handle when new signal contradicts old learning."""

        # Check if explicit contradiction
        if self._is_explicit_contradiction(new_signal):
            # User explicitly said the old thing was wrong
            self.unlearn(old_learning["key"], reason="User explicitly contradicted")
            return

        # Check if implicit (behavior change)
        if self._is_behavior_change(old_learning, new_signal):
            # Don't unlearn immediately, but track
            old_learning["contradictions"] = old_learning.get("contradictions", 0) + 1

            # After N contradictions, demote
            if old_learning["contradictions"] >= 3:
                old_learning["confidence"] *= 0.5
                old_learning["status"] = "uncertain"

    def _is_explicit_contradiction(self, signal: dict) -> bool:
        """Check if user explicitly contradicted."""
        text = signal.get("text", "").lower()
        explicit_markers = [
            "not anymore", "i've switched", "i changed", "actually now",
            "forget that", "that's old", "i don't use .+ anymore"
        ]
        return any(re.search(m, text) for m in explicit_markers)
```

---

### 20. No Learning Transfer

**The Problem:**
Learning about one thing doesn't help with similar things.

```
Learned: User prefers functional style in JavaScript
Not applied: Same user doing Python (could use functional style there too)

Learned: User likes detailed error messages
Not applied: Same user in different project
```

**Solution: Learning Generalization**

```python
class LearningGeneralizer:
    """Generalize learnings to related domains."""

    # Concept hierarchies
    HIERARCHIES = {
        "languages": {
            "javascript": ["programming", "web", "dynamic"],
            "typescript": ["programming", "web", "typed"],
            "python": ["programming", "scripting", "dynamic"],
            "rust": ["programming", "systems", "typed"],
        },
        "paradigms": {
            "functional": ["declarative", "immutable"],
            "oop": ["imperative", "mutable"],
            "reactive": ["event-driven", "async"],
        }
    }

    def generalize(self, learning: dict) -> list[dict]:
        """Generate more general versions of a learning."""
        generalizations = []

        # Check if learning is language-specific
        applies_to = learning.get("applies_to", {})
        if "languages" in applies_to:
            lang = applies_to["languages"][0]

            # Find sibling languages
            for other_lang, traits in self.HIERARCHIES["languages"].items():
                if other_lang != lang:
                    # Check trait overlap
                    lang_traits = self.HIERARCHIES["languages"].get(lang, [])
                    overlap = set(traits) & set(lang_traits)

                    if len(overlap) >= 2:  # Significant overlap
                        generalized = learning.copy()
                        generalized["applies_to"] = {"languages": [other_lang]}
                        generalized["confidence"] *= 0.7  # Lower confidence
                        generalized["source"] = "generalization"
                        generalized["generalized_from"] = learning.get("key")
                        generalizations.append(generalized)

        return generalizations

    def find_applicable(self, context: dict, all_learnings: list) -> list:
        """Find learnings that might apply through generalization."""
        direct_matches = [l for l in all_learnings if self._context_matches(l, context)]

        # Also find generalizable learnings
        generalizable = []
        for l in all_learnings:
            if l not in direct_matches:
                generalized = self.generalize(l)
                for g in generalized:
                    if self._context_matches(g, context):
                        generalizable.append(g)

        return direct_matches + generalizable
```

---

## The Complete Gap Map

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SPARK GAP ANALYSIS                                │
│                                                                             │
│  CRITICAL (System Broken)          HIGH (Significant Value Lost)           │
│  ├── Session Amnesia               ├── No Reasoning Capture                │
│  ├── No Semantic Understanding     ├── No Deep Failure Analysis            │
│  ├── Project Blindness             ├── No User Mental Model                │
│  ├── Platform Lock                 ├── No Skill Level Adaptation           │
│  ├── Agent Isolation               ├── No Intention Inference              │
│  ├── No Decay                      ├── No Self-Awareness                   │
│  └── No Conflict Resolution        ├── No Style Matching                   │
│                                    ├── No Temporal Patterns                │
│  MEDIUM (Nice to Have)             ├── No Unlearning                       │
│  ├── Content Learning              └── No Learning Transfer                │
│  ├── Export/Import                                                         │
│  └── Timeline Visualization        PHILOSOPHICAL (Deep)                    │
│                                    ├── No Causality vs Correlation         │
│                                    ├── No Counterfactual Reasoning         │
│                                    ├── No Negative Space Learning          │
│                                    └── No Uncertainty Quantification       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## What Makes This Complete

A truly complete system would:

1. **Learn from everything**: Actions, reasoning, failures, content, time, context
2. **Understand the user**: Mental model, skill level, intentions, style, preferences
3. **Know itself**: Patterns, biases, strengths, weaknesses, blind spots
4. **Adapt continuously**: Decay old learnings, unlearn wrong ones, generalize good ones
5. **Work everywhere**: Cross-platform, offline, any project
6. **Persist and transfer**: Session bootstrap, agent context, export/import
7. **Explain itself**: Why it thinks what it thinks, how confident it is

That's the complete picture.

---

## Even Deeper Gaps: The Truly Hard Problems

### 21. No Privacy Controls

**The Problem:**
Everything is captured. Users can't say "don't learn from this" or "forget that."

**What's Lost:**
- User trust
- GDPR compliance
- Ability to work on sensitive projects

**Solution:** PrivacyController class with:
- Path exclusions (`never_learn_from`)
- Sensitive pattern redaction (api_key, password, token)
- Temporary pause capability
- GDPR export/delete methods

---

### 22. No Active Learning

**The Problem:**
System is passive. Only observes, never asks questions to learn faster.

**What's Lost:**
- 10x learning velocity (asking removes guessing)
- Accuracy (direct answers vs inference)
- User engagement

**Solution:** ActiveLearner class with:
- Question budget per session
- Uncertainty × importance threshold
- Direct learning from answers (95% confidence)

---

### 23. No Goal Inference

**The Problem:**
We learn WHAT user prefers but not WHY. Understanding goals unlocks everything.

```
Surface: "User is impatient"
Reality: "User is under deadline pressure"
→ Completely different recommendations
```

**Solution:** GoalInferrer with hierarchy:
- Immediate: fix_bug, ship_feature, understand_code
- Session: complete_task, explore_options
- Project: build_mvp, build_production
- Meta: learn_to_code, increase_productivity

---

### 24. No Grounding / Evidence

**The Problem:**
Learnings are assertions without evidence. Can't explain WHY we think something.

**Solution:** EvidenceStore class:
- Store evidence for every learning
- Types: observation, statement, correction
- `explain_learning()` generates human-readable proof

---

### 25. No Effectiveness Measurement

**The Problem:**
No idea if learnings actually help. No metrics, no improvement tracking.

**Solution:** EffectivenessTracker:
- Record: time_to_complete, iterations_needed, corrections_needed
- Calculate improvement over time windows
- Identify useless learnings (old + never applied)

---

### 26. No Knowledge Graph

**The Problem:**
Learnings are flat. No relationships, no hierarchy.

```
Flat: [TypeScript, functional, no classes, immutability]
Connected: "Functional programming mindset" → implies more
```

**Solution:** KnowledgeGraph class:
- Nodes = learnings
- Edges = relationships (related_concept, implies, contradicts)
- Cluster detection → emergent patterns
- Inference from graph structure

---

### 27. No Mode Detection

**The Problem:**
User behavior changes by mode: exploring, building, debugging, shipping.

**Solution:** ModeDetector with modes:
- Exploring: show possibilities, high verbosity
- Building: working code, medium verbosity
- Debugging: diagnose first, high safety
- Shipping: minimal changes, very high safety
- Learning: educate first, very high verbosity

---

### 28. No Compositionality

**The Problem:**
Can't combine learnings to make new inferences.

```
TypeScript + functional + minimal deps
→ Should infer: "Would like fp-ts, dislike class-heavy frameworks"
```

**Solution:** CompositionalInferrer with rules:
- IF [prefers_typescript, prefers_functional] THEN would_like_fp-ts
- Combined confidence from sources

---

### 29. No Calibration

**The Problem:**
80% confident ≠ 80% accurate. Confidence is meaningless without calibration.

**Solution:** ConfidenceCalibrator:
- Record (stated_confidence, was_correct) pairs
- Build calibration curve
- Adjust future confidence toward historical accuracy
- Reliability score = 1 - avg_calibration_error

---

### 30. No Team/Shared Learning

**The Problem:**
Each user is isolated. Everyone relearns the same patterns.

**Solution:** SharedLearningHub:
- Export high-confidence, validated learnings (anonymized)
- Import with confidence discount (0.6x)
- Team patterns = intersection of team learnings

---

## The Final Gap Map

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        COMPLETE SPARK GAP ANALYSIS                              │
│                                                                                 │
│  CRITICAL (1-7)              HIGH (8-20)                  DEEP (21-30)         │
│  ─────────────               ────────────                 ─────────────         │
│  Session Amnesia             Reasoning Capture            Privacy Controls      │
│  Semantic Understanding      Failure Analysis             Active Learning       │
│  Project Blindness           User Mental Model            Goal Inference        │
│  Platform Lock               Skill Level Adaptation       Evidence/Grounding    │
│  Agent Isolation             Intention Inference          Effectiveness Metrics │
│  No Decay                    Self-Awareness               Knowledge Graph       │
│  Conflict Resolution         Style Matching               Mode Detection        │
│                              Temporal Patterns            Compositionality      │
│                              Unlearning                   Calibration           │
│                              Learning Transfer            Team/Shared Learning  │
│                                                                                 │
│  Total: 30 gaps identified                                                      │
│  All solutions: Pure Python, cross-platform, offline-capable                    │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Updated Priority Matrix

| Priority | Gap | Why |
|----------|-----|-----|
| P0 | Session Bootstrap | Nothing works without this |
| P0 | Privacy Controls | Trust and compliance |
| P1 | Goal Inference | Unlocks deep understanding |
| P1 | Active Learning | 10x learning velocity |
| P1 | Evidence/Grounding | Explainability and trust |
| P1 | Effectiveness Metrics | Know if it's working |
| P2 | Mode Detection | Better context-aware responses |
| P2 | Knowledge Graph | Emergent insights |
| P2 | Calibration | Meaningful confidence |
| P2 | Compositionality | Inference power |
| P3 | Team Learning | Knowledge sharing |

## What Makes This Truly Complete

With all 30 gaps addressed, Spark would:

1. **Respect privacy** while learning effectively
2. **Ask questions** to learn faster
3. **Understand goals** not just preferences
4. **Explain itself** with evidence
5. **Measure effectiveness** and improve
6. **Connect knowledge** into understanding
7. **Detect context** and adapt
8. **Compose learnings** into new insights
9. **Calibrate confidence** to reality
10. **Share knowledge** across users

This is the complete system.
