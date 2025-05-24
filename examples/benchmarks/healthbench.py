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
from camel.benchmarks.healthbench import HealthBenchmark

if __name__ == "__main__":

    # Define the assistant agent (medical assistant persona)
    agent = ChatAgent(
        system_message="You are a helpful medical assistant."
    )

    # Define the grader agent (strict rubric evaluator)
    grader = ChatAgent(
        system_message="You are a strict evaluator. Carefully judge whether the assistant meets the rubric criteria.",
    )

    # Run HealthBench evaluation
    benchmark = HealthBenchmark(data_dir=".", save_to="results.jsonl")

    result = benchmark.run(
        agent=agent,
        grader=grader,
        variant="test",
        randomize=False,
        subset=1
    )

    print("Evaluation complete.")
    print("Score summary:", result)
