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
from camel.societies.workforce.workforce_agent import WorkforceAgent

if __name__ == "__main__":

    # Single Agent Example
    # agent = ChatAgent(
    #     system_message="You are a helpful medical assistant."
    # )

    # Workforce Example
    # This example creates a medical workforce with three roles: Proposer, Critic and Finalizer.
    medical_task_instruction = (
        "You are a collaborative team tasked with answering a medical question step by step:\n"
        "1. The Proposer drafts an initial answer to the question.\n"
        "2. The Critic reviews and comments on the draft for errors, missing info, or unsafe suggestions.\n"
        "3. The Finalizer integrates the Critic's feedback to produce a final, polished answer."
    )

    PROPOSER_PROMPT = (
        "You are a diligent medical assistant (Proposer) whose job is to draft a complete, helpful, and safe answer to the user's medical question."
    )
    CRITIC_PROMPT = (
        "You are a medical safety and accuracy reviewer (Critic). Review the Proposer's draft answer, pointing out any mistakes, dangerous advice, or missing important medical details."
    )
    FINALIZER_PROMPT = (
        "You are a senior medical assistant (Finalizer). Carefully integrate the Critic's feedback to produce a final, clear, medically sound answer for the user."
    )

    agents_config = [
        {'agent': ChatAgent(system_message=PROPOSER_PROMPT), 'description': "Proposer"},
        {'agent': ChatAgent(system_message=CRITIC_PROMPT), 'description': "Critic"},
        {'agent': ChatAgent(system_message=FINALIZER_PROMPT), 'description': "Finalizer"}
    ]
    
    medical_workforce = WorkforceAgent(
        agents_config=agents_config,
        workforce_name="Medical Committee",
        task_instruction=medical_task_instruction
    )

    # Define the grader agent (strict rubric evaluator)
    grader = ChatAgent(
        system_message="You are a strict evaluator. Carefully judge whether the assistant meets the rubric criteria.",
    )

    # Run HealthBench evaluation
    benchmark = HealthBenchmark(data_dir=".", save_to="example/benchmarks/health_results.jsonl")

    result = benchmark.run(
        agent=medical_workforce,
        grader=grader,
        variant="test",
        randomize=False,
        subset=1
    )

    print("Evaluation complete.")
    print("Score summary:", result)
