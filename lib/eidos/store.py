"""
EIDOS Store: SQLite Persistence Layer

The canonical memory - simple, inspectable, debuggable.

Tables:
- episodes: Bounded learning units
- steps: Decision packets (the core intelligence unit)
- distillations: Extracted rules (where intelligence lives)
- policies: Operating constraints

This is NOT where tool logs go. Tool logs are ephemeral evidence.
"""

import hashlib
import json
import os
import re
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import (
    Episode, Step, Distillation, Policy,
    Budget, Phase, Outcome, Evaluation, DistillationType, ActionType
)


def _normalize_distillation_statement(text: str) -> str:
    """Normalize statements so semantically identical distillations collapse."""
    s = (text or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    # Canonicalize budget percentage variants of the same heuristic.
    s = re.sub(
        r"when budget is \d+% used without progress",
        "when budget is <pct> used without progress",
        s,
    )
    return s


def _merge_unique_str(items_a: List[str], items_b: List[str]) -> List[str]:
    out: List[str] = []
    for item in (items_a or []) + (items_b or []):
        v = str(item or "").strip()
        if not v:
            continue
        if v not in out:
            out.append(v)
    return out


class EidosStore:
    """
    SQLite-based persistence for EIDOS intelligence primitives.

    Design principles:
    - Source of truth for all durable memory
    - Human-inspectable (just open the SQLite file)
    - Simple schema that maps directly to models
    - Indexes optimized for retrieval patterns
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the store.

        Args:
            db_path: Path to SQLite database. Defaults to ~/.spark/eidos.db
        """
        if db_path is None:
            spark_dir = Path.home() / ".spark"
            spark_dir.mkdir(exist_ok=True)
            db_path = str(spark_dir / "eidos.db")

        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                -- Episodes
                CREATE TABLE IF NOT EXISTS episodes (
                    episode_id TEXT PRIMARY KEY,
                    goal TEXT NOT NULL,
                    success_criteria TEXT,
                    constraints TEXT,  -- JSON
                    budget_max_steps INTEGER DEFAULT 25,
                    budget_max_time_seconds INTEGER DEFAULT 720,
                    budget_max_retries INTEGER DEFAULT 3,
                    phase TEXT DEFAULT 'explore',
                    outcome TEXT DEFAULT 'in_progress',
                    final_evaluation TEXT,
                    start_ts REAL,
                    end_ts REAL,
                    step_count INTEGER DEFAULT 0,
                    error_counts TEXT  -- JSON
                );

                -- Steps (the core intelligence unit)
                CREATE TABLE IF NOT EXISTS steps (
                    step_id TEXT PRIMARY KEY,
                    episode_id TEXT REFERENCES episodes(episode_id),
                    trace_id TEXT,

                    -- Before action
                    intent TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    alternatives TEXT,  -- JSON
                    assumptions TEXT,   -- JSON
                    prediction TEXT,
                    confidence_before REAL DEFAULT 0.5,

                    -- Action
                    action_type TEXT DEFAULT 'reasoning',
                    action_details TEXT,  -- JSON

                    -- After action
                    result TEXT,
                    evaluation TEXT DEFAULT 'unknown',
                    surprise_level REAL DEFAULT 0.0,
                    lesson TEXT,
                    confidence_after REAL DEFAULT 0.5,

                    -- Memory binding
                    retrieved_memories TEXT,  -- JSON
                    memory_cited INTEGER DEFAULT 0,
                    memory_useful INTEGER,

                    -- Validation
                    validated INTEGER DEFAULT 0,
                    validation_method TEXT,

                    created_at REAL DEFAULT (strftime('%s', 'now'))
                );

                -- Distillations (where intelligence lives)
                CREATE TABLE IF NOT EXISTS distillations (
                    distillation_id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    statement TEXT NOT NULL,
                    domains TEXT,       -- JSON
                    triggers TEXT,      -- JSON
                    anti_triggers TEXT, -- JSON

                    source_steps TEXT,  -- JSON
                    validation_count INTEGER DEFAULT 0,
                    contradiction_count INTEGER DEFAULT 0,
                    confidence REAL DEFAULT 0.5,

                    times_retrieved INTEGER DEFAULT 0,
                    times_used INTEGER DEFAULT 0,
                    times_helped INTEGER DEFAULT 0,

                    created_at REAL DEFAULT (strftime('%s', 'now')),
                    revalidate_by REAL
                );

                -- Policies (operating constraints)
                CREATE TABLE IF NOT EXISTS policies (
                    policy_id TEXT PRIMARY KEY,
                    statement TEXT NOT NULL,
                    scope TEXT DEFAULT 'GLOBAL',
                    priority INTEGER DEFAULT 50,
                    source TEXT DEFAULT 'INFERRED',
                    created_at REAL DEFAULT (strftime('%s', 'now'))
                );

                -- Indexes for efficient retrieval
                CREATE INDEX IF NOT EXISTS idx_steps_episode ON steps(episode_id);
                CREATE INDEX IF NOT EXISTS idx_steps_created ON steps(created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_steps_trace ON steps(trace_id);
                CREATE INDEX IF NOT EXISTS idx_distillations_type ON distillations(type);
                CREATE INDEX IF NOT EXISTS idx_distillations_confidence ON distillations(confidence DESC);
                CREATE INDEX IF NOT EXISTS idx_policies_scope ON policies(scope);
                CREATE INDEX IF NOT EXISTS idx_policies_priority ON policies(priority DESC);
            """)
            # Lightweight migration for existing databases.
            try:
                if not self._column_exists(conn, "steps", "trace_id"):
                    conn.execute("ALTER TABLE steps ADD COLUMN trace_id TEXT")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_steps_trace ON steps(trace_id)")
            except Exception:
                pass
            conn.commit()

    def _column_exists(self, conn: sqlite3.Connection, table: str, column: str) -> bool:
        try:
            rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
            return any(r[1] == column for r in rows)
        except Exception:
            return False

    def _fallback_trace_id(self, step: Step) -> str:
        raw = f"{step.step_id}|{step.episode_id}|{step.created_at}"
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]

    def _fallback_trace_id_fields(self, step_id: str, episode_id: str, created_at: float) -> str:
        raw = f"{step_id}|{episode_id}|{created_at}"
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]

    # ==================== Episode Operations ====================

    def save_episode(self, episode: Episode) -> str:
        """Save an episode to the database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO episodes (
                    episode_id, goal, success_criteria, constraints,
                    budget_max_steps, budget_max_time_seconds, budget_max_retries,
                    phase, outcome, final_evaluation, start_ts, end_ts,
                    step_count, error_counts
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                episode.episode_id,
                episode.goal,
                episode.success_criteria,
                json.dumps(episode.constraints),
                episode.budget.max_steps,
                episode.budget.max_time_seconds,
                episode.budget.max_retries_per_error,
                episode.phase.value,
                episode.outcome.value,
                episode.final_evaluation,
                episode.start_ts,
                episode.end_ts,
                episode.step_count,
                json.dumps(episode.error_counts)
            ))
            conn.commit()
        return episode.episode_id

    def get_episode(self, episode_id: str) -> Optional[Episode]:
        """Get an episode by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM episodes WHERE episode_id = ?",
                (episode_id,)
            ).fetchone()

            if not row:
                return None

            return Episode(
                episode_id=row["episode_id"],
                goal=row["goal"],
                success_criteria=row["success_criteria"] or "",
                constraints=json.loads(row["constraints"] or "[]"),
                budget=Budget(
                    max_steps=row["budget_max_steps"],
                    max_time_seconds=row["budget_max_time_seconds"],
                    max_retries_per_error=row["budget_max_retries"]
                ),
                phase=Phase(row["phase"]),
                outcome=Outcome(row["outcome"]),
                final_evaluation=row["final_evaluation"] or "",
                start_ts=row["start_ts"],
                end_ts=row["end_ts"],
                step_count=row["step_count"],
                error_counts=json.loads(row["error_counts"] or "{}")
            )

    def get_recent_episodes(self, limit: int = 10) -> List[Episode]:
        """Get most recent episodes."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM episodes ORDER BY start_ts DESC LIMIT ?",
                (limit,)
            ).fetchall()

            return [self._row_to_episode(row) for row in rows]

    def _row_to_episode(self, row: sqlite3.Row) -> Episode:
        """Convert a database row to Episode object."""
        return Episode(
            episode_id=row["episode_id"],
            goal=row["goal"],
            success_criteria=row["success_criteria"] or "",
            constraints=json.loads(row["constraints"] or "[]"),
            budget=Budget(
                max_steps=row["budget_max_steps"],
                max_time_seconds=row["budget_max_time_seconds"],
                max_retries_per_error=row["budget_max_retries"]
            ),
            phase=Phase(row["phase"]),
            outcome=Outcome(row["outcome"]),
            final_evaluation=row["final_evaluation"] or "",
            start_ts=row["start_ts"],
            end_ts=row["end_ts"],
            step_count=row["step_count"],
            error_counts=json.loads(row["error_counts"] or "{}")
        )

    # ==================== Step Operations ====================

    def save_step(self, step: Step) -> str:
        """Save a step to the database."""
        if not step.trace_id:
            step.trace_id = self._fallback_trace_id(step)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO steps (
                    step_id, episode_id, trace_id, intent, decision, alternatives, assumptions,
                    prediction, confidence_before, action_type, action_details,
                    result, evaluation, surprise_level, lesson, confidence_after,
                    retrieved_memories, memory_cited, memory_useful,
                    validated, validation_method, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                step.step_id,
                step.episode_id,
                step.trace_id,
                step.intent,
                step.decision,
                json.dumps(step.alternatives),
                json.dumps(step.assumptions),
                step.prediction,
                step.confidence_before,
                step.action_type.value,
                json.dumps(step.action_details),
                step.result,
                step.evaluation.value,
                step.surprise_level,
                step.lesson,
                step.confidence_after,
                json.dumps(step.retrieved_memories),
                1 if step.memory_cited else 0,
                1 if step.memory_useful else (0 if step.memory_useful is False else None),
                1 if step.validated else 0,
                step.validation_method,
                step.created_at
            ))
            conn.commit()
        return step.step_id

    def backfill_trace_ids(self, evidence_db_path: Optional[str] = None) -> Dict[str, int]:
        """
        Backfill missing trace_id values on steps using evidence where possible.

        Returns counts for observability.
        """
        evidence_map: Dict[str, str] = {}
        if evidence_db_path:
            try:
                with sqlite3.connect(evidence_db_path) as conn:
                    for row in conn.execute(
                        "SELECT step_id, trace_id FROM evidence WHERE trace_id IS NOT NULL AND trace_id != ''"
                    ):
                        step_id, trace_id = row[0], row[1]
                        if step_id and trace_id and step_id not in evidence_map:
                            evidence_map[step_id] = trace_id
            except Exception:
                pass

        updated = 0
        missing = 0
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT step_id, episode_id, created_at FROM steps WHERE trace_id IS NULL OR trace_id = ''"
            ).fetchall()
            missing = len(rows)
            for step_id, episode_id, created_at in rows:
                trace_id = evidence_map.get(step_id)
                if not trace_id:
                    trace_id = self._fallback_trace_id_fields(
                        step_id, episode_id or "", created_at or 0.0
                    )
                conn.execute(
                    "UPDATE steps SET trace_id = ? WHERE step_id = ?",
                    (trace_id, step_id),
                )
                updated += 1
            conn.commit()

        return {
            "steps_missing": missing,
            "steps_updated": updated,
        }

    def get_step(self, step_id: str) -> Optional[Step]:
        """Get a step by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM steps WHERE step_id = ?",
                (step_id,)
            ).fetchone()

            if not row:
                return None

            return self._row_to_step(row)

    def get_episode_steps(self, episode_id: str) -> List[Step]:
        """Get all steps for an episode."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM steps WHERE episode_id = ? ORDER BY created_at",
                (episode_id,)
            ).fetchall()

            return [self._row_to_step(row) for row in rows]

    def get_recent_steps(self, limit: int = 50) -> List[Step]:
        """Get most recent steps across all episodes."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM steps ORDER BY created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()

            return [self._row_to_step(row) for row in rows]

    def _row_to_step(self, row: sqlite3.Row) -> Step:
        """Convert a database row to Step object."""
        memory_useful = row["memory_useful"]
        if memory_useful is not None:
            memory_useful = bool(memory_useful)

        trace_id = row["trace_id"] if "trace_id" in row.keys() else None

        return Step(
            step_id=row["step_id"],
            episode_id=row["episode_id"],
            trace_id=trace_id,
            intent=row["intent"],
            decision=row["decision"],
            alternatives=json.loads(row["alternatives"] or "[]"),
            assumptions=json.loads(row["assumptions"] or "[]"),
            prediction=row["prediction"] or "",
            confidence_before=row["confidence_before"],
            action_type=ActionType(row["action_type"]),
            action_details=json.loads(row["action_details"] or "{}"),
            result=row["result"] or "",
            evaluation=Evaluation(row["evaluation"]),
            surprise_level=row["surprise_level"],
            lesson=row["lesson"] or "",
            confidence_after=row["confidence_after"],
            retrieved_memories=json.loads(row["retrieved_memories"] or "[]"),
            memory_cited=bool(row["memory_cited"]),
            memory_useful=memory_useful,
            validated=bool(row["validated"]),
            validation_method=row["validation_method"] or "",
            created_at=row["created_at"]
        )

    # ==================== Distillation Operations ====================

    def save_distillation(self, distillation: Distillation) -> str:
        """Save a distillation to the database with duplicate-statement collapsing."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            target_norm = _normalize_distillation_statement(distillation.statement)
            existing = None
            candidates = conn.execute(
                """SELECT * FROM distillations
                   WHERE type = ?""",
                (distillation.type.value,),
            ).fetchall()
            for row in candidates:
                if _normalize_distillation_statement(row["statement"] or "") == target_norm:
                    existing = row
                    break

            if existing:
                merged_domains = _merge_unique_str(
                    json.loads(existing["domains"] or "[]"),
                    distillation.domains,
                )
                merged_triggers = _merge_unique_str(
                    json.loads(existing["triggers"] or "[]"),
                    distillation.triggers,
                )
                merged_anti_triggers = _merge_unique_str(
                    json.loads(existing["anti_triggers"] or "[]"),
                    distillation.anti_triggers,
                )
                merged_source_steps = _merge_unique_str(
                    json.loads(existing["source_steps"] or "[]"),
                    distillation.source_steps,
                )

                merged_validation = int(existing["validation_count"] or 0) + int(distillation.validation_count or 0)
                merged_contradiction = int(existing["contradiction_count"] or 0) + int(distillation.contradiction_count or 0)
                merged_retrieved = int(existing["times_retrieved"] or 0) + int(distillation.times_retrieved or 0)
                merged_used = int(existing["times_used"] or 0) + int(distillation.times_used or 0)
                merged_helped = int(existing["times_helped"] or 0) + int(distillation.times_helped or 0)
                merged_confidence = max(float(existing["confidence"] or 0.0), float(distillation.confidence or 0.0))
                merged_created = min(float(existing["created_at"] or time.time()), float(distillation.created_at or time.time()))

                existing_revalidate = existing["revalidate_by"]
                if existing_revalidate is None:
                    merged_revalidate = distillation.revalidate_by
                elif distillation.revalidate_by is None:
                    merged_revalidate = existing_revalidate
                else:
                    merged_revalidate = max(float(existing_revalidate), float(distillation.revalidate_by))

                conn.execute(
                    """UPDATE distillations
                       SET statement = ?, domains = ?, triggers = ?, anti_triggers = ?,
                           source_steps = ?, validation_count = ?, contradiction_count = ?,
                           confidence = ?, times_retrieved = ?, times_used = ?, times_helped = ?,
                           created_at = ?, revalidate_by = ?
                       WHERE distillation_id = ?""",
                    (
                        str(existing["statement"] or distillation.statement),
                        json.dumps(merged_domains),
                        json.dumps(merged_triggers),
                        json.dumps(merged_anti_triggers),
                        json.dumps(merged_source_steps),
                        merged_validation,
                        merged_contradiction,
                        merged_confidence,
                        merged_retrieved,
                        merged_used,
                        merged_helped,
                        merged_created,
                        merged_revalidate,
                        str(existing["distillation_id"]),
                    ),
                )
                conn.commit()
                return str(existing["distillation_id"])

            conn.execute(
                """
                INSERT OR REPLACE INTO distillations (
                    distillation_id, type, statement, domains, triggers, anti_triggers,
                    source_steps, validation_count, contradiction_count, confidence,
                    times_retrieved, times_used, times_helped, created_at, revalidate_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    distillation.distillation_id,
                    distillation.type.value,
                    distillation.statement,
                    json.dumps(distillation.domains),
                    json.dumps(distillation.triggers),
                    json.dumps(distillation.anti_triggers),
                    json.dumps(distillation.source_steps),
                    distillation.validation_count,
                    distillation.contradiction_count,
                    distillation.confidence,
                    distillation.times_retrieved,
                    distillation.times_used,
                    distillation.times_helped,
                    distillation.created_at,
                    distillation.revalidate_by,
                ),
            )
            conn.commit()
        return distillation.distillation_id

    def get_distillation(self, distillation_id: str) -> Optional[Distillation]:
        """Get a distillation by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM distillations WHERE distillation_id = ?",
                (distillation_id,)
            ).fetchone()

            if not row:
                return None

            return self._row_to_distillation(row)

    def get_distillations_by_type(
        self,
        dtype: DistillationType,
        limit: int = 20
    ) -> List[Distillation]:
        """Get distillations of a specific type."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """SELECT * FROM distillations
                   WHERE type = ?
                   ORDER BY confidence DESC LIMIT ?""",
                (dtype.value, limit)
            ).fetchall()

            return [self._row_to_distillation(row) for row in rows]

    def get_high_confidence_distillations(
        self,
        min_confidence: float = 0.7,
        limit: int = 20
    ) -> List[Distillation]:
        """Get distillations above confidence threshold."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """SELECT * FROM distillations
                   WHERE confidence >= ?
                   ORDER BY confidence DESC LIMIT ?""",
                (min_confidence, limit)
            ).fetchall()

            return [self._row_to_distillation(row) for row in rows]

    def get_distillations_for_revalidation(self) -> List[Distillation]:
        """Get distillations due for revalidation."""
        now = time.time()
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """SELECT * FROM distillations
                   WHERE revalidate_by IS NOT NULL AND revalidate_by <= ?""",
                (now,)
            ).fetchall()

            return [self._row_to_distillation(row) for row in rows]

    def get_distillations_by_trigger(
        self,
        trigger: str,
        limit: int = 20
    ) -> List[Distillation]:
        """Get distillations that match a trigger pattern."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            # Search in JSON triggers array
            rows = conn.execute(
                """SELECT * FROM distillations
                   WHERE triggers LIKE ?
                   ORDER BY confidence DESC, times_used DESC LIMIT ?""",
                (f'%{trigger}%', limit)
            ).fetchall()

            return [self._row_to_distillation(row) for row in rows]

    def get_distillations_by_domain(
        self,
        domain: str,
        limit: int = 20
    ) -> List[Distillation]:
        """Get distillations for a specific domain."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """SELECT * FROM distillations
                   WHERE domains LIKE ?
                   ORDER BY confidence DESC, times_used DESC LIMIT ?""",
                (f'%{domain}%', limit)
            ).fetchall()

            return [self._row_to_distillation(row) for row in rows]

    def get_all_distillations(self, limit: int = 100) -> List[Distillation]:
        """Get all distillations ordered by confidence."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """SELECT * FROM distillations
                   ORDER BY confidence DESC, times_used DESC LIMIT ?""",
                (limit,)
            ).fetchall()

            return [self._row_to_distillation(row) for row in rows]

    def record_distillation_retrieval(self, distillation_id: str):
        """Record that a distillation was retrieved."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """UPDATE distillations
                   SET times_retrieved = times_retrieved + 1
                   WHERE distillation_id = ?""",
                (distillation_id,)
            )
            conn.commit()

    def find_distillation_by_prefix(self, id_prefix: str) -> Optional[str]:
        """Find a distillation ID by its prefix (used for outcome routing).

        The advisor stores truncated IDs (8 chars) in insight_keys.
        This resolves the full ID for usage tracking.
        """
        if not id_prefix or len(id_prefix) < 6:
            return None
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    "SELECT distillation_id FROM distillations WHERE distillation_id LIKE ?",
                    (id_prefix + "%",)
                ).fetchone()
                return row[0] if row else None
        except Exception:
            return None

    def record_distillation_usage(self, distillation_id: str, helped: bool):
        """Record that a distillation was used and whether it helped.

        Also applies confidence decay: when contradiction rate exceeds 80%
        over 10+ uses, confidence drops by 0.05 per contradiction.
        Distillations with confidence < 0.1 are effectively dead.
        """
        with sqlite3.connect(self.db_path) as conn:
            if helped:
                conn.execute(
                    """UPDATE distillations
                       SET times_used = times_used + 1,
                           times_helped = times_helped + 1,
                           validation_count = validation_count + 1
                       WHERE distillation_id = ?""",
                    (distillation_id,)
                )
            else:
                conn.execute(
                    """UPDATE distillations
                       SET times_used = times_used + 1,
                           contradiction_count = contradiction_count + 1
                       WHERE distillation_id = ?""",
                    (distillation_id,)
                )

            # Confidence decay: check if this distillation has a bad track record
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT times_used, times_helped, contradiction_count, confidence "
                "FROM distillations WHERE distillation_id = ?",
                (distillation_id,)
            ).fetchone()

            if row and row["times_used"] >= 10:
                total = row["times_used"]
                contra = row["contradiction_count"]
                contra_rate = contra / max(total, 1)

                if contra_rate > 0.8:
                    # High contradiction rate — decay confidence
                    new_conf = max(0.05, row["confidence"] - 0.05)
                    conn.execute(
                        "UPDATE distillations SET confidence = ? WHERE distillation_id = ?",
                        (round(new_conf, 3), distillation_id)
                    )

            conn.commit()

    def _row_to_distillation(self, row: sqlite3.Row) -> Distillation:
        """Convert a database row to Distillation object."""
        return Distillation(
            distillation_id=row["distillation_id"],
            type=DistillationType(row["type"]),
            statement=row["statement"],
            domains=json.loads(row["domains"] or "[]"),
            triggers=json.loads(row["triggers"] or "[]"),
            anti_triggers=json.loads(row["anti_triggers"] or "[]"),
            source_steps=json.loads(row["source_steps"] or "[]"),
            validation_count=row["validation_count"],
            contradiction_count=row["contradiction_count"],
            confidence=row["confidence"],
            times_retrieved=row["times_retrieved"],
            times_used=row["times_used"],
            times_helped=row["times_helped"],
            created_at=row["created_at"],
            revalidate_by=row["revalidate_by"]
        )

    # ==================== Policy Operations ====================

    def save_policy(self, policy: Policy) -> str:
        """Save a policy to the database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO policies (
                    policy_id, statement, scope, priority, source, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                policy.policy_id,
                policy.statement,
                policy.scope,
                policy.priority,
                policy.source,
                policy.created_at
            ))
            conn.commit()
        return policy.policy_id

    def get_policy(self, policy_id: str) -> Optional[Policy]:
        """Get a policy by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM policies WHERE policy_id = ?",
                (policy_id,)
            ).fetchone()

            if not row:
                return None

            return self._row_to_policy(row)

    def get_policies_by_scope(
        self,
        scope: str = "GLOBAL",
        limit: int = 50
    ) -> List[Policy]:
        """Get policies by scope."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """SELECT * FROM policies
                   WHERE scope = ?
                   ORDER BY priority DESC LIMIT ?""",
                (scope, limit)
            ).fetchall()

            return [self._row_to_policy(row) for row in rows]

    def get_all_policies(self) -> List[Policy]:
        """Get all policies ordered by priority."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM policies ORDER BY priority DESC"
            ).fetchall()

            return [self._row_to_policy(row) for row in rows]

    def _row_to_policy(self, row: sqlite3.Row) -> Policy:
        """Convert a database row to Policy object."""
        return Policy(
            policy_id=row["policy_id"],
            statement=row["statement"],
            scope=row["scope"],
            priority=row["priority"],
            source=row["source"],
            created_at=row["created_at"]
        )

    # ==================== Statistics ====================

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        with sqlite3.connect(self.db_path) as conn:
            episode_count = conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
            step_count = conn.execute("SELECT COUNT(*) FROM steps").fetchone()[0]
            distillation_count = conn.execute("SELECT COUNT(*) FROM distillations").fetchone()[0]
            policy_count = conn.execute("SELECT COUNT(*) FROM policies").fetchone()[0]

            # Success rate
            success_episodes = conn.execute(
                "SELECT COUNT(*) FROM episodes WHERE outcome = 'success'"
            ).fetchone()[0]

            # High confidence distillations
            high_conf_distillations = conn.execute(
                "SELECT COUNT(*) FROM distillations WHERE confidence >= 0.7"
            ).fetchone()[0]

            return {
                "episodes": episode_count,
                "steps": step_count,
                "distillations": distillation_count,
                "policies": policy_count,
                "success_rate": success_episodes / episode_count if episode_count > 0 else 0,
                "high_confidence_distillations": high_conf_distillations,
                "db_path": self.db_path
            }

    def purge_telemetry_distillations(self, dry_run: bool = False, max_preview: int = 20) -> Dict[str, Any]:
        """Remove telemetry/primitive distillations from the EIDOS store."""
        from ..primitive_filter import is_primitive_text
        from ..promoter import is_operational_insight

        def _is_telemetry_distillation(text: str) -> bool:
            t = (text or "").strip()
            if not t:
                return False
            if is_primitive_text(t) or is_operational_insight(t):
                return True
            tl = t.lower()
            if "success rate" in tl:
                return True
            if re.search(r"over\s+\d+\s+uses", tl):
                return True
            if "sequence" in tl and "->" in t:
                return True
            return False

        removed_ids: List[str] = []
        preview: List[str] = []

        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT distillation_id, statement FROM distillations"
            ).fetchall()
            for row in rows:
                dist_id = row[0]
                statement = row[1] or ""
                if _is_telemetry_distillation(statement):
                    removed_ids.append(dist_id)
                    if len(preview) < max_preview:
                        preview.append(statement[:200])

            if not dry_run and removed_ids:
                conn.executemany(
                    "DELETE FROM distillations WHERE distillation_id = ?",
                    [(rid,) for rid in removed_ids]
                )

        return {
            "scanned": len(rows),
            "removed": len(removed_ids),
            "preview": preview,
            "dry_run": dry_run,
        }


# Singleton instance
_store: Optional[EidosStore] = None


def get_store(db_path: Optional[str] = None) -> EidosStore:
    """Get the singleton store instance."""
    global _store
    if _store is None or (db_path and _store.db_path != db_path):
        _store = EidosStore(db_path)
    return _store


def purge_telemetry_distillations(dry_run: bool = False, max_preview: int = 20) -> Dict[str, Any]:
    """Purge telemetry/primitive distillations from the EIDOS store."""
    store = get_store()
    return store.purge_telemetry_distillations(dry_run=dry_run, max_preview=max_preview)
