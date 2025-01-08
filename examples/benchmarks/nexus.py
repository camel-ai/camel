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

from camel.agents import ChatAgent
from camel.benchmarks import NexusBenchmark
from camel.benchmarks.nexus import construct_tool_descriptions

# Set up the agent to be benchmarked
agent = ChatAgent()

# Set up the Nexusraven Function Calling Benchmark
benchmark = NexusBenchmark(
    data_dir="NexusDatasets", save_to="NexusResults.jsonl"
)

# Download the benchmark data
benchmark.download()

# Set the task (sub-dataset) to be benchmarked
task = "OTX"

# Please note that the following step is only for demostration purposes,
# it has been integrated into the run method of the benchmark.
# The tools fetched here are used to construct the prompt for the task,
# which will be passed to the agent for response.
tools = construct_tool_descriptions(task)
print('\nTool descriptions for the task:\n', tools)

# Run the benchmark
result = benchmark.run(agent, task, subset=10)
print("Total:", result["total"])
print("Correct:", result["correct"])
