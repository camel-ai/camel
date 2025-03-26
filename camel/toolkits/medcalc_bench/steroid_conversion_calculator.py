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
This code is borrowed and modified based on the source code from the 'MedCalc-Bench' repository.
Original repository: https://github.com/ncbi-nlp/MedCalc-Bench

Modifications include:
- rewrite function compute_steroid_conversion_explanation
- translation

Date: March 2025
"""

from camel.toolkits.medcalc_bench.utils.rounding import round_number
from camel.toolkits.medcalc_bench.utils.unit_converter_new import (
    conversion_explanation,
)


def compute_steroid_conversion_explanation(input_parameters):
    r"""
    Calculates the patient's equivalent dosage of MethylPrednisoLONE IV and generates a detailed explanatory text.

    Parameters:
        input_parameters (dict): A dictionary containing the following key-value pairs:
            - "input steroid" (tuple): The patient's blood sodium level in the format (value, unit).
                - Steroid name (str): The various corticosteroids are listed below:
                    - Betamethasone: Route = IV, Equivalent Dose = 0.75 mg
                    - Cortisone: Route = PO, Equivalent Dose = 25 mg
                    - Dexamethasone (Decadron): Route = IV or PO, Equivalent Dose = 0.75 mg
                    - Hydrocortisone: Route = IV or PO, Equivalent Dose = 20 mg
                    - MethylPrednisoLONE: Route = IV or PO, Equivalent Dose = 4 mg
                    - PrednisoLONE: Route = PO, Equivalent Dose = 5 mg
                    - PredniSONE: Route = PO, Equivalent Dose = 5 mg
                    - Triamcinolone: Route = IV, Equivalent Dose = 4 mg
                - Value (float): The blood sodium level.
                - Unit (str): The unit of blood sodium level.
            - "target steroid" (str): The target steroid (str).
                - "Betamethasone IV"
                - "Cortisone PO"
                - "Dexamethasone IV"
                - "Dexamethasone PO"
                - "Hydrocortisone IV"
                - "Hydrocortisone PO"
                - "MethylPrednisoLONE IV"
                - "MethylPrednisoLONE PO"
                - "PrednisoLONE PO"
                - "PredniSONE PO"
                - "Triamcinolone IV"

    Returns:
        dict: Contains two key-value pairs:
            - "Explanation" (str): A detailed description of the calculation process.
            - "Answer" (float): The patient's equivalent dosage of MethylPrednisoLONE IV.

    Notes:
        - None

    Example:
        compute_steroid_conversion_explanation({
            'input steroid': ['Hydrocortisone PO', 190.936, 'mg'],
            'target steroid': 'MethylPrednisoLONE IV'})

        output: "{'Explanation': '\n
        The Steroid Conversions providing equivalent doses for various corticosteroids are listed below:\n
        1. Betamethasone: Route = IV, Equivalent Dose = 0.75 mg\n
        2. Cortisone: Route = PO, Equivalent Dose = 25 mg\n
        3. Dexamethasone (Decadron): Route = IV or PO, Equivalent Dose = 0.75 mg\n
        4. Hydrocortisone: Route = IV or PO, Equivalent Dose = 20 mg\n
        5. MethylPrednisoLONE: Route = IV or PO, Equivalent Dose = 4 mg\n
        6. PrednisoLONE: Route = PO, Equivalent Dose = 5 mg\n
        7. PredniSONE: Route = PO, Equivalent Dose = 5 mg\n
        8. Triamcinolone: Route = IV, Equivalent Dose = 4 mg \n
        \n\nThe mass of Hydrocortisone PO is 190.936 mg. To convert from the Hydrocortisone PO to MethylPrednisoLONE IV,
         multiply by the conversion factor, 0.2 mg MethylPrednisoLONE IV/Hydrocortisone PO,
         giving us 190.936 mg Hydrocortisone PO * 0.2 mg
         MethylPrednisoLONE IV/mg Hydrocortisone PO = 38.187 mg MethylPrednisoLONE IV. 190.936 mg of
         Hydrocortisone PO is equal to 38.187 mg of MethylPrednisoLONE IV.\n', 'Answer': 38.187}"
    """

    explanation = """
        The Steroid Conversions providing equivalent doses for various corticosteroids are listed below:
            1. Betamethasone: Route = IV, Equivalent Dose = 0.75 mg
            2. Cortisone: Route = PO, Equivalent Dose = 25 mg
            3. Dexamethasone (Decadron): Route = IV or PO, Equivalent Dose = 0.75 mg
            4. Hydrocortisone: Route = IV or PO, Equivalent Dose = 20 mg
            5. MethylPrednisoLONE: Route = IV or PO, Equivalent Dose = 4 mg
            6. PrednisoLONE: Route = PO, Equivalent Dose = 5 mg
            7. PredniSONE: Route = PO, Equivalent Dose = 5 mg
            8. Triamcinolone: Route = IV, Equivalent Dose = 4 mg 
        """
    conversion_dict = {"Betamethasone IV": 1,
                       "Cortisone PO": 33.33,
                       "Dexamethasone IV": 1,
                       "Dexamethasone PO": 1,
                       "Hydrocortisone IV": 26.67,
                       "Hydrocortisone PO": 26.67,
                       "MethylPrednisoLONE IV": 5.33,
                       "MethylPrednisoLONE PO": 5.33,
                       "PrednisoLONE PO": 6.67,
                       "PredniSONE PO": 6.67,
                       "Triamcinolone IV": 5.33
                       }

    explanation += "\n\n"
    input_drug_mass_exp, input_drug_mass = conversion_explanation(input_parameters["input steroid"][1],
                                                                  input_parameters["input steroid"][0],
                                                                  None,
                                                                  None,
                                                                  input_parameters["input steroid"][2],
                                                                  "mg")
    explanation += input_drug_mass_exp

    target_drug_name = input_parameters["target steroid"]
    input_drug_name = input_parameters["input steroid"][0]
    input_unit = input_parameters["input steroid"][2]

    from_multiplier = conversion_dict[input_drug_name]
    to_multiplier = conversion_dict[target_drug_name]

    conversion_factor = round_number(to_multiplier / from_multiplier)
    converted_amount = round_number(input_drug_mass * conversion_factor)
    input_drug_mass = round_number(input_drug_mass)

    explanation += f"To convert from the {input_drug_name} to {target_drug_name}, multiply by the conversion factor, " \
                   f"{conversion_factor} mg {target_drug_name}/{input_drug_name}, " \
                   f"giving us {input_drug_mass} mg {input_drug_name} * {conversion_factor} mg " \
                   f"{target_drug_name}/mg {input_drug_name} = {converted_amount} mg {target_drug_name}. "

    explanation += f"{input_drug_mass} {input_unit} of {input_drug_name} is equal to " \
                   f"{converted_amount} mg of {target_drug_name}.\n"

    return {"Explanation": explanation, "Answer": converted_amount}


if __name__ == "__main__":
    # Defining test cases
    test_cases = [
        {'input steroid': ['Hydrocortisone PO', 190.936, 'mg'], 'target steroid': 'MethylPrednisoLONE IV'},
        {'input steroid': ['Dexamethasone PO', 8.58, 'mg'], 'target steroid': 'Dexamethasone IV'},
    ]

    # {'input steroid': ['Hydrocortisone PO', 190.936, 'mg'], 'target steroid': 'MethylPrednisoLONE IV'}
    # {'input steroid': ['Dexamethasone PO', 8.58, 'mg'], 'target steroid': 'Dexamethasone IV'}

    # Iterate the test cases and print the results
    for i, input_variables in enumerate(test_cases, 1):
        print(f"Test Case {i}: Input = {input_variables}")
        result = compute_steroid_conversion_explanation(input_variables)
        print(result)
        print("-" * 50)
