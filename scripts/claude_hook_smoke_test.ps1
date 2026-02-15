param(
  [string]$SessionId = "claude_hook_smoke_test",
  [string]$Cwd = (Get-Location).Path
)

$ErrorActionPreference = "Stop"

$sparkDir = Resolve-Path (Join-Path $PSScriptRoot "..") | Select-Object -ExpandProperty Path
$observePath = Join-Path $sparkDir "hooks\\observe.py"
if (!(Test-Path $observePath)) {
  throw "observe.py not found at: $observePath"
}

function Invoke-ObserveHook {
  param([hashtable]$Payload)
  $json = $Payload | ConvertTo-Json -Depth 10 -Compress
  $json | & python $observePath | Out-Null
}

# PreToolUse -> pre_tool
Invoke-ObserveHook @{
  hook_event_name = "PreToolUse"
  session_id = $SessionId
  cwd = $Cwd
  tool_name = "Bash"
  tool_input = @{ command = "echo spark-hook-smoke" }
}

# PostToolUse -> post_tool
Invoke-ObserveHook @{
  hook_event_name = "PostToolUse"
  session_id = $SessionId
  cwd = $Cwd
  tool_name = "Bash"
  tool_input = @{ command = "echo spark-hook-smoke" }
}

# PostToolUseFailure -> post_tool_failure
Invoke-ObserveHook @{
  hook_event_name = "PostToolUseFailure"
  session_id = $SessionId
  cwd = $Cwd
  tool_name = "Bash"
  tool_input = @{ command = "exit 1" }
  tool_error = "smoke-test: simulated tool failure"
}

# UserPromptSubmit -> user_prompt (portable payload shape)
Invoke-ObserveHook @{
  hook_event_name = "UserPromptSubmit"
  session_id = $SessionId
  cwd = $Cwd
  prompt = "[HOOK_SMOKE_TEST] If you see this, user prompts are being captured."
}

Write-Host "[spark] hook smoke test events emitted"
Write-Host "[spark] checking integration status..."
python -m lib.integration_status

