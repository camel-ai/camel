# ST-WebAgentBench

ST-WebAgentBench evaluates web agents on **safety and trustworthiness** across six dimensions in enterprise scenarios (GitLab, ShoppingAdmin, SuiteCRM).

## Installation

```bash
pip install "camel-ai[st_webagentbench]"
```

Install the ST-WebAgentBench package separately (cloned repo):

```bash
git clone https://github.com/segev-shlomov/ST-WebAgentBench external_deps/ST-WebAgentBench
pip install -e external_deps/ST-WebAgentBench -e external_deps/ST-WebAgentBench/browsergym/stwebagentbench
playwright install chromium
```

## Environment Setup

### Option 1: Docker (local)

```bash
./scripts/st_webagentbench/provision.sh docker
```

Starts GitLab and SuiteCRM. ShoppingAdmin requires WebArena's custom image; see `scripts/st_webagentbench/README.md`.

**Local resource guidance:** running GitLab + SuiteCRM comfortably typically needs at least **4 vCPUs and 8 GB RAM** (8 vCPUs/16 GB is ideal for long runs), plus **20–50 GB** of free disk for GitLab data and SuiteCRM’s database.

### Option 2: AWS (full provisioning)

```bash
./scripts/st_webagentbench/provision.sh aws --key-name your-ec2-key-name
```

This provisions the entire setup: launches WebArena AMI, configures GitLab + ShoppingAdmin + SuiteCRM, allocates Elastic IP, and outputs `.env.provisioned` with the URLs. Requires AWS CLI and an EC2 key pair (default region: ap-southeast-1/Singapore, override with `--region`).

Teardown when done:

```bash
./scripts/st_webagentbench/provision_aws_teardown.sh --tag st-webagentbench
```

### Configuration

Copy `.env.example` to `.env` and set:

- `OPENAI_API_KEY` (or your LLM provider key)
- `GITLAB_URL`, `SHOPPING_ADMIN_URL`, `SUITECRM_URL`
- Application credentials as needed

## Usage

### Python API

```python
from camel.agents import ChatAgent
from camel.benchmarks import STWebAgentBenchmark, STWebAgentBenchConfig

agent = ChatAgent(
    system_message="You are a web agent...",
    model="deepseek/deepseek-chat"
)
config = STWebAgentBenchConfig(headless=True)
benchmark = STWebAgentBenchmark(
    data_dir="./data/st_webagentbench",
    save_to="./results/st_webagentbench",
    config=config,
)
benchmark.download().load()
benchmark.run(agent, on="test", subset=10)
print(benchmark.get_summary_metrics())
```

### Example Script

```bash
python examples/benchmarks/st_webagentbench.py --subset 5 --model deepseek/deepseek-chat
```

### Parameters

| Parameter | Description |
|-----------|-------------|
| `on` | Split: `train`, `valid`, `test` |
| `subset` | Max tasks (e.g. `38` for ~10% of 375) |
| `randomize` | Shuffle task order |
| `--model` | Model string (CLI) |

## Metrics

- **CR** (Completion Rate): Raw task success
- **CuP** (Completion under Policy): Success with zero policy violations
- **Risk Ratio**: Per-dimension violation rates

## Data

The full task set (375 tasks) comes from `test.raw.json` in the cloned ST-WebAgentBench repo. It is loaded via the installed `stwebagentbench` package. If not found, the benchmark falls back to a small bundled sample.
