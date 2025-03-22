import age_conversion

def compute_has_bled_score_explanation(input_variables):

   explanation = """
   The criteria for the HAS-BLED score are listed below below:
    
       1. Hypertension (Uncontrolled, >160 mmHg systolic): No = 0 points, Yes = +1 point
       2. Renal disease (Dialysis, transplant, Cr >2.26 mg/dL or >200 µmol/L): No = 0 points, Yes = +1 point
       3. Liver disease (Cirrhosis or bilirubin >2x normal with AST/ALT/AP >3x normal): No = 0 points, Yes = +1 point
       4. Stroke history: No = 0 points, Yes = +1 point
       5. Prior major bleeding or predisposition to bleeding: No = 0 points, Yes = +1 point
       6. Labile INR (Unstable/high INRs, time in therapeutic range <60%): No = 0 points, Yes = +1 point
       7. Age >65: No = 0 points, Yes = +1 point
       8. Medication usage predisposing to bleeding (Aspirin, clopidogrel, NSAIDs): No = 0 points, Yes = +1 point
       9. Alcohol use (≥8 drinks/week): No = 0 points, Yes = +1 point
    
    The total HAS-BLED score is calculated by summing the points for each criterion.
    """

    has_bled_score = 0

    num_alcolic_drinks = input_variables["alcoholic_drinks"]

    explanation += f"The current HAS-BLED score is 0.\n"
    age_explanation, age_value = age_conversion.age_conversion_explanation(input_variables["age"])
    explanation += age_explanation

    if age_value > 65:
        explanation += f"Because the patient's age is greater than 65 years, we increment the score by 1, making the current score {has_bled_score} + 1 = {has_bled_score + 1}.\n"
        has_bled_score += 1
    else:
        explanation += f"Because the patient's age is less than 66 years, we don't change the score, keeping the current score at {has_bled_score}.\n"


    if num_alcolic_drinks >= 8:
        explanation += f"The patient has {num_alcolic_drinks} drinks a week. Because the patient has at least 8 alcoholic drinks a week, we increment the score by 1, making the current score {has_bled_score} + 1 = {has_bled_score + 1}.\n"
        has_bled_score += 1
    else:
        explanation += f"The patient has {num_alcolic_drinks} drinks a week. Because the patient has less than 8 alcoholic drinks a week, we don't change the score, keeping the current score at {has_bled_score}.\n"

    default_parameters_set = {"hypertension": "hypertension", "liver_disease_has_bled":"liver disease", "renal_disease_has_bled":"renal disease", "stroke": "stroke history", "prior_bleeding": "prior bleeding", "labile_inr": "labile inr", "medications_for_bleeding": "medications for bleeding"}

    for parameter, name in default_parameters_set.items():

        if parameter not in input_variables:
            explanation += f"The issue, {name}, is missing from the patient note and so we assume it to be absent and so we do not change the score, keeping the current score at {has_bled_score}.\n"
            input_variables[parameter] = False
        elif not input_variables[parameter]:
            explanation += f"The issue, {name}, is reported to be absent for the patient and so we do not change the score, keeping the current score at {has_bled_score}.\n"
        else:
            explanation += f"The issue, {name}, is reported to be present for the patient note and so we increase the score by 1, making the current score {has_bled_score} + 1 = {has_bled_score + 1}.\n"
            has_bled_score += 1
            

    explanation += f"Hence, the patient's HAS-BLED score is {has_bled_score}.\n"

    return {"Explanation": explanation, "Answer": has_bled_score}
