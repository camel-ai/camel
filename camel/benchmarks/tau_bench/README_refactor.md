# CAMEL Tau-Bench Integration Guide

## Overview
This document describes the refactored integration of the original τ-bench benchmark inside CAMEL. The goal of the refactor is to make τ-bench behave exactly like the reference implementation while:
1. Reusing CAMEL's `ChatAgent` for both assistant and user simulators (no LiteLLM dependency).
2. Allowing τ-bench components (tasks, policies, tools) to remain untouched so results match upstream runs.
3. Exposing a clean BaseBenchmark-compatible API and runnable example.

Directory layout inside `camel/camel/benchmarks/tau_bench/`:
- `benchmark.py` – BaseBenchmark implementation that wraps the upstream env.
- `types.py` – Core τ-bench dataclasses/pydantic models (Action, EnvInfo, etc.).
- `envs/` – Copied tasks, rules, tools, mock data, and domain env classes.
- `README_refactor.md` – this guide.
- `__init__.py` – exports `TauBenchBenchmark` and registers the `tau_bench` alias.

## Major Changes
### 1. `TauBenchBenchmark`
- Lives in `benchmark.py` and subclasses `BaseBenchmark`.
- Accepts the same parameters as the original CLI (`--env`, `--agent-strategy`, `--task-ids`, `--max-concurrency`, etc.) while supporting the standard CAMEL `run(agent, on=..., subset=...)` interface.
- During execution it:
  * Clones the provided `ChatAgent` per task, injects the τ policy wiki as system prompt.
  * Wraps the τ-bench tool schemas as CAMEL `FunctionTool`s so tool calls go through CAMEL's runtime.
  * Logs results/metrics in the exact format used by upstream τ-bench (Pass^k table, reward averages, JSON artifacts).

### 2. User Simulation via ChatAgent
- `envs/user.py` no longer calls LiteLLM directly. Instead:
  * `LLMUserSimulationEnv`, `ReactUserSimulationEnv`, `VerifyUserSimulationEnv`, and `ReflectionUserSimulationEnv` all build a `ChatAgent` using CAMEL's `ModelFactory`.
  * Conversation state is tracked as plain strings, and each step is generated via `agent.step(...)`.
  * Token usage is measured from the ChatAgent response and reported as "cost" back to the environment so reward computation is unchanged.

### 3. Package Alias
- `__init__.py` registers the module under the legacy name `tau_bench` *before* importing submodules. This makes statements such as `from tau_bench.envs import get_env` 
  continue to work even though the code now lives under `camel.benchmarks.tau_bench`.

### 4. Tool Directories
- All tool implementations (`envs/airline/tools`, `envs/retail/tools`) are copied from the original repo. They are required because environment classes import `tau_bench.envs.airline.tools` and expect those modules to exist.

## Usage
### Basic benchmark run
```bash
cd /media/zeyu/DA1474031473E145/camel
python -m examples.benchmarks.tau_bench
```
This example script:
- Creates a GPT-4o-mini assistant `ChatAgent` via `ModelFactory`.
- Configures `TauBenchBenchmark(domain="airline", user_model="gpt-4.1", user_strategy="llm")`.
- Runs tasks 0–4 with `num_trials=1`, `max_concurrency=5`.
- Saves raw JSON output under `examples/benchmarks/` with the same filename pattern as upstream τ-bench.

### Programmatic usage
```python
from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.benchmarks import TauBenchBenchmark

model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O_MINI,
    model_config_dict={"temperature": 0.0},
)
agent = ChatAgent(system_message="You are a helpful agent.", model=model)

benchmark = TauBenchBenchmark(
    domain="retail",
    user_strategy="react",
    user_model="gpt-4.1",
    user_provider="openai",
    save_to="./results/tau_bench",
)
benchmark.load()
benchmark.run(agent=agent, start_index=0, end_index=10, num_trials=2)
metrics = benchmark.evaluate()
print(metrics)
```

### Notes
- The benchmark still requires outbound access to the selected model providers (e.g., OpenAI). In air-gapped environments the run will fail with connection errors.
- To swap to Anthropic/other backends, pass `user_provider="anthropic"` (or a value understood by `ModelPlatformType.from_name`) plus the corresponding model name (e.g., `claude-3-5-sonnet-20241022`).

## Maintaining Parity with Upstream
To ensure results match the official τ-bench metrics:
1. Policy documents (`envs/airline/wiki.md`, etc.) and tasks (`tasks.py`, JSON data) remain untouched.
2. Tool signatures and return strings are identical to the original repository.
3. File names and JSON log structure match the CLI output (e.g., `tool-calling-gpt-4o-0.0_range_0-10_user-gpt-4o-llm_timestamp.json`).
4. Random seeding uses the same defaults (`seed=10`, `shuffle=False`).

## Extending the Integration
- **New User Strategies**: implement a new subclass of `LLMUserSimulationEnv` using CAMEL agents and register it in `UserStrategy` + `load_user`.
- **Additional Domains**: copy the domain directory from upstream (e.g., the τ² telecom domain) into `envs/telecom/`, expose `MockTelecomDomainEnv` in its `__init__.py`, and update `envs/__init__.py::get_env` to handle the new `env_name`.
- **Alternative Assistants**: you can hand a fully custom `ChatAgent` to `benchmark.run()`. Any toolkits/memories already attached to that agent will be preserved when the agent is cloned per task.

## Troubleshooting
| Symptom | Cause | Fix |
|---------|-------|-----|
| `ModuleNotFoundError: tau_bench.envs....` | Alias not registered | Ensure `camel/camel/benchmarks/tau_bench/__init__.py` executes before other imports (use `python -m`). |
| `Connection error` / `Temporary failure in name resolution` | No network to provider | Run in an environment with outbound internet and valid API keys. |
| `Permission denied: __pycache__` | Read-only filesystem | Remove `__pycache__` directory or run with `PYTHONDONTWRITEBYTECODE=1`. |
| Unexpected LiteLLM calls | Using old `tau_bench/envs/user.py` | Confirm you are importing the rebuilt file under `camel/camel/benchmarks/tau_bench/envs/user.py`. |

## Related Files
- `examples/benchmarks/tau_bench.py` – runnable example.
- `camel/benchmarks/__init__.py` – exports `TauBenchBenchmark`.
- `docs/` (future) – consider linking this guide once moved to formal documentation.

