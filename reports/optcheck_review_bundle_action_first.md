# Optimization Review Bundle

Generated: `2026-02-14T19:26:21Z`

Change: `chg-20260214-192454-advisory-action-first-formatting-nex`

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
  "commit": "fdb2e05fd57bc5d1a2e5cee2964556774cad791f",
  "describe": "fdb2e05-dirty",
  "dirty": true,
  "dirty_count": 3,
  "diff_stat": "OPTIMIZATION_CHECKER.md | 31 +++++++++++++++++++++++++++++++\n lib/advisory_engine.py  | 39 +++++++++++++++++++++++++++++++++++++++\n start_spark.bat         |  3 +++\n 3 files changed, 73 insertions(+)"
}
```

## Change record

```json
{
  "schema": "optcheck.change.v1",
  "change_id": "chg-20260214-192454-advisory-action-first-formatting-nex",
  "title": "Advisory: action-first formatting (Next check first line)",
  "status": "planned",
  "started_at": "2026-02-14T19:24:54Z",
  "commit": "",
  "snapshot_before": "",
  "snapshot_after": "",
  "hypothesis": "Putting the actionable Next check command first increases real-time advisory follow-through without increasing noise.",
  "risk": "Low: formatting-only; no new advice content; flagged.",
  "rollback": "git revert <sha>",
  "validation_today": "Trigger advisories; confirm format shows Next check first line; check duplicate suppression still works; ensure no crashes.",
  "validation_next_days": "Watch advice_followed rate + noise_burden; ensure no spam."
}
```

## git diff --stat

```
 OPTIMIZATION_CHECKER.md | 31 +++++++++++++++++++++++++++++++
 lib/advisory_engine.py  | 39 +++++++++++++++++++++++++++++++++++++++
 start_spark.bat         |  3 +++
 3 files changed, 73 insertions(+)

```

## git diff

```diff
diff --git a/OPTIMIZATION_CHECKER.md b/OPTIMIZATION_CHECKER.md
index 6821cfc..aa1aa8b 100644
--- a/OPTIMIZATION_CHECKER.md
+++ b/OPTIMIZATION_CHECKER.md
@@ -441,3 +441,34 @@ Monitor for increased delivered advisories with stable noise burden; ensure no s
 - Day 3: 
 
 - Mark verified: [ ]
+
+### chg-20260214-192454-advisory-action-first-formatting-nex — Advisory: action-first formatting (Next check first line)
+
+- Status: **PLANNED**
+- Started: `2026-02-14T19:24:54Z`
+- Commit: ``
+- Baseline snapshot: ``
+- After snapshot: ``
+
+**Hypothesis:**
+Putting the actionable Next check command first increases real-time advisory follow-through without increasing noise.
+
+**Risk:**
+Low: formatting-only; no new advice content; flagged.
+
+**Rollback:**
+git revert <sha>
+
+**Validation Today:**
+Trigger advisories; confirm format shows Next check first line; check duplicate suppression still works; ensure no crashes.
+
+**Validation Next Days:**
+Watch advice_followed rate + noise_burden; ensure no spam.
+
+**Verification log:**
+- Day 0: 
+- Day 1: 
+- Day 2: 
+- Day 3: 
+
+- Mark verified: [ ]
diff --git a/lib/advisory_engine.py b/lib/advisory_engine.py
index 13e5c9d..3d808ae 100644
--- a/lib/advisory_engine.py
+++ b/lib/advisory_engine.py
@@ -43,6 +43,10 @@ except Exception:
     FALLBACK_RATE_GUARD_WINDOW = 80
 MEMORY_SCOPE_DEFAULT = str(os.getenv("SPARK_MEMORY_SCOPE_DEFAULT", "session") or "session").strip() or "session"
 ACTIONABILITY_ENFORCE = os.getenv("SPARK_ADVISORY_REQUIRE_ACTION", "1") != "0"
+
+# Action-first formatting: move the actionable "Next check" command to the first line.
+ACTION_FIRST_ENABLED = os.getenv("SPARK_ADVISORY_ACTION_FIRST", "0") == "1"
+
 DELIVERY_STALE_SECONDS = float(os.getenv("SPARK_ADVISORY_STALE_S", "900"))
 ADVISORY_TEXT_REPEAT_COOLDOWN_S = float(
     os.getenv("SPARK_ADVISORY_TEXT_REPEAT_COOLDOWN_S", "1800")
@@ -526,6 +530,37 @@ def _ensure_actionability(text: str, tool_name: str, task_plane: str) -> Dict[st
     return {"text": updated, "added": True, "command": command}
 
 
+def _action_first_format(text: str) -> str:
+    """Move the `Next check: ` command to the first line.
+
+    This keeps the same content but makes the action visible instantly, which
+    tends to improve follow-through.
+
+    If no `Next check: ...` is present, returns the input unchanged.
+    """
+    body = str(text or "").strip()
+    if not body:
+        return ""
+
+    # Already action-first.
+    if body.lower().startswith("next check:"):
+        return body
+
+    m = re.search(r"\bnext check:\s*`([^`]{3,})`\.?", body, flags=re.IGNORECASE)
+    if not m:
+        return body
+
+    cmd = str(m.group(1) or "").strip()
+    if not cmd:
+        return body
+
+    # Remove the inline clause and clean punctuation.
+    cleaned = re.sub(r"\s*\bnext check:\s*`[^`]{3,}`\.?\s*", " ", body, flags=re.IGNORECASE)
+    cleaned = re.sub(r"\s+", " ", cleaned).strip()
+
+    return f"Next check: `{cmd}`.\n{cleaned}".strip()
+
+
 def _derive_delivery_badge(
     events: List[Dict[str, Any]],
     *,
@@ -887,6 +922,8 @@ def on_pre_tool(
             # Emit the fallback deterministic text
             action_meta = _ensure_actionability(fallback_text, tool_name, task_plane)
             fallback_text = str(action_meta.get("text") or fallback_text)
+            if ACTION_FIRST_ENABLED:
+                fallback_text = _action_first_format(fallback_text)
             fallback_guard = _fallback_guard_allows()
             if not fallback_guard.get("allowed"):
                 save_state(state)
@@ -1015,6 +1052,8 @@ def on_pre_tool(
 
         action_meta = _ensure_actionability(synth_text, tool_name, task_plane)
         synth_text = str(action_meta.get("text") or synth_text)
+        if ACTION_FIRST_ENABLED:
+            synth_text = _action_first_format(synth_text)
         repeat_meta = _duplicate_repeat_state(state, synth_text)
         if repeat_meta["repeat"]:
             if packet_id:
diff --git a/start_spark.bat b/start_spark.bat
index 64596aa..4153a2c 100644
--- a/start_spark.bat
+++ b/start_spark.bat
@@ -43,6 +43,9 @@ REM Advisory: cheap fallback hint when time budget is low (improves real-time de
 if "%SPARK_ADVISORY_LIVE_QUICK_FALLBACK%"=="" set SPARK_ADVISORY_LIVE_QUICK_FALLBACK=1
 if "%SPARK_ADVISORY_LIVE_QUICK_MIN_REMAINING_MS%"=="" set SPARK_ADVISORY_LIVE_QUICK_MIN_REMAINING_MS=900
 
+REM Advisory: action-first formatting (put Next check command on first line)
+if "%SPARK_ADVISORY_ACTION_FIRST%"=="" set SPARK_ADVISORY_ACTION_FIRST=1
+
 if "%SPARK_NO_MIND%"=="1" goto start_spark
 set MIND_PORT=%SPARK_MIND_PORT%
 if "%MIND_PORT%"=="" set MIND_PORT=8080

```
