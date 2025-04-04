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
- rewrite function compute_meldna_explanation
- translation

Date: March 2025
"""

import math

from camel.toolkits.medcalc_bench.utils.unit_converter_new import (
    conversion_explanation,
)


def compute_meldna_explanation(input_variables):
    r"""
    Calculates the patient's child pugh score and generates a detailed
    explanatory text.

    Parameters:
        input_variables (dict): A dictionary containing the following
        key-value pairs:
            - "creatinine" (tuple): The patient's creatinine information in the
            format (value, unit).
                - Value (float): The value of creatinine.
                - Unit (str): The unit of creatinine,
                which can be "mg/dL", "μmol/L", and so on.
            - "dialysis_twice" (boolean):
            - "inr" (float): The patient's international normalised ratio (
            INR) in the float format.
            - "bilirubin" (array): The patient's bilirubin level in the
            format (value, unit).
                - Value (float): The value of bilirubin level.
                - Unit (str): The unit of bilirubin level, eg. "mmol/L",
                "mEq/L", and so on.
            - "sodium" (array): The patient's bicarbonate level in the
            format (value, unit).
                - Value (float): The value of bicarbonate level.
                - Unit (str): The unit of bicarbonate level, eg. "mmol/L",
                "mEq/L", and so on.
            - "creatinine" (tuple): The patient's creatinine information in the
            format (value, unit).
                - Value (float): The value of creatinine.
                - Unit (str): The unit of creatinine,
                which can be "mg/dL", "μmol/L", and so on.

    Returns:
        dict: Contains two key-value pairs:
            - "Explanation" (str): A detailed description of
            the calculation process.
            - "Answer" (float): The patient's MELD-Na score.

    Notes:
        - None

    Example:
        compute_meldna_explanation({'creatinine': (1.0, 'mg/dL'),
        'dialysis_twice': False,
        'bilirubin': (2.8, 'mg/dL'),
        'inr': 1.5, 'sodium': [139.0, 'mEq/L']})

        output: "{'Explanation': "The formula for computing the MELD Na is
        to first apply the following equation: MELD(i) = 0.957 x ln(Cr) +
        0.378 x ln(bilirubin) + 1.120 x ln(INR) + 0.643.\nIf the MELD(i) is
        greater than 11 after rounding to the nearest tenth and multiplying
        the MELD(i) by 10, we apply the following equation: MELD = MELD(i)
        + 1.32 x (137 - Na) -  [ 0.033 x MELD(i) x (137 - Na)]. The MELD Na
        score is capped at 40. The concentration of Na is mEq/L,
        the concentration of bilirubin is mg/dL, and the concentration of
        creatinine is mg/dL. If the patient's Na concentration is less than
        125 mEq/L, we set it to 125 mEq/L and if the patient's the Na
        concentration is greater 137 mEq/L, we round it to 137 mEq/L.\nThe
        concentration of creatinine is 1.0 mg/dL. \nThe patient has not went
        through dialysis at least twice in the past week.\nWhether the
        patient has gone through continuous veno-venous hemodialysis in the
        past 24 hours is not mentioned, and so we assume this to be false.
        \nThe concentration of bilirubin is 2.8 mg/dL. \nThe patient's INR
        is 1.5. \nThe concentration of sodium is 139.0 mEq/L. The sodium
        concentration is greater than 137 mEq/L, and so we set the sodium
        concentration to 137 mEq/L.\nApplying the first equation givesus
        0.957 x ln(1.0) + 0.378 x ln(2.8) + 1.120 x ln(1.5) + 0.643 =
        1.486317060775622. Rounding to the nearest tenth makesthe MELD (i)
        score 1.5. We then multiply by 10, making the MELD(i) score 15.
        \nBecause the MELD (i) score is greater than 11, we then apply the
        second equation, giving us 15 + 1.32 x (137 - 137) -  [0.033 x
        1.486317060775622 x (137 - 137)] = 15.\nThe MELD Na score is less
        than 40, and so we keep the score as it is. The patient's MELDNa
        score, rounded to the nearest integer, is 15 points.\n", 'Answer': 15}"
    """

    explanation = (
        "The formula for computing the MELD Na is to first apply "
        "the following equation: MELD(i) = 0.957 x ln(Cr) + 0.378 "
        "x ln(bilirubin) + 1.120 x ln(INR) + 0.643.\n"
    )
    explanation += (
        "If the MELD(i) is greater than 11 after rounding to the "
        "nearest tenth and multiplying the MELD(i) by 10, "
        "we apply the following equation: MELD = MELD(i) + "
        "1.32 x (137 - Na) -  [ 0.033 x MELD(i) x (137 - Na)]. "
        "The MELD Na score is capped at 40. "
    )
    explanation += (
        "The concentration of Na is mEq/L, the concentration of "
        "bilirubin is mg/dL, and the concentration of creatinine "
        "is mg/dL. If the patient's Na concentration is less "
        "than 125 mEq/L, we set it to 125 mEq/L and if the "
        "patient's the Na concentration is greater 137 mEq/L, "
        "we round it to 137 mEq/L.\n"
    )

    creatinine_exp, creatinine = conversion_explanation(
        input_variables["creatinine"][0],
        "creatinine",
        113.12,
        None,
        input_variables["creatinine"][1],
        "mg/dL",
    )

    explanation += creatinine_exp + "\n"

    if "dialysis_twice" not in input_variables:
        explanation += (
            "Whether the patient has gone through dialysis at "
            "least twice in the past week is not mentioned, "
            "and so we assume this to be false.\n"
        )
        input_variables["dialysis_twice"] = False
    elif input_variables["dialysis_twice"]:
        explanation += (
            "The patient is reported to have went through "
            "dialysis at least twice in the past week.\n"
        )
    else:
        explanation += (
            "The patient has not went through dialysis at least "
            "twice in the past week.\n"
        )

    if "cvvhd" not in input_variables:
        explanation += (
            "Whether the patient has gone through continuous "
            "veno-venous hemodialysis in the past 24 hours "
            "is not mentioned, and so we assume this to be false.\n"
        )
        input_variables["cvvhd"] = False
    elif input_variables["cvvhd"]:
        explanation += (
            "The patient is reported to have went through "
            "continuous veno-venous hemodialysis in the past 24 "
            "hours.\n"
        )
    else:
        explanation += (
            "The patient is reported to not have done "
            "dialysis at least twice in the past week.\n"
        )

    if creatinine < 1.0:
        explanation += (
            "The patient's creatinine concentration is less than "
            "1.0 mg/dL, and so we set the creatinine "
            "concentration to 1.0 mg/dL.\n"
        )
        creatinine = 1.0
    elif creatinine > 4.0:
        explanation += (
            "The creatinine concentration is greater than 4.0 "
            "mg/dL, and so we set the creatinine "
            "concentration to 4.0 mg/dL.\n"
        )
        creatinine = 4.0
    elif input_variables["dialysis_twice"] or input_variables["cvvhd"]:
        explanation += (
            "Because the patient has gone through at least one "
            "of (i) dialysis two or more times in the past 7 "
            "days or (ii) continuous veno-venous hemodialysis "
            "in the past 24 hours, we set the creatinine "
            "concentration to 4.0 mg/dL.\n"
        )
        creatinine = 4.0

    bilirubin_exp, bilirubin = conversion_explanation(
        input_variables["bilirubin"][0],
        "bilirubin",
        None,
        None,
        input_variables["bilirubin"][1],
        "mg/dL",
    )

    explanation += bilirubin_exp

    if bilirubin < 1.0:
        explanation += (
            "The patient's bilirubin concentration is less than "
            "1.0 mg/dL, and so we set the bilirubin concentration "
            "to 1.0 mg/dL.\n"
        )
        bilirubin = 1.0
    else:
        explanation += "\n"

    inr = input_variables["inr"]

    explanation += f"The patient's INR is {inr}. "

    if inr < 1.0:
        explanation += (
            "The patient's INR is less than 1.0, and so we set "
            "the INR to 1.0.\n"
        )
        inr = 1.0
    else:
        explanation += "\n"

    sodium_exp, sodium = conversion_explanation(
        input_variables["sodium"][0],
        "sodium",
        22.99,
        1,
        input_variables["sodium"][1],
        "mEq/L",
    )

    explanation += sodium_exp

    if sodium < 125:
        explanation += (
            "The sodium concentration is less than 125 mEq/L, "
            "and so we set the sodium concentration to 125 mEq/L.\n"
        )
        sodium = 125
    elif sodium > 137:
        explanation += (
            "The sodium concentration is greater than 137 mEq/L, "
            "and so we set the sodium concentration to 137 mEq/L.\n"
        )
        sodium = 137
    else:
        explanation += "\n"

    meld_i = (
        0.957 * math.log(creatinine)
        + 0.378 * math.log(bilirubin)
        + 1.120 * math.log(inr)
        + 0.643
    )
    meld_i_rounded = round(meld_i, 1)
    meld_10 = round(meld_i_rounded * 10)

    explanation += (
        f"Applying the first equation gives"
        f"us 0.957 x ln({creatinine}) + 0.378 x "
        f"ln({bilirubin}) + 1.120 x ln({inr}) + 0.643 = {meld_i}. "
    )
    explanation += (
        f"Rounding to the nearest tenth makes"
        f"the MELD (i) score {meld_i_rounded}. We then multiply "
        f"by 10, making the MELD(i) score {meld_10}.\n"
    )

    meld = round(
        meld_10 + 1.32 * (137 - sodium) - (0.033 * meld_10 * (137 - sodium))
    )

    if meld_10 > 11:
        explanation += (
            f"Because the MELD (i) score is greater than 11, "
            f"we then apply the second equation, giving us "
            f"{meld_10} + 1.32 x (137 - {sodium}) -  [0.033 x "
            f"{meld_i} x (137 - {sodium})] = {meld}.\n"
        )

        if meld > 40:
            meldna = 40
            explanation += (
                "The maximum the MELD Na score can be is 40, "
                "and so the patient's MELD score is 40."
            )
        else:
            meldna = meld
            explanation += (
                f"The MELD Na score is less than 40, and so we "
                f"keep the score as it is. The patient's MELDNa "
                f"score, rounded to the nearest integer, "
                f"is {round(meldna)} points.\n"
            )

    else:
        meldna = meld_10
        explanation += (
            f"The patient's MELD (i) score is less than 11, "
            f"and so we do not apply the second equation, making "
            f"the patient's MELD Na score, {round(meldna)} "
            f"points.\n"
        )

    return {"Explanation": explanation, "Answer": round(meldna)}


if __name__ == "__main__":
    # Defining test cases
    test_cases = [
        {
            "creatinine": (1.0, "mg/dL"),
            "dialysis_twice": False,
            'bilirubin': (2.8, "mg/dL"),
            "inr": 1.5,
            'sodium': [139.0, 'mEq/L'],
        }
    ]

    # Iterate the test cases and print the results
    for i, input_variables in enumerate(test_cases, 1):
        print(f"Test Case {i}: Input = {input_variables}")
        result = compute_meldna_explanation(input_variables)
        print(result)
        print("-" * 50)
