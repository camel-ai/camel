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
from datetime import datetime
from typing import Iterable, List, cast

from pydantic import BaseModel, Field, ValidationError

from camel.agents import ChatAgent
from camel.logger import get_logger
from camel.models.base_model import BaseModelBackend
from camel.verifiers import BaseVerifier

from .base_generator import BaseGenerator
from .models import DataPoint
from .static_dataset import StaticDataset

logger = get_logger(__name__)


RATIONALE_SYSTEM_PROMPT = """You are an advanced Python code assistant.

Your task is to **solve the given question by writing Python code only**,
without any explanation or natural language output.
The code must compute the answer **programmatically**, not by hardcoding or
guessing the result.

**Rules:**
- Use Python code to perform the actual computation.
- Use {library} to solve the problem. Do not import any other libraries.
- **Do not hardcode the final answer** (e.g., avoid writing `print(1/2)` unless
  that value is computed).
- The result must be obtained through valid computation logic in code.
- Do not include explanations. Output code only.
- The entire code must be wrapped in triple backticks:
```
[Your Python code here]
```

Now, solve the following question using Python. Only output the code:
"""

INSTRUCTION_SYSTEM_PROMPT = """
You are a high-capacity instruction generation assistant.

Your task is to generate a **new, creative, and challenging question** based on
several examples.
These examples may cover different domains or styles, but your goal is to:
- **Understand their specific patterns** in structure, and complexity;
- **Combine and synthesize** ideas from multiple examples, rather than copying
  or lightly editing any single one;
- **Intelligently integrate** multiple reasoning steps, constraints, or
  concepts into a single, coherent question;
- Ensure the new question is **non-trivial** and requires deep thinking or
  multi-step reasoning.

**Guidelines:**
- Use the examples as inspiration for format, depth, and tone.
- Your new question should be self-contained, logically sound, and answerable.
- Do not repeat exact phrasings or create shallow combinations; instead,
  produce something meaningfully new.
- Avoid open-ended or subjective questions that depend on personal opinions or
  discussion.
- The generated question must have a **clear, objective, and verifiable
  answer**.
- Aim for increased depth or novelty through subtle combination or
  transformation.
- Keep the final output to a **single unified question** with one clear answer,
  not a multi-part task.

**Output Format (strict):**
```
Question: [Generated question]
```
"""


class SelfInstructGenerator(BaseGenerator):
    r"""A generator for creating synthetic datapoints using self-instruct.

    It utilizes both a human-provided dataset (seed_dataset) and generated
    machine instructions (machine_instructions) to produce new, synthetic
    datapoints that include a question, a computed rationale (code), and a
    final answer (from a verifier).
    """

    def __init__(
        self,
        seed_dataset: StaticDataset,
        verifier: BaseVerifier,
        instruction_model: BaseModelBackend,
        rationale_model: BaseModelBackend,
        seed: int = 42,
        **kwargs,
    ):
        r"""Initialize the self-instruct generator.

        Args:
            seed_dataset (StaticDataset): Dataset containing seed instructions.
            verifier (BaseVerifier): Verifier instance to validate generated
                solutions.
            instruction_model (BaseModelBackend): Model backend for generating
                instructions.
            rationale_model (BaseModelBackend): Model backend for generating
                rationales (code).
            seed (int): Random seed for reproducibility. (default: :obj:`42`)
            **kwargs: Additional keyword arguments passed to the BaseGenerator.
        """
        super().__init__(seed=seed, **kwargs)
        self.seed_dataset = seed_dataset
        self.verifier = verifier
        # extract packages from verifier
        self.packages: List[str] = getattr(
            self.verifier, "required_packages", []
        )
        self.instruction_model = instruction_model
        self.rationale_model = rationale_model
        # Extract questions from the seed dataset as human_instructions
        self.human_instructions: List[str] = [
            dp.question
            for dp in list(cast(Iterable[DataPoint], self.seed_dataset))
        ]
        self.machine_instructions: List[DataPoint] = []
        # Create an instance-level lock for thread-safe updates to _data
        self._lock = asyncio.Lock()
        self._data = []  # Storage for generated DataPoint instances

    class QuestionSchema(BaseModel):
        """
        Schema for the generated question.
        """

        question: str = Field(description="The question generated")

    class RationaleSchema(BaseModel):
        """
        Schema for the generated rationale code.
        """

        code: str = Field(
            description="The generated code without any formatting"
        )

    def generate_new_instruction(
        self,
        support_human_dps: list[DataPoint],
        support_machine_dps: list[DataPoint],
        model: BaseModelBackend,
    ) -> str:
        r"""Generate a new instruction using self-instruct prompting.

        Args:
            support_human_dps (list[DataPoint]): List of human examples to
                sample.
            support_machine_dps (list[DataPoint]): List of machine examples to
                sample.
            model (BaseModelBackend): The backend model to use for instruction
                generation.

        Returns:
            str: The newly generated question.
        """
        human_sample = [dp.question for dp in list(support_human_dps)]
        machine_sample = [dp.question for dp in list(support_machine_dps)]

        few_shot_examples = human_sample + machine_sample

        # Build the prompt using the few-shot examples
        prompt = "Below are some question examples:\n\n"
        for idx, instr in enumerate(few_shot_examples, start=1):
            prompt += f"Question {idx}: {instr}\n"
        prompt += f"Question {len(few_shot_examples) + 1}:\n"
        prompt += "Now generate a new question based on the given examples.\n"

        question_template = f"Question: {prompt}"
        agent = ChatAgent(INSTRUCTION_SYSTEM_PROMPT, model=model)
        response = cast(
            SelfInstructGenerator.QuestionSchema,
            agent.step(question_template, response_format=self.QuestionSchema)
            .msgs[0]
            .parsed,
        )
        return response.question

    def generate_rationale(
        self,
        question: str,
        support_human_dps: list[DataPoint],
        model: BaseModelBackend,
    ) -> str:
        r"""Generate rationale code (solution) for the given question.

        Args:
            question (str): The question to be solved.
            support_human_dps (list[DataPoint]): List of human examples to
                sample.
            model (BaseModelBackend): The backend model to use for generating
                the code solution.

        Returns:
            str: The generated code solution as a string.
        """
        # Construct few-shot examples block
        few_shot_blocks = []
        for dp in support_human_dps:
            support_q = dp.question.strip()
            support_code = (dp.rationale or "").strip()
            block = (
                f"Question:\n{support_q}\n\n"
                "Code:\n"
                "```python\n"
                f"{support_code}\n"
                "```\n"
            )
            few_shot_blocks.append(block)

        few_shot_prompt = (
            "Below are example questions and their Python solutions:\n\n"
            + "\n\n".join(few_shot_blocks)
            + f"\nNow, write code to solve the question:\n{question}\nCode:\n"
        )

        sys_msg = RATIONALE_SYSTEM_PROMPT.format(
            library=", ".join(self.packages)
        )

        agent = ChatAgent(sys_msg, model=model)
        response = cast(
            SelfInstructGenerator.RationaleSchema,
            agent.step(few_shot_prompt, response_format=self.RationaleSchema)
            .msgs[0]
            .parsed,
        )
        return response.code

    async def generate_new(
        self,
        n: int,
        max_retries: int = 10,
        human_sample_count: int = 3,
        machine_sample_count: int = 1,
        **kwargs,
    ) -> list[DataPoint]:
        r"""Generates and validates `n` new datapoints through
        self-instruct prompting, with a retry limit.

        Args:
            n (int): The number of valid datapoints to generate.
            max_retries (int): Maximum number of retries before stopping.
                (default: :obj:`10`)
            human_sample_count (int): Number of human examples to sample.
                (default: :obj:`3`)
            machine_sample_count (int): Number of machine examples to sample.
                (default: :obj:`1`)
            **kwargs: Additional keyword arguments.

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
        valid_data_points: list[DataPoint] = []
        retries = 0

        while len(valid_data_points) < n and retries < max_retries:
            try:
                human_dps_list = list(cast(List[DataPoint], self.seed_dataset))
                support_human_dps = random.sample(
                    human_dps_list,
                    min(human_sample_count, len(human_dps_list)),
                )

                machine_dps_list = list(self.machine_instructions)
                support_machine_dps = random.sample(
                    machine_dps_list,
                    min(machine_sample_count, len(machine_dps_list)),
                )
                question = self.generate_new_instruction(
                    support_human_dps,
                    support_machine_dps,
                    self.instruction_model,
                )
                rationale = self.generate_rationale(
                    question, support_human_dps, self.rationale_model
                )
                if not isinstance(rationale, str):
                    raise TypeError(f"Rationale {rationale} is not a string.")

                try:
                    verifier_response = await self.verifier.verify(
                        solution=rationale,
                        ground_truth=None,
                    )
                    if not verifier_response or not verifier_response.result:
                        raise ValueError(
                            "Verifier unsuccessful, response: "
                            f"{verifier_response}"
                        )
                except (ValueError, AttributeError) as e:
                    logger.warning(
                        f"Verifier issue: {e}, "
                        f"retrying... ({retries + 1}/{max_retries})"
                    )
                    retries += 1
                    continue
                try:
                    new_datapoint = DataPoint(
                        question=question,
                        rationale=rationale,
                        final_answer=verifier_response.result,
                        metadata={
                            "synthetic": str(True),
                            "created": datetime.now().isoformat(),
                            "generator": "self_instruct",
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

        if len(valid_data_points) < n:
            raise RuntimeError(
                f"Failed to generate {n} valid datapoints "
                f"after {max_retries} retries."
            )

        async with self._lock:
            self._data.extend(valid_data_points)
        return valid_data_points
