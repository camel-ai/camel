# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========

import os
import sys

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
)

from camel.agents import ChatAgent
from camel.benchmarks import TerminalBenchBenchmark

# Set up the agent
agent = ChatAgent()

# Set up the TerminalBench Benchmark
benchmark = TerminalBenchBenchmark(
    data_dir="TerminalBenchDataset",
    save_to="TerminalBenchResults.jsonl",
    processes=1,
    # category="shell",  # optional filter by tag
    # difficulty="easy",  # optional filter by difficulty
)

# Download the benchmark data
benchmark.download()

# Run the benchmark: randomize tasks and run a subset of 10
result = benchmark.run(agent, randomize=True, subset=10)

# Print results summary
print("Terminal-Bench Results:")
print(f"Total tasks: {result['total']}")
print(f"Success: {result['success']}")
print(f"Failure: {result['failure']}")
print(f"Success rate: {result['success_rate']:.1%}")
