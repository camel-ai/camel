#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$ROOT_DIR"

JSONL="${1:-$SCRIPT_DIR/WebVoyager_data.jsonl}"
SKILLS_ROOT="${SKILLS_ROOT:-$SCRIPT_DIR/skills_store}"
OUT_DIR="${OUT_DIR:-$ROOT_DIR/examples/toolkits/session_logs}"
MAX_RETRIES="${MAX_RETRIES:-4}"
MAX_ATTEMPTS_PER_TASK="${MAX_ATTEMPTS_PER_TASK:-}"
MAX_ATTEMPTS_PER_WEBSITE="${MAX_ATTEMPTS_PER_WEBSITE:-32}"
STEP_TIMEOUT="${STEP_TIMEOUT:-600}"
TOOL_TIMEOUT="${TOOL_TIMEOUT:-180}"
START_INDEX="${START_INDEX:-30}"
MAX_TASKS="${MAX_TASKS:-42}"

if [[ -z "$MAX_ATTEMPTS_PER_TASK" ]]; then
  MAX_ATTEMPTS_PER_TASK="$((MAX_RETRIES + 1))"
fi

mkdir -p "$OUT_DIR" "$SKILLS_ROOT" "$ROOT_DIR/.tmp/uv-cache"

echo "JSONL:        $JSONL"
echo "SKILLS_ROOT:  $SKILLS_ROOT"
echo "OUT_DIR:      $OUT_DIR"
echo "START_INDEX:  $START_INDEX"
echo "MAX_TASKS:    $MAX_TASKS"
echo "MAX_ATTEMPTS_PER_TASK: $MAX_ATTEMPTS_PER_TASK"
echo "MAX_ATTEMPTS_PER_WEBSITE: $MAX_ATTEMPTS_PER_WEBSITE"
echo "STEP_TIMEOUT: $STEP_TIMEOUT"
echo "TOOL_TIMEOUT: $TOOL_TIMEOUT"
echo
echo "Note: Requires Chrome/Chromium running with CDP on :9223 (and model env vars configured)."
echo

PYTHONUNBUFFERED=1 \
python "$SCRIPT_DIR/run_webvoyager_tasks.py" \
  --jsonl "$JSONL" \
  --skills-root "$SKILLS_ROOT" \
  --website-filter "Coursera" \
  --start "$START_INDEX" \
  --max-tasks "$MAX_TASKS" \
  --max-attempts-per-task "$MAX_ATTEMPTS_PER_TASK" \
  --max-attempts-per-website "$MAX_ATTEMPTS_PER_WEBSITE" \
  --step-timeout "$STEP_TIMEOUT" \
  --tool-timeout "$TOOL_TIMEOUT" \
  --out-dir "$OUT_DIR"

echo
echo "Done."
echo "Outputs are under: $OUT_DIR/session_<timestamp>/"
