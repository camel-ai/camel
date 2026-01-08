#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

JSONL="${1:-$SCRIPT_DIR/WebVoyager_data.jsonl}"
SKILLS_ROOT="${SKILLS_ROOT:-$SCRIPT_DIR/skills_store}"
OUTPUT_DIR="${OUTPUT_DIR:-$SCRIPT_DIR/runs/run_$(date +%Y%m%d_%H%M%S)}"
MAX_RETRIES="${MAX_RETRIES:-2}"
STEP_TIMEOUT="${STEP_TIMEOUT:-600}"
TOOL_TIMEOUT="${TOOL_TIMEOUT:-180}"

mkdir -p "$OUTPUT_DIR" "$SKILLS_ROOT"

echo "JSONL:        $JSONL"
echo "SKILLS_ROOT:  $SKILLS_ROOT"
echo "OUTPUT_DIR:   $OUTPUT_DIR"
echo "MAX_RETRIES:  $MAX_RETRIES"
echo "STEP_TIMEOUT: $STEP_TIMEOUT"
echo "TOOL_TIMEOUT: $TOOL_TIMEOUT"
echo
echo "Note: Requires Chrome/Chromium running with CDP on :9223 (and model env vars configured)."
echo

PYTHONUNBUFFERED=1 \
python "$SCRIPT_DIR/run_webvoyager_tasks.py" \
  --jsonl "$JSONL" \
  --skills-root "$SKILLS_ROOT" \
  --website-filter "Google Flights" \
  --start 0 \
  --max-tasks 20 \
  --max-retries "$MAX_RETRIES" \
  --step-timeout "$STEP_TIMEOUT" \
  --tool-timeout "$TOOL_TIMEOUT" \
  --run-summary-out "$OUTPUT_DIR/run_summary.json" \
  --results-out "$OUTPUT_DIR/results.json"

echo
echo "Done."
echo "Run summary: $OUTPUT_DIR/run_summary.json"
echo "Results:     $OUTPUT_DIR/results.json"
