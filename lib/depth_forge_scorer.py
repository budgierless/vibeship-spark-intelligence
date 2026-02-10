"""Forge dual-scoring for DEPTH training sessions.

Uses Opus 4.6 (claude -p) and GPT 5.3 Codex (codex exec) to blind-score
each depth's answer, then reconciles into consensus scores. Replaces phi4-mini
scores with calibrated dual-model consensus before the learning pipeline.

Adapted from spark-forge (spark_forge/scorers/cli_opus.py, cli_codex.py,
reconciler.py, tendencies.py, parsing.py). Self-contained — no spark-forge import.

Usage:
    from lib.depth_forge_scorer import score_session

    forge = await score_session(
        steps=result.steps, topic="caching", domain="api_data_flow", mode="vibe",
    )
    # forge["rescored_steps"][i] has consensus score + dimensions + metadata
"""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEPTH_DIMENSIONS = ("actionability", "specificity", "tradeoff_awareness", "real_world_fit")

_LEVEL_NAMES = {
    1: "GROUND", 2: "DECOMPOSE", 3: "COMPARE", 4: "BREAK", 5: "OPTIMIZE",
    6: "EDGE", 7: "EMPATHIZE", 8: "SCALE", 9: "INTEGRATE", 10: "SIMPLIFY",
    11: "TEACH", 12: "PREDICT", 13: "INVENT", 14: "CRITIQUE", 15: "SYNTHESIZE",
}

_LEVEL_SKILLS = {
    1: "Define precisely", 2: "Architect the parts", 3: "Tradeoff analysis",
    4: "Attack the boundaries", 5: "Profile and optimize", 6: "Edge case exposure",
    7: "User empathy", 8: "Scale thinking", 9: "System integration",
    10: "Radical simplification", 11: "Teach it", 12: "Predict change",
    13: "Invent the approach", 14: "Self-critique", 15: "Extract the principle",
}

_CONCURRENCY = 4  # max parallel CLI subprocesses
_OPUS_TIMEOUT = 300
_CODEX_TIMEOUT = 300
_MAX_RETRIES = 3

# ---------------------------------------------------------------------------
# Scoring prompt — calibrated anchors at 3/5/7/9 per dimension
# ---------------------------------------------------------------------------

_SCORING_PROMPT = """\
You are evaluating an engineering reasoning answer on 4 dimensions. Score 1-10. Use the FULL range.

## Context
Domain: {domain} | Topic: {topic} | Level: {depth}/{max_depth} ({level_name} — {skill})

## Question
{question}

## Answer
{answer}

## Scoring Dimensions with Calibration Anchors

### Actionability (Can someone actually DO this?)
- 3/10: Vague suggestions ("consider responsive design")
- 5/10: General steps without specifics ("use media queries")
- 7/10: Concrete steps with named tools ("use clamp() with min 16px, preferred 1.5vw")
- 9/10: Copy-paste ready with exact values and error handling

### Specificity (Does it name real things?)
- 3/10: Generic terms only ("use a framework")
- 5/10: Names a tool but no config ("use Tailwind")
- 7/10: Specific APIs, config values, exact syntax
- 9/10: Production-grade specifics with edge cases, fallbacks

### Tradeoff Awareness (Does it acknowledge costs?)
- 3/10: Presents solution as purely beneficial
- 5/10: Mentions "tradeoffs exist" without naming them
- 7/10: Names 2+ specific tradeoffs with reasoning
- 9/10: Quantified tradeoffs, decision framework, when each approach wins

### Real-World Fit (Would this work in production?)
- 3/10: Textbook answer ignoring operational reality
- 5/10: Viable but assumes ideal conditions
- 7/10: Accounts for team, deadlines, existing codebase
- 9/10: Battle-tested advice with migration paths, monitoring, rollback

## Rules
- DO NOT default to 7. Verify the answer actually meets the 7/10 criteria above.
- Scores of 9-10 should be RARE — only when the answer truly meets those anchors.
- Each dimension is independent.

## Output (strict JSON, nothing else)
{{"dimensions": {{"actionability": {{"score": N, "strength": "...", "gap": "..."}}, "specificity": {{"score": N, "strength": "...", "gap": "..."}}, "tradeoff_awareness": {{"score": N, "strength": "...", "gap": "..."}}, "real_world_fit": {{"score": N, "strength": "...", "gap": "..."}}}}, "overall_score": N, "verdict": "1-2 sentences"}}"""

_CODEX_WRAPPER = """\
You are an engineering quality evaluator. Do NOT execute any commands or modify any files.
Your ONLY task is to read the evaluation prompt below and output a JSON object as your final response.
Do not use any tools. Just respond with the JSON scoring object.

---

{prompt}"""

# ---------------------------------------------------------------------------
# JSON parsing (adapted from spark-forge parsing.py)
# ---------------------------------------------------------------------------


def parse_depth_scorer_json(raw: str) -> Dict[str, Any]:
    """Extract and normalize a DEPTH scoring JSON from raw scorer output."""
    payload = _extract_json(raw)

    raw_dims = payload.get("dimensions")
    if not isinstance(raw_dims, dict):
        raise ValueError("Missing 'dimensions' object in scorer output")

    normalized: Dict[str, Dict[str, Any]] = {}
    for dim in DEPTH_DIMENSIONS:
        dp = raw_dims.get(dim, {})
        if not isinstance(dp, dict):
            dp = {}
        normalized[dim] = {
            "score": _normalize_score(dp.get("score")),
            "strength": str(dp.get("strength", "")).strip(),
            "gap": str(dp.get("gap", "")).strip(),
        }

    overall = payload.get("overall_score")
    if overall is None:
        scores = [normalized[d]["score"] for d in DEPTH_DIMENSIONS]
        overall = round(sum(scores) / len(scores), 1)
    else:
        overall = round(float(overall), 1)

    return {
        "dimensions": normalized,
        "overall_score": overall,
        "verdict": str(payload.get("verdict", "")).strip(),
    }


def _extract_json(raw_text: str) -> Dict[str, Any]:
    text = (raw_text or "").strip()
    if not text:
        raise ValueError("Empty scorer output")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < 0 or end <= start:
        raise ValueError("No JSON object found in scorer output")
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid scorer JSON: {exc}") from exc


def _normalize_score(value: Any) -> int:
    try:
        score = int(round(float(value)))
    except (TypeError, ValueError):
        score = 1
    return max(1, min(10, score))


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------


def build_scoring_prompt(
    question: str,
    answer: str,
    topic: str,
    depth: int,
    domain: str,
    mode: str = "vibe",
) -> str:
    max_depth = 15 if mode == "vibe" else 10
    level_name = _LEVEL_NAMES.get(depth, f"D{depth}")
    skill = _LEVEL_SKILLS.get(depth, "reasoning")
    return _SCORING_PROMPT.format(
        domain=domain,
        topic=topic,
        depth=depth,
        max_depth=max_depth,
        level_name=level_name,
        skill=skill,
        question=question,
        answer=answer,
    )


# ---------------------------------------------------------------------------
# CLI Scorers
# ---------------------------------------------------------------------------


class DepthOpusScorer:
    """Opus 4.6 scorer via locally-authenticated 'claude -p' CLI."""

    def __init__(self, model: str = "claude-opus-4-6", timeout: int = _OPUS_TIMEOUT):
        self._model = model
        self._timeout = timeout

    @property
    def model_id(self) -> str:
        return self._model

    async def score(self, prompt: str) -> Dict[str, Any]:
        last_exc: Optional[Exception] = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                raw = await self._invoke(prompt)
                return parse_depth_scorer_json(raw)
            except Exception as exc:
                last_exc = exc
                logger.warning("DepthOpusScorer attempt %d/%d failed: %s", attempt, _MAX_RETRIES, exc)
                if attempt < _MAX_RETRIES:
                    await asyncio.sleep(2 * attempt)
        raise RuntimeError(f"DepthOpusScorer failed after {_MAX_RETRIES} attempts") from last_exc

    async def _invoke(self, prompt: str) -> str:
        claude_bin = shutil.which("claude")
        if claude_bin is None:
            raise RuntimeError("claude CLI not found on PATH")
        cmd = [
            claude_bin, "-p",
            "--model", self._model,
            "--system-prompt", "Respond only with the JSON object. No preamble.",
            "--output-format", "text",
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(input=prompt.encode("utf-8")),
                timeout=self._timeout,
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise RuntimeError(f"claude CLI timed out after {self._timeout}s")

        if proc.returncode != 0:
            err = stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"claude CLI exited {proc.returncode}: {err}")
        return stdout.decode("utf-8", errors="replace")


class DepthCodexScorer:
    """GPT 5.3 Codex scorer via locally-authenticated 'codex exec' CLI."""

    def __init__(self, model: str = "gpt-5.3-codex", timeout: int = _CODEX_TIMEOUT):
        self._model = model
        self._timeout = timeout

    @property
    def model_id(self) -> str:
        return self._model

    async def score(self, prompt: str) -> Dict[str, Any]:
        last_exc: Optional[Exception] = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                raw = await self._invoke(prompt)
                return parse_depth_scorer_json(raw)
            except Exception as exc:
                last_exc = exc
                logger.warning("DepthCodexScorer attempt %d/%d failed: %s", attempt, _MAX_RETRIES, exc)
                if attempt < _MAX_RETRIES:
                    await asyncio.sleep(2 * attempt)
        raise RuntimeError(f"DepthCodexScorer failed after {_MAX_RETRIES} attempts") from last_exc

    async def _invoke(self, prompt: str) -> str:
        wrapped = _CODEX_WRAPPER.format(prompt=prompt)
        codex_bin = shutil.which("codex")
        if codex_bin is None:
            raise RuntimeError("codex CLI not found on PATH")

        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8")
        output_path = tmp.name
        tmp.close()

        try:
            cmd = [
                codex_bin, "exec",
                "--model", self._model,
                "--sandbox", "read-only",
                "--skip-git-repo-check",
                "-o", output_path,
            ]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(input=wrapped.encode("utf-8")),
                    timeout=self._timeout,
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                raise RuntimeError(f"codex CLI timed out after {self._timeout}s")

            if proc.returncode != 0:
                err = stderr.decode("utf-8", errors="replace").strip()
                raise RuntimeError(f"codex CLI exited {proc.returncode}: {err}")

            out_file = Path(output_path)
            if out_file.exists() and out_file.stat().st_size > 0:
                return out_file.read_text(encoding="utf-8")

            raw_stdout = stdout.decode("utf-8", errors="replace")
            if raw_stdout.strip():
                return raw_stdout

            raise RuntimeError("codex CLI produced no output")
        finally:
            Path(output_path).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Reconciler
# ---------------------------------------------------------------------------


class DepthReconciler:
    """Combine blind scores from Opus + Codex into consensus."""

    def __init__(self, disagreement_threshold: int = 2):
        self.threshold = disagreement_threshold

    def reconcile(
        self,
        scores_a: Dict[str, Any],
        scores_b: Dict[str, Any],
        model_a: str = "opus",
        model_b: str = "codex",
    ) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "consensus": {},
            "disagreements": [],
            "agreement_rate": 0.0,
            "confidence": "low",
        }
        agreements = 0.0

        for dim in DEPTH_DIMENSIONS:
            sa = int(scores_a["dimensions"][dim]["score"])
            sb = int(scores_b["dimensions"][dim]["score"])
            delta = abs(sa - sb)

            if delta <= 1:
                agreements += 1.0
                conf = "high"
            elif delta <= self.threshold:
                agreements += 0.5
                conf = "medium"
            else:
                conf = "low"
                result["disagreements"].append({
                    "dimension": dim,
                    f"{model_a}_score": sa,
                    f"{model_b}_score": sb,
                    "delta": delta,
                })

            consensus_score = round((sa + sb) / 2, 1)

            # Pick the richer strength/gap text
            str_a = scores_a["dimensions"][dim].get("strength", "")
            str_b = scores_b["dimensions"][dim].get("strength", "")
            gap_a = scores_a["dimensions"][dim].get("gap", "")
            gap_b = scores_b["dimensions"][dim].get("gap", "")

            result["consensus"][dim] = {
                "score": consensus_score,
                "confidence": conf,
                model_a: sa,
                model_b: sb,
                "strength": str_a if len(str_a) >= len(str_b) else str_b,
                "gap": gap_a if len(gap_a) >= len(gap_b) else gap_b,
            }

        result["agreement_rate"] = round(agreements / len(DEPTH_DIMENSIONS), 2)
        if result["agreement_rate"] >= 0.85:
            result["confidence"] = "high"
        elif result["agreement_rate"] >= 0.60:
            result["confidence"] = "medium"

        dim_scores = [result["consensus"][d]["score"] for d in DEPTH_DIMENSIONS]
        result["overall_score"] = round(sum(dim_scores) / len(dim_scores), 1)
        return result


# ---------------------------------------------------------------------------
# Tendency Store
# ---------------------------------------------------------------------------


class DepthTendencyStore:
    """Track scorer deltas over time in SQLite."""

    DEFAULT_DB = Path.home() / ".spark" / "depth_tendencies.db"

    def __init__(self, db_path: Path | str | None = None):
        self.db_path = Path(db_path) if db_path else self.DEFAULT_DB
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def record_session(
        self, *, session_id: str, created_at: str,
        model_a: str, model_b: str,
        scores_a: Dict[str, Any], scores_b: Dict[str, Any],
    ) -> None:
        rows = []
        for dim in DEPTH_DIMENSIONS:
            sa = int(scores_a["dimensions"][dim]["score"])
            sb = int(scores_b["dimensions"][dim]["score"])
            rows.append((session_id, created_at, model_a, model_b, dim, sa, sb, sa - sb))
        with sqlite3.connect(self.db_path) as conn:
            conn.executemany(
                "INSERT INTO scorer_tendencies "
                "(session_id, created_at, model_a, model_b, dimension, score_a, score_b, delta) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                rows,
            )
            conn.commit()

    def summarize(self, *, limit_sessions: int = 100) -> Dict[str, Dict[str, float]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            session_rows = conn.execute(
                "SELECT DISTINCT session_id FROM scorer_tendencies "
                "ORDER BY created_at DESC LIMIT ?",
                [limit_sessions],
            ).fetchall()
            session_ids = [r["session_id"] for r in session_rows]
            if not session_ids:
                return {}
            ph = ",".join("?" for _ in session_ids)
            rows = conn.execute(
                f"SELECT dimension, AVG(score_a) AS avg_a, AVG(score_b) AS avg_b, AVG(delta) AS avg_delta "
                f"FROM scorer_tendencies WHERE session_id IN ({ph}) GROUP BY dimension",
                session_ids,
            ).fetchall()
        summary: Dict[str, Dict[str, float]] = {}
        for r in rows:
            summary[r["dimension"]] = {
                "avg_opus": round(float(r["avg_a"]), 2),
                "avg_codex": round(float(r["avg_b"]), 2),
                "avg_delta_opus_minus_codex": round(float(r["avg_delta"]), 2),
            }
        return summary

    def _ensure_schema(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scorer_tendencies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    model_a TEXT NOT NULL,
                    model_b TEXT NOT NULL,
                    dimension TEXT NOT NULL,
                    score_a REAL NOT NULL,
                    score_b REAL NOT NULL,
                    delta REAL NOT NULL
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_dt_session ON scorer_tendencies(session_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_dt_created ON scorer_tendencies(created_at)"
            )
            conn.commit()


# ---------------------------------------------------------------------------
# Main entry point: score an entire session
# ---------------------------------------------------------------------------


async def score_session(
    steps: List[Dict[str, Any]],
    topic: str,
    domain: str,
    mode: str = "vibe",
) -> Dict[str, Any]:
    """Score all steps in a DEPTH training session with Opus + Codex dual scoring.

    Returns dict with:
        rescored_steps: list of dicts per depth with consensus scores + metadata
        agreement_rate: float (0-1)
        confidence: "high" | "medium" | "low"
        disagreements: list of dimension disagreements
        tendency_recorded: bool
    """
    opus = DepthOpusScorer()
    codex = DepthCodexScorer()
    reconciler = DepthReconciler()
    tendency = DepthTendencyStore()
    sem = asyncio.Semaphore(_CONCURRENCY)

    async def _score_one(scorer, prompt: str) -> Dict[str, Any]:
        async with sem:
            return await scorer.score(prompt)

    # Build prompts for each step
    prompts = []
    for step in steps:
        p = build_scoring_prompt(
            question=step.get("question", ""),
            answer=step.get("answer", ""),
            topic=topic,
            depth=step.get("depth", 1),
            domain=domain,
            mode=mode,
        )
        prompts.append(p)

    # Launch all scoring calls in parallel (Opus + Codex for each step)
    tasks = []
    for p in prompts:
        tasks.append(_score_one(opus, p))
        tasks.append(_score_one(codex, p))

    logger.info("Forge scoring %d depths with %s + %s (concurrency=%d)",
                len(steps), opus.model_id, codex.model_id, _CONCURRENCY)

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Pair up results: [opus_0, codex_0, opus_1, codex_1, ...]
    rescored_steps = []
    total_agreements = 0.0
    all_disagreements = []
    now = datetime.now(timezone.utc).isoformat()

    for i, step in enumerate(steps):
        opus_result = results[i * 2]
        codex_result = results[i * 2 + 1]

        # Handle failures — fall back to whichever succeeded, or keep phi4-mini score
        opus_ok = not isinstance(opus_result, BaseException)
        codex_ok = not isinstance(codex_result, BaseException)

        if opus_ok and codex_ok:
            consensus = reconciler.reconcile(opus_result, codex_result)
            score = consensus["overall_score"]
            dims = {d: consensus["consensus"][d] for d in DEPTH_DIMENSIONS}
            strengths = [consensus["consensus"][d].get("strength", "") for d in DEPTH_DIMENSIONS if consensus["consensus"][d].get("strength")]
            gaps = [consensus["consensus"][d].get("gap", "") for d in DEPTH_DIMENSIONS if consensus["consensus"][d].get("gap")]
            meta = {
                "scorer": "forge_dual",
                "opus_overall": opus_result["overall_score"],
                "codex_overall": codex_result["overall_score"],
                "agreement_rate": consensus["agreement_rate"],
                "confidence": consensus["confidence"],
            }
            total_agreements += consensus["agreement_rate"]
            all_disagreements.extend(consensus.get("disagreements", []))

            # Record tendency
            try:
                tendency.record_session(
                    session_id=f"depth_{step.get('depth', i)}_{now}",
                    created_at=now,
                    model_a=opus.model_id,
                    model_b=codex.model_id,
                    scores_a=opus_result,
                    scores_b=codex_result,
                )
            except Exception as exc:
                logger.warning("Tendency record failed for depth %d: %s", step.get("depth", i), exc)

        elif opus_ok:
            score = opus_result["overall_score"]
            dims = opus_result["dimensions"]
            strengths = [dims[d].get("strength", "") for d in DEPTH_DIMENSIONS if dims[d].get("strength")]
            gaps = [dims[d].get("gap", "") for d in DEPTH_DIMENSIONS if dims[d].get("gap")]
            meta = {"scorer": "opus_only", "opus_overall": score, "codex_error": str(codex_result)}
            logger.warning("Depth %d: Codex failed, using Opus only: %s", step.get("depth", i), codex_result)

        elif codex_ok:
            score = codex_result["overall_score"]
            dims = codex_result["dimensions"]
            strengths = [dims[d].get("strength", "") for d in DEPTH_DIMENSIONS if dims[d].get("strength")]
            gaps = [dims[d].get("gap", "") for d in DEPTH_DIMENSIONS if dims[d].get("gap")]
            meta = {"scorer": "codex_only", "codex_overall": score, "opus_error": str(opus_result)}
            logger.warning("Depth %d: Opus failed, using Codex only: %s", step.get("depth", i), opus_result)

        else:
            # Both failed — keep original phi4-mini score
            score = step.get("score", 5)
            dims = step.get("dimensions", {})
            strengths = step.get("strengths", [])
            gaps = step.get("gaps", [])
            meta = {"scorer": "phi4_fallback", "opus_error": str(opus_result), "codex_error": str(codex_result)}
            logger.error("Depth %d: Both scorers failed, keeping phi4-mini score", step.get("depth", i))

        rescored_steps.append({
            "depth": step.get("depth", i + 1),
            "score": score,
            "dimensions": dims,
            "strengths": strengths,
            "gaps": gaps,
            "metadata": meta,
        })

    avg_agreement = total_agreements / max(1, len(steps))
    if avg_agreement >= 0.85:
        overall_conf = "high"
    elif avg_agreement >= 0.60:
        overall_conf = "medium"
    else:
        overall_conf = "low"

    return {
        "rescored_steps": rescored_steps,
        "agreement_rate": round(avg_agreement, 2),
        "confidence": overall_conf,
        "disagreements": all_disagreements,
        "tendency_recorded": True,
    }
