import asyncio
from pathlib import Path

from dotenv import load_dotenv

from camel.configs import ChatGPTConfig
from camel.datasets import FewShotGenerator, StaticDataset
from camel.logger import get_logger
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.verifiers import PythonVerifier
from camel.models.base_model import BaseModelBackend
from camel.verifiers import BaseVerifier

from camel.datasets.base_generator import BaseGenerator
from camel.datasets.models import DataPoint
from camel.datasets.static_dataset import StaticDataset
from typing import List
from pydantic import BaseModel, Field, ValidationError
from datetime import datetime
from camel.agents import ChatAgent
import random
logger = get_logger(__name__)

verifier = PythonVerifier(required_packages=["sympy"], timeout=60)
asyncio.run(verifier.setup())

raw_data2 = [
    {
        "question": "Evaluate the limit as x approaches 0 of (sin(3*x) - 3*x) / x**3.",  # noqa: E501
        "final_answer": "-9/2",
        "rationale": '''from sympy import symbols, limit, sin
x = symbols('x')
expr = (sin(3*x) - 3*x) / x**3
result = limit(expr, x, 0)
print(result)''',
    },
    {
        "question": "Evaluate the definite integral of (1 - x**2)**3 from x = 0 to x = 1.",  # noqa: E501
        "final_answer": "16/35",
        "rationale": '''from sympy import symbols, integrate
x = symbols('x')
expr = (1 - x**2)**3
result = integrate(expr, (x, 0, 1))
print(result)''',
    },
    {
        "question": "Evaluate the limit as n approaches infinity of n*(sqrt(n**2 + 1) - n).",  # noqa: E501
        "final_answer": "1/2",
        "rationale": '''from sympy import symbols, limit, sqrt
n = symbols('n', positive=True)
expr = n*(sqrt(n**2 + 1) - n)
result = limit(expr, n, float("inf"))
print(result)''',
    },
    {
        "question": "Compute the sum of the series sum from n = 1 to 50 of 1/(n*(n+1)).",  # noqa: E501
        "final_answer": "50/51",
        "rationale": '''from sympy import symbols, summation
n = symbols('n', positive=True, integer=True)
expr = 1/(n*(n+1))
result = summation(expr, (n, 1, 50))
print(result)''',
    },
]

seed_dataset = StaticDataset(raw_data2)

load_dotenv()

model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O_MINI,
    model_config_dict=ChatGPTConfig().as_dict(),
)

INSTRUCTION_SYSTEM_PROMPT = """**You are an advanced question generation assistant.**  
Your goal is to generate high-quality synthetic questions based on 
provided examples. Your output must be well-structured, 
logically sound, and formatted correctly. 

**Output Format (Strict)**  
```
Question: [Generated question]
```

**Now, generate a new question based on the given examples.**
"""

RATIONALE_SYSTEM_PROMPT = """**You are an advanced code assistant.**  
You are good at solving questions by writing python code and using sympy library.
**Output Format (Strict)**
```[Your python code that solves the question]```
**Example**
```
Question:
Evaluate the limit as n approaches infinity of n*(sqrt(n**2 + 1) - n).
Your code:
```from sympy import symbols, limit, sqrt
n = symbols('n', positive=True)
expr = n*(sqrt(n**2 + 1) - n)
result = limit(expr, n, float("inf"))
print(result)```
Now, generate a new code that solves the givenquestion.
"""

class SelfInstructGenerator(BaseGenerator):
    def __init__(
        self,
        seed_dataset: StaticDataset,
        verifier: BaseVerifier,
        seed: int = 42,
        **kwargs,
    ):
        super().__init__(seed=seed, **kwargs)
        self.seed_dataset = seed_dataset
        try:
            self._validate_seed_dataset()
        except Exception:
            raise RuntimeError("Seed Data does not follow Datapoint format")
        self.verifier = verifier
        # 从seed_dataset中遍历获取question作为human_instructions
        self.human_instructions = [dp.question for dp in self.seed_dataset]
        self.machine_instructions = []

    async def generate_new_instruction(self, human_sample_count: int = 3, machine_sample_count: int = 1) -> str:
        human_sample = random.sample(self.human_instructions, min(human_sample_count, len(self.human_instructions)))
        machine_sample = []
        if len(self.machine_instructions) >= machine_sample_count:
            machine_sample = random.sample(self.machine_instructions, machine_sample_count)
        
        few_shot_examples = human_sample + machine_sample
        prompt = "Below are some question examples:\n\n"
        for idx, instr in enumerate(few_shot_examples, start=1):
            prompt += f"Question {idx}: {instr}\n"
        prompt += f"Question {len(few_shot_examples) + 1}:\n"
        prompt += (
            "Please generate a new question based on the given examples.\n"
        )

        class QuestionSchema(BaseModel):
            question: str = Field(description="The question generated")

        question_template = f"Question: {prompt}"
        agent = ChatAgent(INSTRUCTION_SYSTEM_PROMPT)
        response = agent.step(question_template, response_format=QuestionSchema).msgs[0].parsed
        return response.question

    def generate_rationale(self, question: str) -> str:
        agent = ChatAgent(RATIONALE_SYSTEM_PROMPT)
        rationale = agent.step(question).msgs[0].content
        if rationale.startswith("```"):
            rationale = rationale[3:].strip()
        if rationale.startswith("python"):
            rationale = rationale[6:].strip()
        if rationale.endswith("```"):
            rationale = rationale[:-3].strip()
        return rationale

    def _validate_seed_dataset(self) -> None:
        pass

    async def generate_new(
        self,
        n: int,
        max_retries: int = 10,
        **kwargs,
    ) -> List[DataPoint]:
        valid_data_points: List[DataPoint] = []
        retries = 0

        while len(valid_data_points) < n and retries < max_retries:
            try:
                question = await self.generate_new_instruction()
                rationale = self.generate_rationale(question)
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
                self.machine_instructions.append(question)
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

        # Thread-safe way to extend the data list
        async with asyncio.Lock():
            self._data.extend(valid_data_points)
        return valid_data_points
    
generator = SelfInstructGenerator(
    seed_dataset=seed_dataset, verifier=verifier
)

new_data = asyncio.run(generator.generate_new(n=5, max_retries=5))

for dp in new_data:
    print(dp)

generator.save_to_jsonl(Path("generated_data.jsonl"))

asyncio.run(verifier.cleanup())