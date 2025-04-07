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
from camel.benchmarks import APIBankBenchmark
from camel.benchmarks.apibank import Evaluator

# Set up the agent to be benchmarked
agent = ChatAgent()

# Set up the APIBench Benchmark
# Please note that the data_dir is predefined
# for better import management of the tools
benchmark = APIBankBenchmark(save_to="APIBankResults.jsonl")

# Download the benchmark data
benchmark.download()

# Set the subset to be benchmarked
level = 'level-1'

# NOTE: You might encounter the following error when
# running the benchmark in Windows:
# UnicodeDecodeError: 'charmap' codec can't decode byte 0x81
# in position 130908: character maps to <undefined>
# To solve this issue, you can navigate to the file
# api_bank/tool_manager.py", line 30 and change the encoding
# with open(os.path.join(init_database_dir, file), 'r',
# encoding='utf-8') as f:


# Run the benchmark
result = benchmark.run(agent, level, api_test_enabled=True, subset=10)

# The following steps are only for demonstration purposes,
# they have been integrated into the run method of the benchmark.
# Get the first example of the test data
example_test = list(benchmark._data.items())[0]  # type: ignore[assignment] # noqa: RUF015
evaluator = Evaluator(example_test)
api_description = evaluator.get_api_description('ToolSearcher')
print('\nAPI description for ToolSearcher:\n', api_description)
'''
===============================================================================
API description for ToolSearcher:
 {"name": "ToolSearcher", "description": "Searches for relevant tools in 
 library based on the keywords.", "input_parameters": {"keywords": {"type": 
 "str", "description": "The keyword to search for."}}, 
 "output_parameters": 
 {"best_matchs": {"type": "Union[List[dict], dict]", 
 "description": "The best match tool(s)."}}}
===============================================================================
'''

# Print the final results
print("Total:", result["total"])
print("Correct:", result["correct"])
'''
===============================================================================
Total: 24
Correct: 10
===============================================================================
'''
