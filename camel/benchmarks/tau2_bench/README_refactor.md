# CAMEL τ²-Bench Refactor Plan

This directory contains the vendored sources and datasets from the upstream
[`tau2-bench`](https://github.com/sierra-research/tau2-bench) repository.  The
goal is to mirror the refactor we performed for the original τ-bench
(`camel/camel/benchmarks/tau_bench`) while extending it to the new τ² feature
set (telecom domain, user tools, RL-friendly splits, gym wrappers, etc.).

## Current status

* `tau2/` – direct copy of the upstream `src/tau2` package so we can re-use the
  orchestrator, environment definitions, evaluation pipeline, etc.
* `data/` – upstream datasets (`/tau2/domains/*`, user simulator guidelines,
  telemetry stubs, etc.) copied verbatim so the benchmark can run without an
  external checkout.
* `adapters.py` – bridges CAMEL `ChatAgent` instances with τ²'s `BaseAgent` and
  `BaseUser` interfaces. Tool calls are surfaced through CAMEL's external tool
  mechanism and replayed through the τ² orchestrator.
* `benchmark.py` – concrete `Tau2BenchBenchmark` that implements the CAMEL
  `BaseBenchmark` API. It mirrors the τ² CLI parameters, launches the native
  τ² orchestrator/evaluator, and records metrics via `compute_metrics`.
* `examples/benchmarks/tau2_bench.py` – runnable example that evaluates
  GPT-4o-mini on three airline tasks with a GPT-4.1-mini user simulator.

## Integration roadmap

1. **Agent/User adapters** ✅ – `CamelTau2Agent` and `CamelTau2User` adapt
   CAMEL's runtime to τ²'s orchestrator without bypassing tool execution. τ²
   tools are registered as CAMEL *external* tools so function-call payloads are
   forwarded rather than executed locally.
2. **Data directory plumbing** ✅ – `tau2.utils.utils.DATA_DIR` now falls back to
   `camel/benchmarks/tau2_bench/data`, meaning no environment variables are
   required.
3. **Benchmark runner** ✅ – `Tau2BenchBenchmark` clones the evaluation agent
   per task/trial, creates CAMEL-powered user simulators, runs the canonical τ²
   orchestrator/evaluator, and writes the resulting `Results` JSON next to the
   provided `save_to` directory.
4. **Examples and docs** – mirror `examples/benchmarks/tau_bench.py` with a
   τ² version plus usage notes in `docs/`. The example script is in place;
   documentation updates are planned next.

## Next steps

* Wire the new benchmark into the longer-form documentation (`docs/`) and add
  guidance for mapping τ² CLI flags to `Tau2BenchBenchmark.run`.
* Stress-test telecom/user-tool heavy runs and capture best practices for
  prompt design inside the docs.
