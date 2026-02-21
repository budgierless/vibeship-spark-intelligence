import subprocess, time
from pathlib import Path

spark = Path.home() / ".spark"
prompt_file = spark / "llm_prompt.txt" 
response_file = spark / "llm_response.txt"
script = r"<REPO_ROOT>\scripts\claude_call.ps1"

prompt_file.write_text("What is 2+2? Reply with just the number.", encoding="utf-8")
if response_file.exists():
    response_file.unlink()

# start /wait /min launches a new console window (minimized) â€” this gives Claude its TTY
cmd = f'start /wait /min powershell -NoProfile -ExecutionPolicy Bypass -File "{script}" -PromptFile "{prompt_file}" -ResponseFile "{response_file}"'
print("Calling Claude via PowerShell bridge...")

r = subprocess.run(cmd, shell=True, timeout=60, capture_output=True, text=True)
print(f"Exit: {r.returncode}")

time.sleep(1)
if response_file.exists():
    resp = response_file.read_text(encoding="utf-8-sig").strip()
    print(f"Response: [{resp}]")
else:
    print("No response file created")

