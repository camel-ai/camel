#!/usr/bin/env bash
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
#
# Shutdown and delete AWS resources used for ST-WebAgentBench.
# Supports: EC2 instances, Elastic IPs, and optionally security groups.
#
# Usage:
#   ./provision_aws_teardown.sh                    # Use INSTANCE_IDS from env or --tag
#   ./provision_aws_teardown.sh i-xxxxx i-yyyyy    # Specific instance IDs
#   ./provision_aws_teardown.sh --tag st-webagentbench  # Find by tag (default tag)
#   ./provision_aws_teardown.sh --dry-run          # Show what would be deleted
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DRY_RUN=false
TAG_NAME="${STWEBAGENTBENCH_TAG:-st-webagentbench}"
INSTANCE_IDS=()

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

usage() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS] [INSTANCE_IDS...]

Shutdown and delete AWS resources used for ST-WebAgentBench benchmarking.

Options:
  --tag NAME       Find instances by tag (default: ${TAG_NAME})
                   Tag filter: Name=tag:NAME,Values=benchmark
  --dry-run        Show resources that would be deleted without deleting
  -h, --help       Show this help

Environment:
  STWEBAGENTBENCH_INSTANCE_IDS  Space-separated instance IDs (alternative to positional args)
  STWEBAGENTBENCH_TAG           Tag name for resource discovery (default: st-webagentbench)

Examples:
  # Delete by instance IDs
  ./provision_aws_teardown.sh i-0123456789abcdef0

  # Delete all instances tagged st-webagentbench=benchmark
  ./provision_aws_teardown.sh --tag st-webagentbench

  # Preview without deleting
  ./provision_aws_teardown.sh --dry-run
EOF
}

# Parse arguments
USE_TAG=false
while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)
            usage
            exit 0
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --tag)
            TAG_NAME="$2"
            USE_TAG=true
            shift 2
            ;;
        -*)
            log_error "Unknown option: $1"
            usage
            exit 1
            ;;
        *)
            INSTANCE_IDS+=("$1")
            shift
            ;;
    esac
done

# If no instance IDs, try env var or tag-based discovery
if [[ ${#INSTANCE_IDS[@]} -eq 0 ]]; then
    if [[ -n "${STWEBAGENTBENCH_INSTANCE_IDS:-}" ]]; then
        read -ra INSTANCE_IDS <<< "$STWEBAGENTBENCH_INSTANCE_IDS"
    fi
    if [[ ${#INSTANCE_IDS[@]} -eq 0 ]]; then
        log_info "Discovering instances with tag ${TAG_NAME}=benchmark..."
        mapfile -t DISCOVERED < <(aws ec2 describe-instances \
            --filters "Name=tag:${TAG_NAME},Values=benchmark" "Name=instance-state-name,Values=running,pending,stopping,stopped" \
            --query 'Reservations[*].Instances[*].InstanceId' \
            --output text 2>/dev/null | tr '\t' '\n' | grep -v '^$' || true)
        INSTANCE_IDS=("${DISCOVERED[@]}")
    fi
fi

if [[ ${#INSTANCE_IDS[@]} -eq 0 ]]; then
    log_warn "No instance IDs provided or found. Nothing to delete."
    log_info "Use: $(basename "$0") i-xxxxx  or  --tag ${TAG_NAME}"
    exit 0
fi

# Flatten and dedupe
INSTANCE_IDS=($(printf '%s\n' "${INSTANCE_IDS[@]}" | sort -u))
log_info "Instances to terminate: ${INSTANCE_IDS[*]}"

# Collect Elastic IPs allocated by these instances before termination
ALLOCATION_IDS=()
for iid in "${INSTANCE_IDS[@]}"; do
    alloc=$(aws ec2 describe-addresses \
        --filters "Name=instance-id,Values=${iid}" \
        --query 'Addresses[*].AllocationId' \
        --output text 2>/dev/null || true)
    if [[ -n "$alloc" ]]; then
        for a in $alloc; do
            ALLOCATION_IDS+=("$a")
        done
    fi
done

# Confirm unless dry-run
if [[ "$DRY_RUN" == "true" ]]; then
    log_info "[DRY RUN] Would terminate instances: ${INSTANCE_IDS[*]}"
    if [[ ${#ALLOCATION_IDS[@]} -gt 0 ]]; then
        log_info "[DRY RUN] Would release Elastic IPs: ${ALLOCATION_IDS[*]}"
    fi
    exit 0
fi

# Terminate instances
log_info "Terminating ${#INSTANCE_IDS[@]} instance(s)..."
if aws ec2 terminate-instances --instance-ids "${INSTANCE_IDS[@]}"; then
    log_info "Termination initiated. Instances may take a few minutes to fully stop."
else
    log_error "Failed to terminate instances"
    exit 1
fi

# Release Elastic IPs (must do after instance is terminated or disassociated)
if [[ ${#ALLOCATION_IDS[@]} -gt 0 ]]; then
    log_info "Waiting for instances to enter 'terminated' state before releasing Elastic IPs..."
    aws ec2 wait instance-terminated --instance-ids "${INSTANCE_IDS[@]}" 2>/dev/null || true

    for alloc in "${ALLOCATION_IDS[@]}"; do
        if aws ec2 release-address --allocation-id "$alloc" 2>/dev/null; then
            log_info "Released Elastic IP: $alloc"
        else
            log_warn "Could not release Elastic IP $alloc (may already be released)"
        fi
    done
fi

log_info "Teardown complete."
