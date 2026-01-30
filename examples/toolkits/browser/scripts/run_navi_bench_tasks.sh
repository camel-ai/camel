#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$ROOT_DIR"

# Some environments protect $HOME/.cache. uv uses UV_CACHE_DIR; redirect it to a
# repo-local writable dir (same pattern as run_one_case_end_to_end.sh).
UV_CACHE_DIR="${UV_CACHE_DIR:-$ROOT_DIR/.tmp/uv-cache}"
mkdir -p "$UV_CACHE_DIR"

# Optional local dependency: if a `navi-bench/` checkout exists, put it on
# PYTHONPATH so Python can import `navi_bench` without in-code sys.path hacks.
if [[ -d "$ROOT_DIR/navi-bench" ]]; then
  export PYTHONPATH="$ROOT_DIR/navi-bench${PYTHONPATH:+:$PYTHONPATH}"
fi

EXAMPLE_ROOT="$ROOT_DIR/toolkits/browser/browser_skills_example"

# Path to a JSONL of Navi-Bench DatasetItem rows.
JSONL="${1:-$ROOT_DIR/toolkits/browser/data/navi_bench_data.jsonl}"

SKILLS_ROOT="${SKILLS_ROOT:-$EXAMPLE_ROOT/skills_store}"
OUT_DIR="${OUT_DIR:-$ROOT_DIR/toolkits/session_logs}"

# Filter by domain (optional): google_flights|opentable|resy|craigslist|apartments
DOMAIN="${DOMAIN:-}"
TASK_ID="${TASK_ID:-}"

CDP_PORT="${CDP_PORT:-9223}"

MAX_RETRIES="${MAX_RETRIES:-4}"
MAX_ATTEMPTS_PER_TASK="${MAX_ATTEMPTS_PER_TASK:-}"
MAX_ATTEMPTS_PER_WEBSITE="${MAX_ATTEMPTS_PER_WEBSITE:-100}"

STEP_TIMEOUT="${STEP_TIMEOUT:-3600}"
TOOL_TIMEOUT="${TOOL_TIMEOUT:-180}"

START_INDEX="${START_INDEX:-0}"
MAX_TASKS="${MAX_TASKS:-0}"

DISABLE_SKILLS="${DISABLE_SKILLS:-0}"
DISABLE_SKILL_EXTRACTION="${DISABLE_SKILL_EXTRACTION:-0}"

if [[ -z "$MAX_ATTEMPTS_PER_TASK" ]]; then
  MAX_ATTEMPTS_PER_TASK="$((MAX_RETRIES + 1))"
fi

mkdir -p "$OUT_DIR" "$SKILLS_ROOT"

echo "JSONL:        $JSONL"
echo "SKILLS_ROOT:  $SKILLS_ROOT"
echo "OUT_DIR:      $OUT_DIR"
echo "DOMAIN:       ${DOMAIN:-<all>}"
echo "TASK_ID:      ${TASK_ID:-<all>}"
echo "START_INDEX:  $START_INDEX"
echo "MAX_TASKS:    $MAX_TASKS (0 = all)"
echo "CDP_PORT:     $CDP_PORT"
echo "MAX_ATTEMPTS_PER_TASK:    $MAX_ATTEMPTS_PER_TASK"
echo "MAX_ATTEMPTS_PER_WEBSITE: $MAX_ATTEMPTS_PER_WEBSITE"
echo "STEP_TIMEOUT: $STEP_TIMEOUT"
echo "TOOL_TIMEOUT: $TOOL_TIMEOUT"
echo "UV_CACHE_DIR: $UV_CACHE_DIR"
echo "DISABLE_SKILLS:           $DISABLE_SKILLS"
echo "DISABLE_SKILL_EXTRACTION: $DISABLE_SKILL_EXTRACTION"
echo
echo "Note: Requires Chrome/Chromium running with CDP on :$CDP_PORT (and model env vars configured)."
echo

ARGS=(
  -m examples.toolkits.browser.browser_skills_example.cli.run_navi_bench_tasks
  --jsonl "$JSONL"
  --skills-root "$SKILLS_ROOT"
  --out-dir "$OUT_DIR"
  --cdp-port "$CDP_PORT"
  --max-attempts-per-task "$MAX_ATTEMPTS_PER_TASK"
  --max-attempts-per-website "$MAX_ATTEMPTS_PER_WEBSITE"
  --step-timeout "$STEP_TIMEOUT"
  --tool-timeout "$TOOL_TIMEOUT"
  --start "$START_INDEX"
)

if [[ "$MAX_TASKS" != "0" ]]; then
  ARGS+=(--max-tasks "$MAX_TASKS")
fi
if [[ -n "${DOMAIN}" ]]; then
  ARGS+=(--domain "$DOMAIN")
fi
if [[ -n "${TASK_ID}" ]]; then
  ARGS+=(--task-id "$TASK_ID")
fi
if [[ "$DISABLE_SKILLS" == "1" ]]; then
  ARGS+=(--disable-skills)
fi
if [[ "$DISABLE_SKILL_EXTRACTION" == "1" ]]; then
  ARGS+=(--disable-skill-extraction)
fi

PYTHONUNBUFFERED=1 UV_CACHE_DIR="$UV_CACHE_DIR" uv run python "${ARGS[@]}"

echo
echo "Done."
echo "Outputs are under: $OUT_DIR/session_<timestamp>/"
