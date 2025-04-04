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
- rewrite function compute_cci_explanation
- translation

Date: March 2025
"""

from camel.toolkits.medcalc_bench.utils.age_conversion import (
    age_conversion_explanation,
)


def compute_cci_explanation(input_parameters):
    r"""
        Calculates the patient's Charlson Comorbidity Index (CCI) and generates
        a detailed explanatory text.

        Parameters:
            input_parameters (dict): A dictionary containing the following
            key-value pairs:
                - "age" (tuple): The patient's albumin concentration in the
                format (value, unit).
                    - Value (float): Age.
                    - Unit (str): The unit can be "months", "years".
                - "mi" (boolean): Myocardial infarction (history of definite or
                probable MI with EKG changes and/or enzyme changes)
                - "chf" (boolean): Congestive heart failure (CHF) (exertional
                or paroxysmal nocturnal dyspnea, responsive to digitalis,
                diuretics, or afterload reducing agents)
                - "peripheral_vascular_disease" (boolean): Peripheral vascular
                disease
                - "cva" (boolean): Cerebrovascular accident (CVA)
                - "tia" (boolean): transient ischemic attack (TIA)
                - "connective_tissue_disease" (boolean): Connective tissue
                    disease
                - "dementia" (boolean): Dementia
                - "copd" (boolean): Chronic obstructive pulmonary disease
                - "connective_tissue_disease" (boolean): Connective tissue
                    disease
                - "peptic_ucler_disease" (boolean): Peptic ulcer disease (any
                history of treatment for ulcer disease or ulcer bleeding)
                - "liver_disease" (str): Liver disease: None, Mild,
                Moderate to severe
                - "moderate_to_severe_ckd" (boolean): Moderate to severe
                chronic kidney disease
                - "diabetes_mellitus" (str): None, diet-controlled,
                    Uncomplicated,
                End-organ damage
                - "hemiplegia" (boolean): Hemiplegia
                - "solid_tumor" (str): None, Localized, Metastatic
                - "leukemia" (boolean): Leukemia
                - "lymphoma" (boolean): Lymphoma
                - "aids" (boolean): AIDS


        Returns:
            dict: Contains two key-value pairs:
                - "Explanation" (str): A detailed description of the
                calculation process.
                - "Answer" (float): The patient's Glomerular
                    Filtration Rate (GFR).

        Notes:
            - Uses the `conversion_explanation` function to convert source unit
            to target unit.

        Example:
            compute_cci_explanation({
                "age": (45, 'years'),
                "mi": False,
                "chf": False,
                "peripheral_vascular_disease": False,
                "cva": False,
                "tia": False,
                "connective_tissue_disease": False,
                "dementia": True,
                "copd": True,
                "hemiplegia": False,
                "peptic_ucler_disease": False,
                "diabetes_mellitus": "Uncomplicated",
                "moderate_to_severe_ckd": False,
                "solid_tumor": "Localized",
                "leukemia": False,
                "lymphoma": False,
                "aids": False,
                "liver_disease": "Mild",
            })

            output: "{'Explanation': "\n    The Charlson Comorbidity Index
            (CCI)
            are listed below:\n    \n       1. Age: <50 years = 0 points,
            50-59 years = +1 point, 60-69 years = +2 points, 70-79 years = +3
            points, ≥80 years = +4 points\n       2. Myocardial infarction (
            history of definite or probable MI with EKG changes and/or enzyme
            changes): No = 0 points, Yes = +1 point\n       3. Congestive heart
            failure (CHF) (exertional or paroxysmal nocturnal dyspnea,
            responsive to digitalis, diuretics, or afterload reducing agents):
            No = 0 points, Yes = +1 point\n       4. Peripheral vascular
            disease (intermittent claudication, past bypass for chronic
            arterial insufficiency, history of gangrene or acute arterial
            insufficiency, untreated thoracic or abdominal aneurysm ≥6 cm):
            No = 0 points, Yes = +1 point\n       5. Cerebrovascular accident
            (CVA) or transient ischemic attack (TIA) (history with minor or
            no residuals): No = 0 points, Yes = +1 point\n       6. Dementia
            (chronic cognitive deficit): No = 0 points, Yes = +1 point\n
            7. Chronic obstructive pulmonary disease (COPD): No = 0 points,
            Yes = +1 point\n       8. Connective tissue disease: No = 0 points,
            Yes = +1 point\n       9. Peptic ulcer disease (any history of
            treatment for ulcer disease or ulcer bleeding): No = 0 points,
            Yes = +1 point\n       10. Liver disease: None = 0 points, Mild =
            +1 point, Moderate to severe = +3 points\n       11. Diabetes
            mellitus: None or diet-controlled = 0 points, Uncomplicated = +1
            point, End-organ damage = +2 points\n       12. Hemiplegia: No =
            0 points, Yes = +2 points\n       13. Moderate to severe chronic
            kidney disease (CKD): No = 0 points, Yes = +2 points\n       14.
            Solid tumor: None = 0 points, Localized = +2 points, Metastatic =
            +6 points\n       15. Leukemia: No = 0 points, Yes = +2 points\n
            16. Lymphoma: No = 0 points, Yes = +2 points\n       17. AIDS: No =
            0 points, Yes = +6 points\n    \n    The total score is calculated
            by summing the points for each criterion.\\n\\n\n    The current
            CCI is value is 0.\nThe patient is 45 years old. Because the
            patient's age is less than 50, we do not add any points to the
            score,
            keeping the current total at 0.\nThe issue,
            'Myocardial infarction,'
            is reported to be absent for the patient and so we do not add any
            points to the score, keeping the current total at 0.\nThe patient's
            CCI score is 0 points.\nThe issue, 'Congestive heart failure,' is
            reported to be absent for the patient and so we do not add any
            points
            to the score, keeping the current total at 0.\nThe patient's CCI
            score is 0 points.\nThe issue, 'Peripheral vascular disease,' is
            reported to be absent for the patient and so we do not add any
            points to the score, keeping the current total at 0.\nThe patient's
            CCI score is 0 points.\nAt least one of transient ischemic attack
            or
            cerebral vascular accident must be present in the patient for a
            point
            to be added to the current total.\nTransient ischemic attacks is
            reported to be absent for the patient.\nCerebral vascular accident
            is
            reported to be absent for the patient.\nNeither of the issues are
            reported to be present for the patient and so we add 0 point to the
            score, keeping the current total at 0.\nThe issue, 'Connective
            tissue
            diease,' is reported to be absent for the patient and so we do not
            add any points to the score, keeping the current total at 0.\nThe
            patient's CCI score is 0 points.\n The issue,'Dementia,' is present
            for the patient and so we add 1 point to the score, making the
            current
            total 0 + 1 = 1.\nThe patient's CCI score is 1 points.\n The issue,
            'Chronic obstructive pulmonary disease,' is present for the patient
            and so we add 1 point to the score, making the current total
            1 + 1 =
            2.\nThe patient's CCI score is 2 points.\nThe issue, 'Hemiplegia,'
            is reported to be absent for the patient and so we do not add any
            points to the score, keeping the current total at 2.\nThe patient's
            CCI score is 2 points.\nThe issue, 'Peptic ulcer disease,' is
            reported
            to be absent for the patient and so we do not add any points to the
            score, keeping the current total at 2.\nThe patient's CCI score is
            2 points.\n The issue,'Diabetes mellitus,' is present for the
            patient
            and so we add 1 point to the score, making the current total
            2 + 1 = 3.
            \nThe patient's CCI score is 3 points.\nThe issue, 'Moderate to
            severe
            chronic kidney disease,' is reported to be absent for the patient
            and
            so we do not add any points to the score, keeping the current total
            at 3.\nThe patient's CCI score is 3 points.\n The issue,'Solid
            tumor,'
            is present for the patient and so we add 1 point to the score,
            making
            the current total 3 + 1 = 4.\nThe patient's CCI score is 4 points.
            \nThe
            issue, 'Leukemia,' is reported to be absent for the patient and
            so we
            do not add any points to the score, keeping
            the current total at 4.
            \nThe patient's CCI score is 4 points.\nThe issue, 'Lymphoma,' is
            reported to be absent for the patient and so we do not add any
            points
            to the score, keeping the current total at 4.\nThe patient's
            CCI score
            is 4 points.\nThe issue, 'AIDS,' is reported to be absent for the
            patient and so we do not add any points to the score, keeping the
            current total at 4.\nThe patient's CCI score is 4 points.\n The
            issue,'Liver Disease,' is present for the patient and so we add 1
            point to the score, making the current total 4 + 1 = 5.\nThe
            patient's CCI score is 5 points.\n", 'Answer': 5}
    "
    """

    parameter_to_name = {
        "mi": "Myocardial infarction",
        'chf': "Congestive heart failure",
        "peripheral_vascular_disease": "Peripheral vascular disease",
        "cva": "Cerebrovascular accident",
        "tia": "Transient ischemic attacks",
        'connective_tissue_disease': "Connective tissue diease",
        "dementia": "Dementia",
        "copd": "Chronic obstructive pulmonary disease",
        'hemiplegia': "Hemiplegia",
        "peptic_ucler_disease": "Peptic ulcer disease",
        "diabetes_mellitus": "Diabetes mellitus",
        "moderate_to_severe_ckd": 'Moderate to severe chronic kidney disease',
        "solid_tumor": "Solid tumor",
        "leukemia": "Leukemia",
        "lymphoma": "Lymphoma",
        "aids": "AIDS",
        "liver_disease": "Liver Disease",
    }

    two_point_params = [
        'hemiplegia',
        "moderate_to_severe_ckd",
        "leukemia",
        "lymphoma",
    ]

    explanation = r"""
    The Charlson Comorbidity Index (CCI) are listed below:
       1. Age: <50 years = 0 points, 50-59 years = +1 point, 60-69 years = +2
        points, 70-79 years = +3 points, ≥80 years = +4 points
       2. Myocardial infarction (history of definite or probable MI with EKG
        changes and/or enzyme changes): No = 0 points, Yes = +1 point
       3. Congestive heart failure (CHF) (exertional or paroxysmal nocturnal
        dyspnea, responsive to digitalis, diuretics, or afterload reducing
        agents): No = 0 points, Yes = +1 point
       4. Peripheral vascular disease (intermittent claudication, past bypass
        for chronic arterial insufficiency, history of gangrene or acute
        arterial insufficiency, untreated thoracic or abdominal
        aneurysm ≥6 cm): No = 0 points, Yes = +1 point
       5. Cerebrovascular accident (CVA) or transient ischemic attack (TIA)
        (history with minor or no residuals): No = 0 points, Yes = +1 point
       6. Dementia (chronic cognitive deficit): No = 0 points, Yes = +1 point
       7. Chronic obstructive pulmonary disease (COPD): No = 0 points,
        Yes = +1 point
       8. Connective tissue disease: No = 0 points, Yes = +1 point
       9. Peptic ulcer disease (any history of treatment for ulcer
        disease or ulcer bleeding): No = 0 points, Yes = +1 point
       10. Liver disease: None = 0 points, Mild = +1 point,
        Moderate to severe = +3 points
       11. Diabetes mellitus: None or diet-controlled = 0 points,
        Uncomplicated = +1 point, End-organ damage = +2 points
       12. Hemiplegia: No = 0 points, Yes = +2 points
       13. Moderate to severe chronic kidney disease (CKD):
        No = 0 points, Yes = +2 points
       14. Solid tumor: None = 0 points, Localized = +2 points,
        Metastatic = +6 points
       15. Leukemia: No = 0 points, Yes = +2 points
       16. Lymphoma: No = 0 points, Yes = +2 points
       17. AIDS: No = 0 points, Yes = +6 points

    The total score is calculated by summing the points for each criterion.\n\n
    """

    age_exp, age = age_conversion_explanation(input_parameters["age"])
    explanation += "The current CCI is value is 0.\n"
    explanation += age_exp
    cci = 0

    if age < 50:
        explanation += (
            f"Because the patient's age is less than 50, "
            f"we do not add any points to the score, "
            f"keeping the current total at {cci}.\n"
        )
    elif 49 < age < 60:
        explanation += (
            f"Because the patient's age is between 50 and 59, "
            f"we add 1 point to the score, "
            f"making the current total = {cci} + 1 = {cci + 1}.\n"
        )
        cci += 1
    elif 59 < age < 70:
        explanation += (
            f"Because the patient's age is between 60 and 69, "
            f"we add 2 points to the score, "
            f"making the current total = {cci} + 2 = {cci + 2}.\n"
        )
        cci += 2
    elif 69 < age < 80:
        explanation += (
            f"Because the patient's age is between 70 and 79, "
            f"we add 3 points to the score, "
            f"making the current total = {cci} + 3 = {cci + 3}.\n"
        )
        cci += 3
    elif age >= 80:
        explanation += (
            f"Because the patient's age is greater than "
            f"or equal to 80 years, we add 4 points to "
            f"the score, making the current "
            f"total = {cci} + 4 = {cci + 4}.\n"
        )
        cci += 4

    for parameter in parameter_to_name:
        if parameter == "tia":
            continue

        if parameter == "cva":
            explanation += (
                "At least one of transient ischemic attack "
                "or cerebral vascular accident must be present "
                "in the patient for a point to be "
                "added to the current total.\n"
            )

            if 'tia' not in input_parameters:
                explanation += (
                    "Transient ischemic attacks is not reported "
                    "for the patient and so we assume it to be "
                    "absent.\n"
                )
                input_parameters["tia"] = False
            elif input_parameters['tia']:
                explanation += (
                    "Transient ischemic attacks is reported to "
                    "be present for the patient.\n"
                )
            else:
                explanation += (
                    "Transient ischemic attacks is reported to "
                    "be absent for the patient.\n"
                )

            if 'cva' not in input_parameters:
                explanation += (
                    "Cerebral vascular accident is not reported "
                    "for the patient and so we assume it to be "
                    "absent.\n"
                )
                input_parameters["cva"] = False
            elif input_parameters['cva']:
                explanation += (
                    "Cerebral vascular accident is reported to "
                    "be present for the patient.\n"
                )
            else:
                explanation += (
                    "Cerebral vascular accident is reported to "
                    "be absent for the patient.\n"
                )

            if input_parameters['cva'] or input_parameters['tia']:
                explanation += (
                    f"Because at least one of the issues is "
                    f"reported to be present for the patient, "
                    f"we add 1 point to the score, making the "
                    f"current total {cci} + 1 = {cci + 1}.\n"
                )
                cci += 1
                continue
            else:
                explanation += (
                    f"Neither of the issues are reported to be "
                    f"present for the patient and so we add 0 "
                    f"point to the score, keeping the current "
                    f"total at {cci}.\n"
                )
                continue

        if parameter == 'solid_tumor' and parameter not in input_parameters:
            explanation += (
                f"The patient's solid tumor status is not "
                f"reported and so we assume that it is 'none.' "
                f"Hence, do not add any points to the score, "
                f"keeping the current total at {cci}.\n"
            )
            continue
        elif (
            parameter == 'solid_tumor'
            and parameter in input_parameters
            and input_parameters[parameter] == 'none'
        ):
            explanation += (
                f"The patient's solid tumor is reported to be "
                f"'none' and so we do not add any points to the "
                f"score, keeping the current total at {cci}.\n"
            )
            continue
        elif (
            parameter == 'solid_tumor'
            and parameter in input_parameters
            and input_parameters[parameter] == 'localized'
        ):
            explanation += (
                f"The patient's solid tumor is reported to be "
                f"'localized' and so we add 2 points to the "
                f"score, making the current total {cci} + 2 = "
                f"{cci + 2}.\n"
            )
            cci += 2
            continue
        elif (
            parameter == 'solid_tumor'
            and parameter in input_parameters
            and input_parameters[parameter] == 'metastatic'
        ):
            explanation += (
                f"The patient's solid tumor is reported to be "
                f"'metastatic' and so we add 6 points to the "
                f"score, making the current total {cci} + 6 = "
                f"{cci + 6}.\n"
            )
            cci += 6
            continue

        if parameter == 'liver_diease' and parameter not in input_parameters:
            explanation += (
                f"The patient's liver disease status is not "
                f"reported and so we assume the value to be "
                f"'none or diet-controlled.' No points are added "
                f"to the score, keeping the current total at "
                f"{cci}.\n"
            )
            continue
        elif (
            parameter == 'liver_disease'
            and parameter in input_parameters
            and input_parameters[parameter] == 'none'
        ):
            explanation += (
                f"The patient's liver disease is reported to be "
                f"'none' and so we do not add any points to the "
                f"score, keeping the current total at {cci}.\n"
            )
            continue
        elif (
            parameter == 'liver_disease'
            and parameter in input_parameters
            and input_parameters[parameter] == 'mild'
        ):
            explanation += (
                f"The patient's liver disease is reported to be "
                f"'mild' and so we add 1 point to the score, "
                f"making the current total {cci} + 1 = {cci + 1}.\n"
            )
            cci += 1
            continue
        elif (
            parameter == 'liver_disease'
            and parameter in input_parameters
            and input_parameters[parameter] == 'moderate to severe'
        ):
            explanation += (
                f"The patient's liver disease is reported to be "
                f"'moderate to severe' and so we add 3 points to "
                f"the score, making the current "
                f"total {cci} + 3 = {cci + 3}.\n"
            )
            cci += 3
            continue

        if (
            parameter == 'diabetes_mellitus'
            and 'diabetes_mellitus' not in input_parameters
        ):
            explanation += (
                f"The patient's diabetes mellitus status is not "
                f"reported and so we assume the value to be "
                f"'none or diet-controlled.' No points are added "
                f"to the score, keeping the current total at "
                f"{cci}.\n"
            )
            continue
        elif (
            parameter == 'diabetes_mellitus'
            and parameter in input_parameters
            and input_parameters[parameter] == 'none or diet-controlled'
        ):
            explanation += (
                f"The patient's diabetes mellitus is reported to "
                f"be 'none or diet-controlled' and so we add 0 "
                f"point to the score, keeping the current total "
                f"at {cci}.\n"
            )
            continue
        elif (
            parameter == 'diabetes_mellitus'
            and parameter in input_parameters
            and input_parameters[parameter] == 'uncomplicated'
        ):
            explanation += (
                f"The patient's diabetes mellitus is reported to "
                f"be 'uncomplicated' and so we add 1 point "
                f"to the score, making the current "
                f"total {cci} + 1 = {cci + 1}.\n"
            )
            cci += 1
            continue
        elif (
            parameter == 'diabetes_mellitus'
            and parameter in input_parameters
            and input_parameters[parameter] == 'end-organ damage'
        ):
            explanation += (
                f"The patient's diabetes mellitus is reported to "
                f"be 'end-organ damage' and so we add 2 points "
                f"to the score, making the current total {cci} + "
                f"2 = {cci + 2}.\n"
            )
            cci += 2
            continue

        if (
            parameter in two_point_params
            and parameter in input_parameters
            and input_parameters[parameter]
        ):
            explanation += (
                f"The issue, '{parameter_to_name[parameter]},"
                f"' is reported to be present for the patient "
                f"and so we add 2 points to the score, "
                f"making the current total {cci} + 2 = {cci + 2}.\n"
            )
            cci += 2
        elif (
            parameter == 'aids'
            and parameter in input_parameters
            and input_parameters['aids']
        ):
            explanation += (
                f'AIDS is reported to be present for the patient '
                f'and so we add 6 points to the score, '
                f'making the current total at '
                f'{cci} + 6 = {cci + 6}.\n'
            )
            cci += 6

        elif (
            parameter not in two_point_params
            and parameter != 'aids'
            and parameter in input_parameters
            and input_parameters[parameter]
        ):
            explanation += (
                f" The issue,'{parameter_to_name[parameter]},"
                f"' is present for the patient and so we add 1 "
                f"point to the score, making the current total "
                f"{cci} + 1 = {cci + 1}.\n"
            )
            cci += 1
        elif parameter in input_parameters and not input_parameters[parameter]:
            explanation += (
                f"The issue, '{parameter_to_name[parameter]},"
                f"' is reported to be absent for the patient and "
                f"so we do not add any points to the score, "
                f"keeping the current total at {cci}.\n"
            )
        elif parameter not in input_parameters:
            explanation += (
                f"The issue, '{parameter_to_name[parameter]},"
                f"' is reported to be absent for the patient and "
                f"so we do not add any points to the score, "
                f"keeping the current total at {cci}.\n"
            )

        explanation += f"The patient's CCI score is {cci} points.\n"

    return {"Explanation": explanation, "Answer": cci}


if __name__ == "__main__":
    # Defining test cases
    test_cases = [
        {
            "age": (45, 'years'),
            "mi": False,
            "chf": False,
            "peripheral_vascular_disease": False,
            "cva": False,
            "tia": False,
            "connective_tissue_disease": False,
            "dementia": True,
            "copd": True,
            "hemiplegia": False,
            "peptic_ucler_disease": False,
            "diabetes_mellitus": "Uncomplicated",
            "moderate_to_severe_ckd": False,
            "solid_tumor": "Localized",
            "leukemia": False,
            "lymphoma": False,
            "aids": False,
            "liver_disease": "Mild",
        }
    ]

    # Iterate the test cases and print the results
    for i, input_variables in enumerate(test_cases, 1):
        print(f"Test Case {i}: Input = {input_variables}")
        result = compute_cci_explanation(input_variables)
        print(result)
        print("-" * 50)
