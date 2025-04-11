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
from pathlib import Path

from dotenv import load_dotenv
import json

from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.datasets import SelfInstructGenerator, StaticDataset

from camel.datagen.evol_instruct import EvolInstructPipeline
from camel.datagen.evol_instruct.scorer import MathScorer
from camel.datagen.evol_instruct.templates import MathEvolInstructTemplates

from camel.logger import get_logger
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.verifiers import PythonVerifier

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

RATIONALE_SYSTEM_PROMPT = """You are an advanced Python code assistant.

Your task is to **solve the given question by writing Python code only**,
without any explanation or natural language output.
The code must compute the answer **programmatically**, not by hardcoding or
guessing the result.

**Rules:**
- Use Python code to perform the actual computation.
- Use sympy to solve the problem. Do not import any other libraries.
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

rationale_agent = ChatAgent(RATIONALE_SYSTEM_PROMPT, model=model)

generator = SelfInstructGenerator(
    seed_dataset=seed_dataset,
    verifier=verifier,
    instruction_agent=None,  # use default instruction agent
    rationale_agent=rationale_agent,
)

NUM_NEW_DATA = 6
new_data = asyncio.run(generator.generate_new(n=NUM_NEW_DATA, max_retries=5))

# for dp in new_data:
#     print(dp)


generator.save_to_jsonl(Path("generated_data.jsonl"))

asyncio.run(verifier.cleanup())

# Format self-instruct generated data for evolution
evolution_prompts = []
for dp in new_data:
    evolution_prompts.append(dp.question)

# Define parameters
evol_model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O_MINI,
    model_config_dict={"temperature": 0.7, "max_tokens": 4096},
)

evol_agent = ChatAgent(model=evol_model)
evol_pipeline = EvolInstructPipeline(
    agent=evol_agent,
    templates=MathEvolInstructTemplates,
)

# Define evolution parameters
evol_spec = [
    "in-depth",
    "in-depth",
    "in-depth",
    "condense",
]

# Execute the evolution pipeline
NUM_ITERATIONS = 8
NUM_GENERATIONS = 4
evol_results = evol_pipeline.generate(
    prompts=evolution_prompts,
    evolution_spec=evol_spec,
    num_iterations=NUM_ITERATIONS,  # Number of iterations to run 0-3
    num_generations=NUM_GENERATIONS,  # Number of generations per input prompt 3
    scorer=MathScorer(),
)

# Save the evolved results
evol_results_path = Path("generated_data_evolved.json")
with open(evol_results_path, mode="w", encoding="utf-8") as file:
    json.dump(evol_results, file, indent=4, ensure_ascii=False)

print(f"Evolution results saved to '{evol_results_path}'")


