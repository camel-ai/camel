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
r"""
This code is borrowed and modified based on the source code from the
'MedCalc-Bench' repository.
Original repository: https://github.com/ncbi-nlp/MedCalc-Bench

Modifications include:
- rewrite function compute_fena_explanation
- translation

Date: March 2025
"""

from camel.toolkits.medcalc_bench.utils.rounding import round_number
from camel.toolkits.medcalc_bench.utils.unit_converter_new import (
    conversion_explanation,
)


def compute_fena_explanation(input_variables):
    explanation = (
        "The formula for computing the FEna percentage is ("
        "creatinine * urine_sodium)/(sodium * urine_creatinine) * "
        "100, where creatinine is the concentration in mg/dL, "
        "urine sodium is the concentration in mEq/L, sodium is "
        "the concentration mEq/L, and urine creatinine is the "
        "concentration in mg/dL.\n"
    )

    sodium_exp, sodium = conversion_explanation(
        input_variables["sodium"][0],
        "sodium",
        22.99,
        1,
        input_variables["sodium"][1],
        "mEq/L",
    )
    creatinine_exp, creatinine = conversion_explanation(
        input_variables["creatinine"][0],
        "creatinine",
        113.12,
        1,
        input_variables["creatinine"][1],
        "mg/dL",
    )
    urine_sodium_exp, urine_sodium = conversion_explanation(
        input_variables["urine_sodium"][0],
        "urine sodium",
        22.99,
        1,
        input_variables["urine_sodium"][1],
        "mEq/L",
    )
    urine_creatinine_exp, urine_creatinine = conversion_explanation(
        input_variables["urine_creatinine"][0],
        "urine creatinine",
        113.12,
        1,
        input_variables["urine_creatinine"][1],
        "mg/dL",
    )

    explanation += sodium_exp + '\n'
    explanation += creatinine_exp + '\n'
    explanation += urine_creatinine_exp + '\n'
    explanation += urine_sodium_exp + '\n'

    result = round_number(
        (creatinine * urine_sodium) / (sodium * urine_creatinine) * 100
    )

    explanation += (
        f"Plugging in these values, we get 100 * ("
        f"{creatinine} * {urine_sodium})/("
        f"{sodium} * {urine_creatinine}) = {result} % FENa.\n"
    )
    explanation += f"Hence, the patient's FEna percentage is {result} %.\n"

    return {"Explanation": explanation, "Answer": result}


if __name__ == "__main__":
    # Defining test cases
    test_cases = [
        {
            "sodium": (134.0, 'mmol/L'),
            "creatinine": (3.7, 'mg/dL'),
            "urine_sodium": (21.0, 'mmol/L'),
            "urine_creatinine": (5.0, 'mg/dL'),
        },
    ]

    # Iterate the test cases and print the results
    for i, input_variables in enumerate(test_cases, 1):
        print(f"Test Case {i}: Input = {input_variables}")
        result = compute_fena_explanation(input_variables)
        print(result)
        print("-" * 50)
