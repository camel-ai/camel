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
import os

from camel.agents import ChatAgent
from camel.configs import DeepSeekConfig
from camel.datasets.medicine import MedicalDataset, load_json_data
from camel.environments import MedicalEnvironment
from camel.environments.base import Action
from camel.extractors import BoxedTextExtractor
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.verifiers import MedicalVerifier

"""
This example demonstrates how to use the DeepSeek Reasoner model
for medical diagnosis.
The model is prompted to provide a diagnosis for a medical case, 
and the diagnosis
is extracted from the boxed text in the response. 
The extracted diagnosis is then
verified against the ground truth.

Please set the below environment variables:
export DEEPSEEK_API_KEY=""
export GET_REASONING_CONTENT="true"
"""


async def main():
    # Load medical dataset
    data_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "datasets",
        "medicine",
        "example_data",
        "RDC.json",
    )

    print(f"Attempting to load data from: {data_path}")

    try:
        raw_data = load_json_data(data_path)
        dataset = MedicalDataset(raw_data)
        await dataset.setup()
        print(f"Dataset size: {len(dataset)}")
    except Exception as e:
        print(f"Error loading dataset: {e}")

    # Create DeepSeek Reasoner model
    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEEPSEEK,
        model_type=ModelType.DEEPSEEK_REASONER,
        model_config_dict=DeepSeekConfig(temperature=0.2).as_dict(),
    )

    # Define system message for medical reasoning
    reason_agent_system_message = """You are a medical expert tasked 
    with diagnosing medical conditions based on case reports and test results.
Analyze the provided information carefully and provide your diagnosis.
Give your final answer within \\boxed{} notation.
For example, if your diagnosis is 'Common Cold', 
write your final answer as: \\boxed{Common Cold}"""

    # Create agent
    reason_agent = ChatAgent(
        system_message=reason_agent_system_message, model=model
    )

    # Create extractor, verifier, and environment
    extractor = BoxedTextExtractor()
    verifier = MedicalVerifier(exact_match=False, case_sensitive=False)
    environment = MedicalEnvironment(
        dataset=dataset,
        verifier=verifier,
        extractor=extractor,
        reward_correct=1.0,
        reward_incorrect=-0.5,
        reward_no_answer=-0.2,
    )

    # Setup components
    await extractor.setup()
    await verifier.setup()
    await environment.setup()

    try:
        # Run a few examples
        num_examples = min(5, len(dataset))
        total_reward = 0.0
        correct_count = 0

        for i in range(num_examples):
            # Reset environment to get a new medical case
            observation = await environment.reset()

            # Get the medical case
            medical_case = observation.question

            # Get the ground truth
            ground_truth = environment._current_data_point.final_answer

            print(f"\n\n{'='*80}")
            print(f"Example {i+1}/{num_examples}")
            print(f"{'='*80}")
            print(f"Medical Case:\n{medical_case}")
            print(f"{'='*80}")
            print(f"Ground Truth: {ground_truth}")

            # Get response from the agent
            response = reason_agent.step(medical_case)
            agent_response = response.msgs[0].content

            print(f"{'='*80}")
            print(f"Agent Response:\n{agent_response}")

            # Create action
            action = Action(
                problem_statement=medical_case,
                llm_response=agent_response,
                final_answer=ground_truth,
            )

            # Take a step in the environment
            step_result = await environment.step(action)

            # Extract diagnosis
            extracted_diagnosis = await extractor.extract(agent_response)

            print(f"{'='*80}")
            print(f"Extracted Diagnosis: {extracted_diagnosis}")
            print(f"Reward: {step_result.reward}")
            print(f"{'='*80}\n")

            # Update statistics
            total_reward += step_result.reward
            if (
                "diagnosis_accuracy" in step_result.rewards_dict
                and step_result.rewards_dict["diagnosis_accuracy"] > 0
            ):
                correct_count += 1

        # Print summary
        print(f"\n{'='*80}")
        print("Summary:")
        print(f"{'='*80}")
        print(f"Total examples: {num_examples}")
        print(f"""Correct diagnoses: {correct_count}/{num_examples} 
        ({correct_count/num_examples*100:.2f}%)""")
        print(f"Total reward: {total_reward}")
        print(f"Average reward: {total_reward/num_examples:.2f}")
        print(f"{'='*80}")

    finally:
        # Clean up
        await extractor.cleanup()
        await verifier.cleanup()
        await environment.teardown()


if __name__ == "__main__":
    asyncio.run(main())
