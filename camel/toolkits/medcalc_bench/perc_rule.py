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

from camel.toolkits.medcalc_bench.utils.age_conversion import (
    age_conversion_explanation,
)


def compute_perc_rule_explanation(input_parameters):
    perc_count = 0

    explanation = r"""
    The PERC Rule critiera are listed below:
    
       1. Age ≥50: No = 0 points, Yes = +1 point
       2. Heart Rate (HR) ≥100: No = 0 points, Yes = +1 point
       3. O₂ saturation on room air <95%: No = 0 points, Yes = +1 point
       4. Unilateral leg swelling: No = 0 points, Yes = +1 point
       5. Hemoptysis: No = 0 points, Yes = +1 point
       6. Recent surgery or trauma (within 4 weeks, requiring treatment 
       with general anesthesia): No = 0 points, Yes = +1 point
       7. Prior pulmonary embolism (PE) or deep vein thrombosis (DVT): No = 
       0 points, Yes = +1 point
       8. Hormone use (oral contraceptives, hormone replacement, 
       or estrogenic hormone use in males or females): No = 0 points, 
       Yes = +1 point
    
    The total number of criteria met is taken by summing 
    the points for each criterion.\n\n
    """

    explanation += "The current count of PERC criteria met is 0.\n"

    age_exp, age = age_conversion_explanation(input_parameters["age"])
    heart_rate = input_parameters["heart_rate"][0]
    oxygen_sat = input_parameters["oxygen_sat"][0]

    parameters = {
        "unilateral_leg_swelling": "unilateral leg swelling",
        "hemoptysis": "hemoptysis",
        "recent_surgery_or_trauma": "recent surgery or trauma",
        "previous_pe": "prior pulmonary embolism",
        "previous_dvt": "prior deep vein thrombosis",
        "hormonal_use": "hormonal use",
    }

    explanation += age_exp
    if age >= 50:
        explanation += (
            f"The patient's age is greater than or equal to 50 "
            f"years, and so we increment the perc critieria met "
            f"by 1, making the current total {perc_count} + 1 = "
            f"{perc_count + 1}.\n"
        )
        perc_count += 1
    else:
        explanation += (
            f"The patient's age is less than 50 years, and so we "
            f"do not increment the criteria count. The current "
            f"total remains at {perc_count}.\n"
        )

    explanation += (
        f"The patient's heart rate is {heart_rate} beats per " f"minute. "
    )

    if heart_rate >= 100:
        explanation += (
            f"The patient's heart rate is greater than or equal "
            f"to 100 beats per minute, and so we increment the "
            f"perc critieria met by 1, making the current total "
            f"{perc_count} + 1 = {perc_count + 1}.\n"
        )
        perc_count += 1
    else:
        explanation += (
            f"The patient's heart rate is less than 100 beats "
            f"per minute, and so we do not increment the "
            f"criteria count. The current total "
            f"remains at {perc_count}.\n"
        )

    explanation += (
        f"The saturated oxygen percentage in the room is "
        f"{oxygen_sat} percent. "
    )

    if oxygen_sat < 95:
        explanation += (
            f"The saturated oxygen is less than 95%, and so we "
            f"increment the perc critieria met by 1, making the "
            f"current total {perc_count} + 1 = {perc_count + 1}.\n"
        )
        perc_count += 1
    else:
        explanation += (
            f"The saturated oxygen is greater than or equal to "
            f"95% and so we do not increment the criteria count. "
            f"The current total remains at {perc_count}.\n"
        )

    for parameter in parameters:
        if parameter == "previous_pe":
            continue

        if parameter == "previous_dvt":
            explanation += (
                "The patient must be diagnosed with at least one "
                "of deep vein thrombosis or pulmonary embolism "
                "in the past for a PERC rule criteria to be met. "
            )

            if 'previous_dvt' not in input_parameters:
                explanation += (
                    "Whether the patient has been diagnosed for "
                    "pulmonary embolism in the past is not "
                    "reported. Hence, we assume it to be absent. "
                )
                input_parameters['previous_dvt'] = False
            elif not input_parameters['previous_dvt']:
                explanation += (
                    "The patient is not reported to have been "
                    "diagnosed with deep vein thrombosis in the "
                    "past. "
                )
            else:
                explanation += (
                    "The patient is reported to have been "
                    "diagnosed with deep vein thrombosis in the "
                    "past. "
                )

            if 'previous_pe' not in input_parameters:
                explanation += (
                    "Whether the patient has been diagnosed for "
                    "pulmonary embolism in the past is not "
                    "reported. Hence, we assume it to be absent. "
                )
                input_parameters['previous_pe'] = False
            elif not input_parameters['previous_pe']:
                explanation += (
                    "The patient is not reported to have been "
                    "diagnosed with pulmonary embolism in the "
                    "past. "
                )
            else:
                explanation += (
                    "The patient is reported to have been "
                    "diagnosed with pulmonary embolism in the "
                    "past. "
                )

            if (
                input_parameters['previous_dvt']
                or input_parameters['previous_pe']
            ):
                explanation += (
                    f"At least one of the criteria is met and so "
                    f"we increment the criteria met by 1, making "
                    f"the current total {perc_count} + 1 = "
                    f"{perc_count + 1}.\n"
                )
                perc_count += 1
            else:
                explanation += (
                    f"Neither criteria is met and so we do "
                    f"increment the criteria count, keep the "
                    f"current total at {perc_count}.\n"
                )
            continue

        if parameter not in input_parameters:
            explanation += (
                f"The patient note does not report a status on '"
                f"{parameters[parameter]}'. Hence, we assume it "
                f"to be absent, and so we do not increment the "
                f"criteria count. The current total remains at "
                f"{perc_count}.\n"
            )
        elif not input_parameters[parameter]:
            explanation += (
                f"The patient note reports '"
                f"{parameters[parameter]}' to be absent in the "
                f"patient and so we do not increment "
                f"the criteria count. The current total remains "
                f"at {perc_count}.\n"
            )
        else:
            explanation += (
                f"The patient note reports '"
                f"{parameters[parameter]}' to be present for the "
                f"patient and so we increment the criteria count "
                f"by 1, making the current total "
                f"{perc_count} + 1  =  {perc_count + 1}.\n"
            )
            perc_count += 1

    explanation += (
        f"Hence, the number of PERC rule criteria met by the "
        f"patient is {perc_count}.\n"
    )

    return {"Explanation": explanation, "Answer": perc_count}


if __name__ == "__main__":
    # Defining test cases
    test_cases = [
        {
            "age": (73, "years"),
            "heart_rate": (92.0, "breaths per minute"),
            "oxygen_sat": (98.0, '%'),
            "unilateral_leg_swelling": False,
            "hemoptysis": False,
            "recent_surgery_or_trauma": True,
            "previous_pe": False,
            "previous_dvt": False,
            "hormonal_use": True,
        }
    ]

    # Iterate the test cases and print the results
    for i, input_variables in enumerate(test_cases, 1):
        print(f"Test Case {i}: Input = {input_variables}")
        result = compute_perc_rule_explanation(input_variables)
        print(result)
        print("-" * 50)
