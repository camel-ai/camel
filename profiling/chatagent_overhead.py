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
"""Benchmark: Measure ChatAgent overhead vs direct OpenAI API calls.

This script measures the overhead introduced by ChatAgent compared to
direct OpenAI API calls. It tests three scenarios:
- basic: Simple text generation
- with_tools: Using MathToolkit tools
- structured_output: Using structured output with Pydantic models

Usage:
    python chatagent_overhead.py --num-runs 20 --output results.json
"""

import argparse
import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

from openai import OpenAI
from pydantic import BaseModel, Field

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import MathToolkit
from camel.types import ModelPlatformType

MODEL = "gpt-4.1-mini-2025-04-14"
PROMPT = "Count from 1 to 10. Format: 1, 2, 3, ..."
TOOL_PROMPT = "What is 123.45 + 678.90?"
STRUCTURED_PROMPT = "Tell me a short joke."


class JokeResponse(BaseModel):
    """Structured response format for jokes."""

    joke: str = Field(description="The joke text")
    funny_level: int = Field(description="Funny level from 1 to 10")


def run_single_benchmark(
    num_runs: int = 20,
    with_tools: bool = False,
    with_structured_output: bool = False,
    quiet: bool = False,
) -> dict:
    """Run a single benchmark configuration.

    Args:
        num_runs: Number of test iterations.
        with_tools: If True, test with MathToolkit tools.
        with_structured_output: If True, test with structured output.
        quiet: If True, suppress per-run output.

    Returns:
        Dictionary containing benchmark results.
    """
    client = OpenAI()
    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=MODEL,
        client=client,
    )

    # Patch client to measure API call time
    original_create = client.chat.completions.create
    original_parse = client.beta.chat.completions.parse
    api_call_times = []
    tool_exec_times = []

    def timed_create(*args, **kwargs):
        start = time.perf_counter()
        result = original_create(*args, **kwargs)
        api_call_times.append(time.perf_counter() - start)
        return result

    def timed_parse(*args, **kwargs):
        start = time.perf_counter()
        result = original_parse(*args, **kwargs)
        api_call_times.append(time.perf_counter() - start)
        return result

    client.chat.completions.create = timed_create
    client.beta.chat.completions.parse = timed_parse

    # Setup tools
    tools = MathToolkit().get_tools() if with_tools else None
    agent = ChatAgent(model=model, tools=tools)

    # Patch FunctionTool.func to measure tool execution time
    if tools:
        for tool in tools:
            original_func = tool.func

            def make_timed_func(orig):
                def timed_func(*args, **kwargs):
                    start = time.perf_counter()
                    result = orig(*args, **kwargs)
                    tool_exec_times.append(time.perf_counter() - start)
                    return result

                return timed_func

            tool.func = make_timed_func(original_func)

    # Determine mode and prompt
    if with_tools:
        mode = "with_tools"
        prompt = TOOL_PROMPT
        response_format = None
    elif with_structured_output:
        mode = "structured_output"
        prompt = STRUCTURED_PROMPT
        response_format = JokeResponse
    else:
        mode = "basic"
        prompt = PROMPT
        response_format = None

    overhead_times = []
    api_call_counts = []
    expected_api_calls = 2 if with_tools else 1

    if not quiet:
        print(f"Running {num_runs} tests ({mode})...\n")

    # Warmup run to eliminate cold start overhead
    agent.step(
        input_message=f"warmup {prompt}", response_format=response_format
    )
    agent.reset()
    api_call_times.clear()
    tool_exec_times.clear()
    if not quiet:
        print("Warmup done.\n")

    for i in range(num_runs):
        api_call_times.clear()
        tool_exec_times.clear()
        start = time.perf_counter()
        response = agent.step(
            input_message=f"{i} {prompt}",
            response_format=response_format,
        )
        total_time = time.perf_counter() - start
        agent.reset()

        api_total = sum(api_call_times)
        tool_total = sum(tool_exec_times)
        overhead = total_time - api_total - tool_total
        overhead_times.append(overhead)
        api_call_counts.append(len(api_call_times))

        if not quiet:
            api_calls_str = (
                f"api={api_total:.3f}s ({len(api_call_times)} calls)"
            )
            if with_tools:
                print(
                    f"Run {i + 1:2d}/{num_runs}: "
                    f"total={total_time:.3f}s, {api_calls_str}, "
                    f"tool={tool_total * 1000:.2f}ms, "
                    f"overhead={overhead * 1000:.1f}ms"
                )
            else:
                print(
                    f"Run {i + 1:2d}/{num_runs}: "
                    f"total={total_time:.3f}s, {api_calls_str}, "
                    f"overhead={overhead * 1000:.1f}ms"
                )

            # Show details on first run
            if i == 0:
                if with_tools:
                    tool_calls = response.info.get("tool_calls", [])
                    if tool_calls:
                        names = [tc.tool_name for tc in tool_calls]
                        print(f"    Tool calls: {names}")
                elif with_structured_output and response.msgs:
                    content = response.msgs[0].content or ""
                    preview = (
                        content[:80] + "..." if len(content) > 80 else content
                    )
                    print(f"    Response: {preview}")

    # Calculate statistics
    avg_overhead = statistics.mean(overhead_times)
    std_overhead = (
        statistics.stdev(overhead_times) if len(overhead_times) > 1 else 0.0
    )
    min_overhead = min(overhead_times)
    max_overhead = max(overhead_times)

    if not quiet:
        print(f"\n{'=' * 50}")
        print(
            f"ChatAgent overhead ({mode}): "
            f"{avg_overhead * 1000:.2f}ms (stdev: {std_overhead * 1000:.2f}ms)"
        )

    # Check API call counts
    invalid_call_counts = [
        c for c in api_call_counts if c != expected_api_calls
    ]

    return {
        "avg_overhead_ms": avg_overhead * 1000,
        "std_overhead_ms": std_overhead * 1000,
        "min_overhead_ms": min_overhead * 1000,
        "max_overhead_ms": max_overhead * 1000,
        "expected_api_calls": expected_api_calls,
        "invalid_api_call_runs": len(invalid_call_counts),
    }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Benchmark ChatAgent overhead vs direct OpenAI API calls."
    )
    parser.add_argument(
        "--num-runs",
        type=int,
        default=20,
        help="Number of test iterations per benchmark (default: 20)",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file path for JSON results",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-run output",
    )

    args = parser.parse_args()

    # Build results
    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "benchmark": "chatagent_overhead",
        "num_runs": args.num_runs,
        "metrics": {},
    }

    # Run all three benchmark modes
    for mode_config in [
        {
            "name": "basic",
            "with_tools": False,
            "with_structured_output": False,
        },
        {
            "name": "with_tools",
            "with_tools": True,
            "with_structured_output": False,
        },
        {
            "name": "structured_output",
            "with_tools": False,
            "with_structured_output": True,
        },
    ]:
        if not args.quiet:
            print(f"\n{'=' * 60}")

        result = run_single_benchmark(
            num_runs=args.num_runs,
            with_tools=mode_config["with_tools"],
            with_structured_output=mode_config["with_structured_output"],
            quiet=args.quiet,
        )
        results["metrics"][mode_config["name"]] = result

    # Output results
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)
        if not args.quiet:
            print(f"\nResults saved to: {args.output}")
    else:
        print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
