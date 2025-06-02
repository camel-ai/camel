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
from camel.benchmarks import DefaultGAIARetriever, GAIABenchmark
from camel.models import ModelFactory
from camel.runtimes import RemoteHttpRuntime
from camel.toolkits import CodeExecutionToolkit
from camel.types import ModelPlatformType, ModelType, StorageType

retriever = DefaultGAIARetriever(
    vector_storage_local_path="local_data2/", storage_type=StorageType.QDRANT
)

benchmark = GAIABenchmark(
    data_dir="datasets_test",
    processes=1,
    save_to="results.jsonl",
    retriever=retriever,
)

print(f"Number of validation examples: {len(benchmark.valid)}")
print(f"Number of test examples: {len(benchmark.test)}")


toolkit = CodeExecutionToolkit(verbose=True)
runtime = RemoteHttpRuntime("localhost").add(
    toolkit.get_tools(),
    "camel.toolkits.CodeExecutionToolkit",
)

task_prompt = """
        You are a general AI assistant. I will ask you a question. Report your
        thoughts, and finish your answer with the following template:
        FINAL ANSWER: [YOUR FINAL ANSWER].
        YOUR FINAL ANSWER should be a number OR as few words as possible OR a
        comma separated list of numbers and/or strings.
        If you are asked for a number, don't use comma to write your number
        neither use units such as $ or percent sign unless specified otherwise.
        If you are asked for a string, don't use articles, neither
        abbreviations (e.g. for cities), and write the digits in plain text
        unless specified otherwise.
        If you are asked for a comma separated list, apply the above rules
        depending of whether the element to be put in the list is a number or
        a string.
        """.strip()

tools = runtime.get_tools()

model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
)


agent = ChatAgent(
    task_prompt,
    model,
    tools=tools,
)

result = benchmark.run(agent, "valid", level="all", subset=3)
print("correct:", result["correct"])
print("total:", result["total"])

# ruff: noqa: E501
"""
Number of validation examples: 165
Number of test examples: 300
correct: 0
total: 3
"""
