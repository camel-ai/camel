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

from dotenv import load_dotenv

from camel.agents import ChatAgent
from camel.benchmarks import APIBankBenchmark
from camel.benchmarks.apibank import Evaluator

# Load environment variables from the .env file
load_dotenv()


# Set up the agent to be benchmarked
agent = ChatAgent()

# Set up the APIBench Benchmark
# Please note that the data_dir is predefined
# for better import management of the tools
benchmark = APIBankBenchmark(save_to="APIBankResults.jsonl")

# Download the benchmark data
# benchmark.download()

# Set the subset to be benchmarked
level = 'level-1'

# Run the benchmark
result = benchmark.run(agent, level, api_test_enabled=True, subset=10)

# The following steps are only for demostration purposes,
# they have been integrated into the run method of the benchmark.

# Get the first example of the test data
example_test = next(benchmark._data.items())
evaluator = Evaluator(example_test)
api_description = evaluator.get_api_description('ToolSearcher')
print('\nAPI description for ToolSearcher:\n', api_description)

# Print the final results
print("Total:", result["total"])
print("Correct:", result["correct"])
