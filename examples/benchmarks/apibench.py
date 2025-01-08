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
from camel.benchmarks import APIBenchBenchmark

# Set up the agent to be benchmarked
agent = ChatAgent()

# Set up the APIBench Benchmark
benchmark = APIBenchBenchmark(
    data_dir="APIBenchDatasets", save_to="APIBenchResults.jsonl"
)

# Download the benchmark data
benchmark.download()

# Set the subset to be benchmarked
subset_name = 'torchhub'

# Run the benchmark
result = benchmark.run(agent, subset_name, subset=10)

# Please note that APIBench does not use 'real function call'
# but instead includes API documentation in the questions
# for the agent to refernce.
# An example question including the API documentation is printed below.
print(
    "\nExample question including API documentation:\n",
    benchmark._data['questions'][0]['text'],
)

print("Total:", result["total"])
print("Correct:", result["correct"])
print("Hallucination:", result["hallucination"])
