import subprocess, os, time
from pathlib import Path

spark = Path.home() / ".spark"
prompt_file = spark / "llm_prompt.txt" 
response_file = spark / "llm_response.txt"

prompt_file.write_text("say just the word OK", encoding="utf-8")
if response_file.exists():
    response_file.unlink()

# Use 'start /wait' to create a new console window
cmd = f'start /wait /min cmd /c "set /p P=<{prompt_file} & claude -p --output-format text "%P%" > {response_file} 2>nul"'
print(f"Running: {cmd}")

r = subprocess.run(cmd, shell=True, timeout=60, capture_output=True, text=True)
print(f"Exit: {r.returncode}")

time.sleep(1)
if response_file.exists():
    resp = response_file.read_text(encoding="utf-8").strip()
    print(f"Response: [{resp}]")
else:
    print("No response file created")
