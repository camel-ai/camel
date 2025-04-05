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
from datetime import datetime
from typing import List

from pydantic import ValidationError

from camel.agents import ChatAgent
from camel.interpreters import SubprocessInterpreter
from camel.logger import get_logger
from camel.models.base_model import BaseModelBackend

from .base_generator import BaseGenerator
from .models import DataPoint
from .static_dataset import StaticDataset

logger = get_logger(__name__)

SYSTEM_PROMPT = """**You are an advanced data generation assistant.**  
Your goal is to generate high-quality synthetic data points based on 
provided examples. Your output must be well-structured, 
logically sound, and formatted correctly. 

**Instructions:**
1. **Follow the Structure**  
   Each data point must include:  
   - **Question**: A clear, well-formed query.  
   - **Rationale**: A step-by-step, executable reasoning process ending 
   with `print(final_answer)`.  
   - **Final Answer**: The correct, concise result.  

2. **Ensure Logical Consistency**  
   - The `rationale` must be code that runs correctly.  
   - The `final_answer` should match the printed output.  

3. **Output Format (Strict)**  
```
Question: [Generated question]
Rationale: [Code that solves the question, ending in a print statement,
outputting the answer.]
Final Answer: [The Final Answer]

**Now, generate a new data point based on the given examples.**
"""


class FewShotGenerator(BaseGenerator):
    r"""A generator for creating synthetic datapoints using few-shot learning.

    This class leverages a seed dataset, an agent, and a verifier to generate
    new synthetic datapoints on demand through few-shot prompting.
    """

    def __init__(
        self,
        seed_dataset: StaticDataset,
        model: BaseModelBackend,
        seed: int = 42,
        **kwargs,
    ):
        r"""Initialize the few-shot generator.

        Args:
            seed_dataset (StaticDataset): Validated static dataset to
                use for examples.
            model (BaseModelBackend): The underlying LLM that the generating
            agent will be initiated with.
            seed (int): Random seed for reproducibility. (default: :obj:`42`)
            **kwargs: Additional generator parameters.
        """
        super().__init__(seed=seed, **kwargs)
        self.seed_dataset = seed_dataset
        try:
            self._validate_seed_dataset()
        except Exception:
            raise RuntimeError("Seed Data does not follow Datapoint format")
        self.agent = ChatAgent(system_message=SYSTEM_PROMPT, model=model)

        self.interpreter = SubprocessInterpreter(
            require_confirm=False,  # No confirmation prompts
            print_stdout=False,  # Suppress stdout unless needed
            print_stderr=True,  # Show errors for debugging
            execution_timeout=30,  # Set a timeout to prevent hanging
        )

    # TODO: Validate that seed dataset contains rationale
    def _validate_seed_dataset(self) -> None:
        """
        Validate that all datapoints in the seed dataset have a rationale.

        Raises:
            ValueError: If any datapoint in the seed dataset has a None
                rationale, with a message listing the indices of the
                offending datapoints.
        """
        missing_indices = [
            idx
            for idx, datapoint in enumerate(self.seed_dataset.data)
            if datapoint.rationale is None
        ]
        if missing_indices:
            raise ValueError(
                f"Seed dataset contains datapoints without rationale "
                f"at indices: {missing_indices}"
            )

    def _construct_prompt(self, examples: List[DataPoint]) -> str:
        r"""Construct a prompt for generating new datapoints
        using a fixed sample of examples from the seed dataset.

        Args:
            examples (List[DataPoint]): Examples to include in the prompt.

        Returns:
            str: Formatted prompt with examples.
        """
        prompt = (
            "Generate a new datapoint similar to the following examples:\n\n"
        )
        for i, example in enumerate(examples, 1):
            prompt += f"Example {i}:\n"
            prompt += f"Question: {example.question}\n"
            if example.rationale is not None:
                prompt += f"Rationale: {example.rationale}\n"
            else:
                prompt += "Rationale: None\n"
            prompt += f"Final Answer: {example.final_answer}\n\n"
        prompt += "New datapoint:"
        return prompt

    async def generate_new(
        self,
        n: int,
        max_retries: int = 10,
        num_examples: int = 3,
        **kwargs,
    ) -> None:
        r"""Generates and validates `n` new datapoints through
        few-shot prompting, with a retry limit.

        Steps:
            1. Samples examples from the seed dataset.
            2. Constructs a prompt using the selected examples.
            3. Uses an agent to generate a new datapoint,
            consisting of a question and code to solve the question.
            4. Executes code using the subprocess interpreter to get pseudo
                ground truth.
            5. Stores valid datapoints in memory.

        Args:
            n (int): Number of valid datapoints to generate.
            max_retries (int): Maximum number of retries before stopping.
                (default: :obj:`10`)
            num_examples (int): Number of examples to sample from the
            seed dataset for few shot prompting.
                (default: :obj:`3`)
            **kwargs: Additional generation parameters.

        Returns:
            List[DataPoint]: A list of newly generated valid datapoints.

        Raises:
            TypeError: If the agent's output is not a dictionary (or does not
                match the expected format).
            KeyError: If required keys are missing from the response.
            AttributeError: If the verifier response lacks attributes.
            ValidationError: If a datapoint fails schema validation.
            RuntimeError: If retries are exhausted before `n` valid datapoints
                are generated.

        Notes:
            - Retries on validation failures until `n` valid datapoints exist
                or `max_retries` is reached, whichever comes first.
            - If retries are exhausted before reaching `n`, a `RuntimeError`
                is raised.
            - Metadata includes a timestamp for tracking datapoint creation.
        """
        valid_data_points: List[DataPoint] = []
        retries = 0

        while len(valid_data_points) < n and retries < max_retries:
            try:
                examples = [
                    self.seed_dataset.sample() for _ in range(num_examples)
                ]
                prompt = self._construct_prompt(examples)

                try:
                    agent_output = (
                        self.agent.step(prompt, response_format=DataPoint)
                        .msgs[0]
                        .parsed
                    )

                    assert isinstance(agent_output, DataPoint)

                    self.agent.reset()

                except (TypeError, KeyError) as e:
                    logger.warning(
                        f"Agent output issue: {e}, retrying... "
                        f"({retries + 1}/{max_retries})"
                    )
                    retries += 1
                    continue

                rationale = agent_output.rationale

                if not isinstance(rationale, str):
                    raise TypeError(f"Rationale {rationale} is not a string.")

                try:
                    output = await asyncio.to_thread(
                        self.interpreter.run, rationale, "python"
                    )

                    if "(stderr:" in output or "(Execution failed" in output:
                        raise ValueError(f"Execution failed: {output}")

                    final_answer = output.strip()

                except (ValueError, AttributeError) as e:
                    logger.warning(
                        f"Interpreter issue: {e}, "
                        f"retrying... ({retries + 1}/{max_retries})"
                    )
                    retries += 1
                    continue

                try:
                    new_datapoint = DataPoint(
                        question=agent_output.question,
                        rationale=rationale,
                        final_answer=final_answer,
                        metadata={
                            "synthetic": str(True),
                            "created": datetime.now().isoformat(),
                            "generator": "few_shot",
                        },
                    )
                except ValidationError as e:
                    logger.warning(
                        f"Datapoint validation failed: {e}, "
                        f"retrying... ({retries + 1}/{max_retries})"
                    )
                    retries += 1
                    continue

                valid_data_points.append(new_datapoint)

            except Exception as e:
                logger.warning(
                    f"Unexpected error: {e}, retrying..."
                    f" ({retries + 1}/{max_retries})"
                )
                retries += 1

        # Thread-safe way to extend the data list
        async with asyncio.Lock():
            self._data.extend(valid_data_points)

        if len(valid_data_points) < n:
            raise RuntimeError(
                f"Failed to generate {n} valid datapoints "
                f"after {max_retries} retries."
            )
