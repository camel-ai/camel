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

from camel.agents import ChatAgent
from camel.benchmarks import NexusBenchmark

# Set up the agent to be benchmarked
agent = ChatAgent()

# Set up the Nexusraven Function Calling Benchmark
benchmark = NexusBenchmark(
    save_to="NexusResults.jsonl", processes=1
)

# Load the benchmark 
benchmark.load(name = "Nexusflow/CVECPEAPIBenchmark")

result = benchmark.run(agent)
print("Total:", result["total"])
print("Correct:", result["correct"])
'''
===============================================================================
Total: 10
Correct: 9
===============================================================================
'''
