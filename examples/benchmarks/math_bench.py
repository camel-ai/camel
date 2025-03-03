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
from pathlib import Path

from camel.agents import ChatAgent
from camel.benchmarks import Mode
from camel.benchmarks.math_benchmarks.math_bench import MATHBenchmark

# Set up the agent to be benchmarked
agent = ChatAgent()

# Set up the Hendrykson MATH Benchmark
benchmark = MATHBenchmark(
    data_dir="MATH-Data", save_to="MATHResults"
    )
benchmark.download()

# Run the benchmark to get results
benchmark = benchmark.run(agent, on="test", subset=10)

total_answers = len(benchmark.results)
correct_answers = sum(row["correct"] for row in benchmark.results)

print("Total:", total_answers)
print("Correct:", correct_answers)
'''
===============================================================================
Total: 10
Correct: 9
===============================================================================
'''