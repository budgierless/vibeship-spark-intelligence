#!/usr/bin/env python3
"""Stress benchmark local Ollama models across Spark-style intelligence tasks."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
import json
import statistics
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple
from urllib import error, request


DEFAULT_MODELS = ("llama3.2:3b", "phi4-mini", "qwen2.5-coder:3b")
DEFAULT_API = "http://localhost:11434"


@dataclass(frozen=True)
class Scenario:
    name: str
    methodology: str
    prompt: str
    required_keywords: Tuple[str, ...] = ()
    forbidden_phrases: Tuple[str, ...] = ("we are given",)
    max_chars: int = 700
    must_be_json: bool = False
    json_keys: Tuple[str, ...] = ()


BASE_SCENARIOS: Tuple[Scenario, ...] = (
    Scenario(
        name="advisory_security",
        methodology="advisory",
        prompt=(
            "You are reviewing an auth endpoint bug report.\n"
            "Observed issues: user controls client-side role flags; logs contain raw JWT tokens.\n"
            "Give exactly 2 concrete remediation bullets. No preamble."
        ),
        required_keywords=("server-side", "redact"),
        max_chars=320,
    ),
    Scenario(
        name="semantic_rag_conflict",
        methodology="semantic_retrieval",
        prompt=(
            "Retrieved notes:\n"
            "R1 (old): 'skip auth middleware for internal tools'.\n"
            "R2 (new): 'all routes require auth middleware + token validation'.\n"
            "R3 (new): 'log hashed request IDs, never tokens'.\n"
            "Task: Return a short action plan that resolves conflict and references winning notes."
        ),
        required_keywords=("R2", "R3", "token"),
        max_chars=420,
    ),
    Scenario(
        name="keyword_trigger_guardrail",
        methodology="keyword_retrieval",
        prompt=(
            "Incoming command: `git push origin main` during release freeze.\n"
            "Give a 3-step guardrail checklist before any deploy. Keep it execution-ready."
        ),
        required_keywords=("rollback", "check", "approval"),
        max_chars=420,
    ),
    Scenario(
        name="chip_router_decision",
        methodology="chip_routing",
        prompt=(
            "Context: 'marketing budget dropped 40%, CAC rising, team asks for channel reallocation'.\n"
            "Available chips: marketing, biz-ops, bench-core, game_dev.\n"
            "Choose one primary chip, one fallback chip, and include confidence 0-1."
        ),
        required_keywords=("marketing", "confidence"),
        max_chars=420,
    ),
    Scenario(
        name="budget_half_no_progress",
        methodology="control_plane",
        prompt=(
            "Episode status: 60% budget used, no validated progress in last 4 steps.\n"
            "Give the immediate next action and one stop condition aligned with strict control-plane logic."
        ),
        required_keywords=("simplify", "validate"),
        max_chars=360,
    ),
    Scenario(
        name="noise_resilience",
        methodology="long_context_noise",
        prompt=(
            "Tool logs (noise): timeout timeout retry warning stacktrace repeated 120 times.\n"
            "Signal: 'database migration fails on missing index users_email_idx'.\n"
            "Output 2 lines only: root cause + next command to run."
        ),
        required_keywords=("index", "command"),
        max_chars=240,
    ),
    Scenario(
        name="json_contract",
        methodology="structured_output",
        prompt=(
            "Return JSON only for this incident triage.\n"
            "Required keys: risk, action, verify.\n"
            "Incident: secrets leaked in debug logs from auth middleware."
        ),
        required_keywords=("risk", "action", "verify"),
        must_be_json=True,
        json_keys=("risk", "action", "verify"),
        max_chars=420,
    ),
)


ACTION_WORDS = (
    "validate",
    "check",
    "redact",
    "review",
    "run",
    "add",
    "remove",
    "enforce",
    "block",
    "rollback",
    "verify",
    "set",
    "monitor",
    "limit",
    "require",
)


def parse_models(raw: str) -> List[str]:
    values = [m.strip() for m in raw.split(",") if m.strip()]
    return values or list(DEFAULT_MODELS)


def _extract_event_context(event: Dict[str, Any]) -> str:
    tool_input = event.get("tool_input")
    if isinstance(tool_input, dict):
        for key in ("prompt", "description", "command", "pattern", "file_path", "path"):
            val = tool_input.get(key)
            if val:
                return str(val)
    data = event.get("data")
    if isinstance(data, dict):
        payload = data.get("payload")
        if isinstance(payload, dict):
            text = payload.get("text")
            if text:
                return str(text)
    return ""


def _methodology_for_tool(tool_name: str) -> str:
    t = (tool_name or "").lower()
    if t in {"grep", "glob", "read"}:
        return "live_retrieval"
    if t in {"bash"}:
        return "live_execution"
    if t in {"edit", "write"}:
        return "live_editing"
    return "live_planning"


def _prompt_for_live_event(tool_name: str, ctx: str) -> str:
    return (
        "Live pipeline replay from Spark events.\n"
        f"Tool: {tool_name}\n"
        f"Observed context: {ctx}\n"
        "Provide concise next-step guidance optimized for correctness, speed, and usefulness.\n"
        "Output 2-4 bullets only."
    )


def load_live_scenarios(log_path: Path, limit: int) -> List[Scenario]:
    if limit <= 0 or not log_path.exists():
        return []

    allowed_tools = {"Task", "TaskUpdate", "Read", "Grep", "Glob", "Bash", "Edit", "Write"}
    per_tool_cap = max(1, limit // 4)
    per_tool_counts: Dict[str, int] = {}
    scenarios: List[Scenario] = []
    seen: set[str] = set()

    try:
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []

    for line in reversed(lines):
        if len(scenarios) >= limit:
            break
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("event_type") != "pre_tool":
            continue
        tool_name = str(event.get("tool_name") or "")
        if tool_name not in allowed_tools:
            continue
        tool_bucket = "Task" if tool_name in {"Task", "TaskUpdate"} else tool_name
        if per_tool_counts.get(tool_bucket, 0) >= per_tool_cap:
            continue
        raw_ctx = _extract_event_context(event).strip()
        if not raw_ctx:
            continue
        compact = " ".join(raw_ctx.split())
        if len(compact) < 25:
            continue
        compact = compact[:260]
        signature = f"{tool_bucket}:{compact.lower()}"
        if signature in seen:
            continue
        seen.add(signature)
        per_tool_counts[tool_bucket] = per_tool_counts.get(tool_bucket, 0) + 1
        methodology = _methodology_for_tool(tool_name)
        scenarios.append(
            Scenario(
                name=f"live_{methodology}_{len(scenarios) + 1}",
                methodology=methodology,
                prompt=_prompt_for_live_event(tool_name, compact),
                required_keywords=(),
                max_chars=420,
            )
        )

    return scenarios


def query_ollama(api: str, model: str, prompt: str, timeout_s: float) -> str:
    payload = {
        "model": model,
        "stream": False,
        "think": False,
        "messages": [
            {
                "role": "system",
                "content": "Provide concise, actionable answers. No problem restatement.",
            },
            {"role": "user", "content": prompt},
        ],
        "options": {
            "temperature": 0.2,
            "num_predict": 220,
        },
    }
    def _do_request() -> str:
        req = request.Request(
            f"{api.rstrip('/')}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        data = json.loads(raw)
        msg = data.get("message", {}) if isinstance(data, dict) else {}
        content = msg.get("content", "") if isinstance(msg, dict) else ""
        return str(content or "").strip()

    # Thread-wrapped timeout prevents indefinite socket hangs.
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(_do_request)
        try:
            return future.result(timeout=max(1.0, timeout_s + 0.25))
        except FuturesTimeoutError as e:
            raise TimeoutError("ollama_timeout") from e


def _score_speed(latency_ms: float, budget_ms: int, soft_budget_ms: int) -> float:
    if latency_ms <= budget_ms:
        return 100.0
    if latency_ms <= soft_budget_ms:
        return 80.0
    overflow = latency_ms - soft_budget_ms
    penalty = min(80.0, (overflow / max(500.0, float(soft_budget_ms))) * 100.0)
    return max(0.0, 80.0 - penalty)


def score_response(text: str, scenario: Scenario) -> Tuple[float, float, float, List[str], bool]:
    issues: List[str] = []
    intelligence = 100.0
    usefulness = 100.0
    lower = text.lower().strip()

    if not lower:
        return 0.0, 0.0, 0.0, ["empty_response"], False

    for phrase in scenario.forbidden_phrases:
        if phrase.lower() in lower:
            intelligence -= 25
            usefulness -= 20
            issues.append(f"forbidden_phrase:{phrase}")

    if len(text) > scenario.max_chars:
        intelligence -= 10
        usefulness -= 20
        issues.append(f"too_long:{len(text)}>{scenario.max_chars}")

    for kw in scenario.required_keywords:
        if kw.lower() not in lower:
            intelligence -= 12
            usefulness -= 8
            issues.append(f"missing_keyword:{kw}")

    if not any(word in lower for word in ACTION_WORDS):
        usefulness -= 20
        issues.append("low_actionability")

    json_ok = True
    if scenario.must_be_json:
        try:
            parsed = json.loads(text)
            if not isinstance(parsed, dict):
                json_ok = False
            else:
                for key in scenario.json_keys:
                    if key not in parsed:
                        json_ok = False
                        issues.append(f"missing_json_key:{key}")
        except json.JSONDecodeError:
            json_ok = False
            issues.append("invalid_json")
        if not json_ok:
            intelligence -= 35
            usefulness -= 15

    intelligence = max(0.0, intelligence)
    usefulness = max(0.0, usefulness)
    quality = round((0.65 * intelligence) + (0.35 * usefulness), 2)
    return intelligence, usefulness, quality, issues, json_ok


def run_suite(
    *,
    models: List[str],
    api: str,
    scenarios: List[Scenario],
    repeats: int,
    budget_ms: int,
    soft_budget_ms: int,
    intelligence_threshold: float,
    usefulness_threshold: float,
) -> Dict[str, Any]:
    started = datetime.now(timezone.utc).isoformat()
    results: List[Dict[str, Any]] = []
    summary: Dict[str, Dict[str, Any]] = {}
    methodology_summary: Dict[str, Dict[str, Dict[str, Any]]] = {}
    timeout_s = max(1.0, (soft_budget_ms / 1000.0) + 0.5)
    total_calls = max(1, len(models) * len(scenarios) * max(1, repeats))
    call_index = 0

    for model in models:
        summary[model] = {
            "runs": 0,
            "hard_budget_passes": 0,
            "soft_budget_passes": 0,
            "intelligence_passes": 0,
            "usefulness_passes": 0,
            "strict_passes": 0,
            "latencies_ms": [],
            "speed_scores": [],
            "intelligence_scores": [],
            "usefulness_scores": [],
            "quality_scores": [],
            "errors": 0,
        }
        for scenario in scenarios:
            methodology_summary.setdefault(scenario.methodology, {})
            methodology_summary[scenario.methodology].setdefault(
                model,
                {
                    "runs": 0,
                    "strict_passes": 0,
                    "hard_budget_passes": 0,
                    "soft_budget_passes": 0,
                    "speed_scores": [],
                    "intelligence_scores": [],
                    "usefulness_scores": [],
                    "quality_scores": [],
                },
            )
            for rep in range(1, repeats + 1):
                call_index += 1
                t0 = time.perf_counter()
                output = ""
                err_msg = ""
                failed = False
                try:
                    output = query_ollama(api, model, scenario.prompt, timeout_s=timeout_s)
                except error.URLError as e:
                    failed = True
                    err_msg = f"urlerror:{e.reason}"
                except TimeoutError:
                    failed = True
                    err_msg = "timeout"
                except Exception as e:  # pragma: no cover - runtime guard
                    failed = True
                    err_msg = f"error:{type(e).__name__}"
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                intelligence, usefulness, quality, issues, json_ok = score_response(output, scenario)
                hard_pass = elapsed_ms <= budget_ms
                soft_pass = elapsed_ms <= soft_budget_ms
                speed_score = _score_speed(elapsed_ms, budget_ms, soft_budget_ms)
                intelligence_pass = intelligence >= intelligence_threshold
                usefulness_pass = usefulness >= usefulness_threshold
                strict_pass = hard_pass and intelligence_pass and usefulness_pass and not failed

                if failed:
                    speed_score = 0.0
                    intelligence = 0.0
                    usefulness = 0.0
                    quality = 0.0
                    issues.append(err_msg)
                    hard_pass = False
                    soft_pass = False
                    intelligence_pass = False
                    usefulness_pass = False
                    strict_pass = False

                row = {
                    "model": model,
                    "scenario": scenario.name,
                    "methodology": scenario.methodology,
                    "repeat": rep,
                    "latency_ms": round(elapsed_ms, 2),
                    "hard_budget_pass": bool(hard_pass),
                    "soft_budget_pass": bool(soft_pass),
                    "speed_score": round(speed_score, 2),
                    "intelligence_score": round(intelligence, 2),
                    "usefulness_score": round(usefulness, 2),
                    "quality_score": round(quality, 2),
                    "intelligence_pass": bool(intelligence_pass),
                    "usefulness_pass": bool(usefulness_pass),
                    "strict_pass": bool(strict_pass),
                    "json_ok": bool(json_ok),
                    "issues": issues,
                    "output": output,
                    "error": err_msg or None,
                }
                results.append(row)

                m = summary[model]
                m["runs"] += 1
                m["hard_budget_passes"] += int(hard_pass)
                m["soft_budget_passes"] += int(soft_pass)
                m["intelligence_passes"] += int(intelligence_pass)
                m["usefulness_passes"] += int(usefulness_pass)
                m["strict_passes"] += int(strict_pass)
                m["latencies_ms"].append(elapsed_ms)
                m["speed_scores"].append(speed_score)
                m["intelligence_scores"].append(intelligence)
                m["usefulness_scores"].append(usefulness)
                m["quality_scores"].append(quality)
                m["errors"] += int(failed)

                ms = methodology_summary[scenario.methodology][model]
                ms["runs"] += 1
                ms["strict_passes"] += int(strict_pass)
                ms["hard_budget_passes"] += int(hard_pass)
                ms["soft_budget_passes"] += int(soft_pass)
                ms["speed_scores"].append(speed_score)
                ms["intelligence_scores"].append(intelligence)
                ms["usefulness_scores"].append(usefulness)
                ms["quality_scores"].append(quality)

                if (call_index % 10 == 0) or (call_index == total_calls):
                    print(
                        f"[progress] {call_index}/{total_calls} "
                        f"model={model} scenario={scenario.name} rep={rep}",
                        flush=True,
                    )

    for model, m in summary.items():
        runs = max(1, int(m["runs"]))
        latencies = m["latencies_ms"] or [0.0]
        speed = m["speed_scores"] or [0.0]
        intelligence = m["intelligence_scores"] or [0.0]
        usefulness = m["usefulness_scores"] or [0.0]
        quality = m["quality_scores"] or [0.0]
        m["hard_budget_pass_rate"] = round(m["hard_budget_passes"] / runs, 4)
        m["soft_budget_pass_rate"] = round(m["soft_budget_passes"] / runs, 4)
        m["intelligence_pass_rate"] = round(m["intelligence_passes"] / runs, 4)
        m["usefulness_pass_rate"] = round(m["usefulness_passes"] / runs, 4)
        m["strict_pass_rate"] = round(m["strict_passes"] / runs, 4)
        m["latency_avg_ms"] = round(statistics.mean(latencies), 2)
        m["latency_p95_ms"] = round(_percentile(latencies, 95), 2)
        m["speed_avg"] = round(statistics.mean(speed), 2)
        m["intelligence_avg"] = round(statistics.mean(intelligence), 2)
        m["usefulness_avg"] = round(statistics.mean(usefulness), 2)
        m["quality_avg"] = round(statistics.mean(quality), 2)
        del m["latencies_ms"]
        del m["speed_scores"]
        del m["intelligence_scores"]
        del m["usefulness_scores"]
        del m["quality_scores"]

    for methodology, by_model in methodology_summary.items():
        for model, ms in by_model.items():
            runs = max(1, int(ms["runs"]))
            ms["hard_budget_pass_rate"] = round(ms["hard_budget_passes"] / runs, 4)
            ms["soft_budget_pass_rate"] = round(ms["soft_budget_passes"] / runs, 4)
            ms["strict_pass_rate"] = round(ms["strict_passes"] / runs, 4)
            ms["speed_avg"] = round(statistics.mean(ms["speed_scores"] or [0.0]), 2)
            ms["intelligence_avg"] = round(statistics.mean(ms["intelligence_scores"] or [0.0]), 2)
            ms["usefulness_avg"] = round(statistics.mean(ms["usefulness_scores"] or [0.0]), 2)
            ms["quality_avg"] = round(statistics.mean(ms["quality_scores"] or [0.0]), 2)
            del ms["speed_scores"]
            del ms["intelligence_scores"]
            del ms["usefulness_scores"]
            del ms["quality_scores"]

    return {
        "started_at": started,
        "models": models,
        "api": api,
        "repeats": repeats,
        "budget_ms": budget_ms,
        "soft_budget_ms": soft_budget_ms,
        "intelligence_threshold": intelligence_threshold,
        "usefulness_threshold": usefulness_threshold,
        "scenario_count": len(scenarios),
        "summary": summary,
        "methodology_summary": methodology_summary,
        "results": results,
    }


def _percentile(values: List[float], pct: int) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    k = (len(ordered) - 1) * (pct / 100.0)
    f = int(k)
    c = min(f + 1, len(ordered) - 1)
    if f == c:
        return ordered[f]
    d0 = ordered[f] * (c - k)
    d1 = ordered[c] * (k - f)
    return d0 + d1


def print_summary(report: Dict[str, Any]) -> None:
    print("\n=== Local AI Stress Summary ===")
    print(f"models={','.join(report['models'])}")
    print(
        f"scenarios={report['scenario_count']} repeats={report['repeats']} "
        f"hard_budget={report['budget_ms']}ms soft_budget={report['soft_budget_ms']}ms"
    )
    for model, s in report["summary"].items():
        print(f"\n[{model}]")
        print(
            f"strict_pass={s['strict_pass_rate']:.1%} "
            f"hard_budget={s['hard_budget_pass_rate']:.1%} "
            f"soft_budget={s['soft_budget_pass_rate']:.1%} "
            f"intelligence_pass={s['intelligence_pass_rate']:.1%} "
            f"usefulness_pass={s['usefulness_pass_rate']:.1%}"
        )
        print(
            f"latency_avg={s['latency_avg_ms']}ms latency_p95={s['latency_p95_ms']}ms "
            f"speed_avg={s['speed_avg']} intelligence_avg={s['intelligence_avg']} "
            f"usefulness_avg={s['usefulness_avg']} quality_avg={s['quality_avg']} errors={s['errors']}"
        )

    print("\n=== By Methodology ===")
    for methodology, by_model in report.get("methodology_summary", {}).items():
        print(f"\n[{methodology}]")
        for model, s in by_model.items():
            print(
                f"  {model}: strict={s['strict_pass_rate']:.1%} hard={s['hard_budget_pass_rate']:.1%} "
                f"speed={s['speed_avg']} intelligence={s['intelligence_avg']} usefulness={s['usefulness_avg']}"
            )


def main() -> int:
    ap = argparse.ArgumentParser(description="Stress-test local Ollama models across Spark workloads.")
    ap.add_argument(
        "--models",
        default=",".join(DEFAULT_MODELS),
        help="Comma-separated Ollama models to benchmark",
    )
    ap.add_argument("--api", default=DEFAULT_API, help="Ollama API base URL")
    ap.add_argument("--repeats", type=int, default=3, help="Runs per scenario per model")
    ap.add_argument("--budget-ms", type=int, default=3000, help="Hard latency budget")
    ap.add_argument("--soft-budget-ms", type=int, default=3500, help="Soft latency budget")
    ap.add_argument("--intelligence-threshold", type=float, default=70.0, help="Minimum intelligence score")
    ap.add_argument("--usefulness-threshold", type=float, default=70.0, help="Minimum usefulness score")
    ap.add_argument(
        "--out",
        default=str(Path("benchmarks") / "out" / "local_model_stress_report.json"),
        help="Output JSON report path",
    )
    ap.add_argument(
        "--live-log",
        default=str(Path.home() / ".spark" / "queue" / "events.jsonl"),
        help="Path to live Spark events log used for dynamic scenarios",
    )
    ap.add_argument(
        "--live-scenarios",
        type=int,
        default=0,
        help="Number of additional scenarios synthesized from live events",
    )
    ap.add_argument("--dry-run", action="store_true", help="Print resolved config and exit")
    args = ap.parse_args()

    models = parse_models(args.models)
    base_scenarios = list(BASE_SCENARIOS)
    live_scenarios = load_live_scenarios(Path(args.live_log), max(0, int(args.live_scenarios)))
    all_scenarios = base_scenarios + live_scenarios
    if args.dry_run:
        print("Resolved config:")
        print(f"models={models}")
        print(f"api={args.api}")
        print(f"repeats={args.repeats}")
        print(f"budget_ms={args.budget_ms} soft_budget_ms={args.soft_budget_ms}")
        print(f"base_scenarios={len(base_scenarios)} live_scenarios={len(live_scenarios)} total={len(all_scenarios)}")
        return 0

    report = run_suite(
        models=models,
        api=args.api,
        scenarios=all_scenarios,
        repeats=max(1, int(args.repeats)),
        budget_ms=max(500, int(args.budget_ms)),
        soft_budget_ms=max(500, int(args.soft_budget_ms)),
        intelligence_threshold=float(args.intelligence_threshold),
        usefulness_threshold=float(args.usefulness_threshold),
    )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print_summary(report)
    print(f"\nreport={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
