#!/usr/bin/env bash
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# See the License for the specific language governing permissions and
# limitations in the License.
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
#
# Provision ST-WebAgentBench on AWS in one script.
# Launches WebArena AMI, configures GitLab + ShoppingAdmin, optionally SuiteCRM.
# Use provision_aws_teardown.sh to shut down when done.
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Default region is ap-southeast-1 (Singapore); override via AWS_REGION or --region.
REGION="${AWS_REGION:-ap-southeast-1}"
AMI_ID="ami-06290d70feea35450"
INSTANCE_TYPE="${STWEBAGENTBENCH_INSTANCE_TYPE:-t3a.xlarge}"
TAG_NAME="${STWEBAGENTBENCH_TAG:-st-webagentbench}"
SG_NAME="st-webagentbench-sg"
KEY_NAME=""
KEY_FILE=""
DRY_RUN=false
SKIP_SUITECRM=false

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'
log_info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

usage() {
    cat << EOF
Usage: $(basename "$0") --key-name NAME [OPTIONS]

Provision ST-WebAgentBench on AWS: launch WebArena AMI, configure services, expose URLs.

Required:
  --key-name NAME     AWS EC2 key pair name (must exist in region $REGION)

Options:
  --key-file PATH     Path to private key for SSH (default: ~/.ssh/<key-name>.pem)
  --instance-type T   Instance type (default: $INSTANCE_TYPE)
  --region R          AWS region (default: $REGION)
  --tag NAME         Tag for teardown (default: $TAG_NAME)
  --skip-suitecrm     Skip SuiteCRM setup (GitLab + ShoppingAdmin only)
  --dry-run           Show what would be done without provisioning
  -h, --help          Show this help

Environment:
  STWEBAGENTBENCH_VPC_ID   VPC ID for security group (default: auto-detect)
  STWEBAGENTBENCH_INSTANCE_TYPE  Instance type (default: t3a.xlarge)

Prerequisites:
  - AWS CLI installed and configured (aws configure)
  - EC2 key pair created in the target region
  - Sufficient EC2/Elastic IP quota

Teardown:
  ./provision_aws_teardown.sh --tag $TAG_NAME
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --key-name)   KEY_NAME="$2"; shift 2 ;;
        --key-file)   KEY_FILE="$2"; shift 2 ;;
        --instance-type) INSTANCE_TYPE="$2"; shift 2 ;;
        --region)     REGION="$2"; shift 2 ;;
        --tag)        TAG_NAME="$2"; shift 2 ;;
        --skip-suitecrm) SKIP_SUITECRM=true; shift ;;
        --dry-run)    DRY_RUN=true; shift ;;
        -h|--help)    usage; exit 0 ;;
        *)            log_error "Unknown option: $1"; usage; exit 1 ;;
    esac
done

if [[ -z "$KEY_NAME" ]]; then
    log_error "Missing required --key-name"
    usage
    exit 1
fi

KEY_FILE="${KEY_FILE:-$HOME/.ssh/${KEY_NAME}.pem}"
if [[ ! -f "$KEY_FILE" ]] && [[ "$DRY_RUN" != "true" ]]; then
    log_error "Key file not found: $KEY_FILE"
    exit 1
fi

if ! command -v aws &>/dev/null; then
    log_error "AWS CLI required. Install: https://aws.amazon.com/cli/"
    exit 1
fi

# Resolve VPC (default or first available; override via STWEBAGENTBENCH_VPC_ID)
get_vpc() {
    local vpc_id
    vpc_id=$(aws ec2 describe-vpcs --region "$REGION" --filters "Name=is-default,Values=true" \
        --query 'Vpcs[0].VpcId' --output text 2>/dev/null || true)
    if [[ -z "$vpc_id" || "$vpc_id" == "None" ]]; then
        vpc_id=$(aws ec2 describe-vpcs --region "$REGION" --query 'Vpcs[0].VpcId' --output text)
    fi
    echo "$vpc_id"
}

# Resolve subnet (default VPC, first available subnet)
get_subnet() {
    local vpc_id="${1:-$(get_vpc)}"
    aws ec2 describe-subnets --region "$REGION" --filters "Name=vpc-id,Values=$vpc_id" "Name=map-public-ip-on-launch,Values=true" \
        --query 'Subnets[0].SubnetId' --output text
}

if [[ "$DRY_RUN" == "true" ]]; then
    log_info "[DRY RUN] Would provision in $REGION with key $KEY_NAME"
    exit 0
fi

#
# Idempotent instance discovery: reuse existing tagged instance if present.
#
EXISTING_DESC=$(aws ec2 describe-instances \
    --region "$REGION" \
    --filters "Name=tag:$TAG_NAME,Values=benchmark" \
              "Name=instance-state-name,Values=running,pending,stopping,stopped" \
    --query 'Reservations[0].Instances[0].[InstanceId,State.Name,PublicIpAddress]' \
    --output text 2>/dev/null || true)

INSTANCE_ID=""
INSTANCE_STATE=""
PUBLIC_IP=""

if [[ -n "$EXISTING_DESC" && "$EXISTING_DESC" != "None" ]]; then
    read -r INSTANCE_ID INSTANCE_STATE PUBLIC_IP <<< "$EXISTING_DESC"
    log_info "Found existing instance $INSTANCE_ID (state: $INSTANCE_STATE) with tag $TAG_NAME=benchmark"
    if [[ "$INSTANCE_STATE" != "running" ]]; then
        log_info "Starting existing instance $INSTANCE_ID..."
        aws ec2 start-instances --region "$REGION" --instance-ids "$INSTANCE_ID" >/dev/null
    fi
else
    VPC_ID="${STWEBAGENTBENCH_VPC_ID:-$(get_vpc)}"
    log_info "No existing instance found. Creating security group $SG_NAME in $REGION (VPC: $VPC_ID)..."
    SG_ID=$(aws ec2 create-security-group \
        --region "$REGION" \
        --vpc-id "$VPC_ID" \
        --group-name "$SG_NAME" \
        --description "ST-WebAgentBench: GitLab, ShoppingAdmin, SuiteCRM" \
        --output text 2>/dev/null) || true

    if [[ -z "$SG_ID" || "$SG_ID" == "None" ]]; then
        SG_ID=$(aws ec2 describe-security-groups --region "$REGION" \
            --filters "Name=group-name,Values=$SG_NAME" "Name=vpc-id,Values=$VPC_ID" \
            --query 'SecurityGroups[0].GroupId' --output text)
        if [[ -z "$SG_ID" || "$SG_ID" == "None" ]]; then
            log_error "Could not create or find security group"
            exit 1
        fi
        log_info "Using existing security group $SG_ID"
    fi
    for port in 22 80 3000 7770 7780 8023 8081 8888 9999; do
        aws ec2 authorize-security-group-ingress --region "$REGION" --group-id "$SG_ID" \
            --protocol tcp --port "$port" --cidr 0.0.0.0/0 2>/dev/null || true
    done

    SUBNET_ID=$(get_subnet "$VPC_ID")
    log_info "Launching instance from WebArena AMI $AMI_ID..."
    INSTANCE_ID=$(aws ec2 run-instances \
        --region "$REGION" \
        --image-id "$AMI_ID" \
        --instance-type "$INSTANCE_TYPE" \
        --key-name "$KEY_NAME" \
        --subnet-id "$SUBNET_ID" \
        --security-group-ids "$SG_ID" \
        --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":1000}}]' \
        --tag-specifications "ResourceType=instance,Tags=[{Key=$TAG_NAME,Value=benchmark}]" \
        --query 'Instances[0].InstanceId' --output text)
    log_info "Created instance: $INSTANCE_ID"
fi

log_info "Waiting for instance $INSTANCE_ID to be running..."
aws ec2 wait instance-running --region "$REGION" --instance-ids "$INSTANCE_ID"

# Ensure we have a public IP (reuse existing Elastic IP association if present).
if [[ -z "$PUBLIC_IP" || "$PUBLIC_IP" == "None" ]]; then
    PUBLIC_IP=$(aws ec2 describe-instances \
        --region "$REGION" \
        --instance-ids "$INSTANCE_ID" \
        --query 'Reservations[0].Instances[0].PublicIpAddress' \
        --output text 2>/dev/null || true)
fi

if [[ -z "$PUBLIC_IP" || "$PUBLIC_IP" == "None" ]]; then
    log_info "Allocating Elastic IP for instance $INSTANCE_ID..."
    ALLOC_ID=$(aws ec2 allocate-address --region "$REGION" --domain vpc --query 'AllocationId' --output text)
    PUBLIC_IP=$(aws ec2 describe-addresses --region "$REGION" --allocation-ids "$ALLOC_ID" \
        --query 'Addresses[0].PublicIp' --output text)
    log_info "Associating Elastic IP $PUBLIC_IP with instance..."
    aws ec2 associate-address --region "$REGION" --instance-id "$INSTANCE_ID" --allocation-id "$ALLOC_ID" >/dev/null
fi

# Hostname for config (use IP if no reverse DNS)
HOSTNAME="${PUBLIC_IP}"
log_info "Hostname: $HOSTNAME"

log_info "Waiting for SSH (up to 120s)..."
for i in $(seq 1 24); do
    if ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -o BatchMode=yes \
        -i "$KEY_FILE" "ubuntu@$HOSTNAME" "echo ok" 2>/dev/null; then
        break
    fi
    [[ $i -eq 24 ]] && { log_error "SSH timeout"; exit 1; }
    sleep 5
done

run_ssh() {
    ssh -o StrictHostKeyChecking=no -o ConnectTimeout=30 -i "$KEY_FILE" "ubuntu@$HOSTNAME" "$@"
}

log_info "Starting WebArena Docker services..."
run_ssh "docker start gitlab shopping shopping_admin forum 2>/dev/null || true"
run_ssh "docker start kiwix33 2>/dev/null || true"
if run_ssh "test -d /home/ubuntu/openstreetmap-website" 2>/dev/null; then
    run_ssh "cd /home/ubuntu/openstreetmap-website && docker compose start 2>/dev/null || true"
fi
log_info "Waiting 60s for services to start..."
sleep 60

log_info "Configuring base URLs for hostname $HOSTNAME..."
run_ssh "docker exec shopping /var/www/magento2/bin/magento setup:store-config:set --base-url=\"http://${HOSTNAME}:7770\" 2>/dev/null || true"
run_ssh "docker exec shopping mysql -u magentouser -pMyPassword magentodb -e \"UPDATE core_config_data SET value='http://${HOSTNAME}:7770/' WHERE path = 'web/secure/base_url';\" 2>/dev/null || true"
run_ssh "docker exec shopping_admin php /var/www/magento2/bin/magento config:set admin/security/password_is_forced 0 2>/dev/null || true"
run_ssh "docker exec shopping_admin php /var/www/magento2/bin/magento config:set admin/security/password_lifetime 0 2>/dev/null || true"
run_ssh "docker exec shopping /var/www/magento2/bin/magento cache:flush 2>/dev/null || true"
run_ssh "docker exec shopping_admin /var/www/magento2/bin/magento setup:store-config:set --base-url=\"http://${HOSTNAME}:7780\" 2>/dev/null || true"
run_ssh "docker exec shopping_admin mysql -u magentouser -pMyPassword magentodb -e \"UPDATE core_config_data SET value='http://${HOSTNAME}:7780/' WHERE path = 'web/secure/base_url';\" 2>/dev/null || true"
run_ssh "docker exec shopping_admin /var/www/magento2/bin/magento cache:flush 2>/dev/null || true"
run_ssh "docker exec gitlab sed -i \"s|^external_url.*|external_url 'http://${HOSTNAME}:8023'|\" /etc/gitlab/gitlab.rb 2>/dev/null || true"
run_ssh "docker exec gitlab gitlab-ctl reconfigure 2>/dev/null || true"

# iptables redirect if services not accessible (per WebArena README)
run_ssh "sudo iptables -t nat -A PREROUTING -p tcp --dport 7770 -j REDIRECT --to-port 7770 2>/dev/null || true"
run_ssh "sudo iptables -t nat -A PREROUTING -p tcp --dport 7780 -j REDIRECT --to-port 7780 2>/dev/null || true"
run_ssh "sudo iptables -t nat -A PREROUTING -p tcp --dport 8023 -j REDIRECT --to-port 8023 2>/dev/null || true"

if [[ "$SKIP_SUITECRM" != "true" ]]; then
    log_info "Starting SuiteCRM (Bitnami) on port 8081..."
    run_ssh "docker run -d --name st-webagentbench-mariadb --restart unless-stopped \
        -e MARIADB_ROOT_PASSWORD=root -e MARIADB_DATABASE=bitnami_suitecrm \
        -e MARIADB_USER=bn_suitecrm -e MARIADB_PASSWORD=bitnami \
        bitnami/mariadb:latest 2>/dev/null || docker start st-webagentbench-mariadb 2>/dev/null || true"
    sleep 10
    run_ssh "docker run -d --name st-webagentbench-suitecrm --restart unless-stopped -p 8081:8080 \
        --link st-webagentbench-mariadb:mariadb \
        -e SUITECRM_USERNAME=admin -e SUITECRM_PASSWORD=bitnami -e MARIADB_HOST=mariadb \
        bitnami/suitecrm:latest 2>/dev/null || docker start st-webagentbench-suitecrm 2>/dev/null || true"
    log_info "SuiteCRM starting (may take 1-2 min). Default: admin/bitnami"
else
    log_warn "SuiteCRM skipped. For full benchmark, run without --skip-suitecrm or use ST-WebAgentBench suitecrm_setup."
fi

ENV_FILE="$SCRIPT_DIR/.env.provisioned"
cat > "$ENV_FILE" << ENVEOF
# ST-WebAgentBench AWS provisioned - $(date +%Y-%m-%dT%H:%M:%S)
# Instance: $INSTANCE_ID | Elastic IP: $PUBLIC_IP

GITLAB_URL=http://${HOSTNAME}:8023
SHOPPING_ADMIN_URL=http://${HOSTNAME}:7780/admin
SUITECRM_URL=http://${HOSTNAME}:8081

# Copy to .env and add OPENAI_API_KEY, credentials:
# cp $ENV_FILE .env
ENVEOF

log_info ""
log_info "=== Provisioning complete ==="
log_info "Instance ID: $INSTANCE_ID"
log_info "Public URL: http://$HOSTNAME"
log_info ""
log_info "Add to your .env:"
log_info "  GITLAB_URL=http://${HOSTNAME}:8023"
log_info "  SHOPPING_ADMIN_URL=http://${HOSTNAME}:7780/admin"
log_info "  SUITECRM_URL=http://${HOSTNAME}:8081"
log_info ""
log_info "Config saved to: $ENV_FILE"
log_info "Teardown: ./provision_aws_teardown.sh --tag $TAG_NAME"
