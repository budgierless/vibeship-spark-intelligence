# Optimization Review Bundle

Generated: `2026-02-14T19:10:40Z`

Change: `chg-20260214-190824-advisory-quick-fallback-when-time-bu`

## Anti-hallucination rules

- Only make claims that are supported by the evidence below.
- When recommending code changes, cite: file path + function/line region.
- If unsure, ask for a command output instead of guessing.
- Prefer reversible/flagged changes. One commit per optimization.

## Git context

```json
{
  "is_git": true,
  "git_root": "C:\\Users\\USER\\Desktop\\vibeship-spark-intelligence",
  "branch": "main",
  "commit": "6ef84c24f4f27b2d9c463ec1a712b6b80e598db0",
  "describe": "6ef84c2-dirty",
  "dirty": true,
  "dirty_count": 3,
  "diff_stat": "OPTIMIZATION_CHECKER.md | 31 ++++++++++++++++++++\n lib/advisory_engine.py  | 76 +++++++++++++++++++++++++++++++++++++++++++------\n start_spark.bat         |  4 +++\n 3 files changed, 103 insertions(+), 8 deletions(-)"
}
```

## Change record

```json
{
  "schema": "optcheck.change.v1",
  "change_id": "chg-20260214-190824-advisory-quick-fallback-when-time-bu",
  "title": "Advisory: quick fallback when time budget is low",
  "status": "planned",
  "started_at": "2026-02-14T19:08:24Z",
  "commit": "",
  "snapshot_before": "",
  "snapshot_after": "",
  "hypothesis": "When live advisory is slow or budget is tight, a quick deterministic hint increases real-time advisory delivery + usage without adding latency.",
  "risk": "Low: uses baseline/quick advice only when remaining_ms is low; still gated + duplicate-suppressed; flagged.",
  "rollback": "git revert <sha>",
  "validation_today": "Run services; check advisories still appear; ensure no new crashes; check advisory_engine logs for route=live_quick.",
  "validation_next_days": "Monitor for increased delivered advisories with stable noise burden; ensure no spam via repeat cooldown."
}
```

## git diff --stat

```
 OPTIMIZATION_CHECKER.md | 31 ++++++++++++++++++++
 lib/advisory_engine.py  | 76 +++++++++++++++++++++++++++++++++++++++++++------
 start_spark.bat         |  4 +++
 3 files changed, 103 insertions(+), 8 deletions(-)

```

## git diff

```diff
diff --git a/OPTIMIZATION_CHECKER.md b/OPTIMIZATION_CHECKER.md
index 959742b..6821cfc 100644
--- a/OPTIMIZATION_CHECKER.md
+++ b/OPTIMIZATION_CHECKER.md
@@ -410,3 +410,34 @@ No issues; artifacts continue to be generated locally but not committed.
 - Day 3: 
 
 - Mark verified: [ ]
+
+### chg-20260214-190824-advisory-quick-fallback-when-time-bu — Advisory: quick fallback when time budget is low
+
+- Status: **PLANNED**
+- Started: `2026-02-14T19:08:24Z`
+- Commit: ``
+- Baseline snapshot: ``
+- After snapshot: ``
+
+**Hypothesis:**
+When live advisory is slow or budget is tight, a quick deterministic hint increases real-time advisory delivery + usage without adding latency.
+
+**Risk:**
+Low: uses baseline/quick advice only when remaining_ms is low; still gated + duplicate-suppressed; flagged.
+
+**Rollback:**
+git revert <sha>
+
+**Validation Today:**
+Run services; check advisories still appear; ensure no new crashes; check advisory_engine logs for route=live_quick.
+
+**Validation Next Days:**
+Monitor for increased delivered advisories with stable noise burden; ensure no spam via repeat cooldown.
+
+**Verification log:**
+- Day 0: 
+- Day 1: 
+- Day 2: 
+- Day 3: 
+
+- Mark verified: [ ]
diff --git a/lib/advisory_engine.py b/lib/advisory_engine.py
index b3dc472..13e5c9d 100644
--- a/lib/advisory_engine.py
+++ b/lib/advisory_engine.py
@@ -23,6 +23,14 @@ INCLUDE_MIND_IN_MEMORY = os.getenv("SPARK_ADVISORY_INCLUDE_MIND", "0") == "1"
 ENABLE_PREFETCH_QUEUE = os.getenv("SPARK_ADVISORY_PREFETCH_QUEUE", "1") != "0"
 ENABLE_INLINE_PREFETCH_WORKER = os.getenv("SPARK_ADVISORY_PREFETCH_INLINE", "1") != "0"
 PACKET_FALLBACK_EMIT_ENABLED = os.getenv("SPARK_ADVISORY_PACKET_FALLBACK_EMIT", "0") == "1"
+
+# When live advisory is running out of budget, emit a cheap deterministic hint
+# instead of returning no advice (increases real-time advisory delivery).
+LIVE_QUICK_FALLBACK_ENABLED = os.getenv("SPARK_ADVISORY_LIVE_QUICK_FALLBACK", "0") == "1"
+LIVE_QUICK_FALLBACK_MIN_REMAINING_MS = float(
+    os.getenv("SPARK_ADVISORY_LIVE_QUICK_MIN_REMAINING_MS", "900")
+)
+
 FALLBACK_RATE_GUARD_ENABLED = os.getenv("SPARK_ADVISORY_FALLBACK_RATE_GUARD", "1") != "0"
 FALLBACK_RATE_GUARD_MAX_RATIO = float(
     os.getenv("SPARK_ADVISORY_FALLBACK_RATE_MAX_RATIO", "0.55")
@@ -82,6 +90,8 @@ def apply_engine_config(cfg: Dict[str, Any]) -> Dict[str, List[str]]:
     global ENABLE_PREFETCH_QUEUE
     global ENABLE_INLINE_PREFETCH_WORKER
     global PACKET_FALLBACK_EMIT_ENABLED
+    global LIVE_QUICK_FALLBACK_ENABLED
+    global LIVE_QUICK_FALLBACK_MIN_REMAINING_MS
     global FALLBACK_RATE_GUARD_ENABLED
     global FALLBACK_RATE_GUARD_MAX_RATIO
     global FALLBACK_RATE_GUARD_WINDOW
@@ -128,6 +138,22 @@ def apply_engine_config(cfg: Dict[str, Any]) -> Dict[str, List[str]]:
         )
         applied.append("packet_fallback_emit_enabled")
 
+    if "live_quick_fallback_enabled" in cfg:
+        LIVE_QUICK_FALLBACK_ENABLED = _parse_bool(
+            cfg.get("live_quick_fallback_enabled"),
+            LIVE_QUICK_FALLBACK_ENABLED,
+        )
+        applied.append("live_quick_fallback_enabled")
+
+    if "live_quick_min_remaining_ms" in cfg:
+        try:
+            LIVE_QUICK_FALLBACK_MIN_REMAINING_MS = max(
+                100.0, min(5000.0, float(cfg.get("live_quick_min_remaining_ms")))
+            )
+            applied.append("live_quick_min_remaining_ms")
+        except Exception:
+            warnings.append("invalid_live_quick_min_remaining_ms")
+
     if "fallback_rate_guard_enabled" in cfg:
         FALLBACK_RATE_GUARD_ENABLED = _parse_bool(
             cfg.get("fallback_rate_guard_enabled"),
@@ -746,14 +772,48 @@ def on_pre_tool(
             packet_id = str(packet.get("packet_id") or "")
             advice_items = _packet_to_advice(packet)
         else:
-            advice_items = advise_on_tool(
-                tool_name,
-                tool_input or {},
-                context=state.user_intent,
-                include_mind=INCLUDE_MIND_IN_MEMORY,
-                trace_id=resolved_trace_id,
-            )
-            route = "live"
+            # If we're low on remaining budget, skip heavy retrieval and emit a
+            # cheap deterministic hint instead. This improves real-time advisory
+            # delivery (better than returning None due to slow paths).
+            elapsed_ms_pre = (time.time() * 1000.0) - start_ms
+            remaining_ms_pre = MAX_ENGINE_MS - elapsed_ms_pre
+            if LIVE_QUICK_FALLBACK_ENABLED and remaining_ms_pre < float(LIVE_QUICK_FALLBACK_MIN_REMAINING_MS):
+                try:
+                    from .advisor import Advice, get_quick_advice
+
+                    quick_text = (get_quick_advice(tool_name) or "").strip()
+                    if not quick_text:
+                        quick_text = _baseline_text(intent_family).strip()
+                    advice_items = [
+                        Advice(
+                            advice_id=f"quick_{tool_name.lower()}_0",
+                            insight_key="quick_fallback",
+                            text=quick_text,
+                            confidence=0.78,
+                            source="quick",
+                            context_match=0.78,
+                            reason=f"quick_fallback remaining_ms={int(remaining_ms_pre)}",
+                        )
+                    ]
+                    route = "live_quick"
+                except Exception:
+                    advice_items = advise_on_tool(
+                        tool_name,
+                        tool_input or {},
+                        context=state.user_intent,
+                        include_mind=INCLUDE_MIND_IN_MEMORY,
+                        trace_id=resolved_trace_id,
+                    )
+                    route = "live"
+            else:
+                advice_items = advise_on_tool(
+                    tool_name,
+                    tool_input or {},
+                    context=state.user_intent,
+                    include_mind=INCLUDE_MIND_IN_MEMORY,
+                    trace_id=resolved_trace_id,
+                )
+                route = "live"
         advice_source_counts = _advice_source_counts(advice_items)
 
         if not advice_items:
diff --git a/start_spark.bat b/start_spark.bat
index c8956be..64596aa 100644
--- a/start_spark.bat
+++ b/start_spark.bat
@@ -39,6 +39,10 @@ if "%SPARK_MEMORY_DELTA_MIN_SIM%"=="" set SPARK_MEMORY_DELTA_MIN_SIM=0.86
 REM Phase 3 advisory intelligence flags (overridable via environment).
 if "%SPARK_OUTCOME_PREDICTOR%"=="" set SPARK_OUTCOME_PREDICTOR=1
 
+REM Advisory: cheap fallback hint when time budget is low (improves real-time delivery).
+if "%SPARK_ADVISORY_LIVE_QUICK_FALLBACK%"=="" set SPARK_ADVISORY_LIVE_QUICK_FALLBACK=1
+if "%SPARK_ADVISORY_LIVE_QUICK_MIN_REMAINING_MS%"=="" set SPARK_ADVISORY_LIVE_QUICK_MIN_REMAINING_MS=900
+
 if "%SPARK_NO_MIND%"=="1" goto start_spark
 set MIND_PORT=%SPARK_MIND_PORT%
 if "%MIND_PORT%"=="" set MIND_PORT=8080

```
