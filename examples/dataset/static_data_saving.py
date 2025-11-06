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

from pathlib import Path

from camel.datasets import StaticDataset

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


# Save to JSON file
seed_dataset.save_to_json("./localdata/output.json")
# or
seed_dataset.save_to_json(Path("./localdata/output.json"))


# Save to Hugging Face Hub (first time)
seed_dataset.save_to_huggingface(
    dataset_name="zjrwtxtechstudio/testloongdata04",
    description="A dataset containing question-answer pairs",
    private=False,
    tags=["LOONG_TEST", "qa"],
    language=["en"],
    overwrite=True,
)
