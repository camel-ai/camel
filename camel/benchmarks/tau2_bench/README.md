# CAMEL τ²-Bench Integration

This directory contains a self-contained, CAMEL-native port of the
[`tau2-bench`](https://github.com/sierra-research/tau2-bench) project.  The aim
is to reproduce τ²’s official benchmark results (airline/retail/telecom domains)
while running entirely on CAMEL `ChatAgent`s rather than LiteLLM.  All code,
tools, policies, and datasets required for the benchmark are vendored here so
no external checkout is needed.

---

## Directory Layout

```
camel/benchmarks/tau2_bench/
├── adapters.py                 # CAMEL <-> τ² agent/user bridges
├── benchmark.py                # Tau2BenchBenchmark (BaseBenchmark subclass)
├── data/                       # Vendored task DBs, policies, user guidelines
│   └── tau2/domains/...        # airline / retail / telecom / mock
├── tau2/                       # Vendored upstream runtime (env, registry, etc.)
└── README.md                   # This document
```

Notable files inside `tau2/`:

- `agent/`, `user/`, `orchestrator/`: τ²’s conversation runtime.
- `domains/`: environment implementations + toolkits for airline/retail/telecom.
- `evaluator/` + `metrics/`: reward computation + Pass@k/avg_reward.
- `run.py`: helper utilities used by our benchmark wrapper (task loading, info).

We removed CLI-, FastAPI-, and Gym-related folders (`cli.py`, `scripts/`,
`api_service/`, `gym/`) since CAMEL only needs the programmatic API and
benchmark runtime.

---

## Why a Full Vendoring?

τ²-bench is far more than a set of QA prompts.  Each task is a multi-step tool
interaction between a service agent, simulated user, and domain environment.
To keep behavior identical to upstream we need:

1. **Original tools/policies/tasks** (verbatim copy).
2. **τ² orchestrator, evaluators, metrics** so reward computation matches the
   leaderboard.
3. **CAMEL adapters** that map a `ChatAgent` to τ²’s `BaseAgent`/`BaseUser`
   without bypassing tool execution.

The result is a tree with over 100 files, but it guarantees functional parity
and makes the benchmark self-contained (no HuggingFace downloads or LiteLLM).

---

## CAMEL-Specific Additions

### `CamelTau2Agent` / `CamelTau2User` (`adapters.py`)

- Wrap any `ChatAgent` so τ² sees it as a native agent/user.
- Tool schemas from the environment (`Tool.openai_schema`) are registered as
  **external tools**.  When the model emits a function call we forward the call
  back to `env.step(Action(...))`, keeping tool execution identical to τ².
- Tool responses are replayed into CAMEL’s memory as structured messages rather
  than free-form strings, so the model observes the same JSON as LiteLLM did.
- Seeds are propagated by editing the internal model config (e.g., OpenAI
  `seed`), ensuring deterministic trials when the backend supports it.

### Policy Injection

`Tau2BenchBenchmark` clones the evaluation `ChatAgent` per task and rewrites its
system prompt to include the domain policy:

```
[original system message]

<policy>
...domain policy text...
</policy>
```

This mirrors τ²’s “policy + wiki as system prompt” behavior.

### Concurrency & Result Logging

- Uses `ThreadPoolExecutor` with user-configurable `max_concurrency` to mirror
  τ²’s parallel execution.
- Writes output in the exact `Results.model_dump_json()` format.  Files are
  stored under `results/tau2_bench/<timestamp>_<domain>.json` by default.
- `benchmark.evaluate()` simply proxies `tau2.metrics.agent_metrics.compute_metrics`.

### LiteLLM Removal

All upstream references to LiteLLM have been stubbed out.  The vendored
`tau2/utils/llm_utils.py` now only provides helper functions for cost/usage
(currently unused).  Any attempt to call the old `generate()` raises an error,
ensuring the runtime always goes through CAMEL’s `ModelFactory`.

---

## Installing Dependencies

`pyproject.toml` now includes the extra Python packages τ² depends on:

- `rich`, `loguru`, `deepdiff`, `docstring-parser`, etc.

Install CAMEL in editable mode (recommended):

```bash
pip install -e .
```

Ensure your `.env` provides the relevant model credentials (OpenAI, etc.).

---

## Running the Benchmark

### 1. Quick smoke test

Examples target `examples/benchmarks/tau2_bench.py`.  It evaluates GPT‑4o-mini
on three airline tasks with a GPT‑4.1-mini user:

```bash
python examples/benchmarks/tau2_bench.py
```

### 2. Programmatic usage

```python
from camel.agents import ChatAgent
from camel.benchmarks import Tau2BenchBenchmark
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O,
    model_config_dict={"temperature": 0.0},
)
agent = ChatAgent(system_message="You are an airline agent.", model=model)

benchmark = Tau2BenchBenchmark(
    domain="airline",
    user_model=ModelType.GPT_4_1,
    user_model_platform=ModelPlatformType.OPENAI,
    user_model_config={"temperature": 0.0},
    save_to="results/tau2_bench",
)
benchmark.load()
benchmark.run(
    agent=agent,
    num_trials=1,
    max_steps=60,
    max_errors=5,
    max_concurrency=10,
)
print(benchmark.evaluate())
```

Key parameters:

| Argument | Description |
| --- | --- |
| `domain` | `"airline"`, `"retail"`, `"telecom"`, `"mock"` |
| `max_steps`, `max_errors` | Match τ² defaults (`100`, `10`) unless you need faster smoke tests |
| `max_concurrency` | Number of tasks executed in parallel |
| `task_ids`, `num_tasks` | Restrict the task set for debugging |
| `user_model*` | Configure the user simulator (defaults to GPT‑4.1 mini) |
| `save_to` | Directory or file path for the JSON results |

### Reproducing Published Numbers

We validated the integration with the following settings (single trial):

| Domain | Agent/User | Concurrency | Pass@1 | Notes |
| --- | --- | --- | --- | --- |
| airline | GPT‑4o / GPT‑4.1 | 10 | 0.46 | close to τ² official 0.42 |
| retail  | GPT‑4o / GPT‑4.1 | 10 | 0.69 | matches τ² leaderboard (~0.70) |
| airline | GPT‑5 / GPT‑4.1  | 5  | 0.62 | reasoning model, ~50 min runtime |

To run these yourself, set up `.env` with the relevant API keys and use the
sample script above.  Expect GPT‑5 runs to take significantly longer due to
rate limits; lowering `max_concurrency` helps avoid server-side throttling.

---

## Differences vs. Upstream τ²-Bench

1. **No LiteLLM** – everything runs through CAMEL `ChatAgent`s.
2. **No CLI / FastAPI / Gym** – we trimmed non-benchmark tooling to keep the
   vendored code leaner.  Only the components needed for evaluation remain.
3. **Policy injection via system prompt** – upstream uses wiki/policy injection
   in the CLI; we replicate it manually when cloning the agent.
4. **Cost/usage tracking** – τ²’s cost computation relied on LiteLLM metadata.
   We currently set `agent_cost`/`user_cost` to `None` to avoid misleading
   numbers.  This can be revisited once CAMEL exposes unified usage stats.

Otherwise, tasks, tools, reward evaluators, and JSON artifacts are identical.

---

## Known Limitations / FAQ

### Why is the repo so large?
Because τ² includes full tool implementations (JSON DBs, policies, workflow
graphs) we need to vendor them to stay self-contained.  Removing them would
break parity with the upstream benchmark.

### Can I still use τ²’s CLI?
No.  We deliberately removed `cli.py` and related scripts to avoid shipping
unused dependencies.  Use the CAMEL `Tau2BenchBenchmark` API instead.

### How do I run only a subset of tasks?
Pass `task_ids=[...]` or `num_tasks=N` to `benchmark.run(...)`.  This is useful
when experimenting with new prompts or expensive models (e.g., GPT‑5).

### Why do GPT‑5 runs take so long?
Reasoning models have high latency and strict rate limits.  Try smaller
concurrency (e.g., 5) and allow 30–60 minutes for a full domain run.

---

## Contributing / Maintenance Tips

1. **Policy updates**: when upstream policies change, replace the files in
   `data/tau2/domains/<domain>/` and rerun the smoke tests.
2. **New domains**: copy the domain folder from upstream `src/tau2/domains/`
   into `tau2/domains/`, update `registry.py` to register it, and make sure the
   dataset lives under `data/tau2/domains/<new-domain>/`.
3. **Adapters**: if CAMEL `ChatAgent` APIs evolve (e.g., different tool schema),
   update `adapters.py` accordingly.  The τ² runtime expects `ToolMessage`s to
   be broadcast between agent/user exactly as in upstream, so keep that contract.
4. **Testing**: use the example script or small task subsets (e.g., `num_tasks=3`)
   before launching full runs.  Keep `max_concurrency` conservative to avoid
   exhausting API quotas during development.

---

For questions or regressions, open an issue in the main CAMEL repository and
tag it with `tau2-bench`.  Happy benchmarking!
