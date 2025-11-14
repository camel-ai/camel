# Tau-Bench Integration with CAMEL

This directory embeds the official τ-bench benchmark inside CAMEL so that
CAMEL agents can be evaluated on realistic, policy-heavy customer service
scenarios (airline and retail domains). The goal is functional parity with
the upstream repository while keeping the codebase consistent with CAMEL’s
style and tooling.

## Layout

```
camel/benchmarks/tau_bench/
├── __init__.py                     # Re-exports TauBenchBenchmark
├── benchmark.py                    # BaseBenchmark-compatible runner
├── types.py                        # Dataclasses and enums
├── envs/
│   ├── base.py                     # Shared Env implementation
│   ├── user.py                     # User simulation agents
│   ├── airline/
│   │   ├── env.py                  # Domain-specific Env subclass
│   │   ├── tasks_test.py           # Upstream test split (JSON -> Task objects)
│   │   ├── wiki.md                 # Policy / knowledge base
│   │   └── tools/                  # FC wrappers around tau_bench tools
│   └── retail/
│       ├── env.py
│       ├── tasks_{train,dev,test}.py
│       ├── wiki.md
│       └── tools/
└── README_refactor.md              # Upstream parity notes
```

> **Note:** The long instruction strings in `tasks_*.py` and `rules.py`
> remain untouched to preserve upstream behaviour. Ruff is configured to
> ignore `E501` for those files.

## Running the Benchmark

```python
from camel.agents import ChatAgent
from camel.benchmarks import TauBenchBenchmark
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

# Assistant agent (GPT-4o in this example)
model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O,
    model_config_dict={"temperature": 0.0},
)
agent = ChatAgent(
    system_message="You are a meticulous airline support agent.",
    model=model,
)

# Configure tau-bench
benchmark = TauBenchBenchmark(
    domain="airline",          # or "retail"
    user_strategy="llm",
    user_model="gpt-4.1",
    user_provider="openai",
    user_temperature=1.0,      # matches paper setting
    save_to="examples/benchmarks",
)
benchmark.load()

# Run tasks 0-49 (full airline test split)
benchmark.run(
    agent=agent,
    start_index=0,
    end_index=-1,
    num_trials=3,
    shuffle=True,
    max_steps=30,
    max_concurrency=5,
)

# Aggregate metrics (Pass@k, avg_reward, etc.)
metrics = benchmark.evaluate()
print(metrics)
```

### Common Parameters

| Parameter          | Description                                                       |
|--------------------|-------------------------------------------------------------------|
| `domain`           | `"airline"` or `"retail"`                                         |
| `user_strategy`    | `"llm"`, `"react"`, `"verify"`, `"reflection"` (see `envs/user.py`) |
| `user_model`       | Model name understood by `ModelFactory`                           |
| `user_temperature` | Temperature used for the simulated user (paper uses `1.0`)        |
| `num_trials`       | Number of runs per task (paper averages ≥3 trials)                |
| `shuffle`          | Randomize task order each trial                                   |
| `max_steps`        | Max assistant turns per task (τ-bench default is 30)              |
| `max_concurrency`  | Threaded parallelism for `_run_task`                              |

## Example CLI Run

An end-to-end reference is provided at `examples/benchmarks/tau_bench.py`.
Running it with the default environment variables will execute the airline
domain (tasks 0‑4) and save logs to `examples/benchmarks`.

```bash
python -m examples.benchmarks.tau_bench
```

## Current Status (Apr 2025)

- ✅ Airline & retail domains embedded with original tasks/tools/wiki data.
- ✅ τ-bench metrics (Pass@k, avg reward) reproduced inside CAMEL.
- ✅ User simulator rewritten using CAMEL `ChatAgent` to avoid litellm.
- ⚠️ Pre-commit Ruff ignores `E501` for the upstream data/Rule files only.
- ⚠️ `mypy` pre-commit hook depends on `uv`; install via `pip install uv`
  if you want `pre-commit run --all-files` to succeed locally.

## Tips & Debugging

- **Result Files:** Every `benchmark.run()` writes a JSON checkpoint under
  `save_to`. Filenames follow the upstream format
  `tool-calling-<model>-<temp>_range_<start>-<end>_user-...json`.
- **User Behaviour:** Paper settings use GPT‑4.1 users with temperature 1.0.
  Using colder users can make tasks harder because instructions get dumped
  immediately.
- **Pass@k Interpretation:** `evaluate()` reports pass@1 and pass@k (when
  `num_trials > 1`). These match the original τ‑bench formula and can differ
  from simply “% of tasks solved at least once”.
- **Pre-commit:** Long upstream text files intentionally bypass `E501` via
  `[tool.ruff.lint.per-file-ignores]` in `pyproject.toml`. If you add new
  long-form instruction files, extend that list instead of rewrapping text.

## References

- [tau-bench GitHub](https://github.com/sierra-research/tau-bench)
- [τ-bench paper](https://arxiv.org/abs/2406.12045)
- `README_refactor.md` inside this directory for deeper parity notes.

### Basic Example

```python
from camel.agents import ChatAgent
from camel.benchmarks import TauBenchBenchmark
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

# Create assistant agent
model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O,
)
agent = ChatAgent(model=model)

# Run benchmark
benchmark = TauBenchBenchmark(
    domain="airline",  # or "retail"
    user_model="gpt-4o",
    user_strategy="llm",
)
benchmark.load()

# Simple usage (BaseBenchmark interface)
benchmark.run(agent=agent, on="test", subset=5)

# Advanced usage (tau-bench specific parameters)
benchmark.run(
    agent=agent,
    on="test",
    start_index=0,
    end_index=10,
    num_trials=1,
    temperature=0.0,
)

# Evaluate
results = benchmark.evaluate()
print(f"Pass@1: {results['pass@1']:.2%}")
```

### Using Different User Strategies

```python
# LLM strategy (default)
benchmark = TauBenchBenchmark(user_strategy="llm")

# ReAct strategy (with reasoning)
benchmark = TauBenchBenchmark(user_strategy="react")

# Verify strategy (validates goal completion)
benchmark = TauBenchBenchmark(user_strategy="verify")

# Reflection strategy (self-corrects responses)
benchmark = TauBenchBenchmark(user_strategy="reflection")
```

### Testing Both Domains

```python
# Test airline domain
airline_bench = TauBenchBenchmark(domain="airline")
airline_bench.load().run(agent, on="test")
airline_results = airline_bench.evaluate()

# Test retail domain
retail_bench = TauBenchBenchmark(domain="retail")
retail_bench.load().run(agent, on="test")
retail_results = retail_bench.evaluate()

print(f"Airline Pass@1: {airline_results['pass@1']:.2%}")
print(f"Retail Pass@1: {retail_results['pass@1']:.2%}")
```

## Components

### TauBenchBenchmark

Main class for running evaluations.

**Key Methods:**
- `load()`: Load tasks and environment
- `run(agent, on='test', subset=None, num_trials=1)`: Run evaluation
- `evaluate()`: Calculate metrics (Pass@1, Pass@k, etc.)

### User Agents (user_agent.py)

Independent user simulation agents for testing:

- `LLMUserAgent`: Basic LLM-based simulation
- `ReactUserAgent`: ReAct-style reasoning
- `VerifyUserAgent`: Goal verification
- `ReflectionUserAgent`: Self-reflection

**Usage:**
```python
from camel.benchmarks.tau_bench.user_agent import create_user_agent
from camel.agents import ChatAgent

# Create user agent separately
user_camel_agent = ChatAgent(...)
user_agent = create_user_agent(strategy="llm", agent=user_camel_agent)

# Reset with instruction
initial_msg = user_agent.reset(instruction="I want to cancel my flight")

# Interact
response = user_agent.step("Sure, can I have your booking ID?")
```

## Testing & Reproduction

To reproduce original tau-bench results:

1. **Setup**:
```bash
pip install litellm  # Required for original tau-bench
```

2. **Run with original models**:
```python
benchmark = TauBenchBenchmark(
    domain="airline",
    user_model="gpt-4o",  # Original user model
    user_strategy="llm",
)
# Test with GPT-4o as assistant
# Results should match original tau-bench leaderboard
```

3. **Compare results**:
   - Airline domain baseline (gpt-4o): ~46% Pass@1
   - Retail domain baseline (gpt-4o): ~69% Pass@1

## Data Files

Task definitions and policies are copied from the original tau-bench:

- `envs/airline/tasks.py`: 100 airline customer service tasks
- `envs/airline/wiki.md`: Airline policy guidelines
- `envs/retail/tasks*.py`: Retail tasks (train/test/dev splits)
- `envs/retail/wiki.md`: Retail policy guidelines

## Dependencies

- **CAMEL**: Core agent framework
- **litellm**: For original tau-bench compatibility (optional)
- **Original tau-bench**: Can be installed alongside for full compatibility

## Limitations & Future Work

Current implementation:
- ✅ Clean architecture with separated components
- ✅ Embedded task data
- ✅ Independent user agent
- ⚠️ Uses original tau-bench agent implementation (not CAMEL agent yet)

Future improvements:
- [ ] Full CAMEL agent integration (replace tau-bench agent)
- [ ] Native tool calling without litellm dependency
- [ ] More sophisticated evaluation metrics
- [ ] Extended to tau²-bench (dual-control environments)

## References

- **Original Tau-Bench**: https://github.com/sierra-research/tau-bench
- **Paper**: https://arxiv.org/abs/2406.12045
- **Leaderboard**: https://taubench.com
- **CAMEL**: https://github.com/camel-ai/camel

## Citation

```bibtex
@article{taubench2024,
  title={$\tau$-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains},
  journal={arXiv preprint arXiv:2406.12045},
  year={2024}
}
```

## License

Apache 2.0 (consistent with CAMEL and original tau-bench)
