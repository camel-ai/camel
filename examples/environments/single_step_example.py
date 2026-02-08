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
import asyncio
import random

from camel.datasets import StaticDataset
from camel.environments.models import Action
from camel.environments.single_step import SingleStepEnv
from camel.verifiers import MathVerifier


async def run_batch_qa():
    r"""Run a batch of QA examples with SingleStepEnv.

    This example uses a static dataset of simple math questions and
    demonstrates how to set up a SingleStepEnv, reset it with a batch,
    and process the responses with a basic verifier.
    """
    # Create a simple dataset of math questions
    data = [
        {
            "question": "What is 2 + 2?",
            "final_answer": "4",
            "rationale": "Adding 2 and 2 gives 4.",
        },
        {
            "question": "What is 5 * 3?",
            "final_answer": "15",
            "rationale": "Multiplying 5 and 3 gives 15.",
        },
        {
            "question": "What is 10 - 7?",
            "final_answer": "3",
            "rationale": "Subtracting 7 from 10 gives 3.",
        },
        {
            "question": "What is 20 / 4?",
            "final_answer": "5",
            "rationale": "Dividing 20 by 4 gives 5.",
        },
    ]

    # Create a static dataset from our questions
    dataset = StaticDataset(data)

    # Create a simple verifier that checks for exact matches
    verifier = MathVerifier()

    # Initialize the environment with our dataset and verifier
    env = SingleStepEnv(dataset=dataset, verifier=verifier)

    # Set up the environment
    await env.setup()
    print("Environment setup complete")

    # Reset environment and get initial observation for batch size 2
    # This will randomly sample 2 questions from our dataset
    observations = await env.reset(batch_size=2, seed=42)

    print("Initial Observations:\n")
    for i, obs in enumerate(observations):
        print(f"Question {i+1}: {obs.question}\n")

    # Simulate responses for each question in the batch
    # In real scenarios, these responses would come from an LLM

    # In this example, we'll simulate both correct and incorrect answers
    responses = [
        "4",  # Correct answer for "2 + 2"
        "16",  # Wrong answer for the second question
    ]

    actions = [
        Action(index=0, llm_response=responses[0]),
        Action(index=1, llm_response=responses[1]),
    ]

    # Submit the actions to the environment and get results
    results = await env.step(actions)

    # Process the results
    print("\nResults:")
    for i, (_observation, reward, done, info) in enumerate(results):
        print(f"\nQuestion {i+1}:")
        print(f"  Response: \"{info['proposed_solution']}\"")
        print(f"  Verification: {info['verification_result'].status}")
        print(f"  Reference Answer: {info['state'].final_answer}")
        print(f"  Reward: {reward}")
        print(f"  Done: {done}")

    # Reset for another batch with batch_size=1
    print("\nResetting for a single question...")
    observation = await env.reset(batch_size=1, seed=84)
    print(f"New question: {observation.question}")

    # Simulate a random response
    response = random.choice(["3", "4", "5"])
    action = Action(
        llm_response=response
    )  # For batch_size=1, index defaults to 0

    # Submit the action and get results
    result = await env.step(action)
    _observation, reward, done, info = result

    print("\nSingle question result:")
    print(f"  Response: \"{info['proposed_solution']}\"")
    print(f"  Verification: {info['verification_result'].status}")
    print(f"  Reference Answer: {info['state'].final_answer}")
    print(f"  Reward: {reward}")
    print(f"  Done: {done}")

    # Clean up
    await env.close()
    print("\nEnvironment closed")


if __name__ == "__main__":
    asyncio.run(run_batch_qa())
