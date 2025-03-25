r"""
This code is borrowed and modified based on the source code from the 'MedCalc-Bench' repository.
Original repository: https://github.com/ncbi-nlp/MedCalc-Bench

Modifications include:
- rewrite function calculate_pe_wells_explanation
- translation

Date: March 2025
"""


def calculate_pe_wells_explanation(variables):
    r"""
    Calculates the patient's score of Wells' criteria for Pulmonary Embolism and generates a detailed explanatory text.

    Parameters:
        variables (dict): A dictionary containing the following key-value pairs:
            - "clinical_dvt" (boolean): Clinical signs and symptoms of DVT: No = 0 points, Yes = +3 points.
            - "previous_pe" (boolean): Previous, objectively diagnosed PE: No = 0 points, Yes = +1.5 points.
            - "previous_dvt" (boolean): Previous, objectively diagnosed DVT: No = 0 points, Yes = +1.5 points.
            - "heart_rate" (tuple): The patient's heart rate in the format (value, unit).
                - Value (float): The value of the patient's heart rate.
                - Unit (str): The unit of heart rate should be "beats per minute".
            - "immobilization_for_3days" (boolean): Immobilization at least 3 days OR surgery in the previous 4 weeks: No = 0 points, Yes = +1.5 points.
            - "hemoptysis" (boolean): No = 0 points, Yes = +1 point.
            - "surgery_in_past4weeks" (boolean): Whether the patient has had a surgery for the past 4 weeks.
            - "malignancy_with_treatment" (boolean): Malignancy with treatment within 6 months or palliative: No = 0 points, Yes = +1 point.
            - "pe_number_one" (boolean): Hemoptysis: PE is #1 diagnosis OR equally likely: No = 0 points, Yes = +3 points.

    Returns:
        dict: Contains two key-value pairs:
            - "Explanation" (str): A detailed description of the calculation process.
            - "Answer" (float): The patient's score of Wells' criteria for Pulmonary Embolism.

    Notes:
        - None.

    Example:
        calculate_pe_wells_explanation({
            "previous_pe": False,
            "heart_rate": (78.0, 'beats per minute'),
            "immobilization_for_3days": False,
            "hemoptysis": False,
            "surgery_in_past4weeks": False,
            "malignancy_with_treatment": False,
            "pe_number_one": False,
            "previous_dvt": False
        })
        output: "{'Explanation': "\n    The criteria for the Wells' Criteria for Pulmonary Embolism score are listed below:\n\n        1. Clinical signs and symptoms of DVT: No = 0 points, Yes = +3 points\n        2. PE is #1 diagnosis OR equally likely: No = 0 points, Yes = +3 points\n        3. Heart rate > 100: No = 0 points, Yes = +1.5 points\n        4. Immobilization at least 3 days OR surgery in the previous 4 weeks: No = 0 points, Yes = +1.5 points\n        5. Previous, objectively diagnosed PE or DVT: No = 0 points, Yes = +1.5 points\n        6. Hemoptysis: No = 0 points, Yes = +1 point\n        7. Malignancy with treatment within 6 months or palliative: No = 0 points, Yes = +1 point\n\n    The total score is calculated by summing the points for each criterion.\\n\\n\n    The Well's score for pulmonary embolism is currently 0.\nClinical signs and symptoms of DVT are not reported and so we assume that this is missing from the patient, keeping the current total at 0. Pulmonary Embolism is not reported to be the #1 diagnosis and so the total score remains unchanged, keeping the total score at 0.\nThe patient's heart rate is 78.0 beats per minute. The heart rate is less than 100 bpm, and so the score remains unchanged, keeping the total score at 0.\nBecause the patient has not had an immobilization for at least 3 days, and the patient did not have a surgery in the past 4 weeks, the score remains at 0.\nBecause the patient has no previous diagnosis of pulmonary embolism (PE) or deep vein thrombosis (DVT), the score remains at 0.\nHemoptysis is reported to be absent and so the total score remains unchanged, keeping the total score at 0.\nMalignany with treatment within 6 months or palliative is reported to be absent and so the total score remains unchanged, keeping the total score at 0.\nThe patient's Well's score for pulmonary embolism is 0.\n", 'Answer': 0}"
    """

    explanation = r"""
    The criteria for the Wells' Criteria for Pulmonary Embolism score are listed below:

        1. Clinical signs and symptoms of DVT: No = 0 points, Yes = +3 points
        2. PE is #1 diagnosis OR equally likely: No = 0 points, Yes = +3 points
        3. Heart rate > 100: No = 0 points, Yes = +1.5 points
        4. Immobilization at least 3 days OR surgery in the previous 4 weeks: No = 0 points, Yes = +1.5 points
        5. Previous, objectively diagnosed PE or DVT: No = 0 points, Yes = +1.5 points
        6. Hemoptysis: No = 0 points, Yes = +1 point
        7. Malignancy with treatment within 6 months or palliative: No = 0 points, Yes = +1 point

    The total score is calculated by summing the points for each criterion.\n\n
    """

    explanation += "The Well's score for pulmonary embolism is currently 0.\n"

    score = 0

    if 'clinical_dvt' in variables:
        if variables['clinical_dvt']:
            explanation += f'Clinical signs and symptoms of DVT are reported to be present and so three points are added to the score, making the current total {score} + 3 = {score + 3}. '
            score += 3
        else:
            explanation += f'Clinical signs and symptoms of DVT are repoted to be absent and so the total score remains unchanged, keeping the total score at {score}. '
    else:
        explanation += f'Clinical signs and symptoms of DVT are not reported and so we assume that this is missing from the patient, keeping the current total at {score}. '

    if 'pe_number_one' in variables:
        if variables['pe_number_one']:
            explanation += f'Pulmonary Embolism is reported to be the #1 diagnosis or equally likely to be the #1 diagonsis and so we add 3 points to the score making the current total = {score} + 3 = {score + 3}.\n'
            score += 3
        else:
            explanation += f'Pulmonary Embolism is not reported to be the #1 diagnosis and so the total score remains unchanged, keeping the total score at {score}.\n'
    else:
        explanation += f'Whether Pulmonary Embolism is the #1 diagonsis or is equally likely to being the #1 diagnosis is not reported and so we assume this statement is false, keeping the total unchanged at {score}.\n'

    explanation += f"The patient's heart rate is {variables['heart_rate'][0]} beats per minute. "
    if variables['heart_rate'][0] > 100:
        explanation += f'The heart rate is more than 100 bpm, and so the score is increased by 1.5, making the total score, {score} + 1.5 = {score + 1.5}.\n'
        score += 1.5
    else:
        explanation += f'The heart rate is less than 100 bpm, and so the score remains unchanged, keeping the total score at {score}.\n'

    if 'immobilization_for_3days' not in variables:
        explanation += f"The report does not give an indication on whether the patient has had an immobilization for at least 3 days and so we assume this to be false."
        variables['immobilization_for_3days'] = False

    if 'surgery_in_past4weeks' not in variables:
        explanation += f"The report does not give an indication on whether the patient has had a surgery for the past 4 weeks and so we assume this to be false."
        variables['surgery_in_past4weeks'] = False

    if not variables['immobilization_for_3days'] and not variables['surgery_in_past4weeks']:
        explanation += f"Because the patient has not had an immobilization for at least 3 days, and the patient did not have a surgery in the past 4 weeks, the score remains at {score}.\n"
    elif not variables['immobilization_for_3days'] and variables['surgery_in_past4weeks']:
        explanation += f'Because the patient did not have an immobilization for at least 3 days but the patient had a surgery in the past 4 weeks, the score increases to {score} + 1.5 = {score + 1.5}.\n'
        score += 1.5
    elif variables['immobilization_for_3days'] and not variables['surgery_in_past4weeks']:
        explanation += f'Because the patient has had an immobilization for at least 3 days but the patient did not have a surgery in the past 4 weeks, the score increases to {score} + 1.5 = {score + 1.5}.\n'
        score += 1.5
    elif variables['immobilization_for_3days'] and variables['surgery_in_past4weeks']:
        explanation += f'Because the patient has had an immobilization for at least 3 days and the patient had a surgery in the past 4 weeks, the score increases to {score} + 1.5 =  {score + 1.5}.\n'
        score += 1.5

    if 'previous_pe' not in variables:
        explanation += f"The report does not give an indication on if the patient has previously had pulmonary embolism diagnosed and so we assume this to be false."
        variables['previous_pe'] = False

    if 'previous_dvt' not in variables:
        explanation += f"The report does not give an indication on if the patient has previously been diagnosed with deep vein thrombosis and so we assume this to be false."
        variables['previous_dvt'] = False

    if not variables['previous_pe'] and not variables['previous_dvt']:
        explanation += f'Because the patient has no previous diagnosis of pulmonary embolism (PE) or deep vein thrombosis (DVT), the score remains at {score}.\n'
    elif not variables['previous_pe'] and variables['previous_dvt']:
        explanation += f'The patient not been diagnosed with pulmonary embolis (PE), but the patient has previously been diagnosed with deep vein thrombosis (DVT), we increase the current total by 1.5 so that {score} + 1.5 = {score + 1.5}.\n'
        score += 1.5
    elif variables['previous_pe'] and not variables['previous_dvt']:
        explanation += f'Because the patient has been previously diagnosed for pulmonary embolism (PE), but the patient has never been diagnosed for deep vein thrombosis (DVT), we increase the current total by 1.5 so that {score} + 1.5 = {score + 1.5}.\n'
        score += 1.5
    elif variables['previous_pe'] and variables['previous_dvt']:
        explanation += f'Because the patient has previously been diagnosed for pulmonary embolism (PE) and deep vein thrombosis (DVT), we increase the current total by 1.5 so that {score} + 1.5 = {score + 1.5}.\n'
        score += 1.5

    if 'hemoptysis' in variables:
        if variables['hemoptysis']:
            explanation += f'Hemoptysis is reported to be present and so one point is incremented to the score, making the current total {score} + 1 = {score + 1}.\n'
            score += 1
        else:
            explanation += f'Hemoptysis is reported to be absent and so the total score remains unchanged, keeping the total score at {score}.\n'
    else:
        explanation += f'Hemoptysis is not reported in the patient note and so we assume that it is missing from the patient, keeping the total score at {score}.\n'

    if 'malignancy_with_treatment' in variables:
        if variables['malignancy_with_treatment']:
            explanation += f'Malignany with treatment within 6 months or palliative is reported to be present and so one point is added to the score, making the total score {score} + 1 =  {score + 1}.\n'
            score += 1
        else:
            explanation += f'Malignany with treatment within 6 months or palliative is reported to be absent and so the total score remains unchanged, keeping the total score at {score}.\n'
    else:
        explanation += f'Malignany with treatment within 6 months or palliative is not reported in the patient note and so we assume that this is absent for the patient, keeping the score at {score}.\n'

    explanation += f"The patient's Well's score for pulmonary embolism is {score}.\n"

    return {"Explanation": explanation, "Answer": score}


if __name__ == "__main__":
    # Defining test cases
    test_cases = [
        {
            "previous_pe": False,
            "heart_rate": (78.0, 'beats per minute'),
            "immobilization_for_3days": False,
            "hemoptysis": False,
            "surgery_in_past4weeks": False,
            "malignancy_with_treatment": False,
            "pe_number_one": False,
            "previous_dvt": False
        },
        {
            "previous_pe": False,
            "heart_rate": (106.0, 'beats per minute'),
            "immobilization_for_3days": False,
            "hemoptysis": False,
            "surgery_in_past4weeks": True,
            "malignancy_with_treatment": False,
            "pe_number_one": False,
            "previous_dvt": False
        },
        {
            "previous_pe": False,
            "heart_rate": (129.0, 'beats per minute'),
            "immobilization_for_3days": False,
            "surgery_in_past4weeks": False,
            "clinical_dvt": True,
            "malignancy_with_treatment": False,
            "pe_number_one": True,
            "previous_dvt": False
        }
    ]
    # {'Previously Documented Pulmonary Embolism': False, 'Heart Rate or Pulse': [78.0, 'beats per minute'], 'Immobilization for at least 3 days': False, 'Hemoptysis': False, 'Surgery in the previous 4 weeks': False, 'Malignancy with treatment within 6 months or palliative': False, 'Pulmonary Embolism is #1 diagnosis OR equally likely': False, 'Previously documented Deep Vein Thrombosis': False}

    # {'Heart Rate or Pulse': [106.0, 'beats per minute'], 'Immobilization for at least 3 days': False, 'Hemoptysis': False, 'Surgery in the previous 4 weeks': True, 'Malignancy with treatment within 6 months or palliative': False, 'Pulmonary Embolism is #1 diagnosis OR equally likely': False, 'Previously Documented Pulmonary Embolism': False, 'Previously documented Deep Vein Thrombosis': False}

    # {'Heart Rate or Pulse': [129.0, 'beats per minute'], 'Immobilization for at least 3 days': False, 'Surgery in the previous 4 weeks': False, 'Clinical signs and symptoms of Deep Vein Thrombosis': True, 'Malignancy with treatment within 6 months or palliative': False, 'Pulmonary Embolism is #1 diagnosis OR equally likely': True, 'Previously Documented Pulmonary Embolism': False, 'Previously documented Deep Vein Thrombosis': False}

    # Iterate the test cases and print the results
    for i, input_variables in enumerate(test_cases, 1):
        print(f"Test Case {i}: Input = {input_variables}")
        result = calculate_pe_wells_explanation(input_variables)
        print(result)
        print("-" * 50)
