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

from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.datasets import SelfInstructGenerator, StaticDataset
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

instruction_agent = ChatAgent(INSTRUCTION_SYSTEM_PROMPT, model=model)

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
    instruction_agent=instruction_agent,
    rationale_agent=rationale_agent,
)

new_data = asyncio.run(generator.generate_new(n=3, max_retries=5))

for dp in new_data:
    print(dp)

generator.save_to_jsonl(Path("generated_data.jsonl"))

asyncio.run(verifier.cleanup())
