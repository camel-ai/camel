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
- rewrite function compute_fib4_explanation
- translation

Date: March 2025
"""

import math

from camel.toolkits.medcalc_bench.utils.age_conversion import (
    age_conversion_explanation,
)
from camel.toolkits.medcalc_bench.utils.rounding import round_number
from camel.toolkits.medcalc_bench.utils.unit_converter_new import (
    convert_to_units_per_liter_explanation,
)


def compute_fib4_explanation(input_parameters):
    r"""
    Calculates the patient's Fibrosis-4 (FIB-4) index and generates a
    detailed explanatory text.

    Parameters:
        input_parameters (dict): A dictionary containing the following
        key-value pairs:
            - "age" (tuple): The patient's albumin concentration in the
            format (value, unit).
                - Value (float): Age.
                - Unit (str): The unit can be "months", "years".
            - "alt" (tuple): The patient's Alanine aminotransferase in the
            format (value, unit).
                - Value (float): The value of Alanine aminotransferase.
                - Unit (str): The unit of Alanine aminotransferase,
                eg. "U/L" and so on.
            - "ast" (tuple): The patient's Aspartate aminotransferase in the
            format (value, unit).
                - Value (float): The value of Aspartate aminotransferase.
                - Unit (str): The unit of Aspartate aminotransferase,
                e.g. "U/L" and so on.
            - "platelet_count" (tuple): The patient's platelet count in the
            format (value, unit).
                - Value (float): The value of platelet count.
                - Unit (str): The unit of platelet count,
                e.g. "µL" and so on.

    Returns:
        dict: Contains two key-value pairs:
            - "Explanation" (str): A detailed description of
            the calculation process.
            - "Answer" (float): The patient's Fibrosis-4 (FIB-4) index.

    Notes:
        - None

    Example:
        compute_homa_ir_explanation({'age': (17, 'years'),
        'alt': (144.0, 'U/L'),
        'ast': (108.0, 'U/L'),
        'platelet_count': (277000.0, 'µL')})

        output: "{'Explanation': "The formula for computing Fibrosis-4 is
        Fib-4 = (Age * AST) / (Platelet count (in billions) * √ALT),
        where platelet count is the number of billions per L, and the units
        for AST and ALT are both U/L.\nThe patient's concentration of
        AST is 108.0 U/L.\nThe patient's concentration of ALT is 144.0
        U/L.\nThe patient's concentration of platelets is 277000.0 count/µL.
        To convert 277000.0 count/µL of platelets to L,
        multiply by the conversion factor 1000000.0 µL/L which
        will give 277000.0 platelets count/µL * 1000000.0 µL/L =
        277000000000.0 platelets count/L. This means that there
        are 277000000000.0/(10^9) = 277.0 billion platelet counts
        per liter.\nPlugging these values into the formula,
        we get (17 * 108.0)/(277.0 * sqrt(144.0)) = 0.552.
        \nHence, the Fibrosis-4 score is 0.552.", 'Answer': 0.552}"
    """

    explanation = ""

    age_explanation, age = age_conversion_explanation(input_parameters["age"])
    explanation += age_explanation

    ast_value = input_parameters["ast"][0]
    alt_value = input_parameters["alt"][0]
    src_value = input_parameters["platelet_count"][0]
    src_unit = input_parameters["platelet_count"][1]
    explanation = (
        "The formula for computing Fibrosis-4 is Fib-4 = (Age * "
        "AST) / (Platelet count (in billions) * √ALT), "
        "where platelet count is the number of billions per L, "
        "and the units for AST and ALT are both U/L.\n"
    )

    explanation_platelet, platelet_value = (
        convert_to_units_per_liter_explanation(
            src_value, src_unit, "platelets", "L"
        )
    )

    count_platelet_billions = platelet_value / 1e9
    result = round_number(
        (age * ast_value) / (count_platelet_billions * math.sqrt(alt_value))
    )

    explanation += f"The patient's concentration of AST is {ast_value} U/L.\n"
    explanation += f"The patient's concentration of ALT is {alt_value} U/L.\n"

    explanation += (
        f"{explanation_platelet}This means that there are "
        f"{platelet_value}/(10^9) = {count_platelet_billions} "
        f"billion platelet counts per liter.\n"
    )
    explanation += (
        f"Plugging these values into the formula, "
        f"we get ({age} * {ast_value})/"
        f"({count_platelet_billions} * "
        f"sqrt({alt_value})) = {result}.\n"
    )
    explanation += f"Hence, the Fibrosis-4 score is {result}."

    return {"Explanation": explanation, "Answer": result}


if __name__ == "__main__":
    # Defining test cases
    test_cases = [
        {
            "age": (17, 'years'),
            "alt": (144.0, 'U/L'),
            "ast": (108.0, 'U/L'),
            "platelet_count": (277000.0, 'µL'),
        }
    ]

    # Iterate the test cases and print the results
    for i, input_variables in enumerate(test_cases, 1):
        print(f"Test Case {i}: Input = {input_variables}")
        result = compute_fib4_explanation(input_variables)
        print(result)
        print("-" * 50)
