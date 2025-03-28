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
- rewrite function compute_perc_rule_explanation
- translation

Date: March 2025
"""

from camel.toolkits.medcalc_bench.utils.rounding import round_number
from camel.toolkits.medcalc_bench.utils.unit_converter_new import (
    conversion_explanation,
)


def mme_explanation(input_parameters):
    explanation = r"""
    The Opioid Conversion Table with MME (Morphine Milligram Equivalent) 
    conversion factors are listed below:
       1. Codeine: MME conversion factor = 0.15
       2. FentaNYL buccal: MME conversion factor = 0.13
       3. HYDROcodone: MME conversion factor = 1
       4. HYDROmorphone: MME conversion factor = 5
       5. Methadone: MME conversion factor = 4.7
       6. Morphine: MME conversion factor = 1
       7. OxyCODONE: MME conversion factor = 1.5
       8. OxyMORphone: MME conversion factor = 3
       9. Tapentadol: MME conversion factor = 0.4
       10. TraMADol: MME conversion factor = 0.2
       11. Buprenorphine: MME conversion factor = 10
    """

    explanation += (
        "\n\nThe curent Morphine Milligram Equivalents "
        "(MME) is 0 MME per day.\n"
    )

    mme_drug = {
        "Codeine": 0.15,
        "FentaNYL buccal": 0.13,
        "FentANYL patch": 2.4,
        "HYDROcodone": 1,
        "HYDROmorphone": 5,
        "Methadone": 4.7,
        "Morphine": 1,
        "OxyCODONE": 1.5,
        "OxyMORphone": 3,
        "Tapentadol": 0.4,
        "TraMADol": 0.2,
        "Buprenorphine": 10,
    }

    mme_equivalent = 0

    for drug_name in input_parameters:
        if "Day" in drug_name:
            continue

        name = drug_name.split(" Dose")[0]

        units = input_parameters[name + " Dose"][1]

        if name != "FentaNYL buccal" and name != "FentaNYL patch":
            drug_mg_exp, drug_mg = conversion_explanation(
                input_parameters[name + " Dose"][0],
                name,
                None,
                None,
                units,
                "mg",
            )
            if units == "mg":
                explanation += (
                    f"The patient's dose of {name} is {drug_mg} " f"mg. "
                )
            else:
                explanation += (
                    f"The patient's dose of {name} is measured "
                    f"in {units}. We need to convert this to mg. "
                )
                explanation += drug_mg_exp + "\n"
        else:
            drug_mg_exp, drug_mg = conversion_explanation(
                input_parameters[name + " Dose"][0],
                name,
                None,
                None,
                units,
                "µg",
            )
            if units == "µg":
                explanation += (
                    f"The patient's dose of {name} is {drug_mg} " f"µg.\n"
                )
            else:
                explanation += (
                    f"The patient's dose of {name} is measured "
                    f"in {units}. We need to convert this to µg. "
                )
                explanation += drug_mg_exp + "\n"

        target_unit = (
            "mg"
            if name != "FentaNYL buccal" and name != "FentaNYL patch"
            else "µg"
        )

        dose_per_day_key = name + " Dose Per Day"

        dose_per_day = input_parameters[dose_per_day_key][0]

        total_per_day = round_number(drug_mg * dose_per_day)

        explanation += (
            f"The patient takes {dose_per_day} doses/day of "
            f"{name}. This means that the patient takes "
            f"{round_number(drug_mg)} {target_unit}/dose "
            f"{name} * {dose_per_day} dose/day = "
            f"{total_per_day} {target_unit}/day. "
        )

        explanation += (
            f"To convert to mme/day of {name}, multiply the "
            f"{total_per_day} {target_unit}/day by the mme "
            f"conversion factor, {mme_drug[name]} mme/"
            f"{target_unit}, giving us "
            f"{round_number(mme_drug[name] * total_per_day)} "
            f"mme/day. "
        )

        explanation += (
            f"Adding the mme/day of {name} to the total mme/day "
            f"gives us {round_number(mme_equivalent)} + "
            f"{round_number(mme_drug[name] * total_per_day)} = "
            f"{round_number(mme_equivalent + mme_drug[name] * total_per_day)} "
            f"mme/day.\n"
        )

        mme_equivalent += dose_per_day * mme_drug[name] * drug_mg

        mme_equivalent = round_number(mme_equivalent)

    explanation += f"The patient's mme/day is {mme_equivalent} mme/day."

    return {"Explanation": explanation, "Answer": mme_equivalent}


if __name__ == "__main__":
    # Defining test cases
    test_cases = [
        {
            'Tapentadol Dose': (10, 'mg'),
            'Tapentadol Dose Per Day': (2, 'per day'),
            'HYDROcodone Dose': (30, 'mg'),
            'HYDROcodone Dose Per Day': (2, 'per day'),
            'FentANYL patch Dose': (70, 'mg'),
            'FentANYL patch Dose Per Day': (2, 'per day'),
        }
    ]

    # Iterate the test cases and print the results
    for i, input_variables in enumerate(test_cases, 1):
        print(f"Test Case {i}: Input = {input_variables}")
        result = mme_explanation(input_variables)
        print(result)
        print("-" * 50)
