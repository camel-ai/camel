#!/usr/bin/env bash
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
#
# Main provision script for ST-WebAgentBench.
# Supports: docker (local), aws (instructions), verify (health check).
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODE="${1:-}"

usage() {
    cat << EOF
Usage: $(basename "$0") [MODE]

Modes:
  docker   Start Docker-based local environments (GitLab, SuiteCRM)
  aws      Provision full AWS setup (requires --key-name). See provision_aws.sh --help
  verify   Check prerequisites (Python, Docker, Playwright)
  help     Show this help

ST-WebAgentBench also requires the stwebagentbench package:
  pip install -e external_deps/ST-WebAgentBench -e external_deps/ST-WebAgentBench/browsergym/stwebagentbench
  playwright install chromium
EOF
}

case "${MODE}" in
    docker)
        exec "$SCRIPT_DIR/provision_docker.sh"
        ;;
    aws)
        shift
        exec "$SCRIPT_DIR/provision_aws.sh" "$@"
        ;;
    verify)
        echo "Checking prerequisites..."
        command -v python3 &>/dev/null && echo "  Python: OK" || echo "  Python: missing"
        command -v docker &>/dev/null && echo "  Docker: OK" || echo "  Docker: missing"
        python3 -c "import playwright" 2>/dev/null && echo "  Playwright: OK" || echo "  Playwright: pip install playwright && playwright install chromium"
        python3 -c "import browsergym.stwebagentbench" 2>/dev/null && echo "  stwebagentbench: OK" || echo "  stwebagentbench: install from ST-WebAgentBench repo"
        if [[ ! -f "$SCRIPT_DIR/.env" && -f "$SCRIPT_DIR/.env.example" ]]; then
            echo ""
            echo "  Copy .env.example to .env and fill in credentials."
        fi
        ;;
    help|""|-h|--help)
        usage
        ;;
    *)
        echo "Unknown mode: $MODE"
        usage
        exit 1
        ;;
esac
