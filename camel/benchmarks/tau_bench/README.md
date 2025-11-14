# Tau-Bench Integration with CAMEL

This module integrates the Tau-Bench benchmark into CAMEL for evaluating tool-agent-user interaction.

## Overview

Tau-Bench (τ-bench) tests agents on realistic customer service scenarios where they must:
- Use domain-specific API tools
- Follow policy guidelines
- Interact naturally with simulated users
- Complete user goals effectively

## Architecture

```
camel/benchmarks/tau_bench/
├── __init__.py              # Exports: TauBenchBenchmark
├── types.py                 # Core types (Task, TaskResult, etc.)
├── benchmark.py             # Main TauBenchBenchmark class
├── user_agent.py            # User simulation agents (independent)
├── envs/
│   ├── airline/
│   │   ├── tasks.py        # Task definitions (from original)
│   │   └── wiki.md         # Policy guidelines (from original)
│   └── retail/
│       ├── tasks*.py       # Task definitions (from original)
│       └── wiki.md         # Policy guidelines (from original)
```

## Key Design Principles

1. **Clean Export**: Only `TauBenchBenchmark` is exported from the package
2. **Separated Agents**: User agent and assistant agent are independently callable
3. **Data Integration**: Task and wiki files are embedded from original tau-bench
4. **Test-Friendly**: Easy to test and reproduce original tau-bench results

## Usage

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
