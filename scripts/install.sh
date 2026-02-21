#!/bin/bash
# Spark Installation Script
# One-command setup for the self-evolving intelligence layer

set -e

SPARK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$SPARK_DIR/.venv"
CLAUDE_CONFIG_DIR="$HOME/.claude"
PYTHON_BIN="python3"

error_if_managed() {
  local code=$1
  local out=$2
  if [ "$code" -ne 0 ] && [ -f "$out" ] && grep -qi "externally-managed-environment" "$out" >/dev/null 2>&1; then
    return 0
  fi
  return 1
}

pip_install_editable() {
  local package_path=$1
  local err_file
  err_file="$(mktemp)"
  "$PYTHON_BIN" -m pip install -e "$package_path" --quiet 2>"$err_file"
  local code=$?
  if [ "$code" -eq 0 ]; then
    rm -f "$err_file"
    return 0
  fi

  if error_if_managed "$code" "$err_file"; then
    rm -f "$err_file"
    return 10
  fi

  cat "$err_file"
  rm -f "$err_file"
  return "$code"
}

ensure_venv() {
  if [ -n "${VIRTUAL_ENV:-}" ]; then
    return 0
  fi

  if [ -d "$VENV_DIR" ]; then
    # shellcheck disable=SC1090
    . "$VENV_DIR/bin/activate"
    PYTHON_BIN="python"
    return 0
  fi

  echo "Detected an externally-managed Python environment."
  echo "Creating local project virtual environment: $VENV_DIR"
  if ! python3 -m venv "$VENV_DIR"; then
    echo "Failed to create virtualenv. Install python3-venv and retry:"
    echo "  sudo apt-get install python3-venv"
    exit 1
  fi

  # shellcheck disable=SC1090
  . "$VENV_DIR/bin/activate"
  PYTHON_BIN="python"
  "$PYTHON_BIN" -m pip install --upgrade pip > /dev/null
}

echo "========================================"
echo "  SPARK - Self-Evolving Intelligence"
echo "========================================"
echo ""

# Check Python version
echo "Checking Python..."
if ! command -v python3 > /dev/null; then
  echo "Python 3 not found. Please install Python 3.10+"
  exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Python $PYTHON_VERSION found"

python3 - <<'PY'
import sys
if sys.version_info < (3, 10):
    raise SystemExit('Python 3.10+ required')
PY

# Install dependencies
echo ""
echo "Installing dependencies..."
if [ -f "$SPARK_DIR/pyproject.toml" ]; then
  code=0
  pip_install_editable "$SPARK_DIR"
  code=$?
  if [ "$code" -ne 0 ]; then
    if [ "$code" -ne 10 ]; then
      exit "$code"
    fi
    ensure_venv
    pip_install_editable "$SPARK_DIR" || exit $?
  fi
  echo "Core dependencies installed"
else
  "$PYTHON_BIN" -m pip install requests --quiet
  echo "Fallback dependency requests installed"
fi

# Optional: Install fastembed for embeddings
echo ""
read -r -p "Install embeddings support (fastembed)? [y/N]: " reply
echo ""
if [[ "$reply" =~ ^[Yy]$ ]]; then
  "$PYTHON_BIN" -m pip install fastembed --quiet
  echo "Embeddings enabled"
fi

# Create Spark config directory
echo ""
echo "Setting up Spark config..."
mkdir -p "$HOME/.spark"
echo "Config directory: ~/.spark"

# Set up Claude Code hooks (if Claude Code is installed)
if [ -d "$CLAUDE_CONFIG_DIR" ]; then
  echo ""
  read -r -p "Set up Claude Code hooks for auto-capture? [Y/n]: " hook_reply
  echo ""
  if [[ ! "$hook_reply" =~ ^[Nn]$ ]]; then
    cat > "$CLAUDE_CONFIG_DIR/spark-hooks.json" <<'HOOKS'
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": "python3 $SPARK_DIR/hooks/observe.py"
      }]
    }],
    "PostToolUseFailure": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": "python3 $SPARK_DIR/hooks/observe.py"
      }]
    }]
  }
}
HOOKS
    echo "Claude Code hooks configured"
    echo "  Note: Merge with your existing settings.json if you have custom hooks"
  fi
fi

# Test installation
echo ""
echo "Testing installation..."
cd "$SPARK_DIR"
if "$PYTHON_BIN" -m spark.cli health > /dev/null 2>&1; then
  echo "Spark is working!"
else
  echo "Some components may need configuration"
fi

# Print summary
echo ""
echo "========================================"
echo "  Installation Complete!"
echo "========================================"
echo ""
echo "Spark directory: $SPARK_DIR"
echo ""
echo "Quick start:"
echo "  cd $SPARK_DIR"
echo "  $PYTHON_BIN -m spark.cli status    # Check status"
echo "  $PYTHON_BIN -m spark.cli health    # Health check"
echo "  $PYTHON_BIN -m spark.cli learnings # View learnings"
echo ""
echo "For Mind integration (recommended):"
echo "  $PYTHON_BIN -m pip install vibeship-mind"
echo "  $PYTHON_BIN -m mind.lite_tier  # Start Mind server"
echo "  $PYTHON_BIN -m spark.cli sync   # Sync learnings"
echo ""
echo "Documentation: $SPARK_DIR/README.md"
echo ""
