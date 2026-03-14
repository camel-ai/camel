# Benchmark Running Cookbook

This cookbook shows a practical workflow for running CAMEL benchmarks and
comparing agent behaviors in a reproducible way.

## 1. Environment setup

```bash
uv sync --extra all
cp .env.example .env
```

Configure your model credentials in `.env` (for example `OPENAI_API_KEY`).

## 2. Pick a benchmark

CAMEL includes benchmark examples in `examples/benchmarks/`:

- `apibank.py`
- `apibench.py`
- `gaia.py`
- `nexus.py`
- `ragbench.py`
- `browsecomp_*.py`

## 3. Run a quick benchmark

```bash
uv run python examples/benchmarks/apibank.py
```

The script writes JSONL output (for example `APIBankResults.jsonl`) with
evaluation results.

## 4. Run GAIA benchmark (tool-using agent)

`examples/benchmarks/gaia.py` uses a Docker runtime for tool execution.

```bash
cd examples/runtimes/ubuntu_docker_runtime
./manage_camel_docker.sh build
cd ../../../
uv run python examples/benchmarks/gaia.py
```

## 5. Compare benchmark runs

Store each run in a different JSONL file (for example by model or prompt
variant), then compare key fields such as:

- `total`
- `correct`
- any benchmark-specific score fields

## 6. Tips for reproducibility

- keep `subset` fixed while iterating quickly
- pin model names and important generation settings
- commit benchmark scripts/config changes together with results metadata

## Related examples

- `examples/benchmarks/apibank.py`
- `examples/benchmarks/gaia.py`
- `examples/benchmarks/ragbench.py`
