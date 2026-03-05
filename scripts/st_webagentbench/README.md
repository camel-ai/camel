# ST-WebAgentBench Provision Scripts

Scripts for provisioning and tearing down ST-WebAgentBench test environments.

## Quick Start

```bash
# Verify prerequisites
./provision.sh verify

# Local Docker (GitLab + SuiteCRM)
./provision.sh docker

# AWS (full provisioning; requires EC2 key pair)
./provision.sh aws --key-name your-key-name

# Teardown AWS when done
./provision_aws_teardown.sh --tag st-webagentbench
```

## Prerequisites

- Install stwebagentbench: `pip install -e external_deps/ST-WebAgentBench -e external_deps/ST-WebAgentBench/browsergym/stwebagentbench`
- Playwright: `pip install playwright && playwright install chromium`
- Copy `.env.example` to `.env` and configure URLs/credentials

## Docker (Local)

`provision_docker.sh` starts GitLab and SuiteCRM via Docker Compose. ShoppingAdmin requires WebArena's custom image—see WebArena repo for `shopping_admin_final_0719.tar`.

**Resource requirements (local):**

- **Recommended minimum:** 4 vCPUs and 8 GB RAM for GitLab + SuiteCRM
- **Comfortable for heavy runs:** 8 vCPUs and 16 GB RAM
- **Disk:** At least 20–50 GB free for GitLab data, logs, and SuiteCRM database

GitLab is particularly memory-heavy; if your Docker Desktop/daemon has less than ~4 GB allocated, containers may restart or respond slowly.

## AWS (Full Provisioning)

`provision_aws.sh` provisions the entire setup in one script:

1. Creates security group with required ports
2. Launches WebArena AMI instance (GitLab + ShoppingAdmin)
3. Allocates Elastic IP and associates it
4. SSHs in and configures base URLs for services
5. Optionally starts SuiteCRM (Bitnami) for full 375-task benchmark
6. Outputs `.env.provisioned` with URLs

**Usage:**
```bash
./provision_aws.sh --key-name your-ec2-key-name
# Optional: --key-file /path/to/key.pem --region ap-southeast-1 --skip-suitecrm
```

**Environment:** Set `STWEBAGENTBENCH_VPC_ID` if you have no default VPC (e.g. `export STWEBAGENTBENCH_VPC_ID=vpc-xxxxx`).

**Prerequisites:** AWS CLI configured, EC2 key pair in your chosen region (default: ap-southeast-1/Singapore).

## AWS Teardown

Use `provision_aws_teardown.sh` to shut down and delete AWS resources after benchmarking.

### Prerequisites

- [AWS CLI](https://aws.amazon.com/cli/) installed and configured
- Permissions to terminate EC2 instances and release Elastic IPs

### Usage

**Delete specific instance(s):**
```bash
./provision_aws_teardown.sh i-0123456789abcdef0 i-0fedcba9876543210
```

**Delete all instances tagged for ST-WebAgentBench:**
```bash
./provision_aws_teardown.sh --tag st-webagentbench
```

Tag instances when launching (e.g., via AWS Console or CLI):
```bash
aws ec2 run-instances ... --tag-specifications 'ResourceType=instance,Tags=[{Key=st-webagentbench,Value=benchmark}]'
```

**Preview without deleting (dry run):**
```bash
./provision_aws_teardown.sh --dry-run
```

**Environment variables:**
- `STWEBAGENTBENCH_INSTANCE_IDS` – Space-separated instance IDs
- `STWEBAGENTBENCH_TAG` – Tag name for discovery (default: `st-webagentbench`)

### Resources Removed

- EC2 instances (terminated)
- Elastic IPs associated with those instances (released)

EBS volumes with `DeleteOnTermination=true` (default) are removed automatically when instances terminate.
