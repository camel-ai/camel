#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT_DIR"

CDP_PORT="${CDP_PORT:-9223}"

# {"web_name": "Google Flights", "id": "Google Flights--1", "ques": "Show me the list of one-way flights on January 25, 2026 from Chicago to Paris.", "web": "https://www.google.com/travel/flights/"}
CASE_WEB_NAME="${CASE_WEB_NAME:-Google Flights}"
CASE_ID="${CASE_ID:-Google Flights--1}"
CASE_QUES="${CASE_QUES:-Show me the list of one-way flights on January 25, 2026 from Chicago to Paris.}"
CASE_WEB="${CASE_WEB:-https://www.google.com/travel/flights/}"

TMP_DIR="${TMP_DIR:-$(mktemp -d)}"
SKILLS_ROOT="${SKILLS_ROOT:-$TMP_DIR/browser_skills}"
WEBSITE_SLUG="$(echo "$CASE_WEB_NAME" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/_/g; s/^_+|_+$//g; s/_+/_/g')"
SKILLS_DIR="${SKILLS_DIR:-$SKILLS_ROOT/$WEBSITE_SLUG}"
UV_CACHE_DIR="${UV_CACHE_DIR:-$ROOT_DIR/.tmp/uv-cache}"

mkdir -p "$SKILLS_DIR"
mkdir -p "$UV_CACHE_DIR"

echo "Repo: $ROOT_DIR"
echo "Temp: $TMP_DIR"
echo "Case: $CASE_ID ($CASE_WEB_NAME) — $CASE_WEB"
echo "Skills root: $SKILLS_ROOT"
echo "Skills dir:  $SKILLS_DIR"
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

echo "Preflight: CDP (Chrome DevTools Protocol) @ localhost:${CDP_PORT}"
check_cdp "$CDP_PORT" || {
  echo "WARNING: Cannot reach http://localhost:${CDP_PORT}/json/version."
  echo "Start Chrome/Chromium with e.g.:"
  echo "  google-chrome --remote-debugging-port=${CDP_PORT} --user-data-dir=/tmp/cdp-profile"
}

echo
echo "Step 1/4: First run with EMPTY skills dir (expect: few/no subtask functions)."
RUN1_LOG="$TMP_DIR/run1.log"
STEP_TIMEOUT="${STEP_TIMEOUT:-600}"
TOOL_TIMEOUT="${TOOL_TIMEOUT:-600}"
PYTHONUNBUFFERED=1 UV_CACHE_DIR="$UV_CACHE_DIR" uv run python examples/toolkits/browser_skills_example/run_single_case.py \
  --skills-dir "$SKILLS_DIR" \
  --web-name "$CASE_WEB_NAME" \
  --web "$CASE_WEB" \
  --task "$CASE_QUES" \
  --step-timeout "$STEP_TIMEOUT" \
  --tool-timeout "$TOOL_TIMEOUT" \
  | tee "$RUN1_LOG"

extract_session_dir() {
  local log_file="$1"
  grep -E "^Session dir: " "$log_file" | tail -n1 | sed 's/^Session dir: //'
}

SESSION1="$(extract_session_dir "$RUN1_LOG")"
if [[ -z "${SESSION1}" ]]; then
  echo "ERROR: Could not parse session dir from first run log: $RUN1_LOG"
  exit 1
fi
echo
echo "First run session: $SESSION1"

echo
echo "Step 2/4: Verify task success (Vision-WebJudge)."
VERDICT1_JSON="$TMP_DIR/verdict1.json"
VERDICT1_OUT_JSON="$SESSION1/verdict1.json"
PYTHONUNBUFFERED=1 UV_CACHE_DIR="$UV_CACHE_DIR" uv run python examples/toolkits/browser_skills_example/eval_webjudge_session.py \
  "$SESSION1" \
  --out "$VERDICT1_JSON"

cp -f "$VERDICT1_JSON" "$VERDICT1_OUT_JSON"

if ! grep -Eq '"success"[[:space:]]*:[[:space:]]*true' "$VERDICT1_JSON"; then
  echo "❌ First run is NOT verified successful; skipping skill extraction to avoid unstable skills."
  echo "Verdict JSON: $VERDICT1_JSON"
  echo "Verdict JSON (out-dir): $VERDICT1_OUT_JSON"
  exit 1
fi

echo "✅ Verified success. Extracting skills into SKILLS_DIR."
PYTHONUNBUFFERED=1 UV_CACHE_DIR="$UV_CACHE_DIR" uv run python examples/toolkits/browser_skills_example/subtask_extractor.py \
  "$SESSION1" "$SKILLS_DIR" \
  | tee "$TMP_DIR/skill_extract.log"

echo
echo "Skills dir now contains:"
ls -la "$SKILLS_DIR"

echo
echo "Step 3/4: Second run WITH skills (expect: subtask reuse)."
RUN2_LOG="$TMP_DIR/run2.log"
PYTHONUNBUFFERED=1 UV_CACHE_DIR="$UV_CACHE_DIR" uv run python examples/toolkits/browser_skills_example/run_single_case.py \
  --skills-dir "$SKILLS_DIR" \
  --web-name "$CASE_WEB_NAME" \
  --web "$CASE_WEB" \
  --task "$CASE_QUES" \
  --step-timeout "$STEP_TIMEOUT" \
  --tool-timeout "$TOOL_TIMEOUT" \
  | tee "$RUN2_LOG"

SESSION2="$(extract_session_dir "$RUN2_LOG")"
if [[ -z "${SESSION2}" ]]; then
  echo "ERROR: Could not parse session dir from second run log: $RUN2_LOG"
  exit 1
fi
echo
echo "Second run session: $SESSION2"

echo
echo "Step 4/4: Evidence of skill reuse (any of these is sufficient)."
echo "To inspect subtask reuse, open:"
echo "  - $SESSION2/action_timeline.json  (look for timeline[].action_type == \"subtask_replay\")"
echo "  - $SESSION2/agent_communication_log.json  (look for communications[].type == \"subtask_call\")"
echo "  - $SESSION2/subtask_*_replay_actions.json"

COMM_JSON="$SESSION2/agent_communication_log.json"
TIMELINE_JSON="$SESSION2/action_timeline.json"

SUBTASK_CALLS=0
SUBTASK_REPLAY_ENTRIES=0
REPLAY_FILES=0

if [[ -f "$COMM_JSON" ]]; then
  SUBTASK_CALLS="$(grep -Eo '"type"[[:space:]]*:[[:space:]]*"subtask_call"' "$COMM_JSON" | wc -l | tr -d ' ')"
fi

if [[ -f "$TIMELINE_JSON" ]]; then
  SUBTASK_REPLAY_ENTRIES="$(grep -Eo '"action_type"[[:space:]]*:[[:space:]]*"subtask_replay"' "$TIMELINE_JSON" | wc -l | tr -d ' ')"
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
echo "Run logs:"
echo "  - $RUN1_LOG"
echo "  - $RUN2_LOG"
echo "Sessions:"
echo "  - $SESSION1"
echo "  - $SESSION2"
