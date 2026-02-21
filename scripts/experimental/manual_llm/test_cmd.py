import subprocess, os
from pathlib import Path

spark = Path.home() / ".spark"
prompt_file = spark / "llm_prompt.txt"
response_file = spark / "llm_response.txt"
script = r"<REPO_ROOT>\scripts\claude_call.cmd"

prompt_file.write_text("say just the word OK", encoding="utf-8")
if response_file.exists():
    response_file.unlink()

print("Calling via cmd.exe...")
r = subprocess.run(
    ["cmd", "/c", script, str(prompt_file), str(response_file)],
    capture_output=True, text=True, timeout=60,
)
print(f"Exit: {r.returncode}")
print(f"Stderr: {r.stderr[:200]}")

if response_file.exists():
    resp = response_file.read_text(encoding="utf-8").strip()
    print(f"Response: [{resp}]")
else:
    print("No response file!")

