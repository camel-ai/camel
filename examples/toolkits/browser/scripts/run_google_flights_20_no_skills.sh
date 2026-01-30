#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$ROOT_DIR"

EXAMPLE_ROOT="$ROOT_DIR/toolkits/browser/browser_skills_example"

JSONL="${1:-$ROOT_DIR/toolkits/browser/data/WebVoyager_data.jsonl}"
SKILLS_ROOT="${SKILLS_ROOT:-$EXAMPLE_ROOT/skills_store}"
OUT_DIR="${OUT_DIR:-$ROOT_DIR/toolkits/session_logs}"
MAX_RETRIES="${MAX_RETRIES:-0}"
MAX_ATTEMPTS_PER_TASK="${MAX_ATTEMPTS_PER_TASK:-}"
STEP_TIMEOUT="${STEP_TIMEOUT:-600}"
TOOL_TIMEOUT="${TOOL_TIMEOUT:-180}"
START_INDEX="${START_INDEX:-5}"
MAX_TASKS="${MAX_TASKS:-20}"

if [[ -z "$MAX_ATTEMPTS_PER_TASK" ]]; then
  MAX_ATTEMPTS_PER_TASK="$((MAX_RETRIES + 1))"
fi

mkdir -p "$OUT_DIR" "$SKILLS_ROOT" "$ROOT_DIR/.tmp/uv-cache"

echo "JSONL:        $JSONL"
echo "SKILLS_ROOT:  $SKILLS_ROOT (not used, skills disabled)"
echo "OUT_DIR:      $OUT_DIR"
echo "START_INDEX:  $START_INDEX"
echo "MAX_TASKS:    $MAX_TASKS"
echo "MAX_ATTEMPTS_PER_TASK: $MAX_ATTEMPTS_PER_TASK"
echo "STEP_TIMEOUT: $STEP_TIMEOUT"
echo "TOOL_TIMEOUT: $TOOL_TIMEOUT"
echo "SKILLS:       DISABLED (agent will use browser tools only)"
echo
echo "Note: Requires Chrome/Chromium running with CDP on :9223 (and model env vars configured)."
echo

PYTHONUNBUFFERED=1 \
python -m examples.toolkits.browser.browser_skills_example.cli.run_webvoyager_tasks \
  --jsonl "$JSONL" \
  --skills-root "$SKILLS_ROOT" \
  --website-filter "Google Flights" \
  --start "$START_INDEX" \
  --max-tasks "$MAX_TASKS" \
  --max-attempts-per-task "$MAX_ATTEMPTS_PER_TASK" \
  --step-timeout "$STEP_TIMEOUT" \
  --tool-timeout "$TOOL_TIMEOUT" \
  --out-dir "$OUT_DIR" \
  --disable-skills

echo
echo "Done."
echo "Outputs are under: $OUT_DIR/session_<timestamp>/"
