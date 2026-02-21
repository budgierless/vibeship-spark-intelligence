#!/usr/bin/env python3
"""Test different subprocess approaches for Claude CLI on Windows."""
import subprocess, time

claude = r"<NPM_GLOBAL>\claude.cmd"
prompt = "say just the word OK"

# Test 1: shell=True
print("=== Test 1: shell=True ===")
try:
    r = subprocess.run(
        f'claude.cmd -p "{prompt}"',
        capture_output=True, text=True, timeout=30, shell=True
    )
    print(f"  code={r.returncode} out=[{r.stdout.strip()}] err=[{r.stderr.strip()[:100]}]")
except Exception as e:
    print(f"  ERROR: {e}")

# Test 2: cmd /c
print("=== Test 2: cmd /c ===")
try:
    r = subprocess.run(
        ["cmd", "/c", "claude.cmd", "-p", prompt],
        capture_output=True, text=True, timeout=30
    )
    print(f"  code={r.returncode} out=[{r.stdout.strip()}] err=[{r.stderr.strip()[:100]}]")
except Exception as e:
    print(f"  ERROR: {e}")

# Test 3: cmd /c with full path
print("=== Test 3: cmd /c full path ===")
try:
    r = subprocess.run(
        ["cmd", "/c", claude, "-p", prompt],
        capture_output=True, text=True, timeout=30
    )
    print(f"  code={r.returncode} out=[{r.stdout.strip()}] err=[{r.stderr.strip()[:100]}]")
except Exception as e:
    print(f"  ERROR: {e}")

# Test 4: node directly (claude is a node script)
print("=== Test 4: node ===")
try:
    # Find the actual JS file
    import os
    claude_dir = os.path.dirname(claude)
    # claude.cmd usually calls node with a .js file
    with open(claude, 'r') as f:
        content = f.read()
    print(f"  claude.cmd content: {content[:300]}")
except Exception as e:
    print(f"  ERROR: {e}")

print("\nDone")

