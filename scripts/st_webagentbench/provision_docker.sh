#!/usr/bin/env bash
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
#
# Start ST-WebAgentBench environments via Docker Compose.
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if ! command -v docker &>/dev/null; then
    echo "Error: Docker is required. Install Docker and try again." >&2
    exit 1
fi

if ! docker compose version &>/dev/null && ! docker-compose version &>/dev/null; then
    echo "Error: Docker Compose is required. Install docker-compose or Docker Compose V2." >&2
    exit 1
fi

echo "Starting ST-WebAgentBench Docker environments..."
if docker compose version &>/dev/null; then
    docker compose -f docker-compose.yml up -d
else
    docker-compose -f docker-compose.yml up -d
fi

echo ""
echo "Services started. Configure .env with:"
echo "  GITLAB_URL=http://localhost:8023"
echo "  SHOPPING_ADMIN_URL=http://localhost:7780"
echo "  SUITECRM_URL=http://localhost:8081"
echo ""
echo "Note: GitLab may take several minutes to initialize."
echo "Stop with: docker compose -f docker-compose.yml down"
