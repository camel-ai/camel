#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$ROOT_DIR"

# End-to-end flow (aligned with run_one_case_end_to_end.sh):
# 1) Run task with EMPTY skills dir
# 2) Verify once (via navi-bench evaluator result JSON)
# 3) Extract skills
# 4) Re-run the same task WITH skills (and verify)
# 5) Print reuse evidence (best-effort)
#
# Some environments protect $HOME/.cache. uv uses UV_CACHE_DIR; redirect it to a
# repo-local writable dir (same pattern as run_one_case_end_to_end.sh).
UV_CACHE_DIR="${UV_CACHE_DIR:-$ROOT_DIR/.tmp/uv-cache}"
PYTHONUNBUFFERED="${PYTHONUNBUFFERED:-1}"
mkdir -p "$UV_CACHE_DIR"

# Defaults: run the small one-task JSONL checked in for quick iteration.
JSONL="${JSONL:-$SCRIPT_DIR/navi_bench_data.jsonl}"
# If TASK_ID is set, run that single task end-to-end (2 runs + skill extraction).
# If TASK_ID is empty, run ONE task per domain (prompt smoke test; no skill extraction).
TASK_ID="${TASK_ID:-}"
# Optional: when TASK_ID is empty, restrict the smoke test to one or more domains.
# Examples:
#   DOMAIN_FILTER=opentable bash .../run_navi_bench_one.sh
#   DOMAIN_FILTER=opentable,resy bash .../run_navi_bench_one.sh
DOMAIN_FILTER="${DOMAIN_FILTER:-${DOMAIN:-}}"

# By default, write *all* run artifacts under the repo session_logs dir so the
# user can inspect/debug after the script exits.
SESSION_LOGS_DIR="${SESSION_LOGS_DIR:-$ROOT_DIR/examples/toolkits/session_logs}"
RUN_STAMP="${RUN_STAMP:-$(date +%Y%m%d_%H%M%S)}"
RUN_ROOT="${RUN_ROOT:-$SESSION_LOGS_DIR/navi_bench_one_$RUN_STAMP}"

# TMP_DIR is used for run logs and skill extraction logs. Keep the name for
# backward compatibility with existing log messages/env overrides.
TMP_DIR="${TMP_DIR:-$RUN_ROOT}"
SKILLS_ROOT="${SKILLS_ROOT:-$RUN_ROOT/browser_skills}"
OUT_DIR="${OUT_DIR:-$RUN_ROOT/navi_runs}"
CDP_PORT="${CDP_PORT:-9223}"

MAX_ATTEMPTS_PER_TASK="${MAX_ATTEMPTS_PER_TASK:-1}" # this script orchestrates the second run explicitly
MAX_ATTEMPTS_PER_WEBSITE="${MAX_ATTEMPTS_PER_WEBSITE:-5}"
STEP_TIMEOUT="${STEP_TIMEOUT:-600}"
TOOL_TIMEOUT="${TOOL_TIMEOUT:-600}"

mkdir -p "$SKILLS_ROOT" "$OUT_DIR"

echo "Repo:         $ROOT_DIR"
echo "UV_CACHE_DIR: $UV_CACHE_DIR"
echo "RUN_ROOT:     $RUN_ROOT"
echo "Logs dir:     $TMP_DIR"
echo "JSONL:        $JSONL"
echo "TASK_ID:      ${TASK_ID:-<auto: one per domain>}"
echo "DOMAIN_FILTER:${DOMAIN_FILTER:-<none>}"
echo "SKILLS_ROOT:  $SKILLS_ROOT"
echo "OUT_DIR:      $OUT_DIR"
echo "CDP_PORT:     $CDP_PORT"
echo "MAX_ATTEMPTS_PER_TASK:    $MAX_ATTEMPTS_PER_TASK"
echo "MAX_ATTEMPTS_PER_WEBSITE: $MAX_ATTEMPTS_PER_WEBSITE"
echo "STEP_TIMEOUT: $STEP_TIMEOUT"
echo "TOOL_TIMEOUT: $TOOL_TIMEOUT"
echo

check_cdp() {
  local port="${1:-9223}"
  local url="http://127.0.0.1:${port}/json/version"

  if ! command -v curl >/dev/null 2>&1; then
    echo "WARNING: Preflight skipped (missing: curl)."
    return 1
  fi

  curl -fsS --max-time 1 "$url" >/dev/null
}

extract_field() {
  local log_file="$1"
  local prefix="$2"
  grep -E "^${prefix}[[:space:]]+" "$log_file" | tail -n1 | sed -E "s/^${prefix}[[:space:]]+//"
}

verify_eval_success() {
  local eval_json="$1"
  if [[ -z "$eval_json" || "$eval_json" == "None" || ! -f "$eval_json" ]]; then
    echo "Verifier: missing eval json: $eval_json"
    return 1
  fi
  UV_CACHE_DIR="$UV_CACHE_DIR" uv run python - "$eval_json" <<'PY'
import json
import sys
from pathlib import Path

p = Path(sys.argv[1])
data = json.loads(p.read_text(encoding="utf-8"))
ok = bool(data.get("success"))
score = data.get("score")
print(f"Verifier: success={ok} score={score!r} eval={p}")
raise SystemExit(0 if ok else 1)
PY
}

run_case() {
  local log_file="$1"
  shift

  set +e
  UV_CACHE_DIR="$UV_CACHE_DIR" PYTHONUNBUFFERED="$PYTHONUNBUFFERED" uv run python "$@" | tee "$log_file"
  local status="${PIPESTATUS[0]}"
  set -e
  return "$status"
}

echo "Preflight: CDP (Chrome DevTools Protocol) @ localhost:${CDP_PORT}"
check_cdp "$CDP_PORT" || {
  echo "WARNING: Cannot reach http://localhost:${CDP_PORT}/json/version."
  echo "Start Chrome/Chromium with e.g.:"
  echo "  google-chrome --remote-debugging-port=${CDP_PORT} --user-data-dir=/tmp/cdp-profile"
}

echo
if [[ -n "${TASK_ID}" ]]; then
  DOMAIN="$(echo "$TASK_ID" | cut -d/ -f2)"
  WEBSITE_SLUG="$(echo "$DOMAIN" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/_/g; s/^_+|_+$//g; s/_+/_/g')"
  SKILLS_DIR="${SKILLS_DIR:-$SKILLS_ROOT/$WEBSITE_SLUG}"
  mkdir -p "$SKILLS_DIR"

  echo "SKILLS_DIR:   $SKILLS_DIR"
  echo
  echo "Step 1/5: First run with EMPTY skills dir (expect: few/no subtask functions)."
  RUN1_LOG="$TMP_DIR/run1.log"
  if ! run_case "$RUN1_LOG" examples/toolkits/browser_skills_example/run_navi_bench_case.py \
      --jsonl "$JSONL" \
      --task-id "$TASK_ID" \
      --skills-root "$SKILLS_ROOT" \
      --skills-dir "$SKILLS_DIR" \
      --out-dir "$OUT_DIR" \
      --cdp-port "$CDP_PORT" \
      --max-attempts-per-task "$MAX_ATTEMPTS_PER_TASK" \
      --max-attempts-per-website "$MAX_ATTEMPTS_PER_WEBSITE" \
      --step-timeout "$STEP_TIMEOUT" \
      --tool-timeout "$TOOL_TIMEOUT" \
      --disable-skills \
      --disable-skill-extraction; then
    echo "WARNING: First run command failed (non-zero exit). Continuing to parse logs."
  fi

  SESSION1="$(extract_field "$RUN1_LOG" "session:")"
  EVAL1="$(extract_field "$RUN1_LOG" "eval:")"
  if [[ -z "${SESSION1}" || -z "${EVAL1}" ]]; then
    echo "ERROR: Could not parse session/eval paths from run1 log: $RUN1_LOG"
    exit 1
  fi

  echo
  echo "First run session: $SESSION1"
  echo "First run eval:    $EVAL1"

  echo
  echo "Step 2/5: Verify task success (Navi-Bench evaluator)."
  verify_eval_success "$EVAL1" || {
    echo "❌ First run is NOT verified successful; skipping skill extraction to avoid unstable skills."
    echo "Run1 log: $RUN1_LOG"
    exit 1
  }

  echo
  echo "Step 3/5: Extracting skills into SKILLS_DIR."
  UV_CACHE_DIR="$UV_CACHE_DIR" PYTHONUNBUFFERED="$PYTHONUNBUFFERED" uv run python examples/toolkits/browser_skills_example/subtask_extractor.py \
    "$SESSION1" "$SKILLS_DIR" \
    | tee "$TMP_DIR/skill_extract.log"

  echo
  echo "Skills dir now contains:"
  ls -la "$SKILLS_DIR"

  echo
  echo "Step 4/5: Second run WITH skills (expect: subtask reuse)."
  RUN2_LOG="$TMP_DIR/run2.log"
  if ! run_case "$RUN2_LOG" examples/toolkits/browser_skills_example/run_navi_bench_case.py \
      --jsonl "$JSONL" \
      --task-id "$TASK_ID" \
      --skills-root "$SKILLS_ROOT" \
      --skills-dir "$SKILLS_DIR" \
      --out-dir "$OUT_DIR" \
      --cdp-port "$CDP_PORT" \
      --max-attempts-per-task "$MAX_ATTEMPTS_PER_TASK" \
      --max-attempts-per-website "$MAX_ATTEMPTS_PER_WEBSITE" \
      --step-timeout "$STEP_TIMEOUT" \
      --tool-timeout "$TOOL_TIMEOUT" \
      --disable-skill-extraction; then
    echo "WARNING: Second run command failed (non-zero exit)."
  fi

  SESSION2="$(extract_field "$RUN2_LOG" "session:")"
  EVAL2="$(extract_field "$RUN2_LOG" "eval:")"
  if [[ -z "${SESSION2}" || -z "${EVAL2}" ]]; then
    echo "ERROR: Could not parse session/eval paths from run2 log: $RUN2_LOG"
    exit 1
  fi

  echo
  echo "Second run session: $SESSION2"
  echo "Second run eval:    $EVAL2"

  echo
  echo "Step 5/5: Evidence of skill reuse (any of these is sufficient)."
  echo "To inspect subtask reuse, open:"
  echo "  - $SESSION2/action_timeline.json  (look for timeline[].action_type == \"subtask_replay\")"
  echo "  - $SESSION2/agent_communication_log.json  (look for communications[].type == \"subtask_call\")"
  echo "  - $SESSION2/subtask_*_replay_actions.json"

  echo
  echo "Verifying second run success (Navi-Bench evaluator)."
  verify_eval_success "$EVAL2" || {
    echo "❌ Second run (WITH skills) is NOT verified successful."
    echo "Run2 log: $RUN2_LOG"
    exit 1
  }

  COMM_JSON="$SESSION2/agent_communication_log.json"
  TIMELINE_JSON="$SESSION2/action_timeline.json"

  SUBTASK_CALLS=0
  SUBTASK_REPLAY_ENTRIES=0
  REPLAY_FILES=0

  if [[ -f "$COMM_JSON" ]]; then
    SUBTASK_CALLS="$(grep -Eo '\"type\"[[:space:]]*:[[:space:]]*\"subtask_call\"' "$COMM_JSON" | wc -l | tr -d ' ')"
  fi

  if [[ -f "$TIMELINE_JSON" ]]; then
    SUBTASK_REPLAY_ENTRIES="$(grep -Eo '\"action_type\"[[:space:]]*:[[:space:]]*\"subtask_replay\"' "$TIMELINE_JSON" | wc -l | tr -d ' ')"
  fi

  if compgen -G "$SESSION2/subtask_*_replay_actions.json" >/dev/null; then
    REPLAY_FILES="$(ls -1 "$SESSION2"/subtask_*_replay_actions.json 2>/dev/null | wc -l | tr -d ' ')"
  fi

  echo "Reuse summary:"
  echo "  - Subtask calls (agent_communication_log.json): $SUBTASK_CALLS"
  echo "  - Replay files (subtask_*_replay_actions.json): $REPLAY_FILES"
  echo "  - subtask_replay entries (action_timeline.json): $SUBTASK_REPLAY_ENTRIES"

  if [[ "$SUBTASK_CALLS" -eq 0 && "$REPLAY_FILES" -eq 0 && "$SUBTASK_REPLAY_ENTRIES" -eq 0 ]]; then
    echo "WARNING: No clear reuse evidence detected in this session."
  fi

  echo
  echo "Done."
  echo "Run dir:"
  echo "  - $RUN_ROOT"
  echo "Run logs:"
  echo "  - $RUN1_LOG"
  echo "  - $RUN2_LOG"
  echo "Skill extraction log:"
  echo "  - $TMP_DIR/skill_extract.log"
  echo "Sessions:"
  echo "  - $SESSION1"
  echo "  - $SESSION2"
  exit 0
fi

echo "Prompt smoke test: running ONE case per domain from:"
echo "  $JSONL"
if [[ -n "$DOMAIN_FILTER" ]]; then
  echo "Domain filter:"
  echo "  $DOMAIN_FILTER"
fi
echo

DOMAINS_AND_TASKS="$(
  UV_CACHE_DIR="$UV_CACHE_DIR" uv run python - "$JSONL" "$DOMAIN_FILTER" <<'PY'
import json
import sys
from collections import OrderedDict
from pathlib import Path

p = Path(sys.argv[1])
domain_filter_raw = (sys.argv[2] if len(sys.argv) > 2 else "").strip()
domain_allow = None
if domain_filter_raw:
    # Comma-separated list of domains (e.g., "opentable,resy").
    domain_allow = {d.strip() for d in domain_filter_raw.split(",") if d.strip()}
    if not domain_allow:
        domain_allow = None

seen = OrderedDict()
for line in p.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line:
        continue
    row = json.loads(line)
    domain = (row.get("domain") or "").strip()
    task_id = (row.get("task_id") or "").strip()
    if domain_allow is not None and domain not in domain_allow:
        continue
    if domain and task_id and domain not in seen:
        seen[domain] = task_id
for domain, task_id in seen.items():
    # Print a *real* tab so bash can split with IFS=$'\\t'.
    print(f"{domain}\t{task_id}")
PY
)"

if [[ -z "$DOMAINS_AND_TASKS" ]]; then
  echo "ERROR: Could not select one task per domain from: $JSONL"
  exit 2
fi

FAILS=0
printf "%-16s %-6s %-64s %s\n" "domain" "ok?" "eval_json" "session_dir"
echo "--------------------------------------------------------------"

while IFS=$'\t' read -r DOMAIN TASK_ID_SELECTED; do
  WEBSITE_SLUG="$(echo "$DOMAIN" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/_/g; s/^_+|_+$//g; s/_+/_/g')"
  SKILLS_DIR="$SKILLS_ROOT/$WEBSITE_SLUG"
  mkdir -p "$SKILLS_DIR"

  RUN_LOG="$TMP_DIR/${WEBSITE_SLUG}.log"
  if ! run_case "$RUN_LOG" examples/toolkits/browser_skills_example/run_navi_bench_case.py \
      --jsonl "$JSONL" \
      --task-id "$TASK_ID_SELECTED" \
      --skills-root "$SKILLS_ROOT" \
      --skills-dir "$SKILLS_DIR" \
      --out-dir "$OUT_DIR" \
      --cdp-port "$CDP_PORT" \
      --max-attempts-per-task "$MAX_ATTEMPTS_PER_TASK" \
      --max-attempts-per-website "$MAX_ATTEMPTS_PER_WEBSITE" \
      --step-timeout "$STEP_TIMEOUT" \
      --tool-timeout "$TOOL_TIMEOUT" \
      --disable-skills \
      --disable-skill-extraction; then
    echo "WARNING: Run command failed for domain=$DOMAIN task_id=$TASK_ID_SELECTED (non-zero exit)."
  fi

  SESSION="$(extract_field "$RUN_LOG" "session:")"
  EVAL="$(extract_field "$RUN_LOG" "eval:")"

  OK="no"
  if verify_eval_success "$EVAL" >/dev/null 2>&1; then
    OK="yes"
  else
    FAILS="$((FAILS + 1))"
  fi

  printf "%-16s %-6s %-64s %s\n" "$DOMAIN" "$OK" "${EVAL:-<missing>}" "${SESSION:-<missing>}"
done <<<"$DOMAINS_AND_TASKS"

echo "--------------------------------------------------------------"
echo "Logs dir: $TMP_DIR"
echo "Fails:    $FAILS"

if [[ "$FAILS" -gt 0 ]]; then
  exit 1
fi
