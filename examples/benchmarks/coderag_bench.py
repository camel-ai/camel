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

from camel.benchmarks import CodeRagBenchmark
from camel.agents import ChatAgent
from camel.retrievers import AutoRetriever

assistant_sys_msg = """You are a helpful assistant to write codes,
         I will give you the Original Coding Query and Retrieved Context,
        answer the Original Coding Query based on the Retrieved Context,
        if you can't answer the question, just leave it blank"""
agent = ChatAgent(assistant_sys_msg)
retriever = AutoRetriever()


benchmark = CodeRagBenchmark(
    data_dir="./CodeRag_Bench_Datasets",
    save_to="./CodeRag_Bench_Datasets",
    retriever=retriever,
    run_mode = 'retrieve_generate',
    task = 'humaneval',
    subset_size = 10,
    retrieval_type = "canonical",
    allow_code_execution = True,
    )
benchmark.load()
benchmark.run(agent, retriever)
