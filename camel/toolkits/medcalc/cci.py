import age_conversion

def compute_cci_explanation(input_parameters):
    parameter_to_name = {"mi": "Myocardial infarction", 'chf': "Congestive heart failure", 
                         "peripheral_vascular_disease": "Peripheral vascular disease", 
                         "cva": "Cerebrovascular accident", "tia": "Transient ischemic attacks", 'connective_tissue_disease': "Connective tissue diease",
                         "dementia": "Dementia", "copd": "Chronic obstructive pulmonary disease", 'hemiplegia': "Hemiplegia",
                         "peptic_ucler_disease": "Peptic ulcer disease", "liver_disease": "Liver disease",
                         "diabetes_mellitus": "Diabetes mellitus", "moderate_to_severe_ckd": 'Moderate to severe chronic kidney disease', 
                         "solid_tumor": "Solid tumor", "leukemia": "Leukemia", "lymphoma": "Lymphoma", "aids": "AIDS",
                         "liver_disease": "Liver Disease"}
    
    
     
    two_point_params = set(['hemiplegia', "moderate_to_severe_ckd", "leukemia", "lymphoma"])

    explanation = """
    The Charlson Comorbidity Index (CCI) are listed below:
    
       1. Age: <50 years = 0 points, 50-59 years = +1 point, 60-69 years = +2 points, 70-79 years = +3 points, ≥80 years = +4 points
       2. Myocardial infarction (history of definite or probable MI with EKG changes and/or enzyme changes): No = 0 points, Yes = +1 point
       3. Congestive heart failure (CHF) (exertional or paroxysmal nocturnal dyspnea, responsive to digitalis, diuretics, or afterload reducing agents): No = 0 points, Yes = +1 point
       4. Peripheral vascular disease (intermittent claudication, past bypass for chronic arterial insufficiency, history of gangrene or acute arterial insufficiency, untreated thoracic or abdominal aneurysm ≥6 cm): No = 0 points, Yes = +1 point
       5. Cerebrovascular accident (CVA) or transient ischemic attack (TIA) (history with minor or no residuals): No = 0 points, Yes = +1 point
       6. Dementia (chronic cognitive deficit): No = 0 points, Yes = +1 point
       7. Chronic obstructive pulmonary disease (COPD): No = 0 points, Yes = +1 point
       8. Connective tissue disease: No = 0 points, Yes = +1 point
       9. Peptic ulcer disease (any history of treatment for ulcer disease or ulcer bleeding): No = 0 points, Yes = +1 point
       10. Liver disease: None = 0 points, Mild = +1 point, Moderate to severe = +3 points
       11. Diabetes mellitus: None or diet-controlled = 0 points, Uncomplicated = +1 point, End-organ damage = +2 points
       12. Hemiplegia: No = 0 points, Yes = +2 points
       13. Moderate to severe chronic kidney disease (CKD): No = 0 points, Yes = +2 points
       14. Solid tumor: None = 0 points, Localized = +2 points, Metastatic = +6 points
       15. Leukemia: No = 0 points, Yes = +2 points
       16. Lymphoma: No = 0 points, Yes = +2 points
       17. AIDS: No = 0 points, Yes = +6 points
    
    The total score is calculated by summing the points for each criterion.\n\n
    """

 
    age_exp, age = age_conversion.age_conversion_explanation(input_parameters["age"])
    explanation += "The current CCI is value is 0.\n"
    explanation += age_exp
    cci = 0

    if age < 50:
        explanation += f"Because the patient's age is less than 50, we do not add any points to the score, keeping the current total at {cci}.\n"
    elif 49 < age < 60:
        explanation += f"Because the patient's age is between 50 and 59, we add 1 point to the score, making the current total = {cci} + 1 = {cci + 1}.\n"
        cci += 1
    elif 59 < age < 70:
        explanation += f"Because the patient's age is between 60 and 69, we add 2 points to the score, making the current total = {cci} + 2 = {cci + 2}.\n"
        cci += 2
    elif 69 < age < 80:
        explanation += f"Because the patient's age is between 70 and 79, we add 3 points to the score, making the current total = {cci} + 3 = {cci + 3}.\n"
        cci += 3
    elif age >= 80:
        explanation += f"Because the patient's age is greater than or equal to 80 years, we add 4 points to the score, making the current total = {cci} + 4 = {cci + 4}.\n"
        cci += 4

    for parameter in parameter_to_name:

        if parameter == "tia":
            continue

        if parameter == "cva":
            explanation += "At least one of transient ischemic attack or cerebral vascular accident must be present in the patient for a point to be added to the current total.\n"

            if 'tia' not in input_parameters:
                explanation += f"Transient ischemic attacks is not reported for the patient and so we assume it to be absent.\n"
                input_parameters["tia"] = False
            elif input_parameters['tia']:
                explanation += f"Transient ischemic attacks is reported to be present for the patient.\n"
            else:
                explanation += f"Transient ischemic attacks is reported to be absent for the patient.\n"

            if 'cva' not in input_parameters:
                explanation += f"Cerebral vascular accident is not reported for the patient and so we assume it to be absent.\n"
                input_parameters["cva"] = False 
            elif input_parameters['cva']:
                explanation += f"Cerebral vascular accident is reported to be present for the patient.\n"
            else:
                explanation += f"Cerebral vascular accident is reported to be absent for the patient.\n"
           

            if input_parameters['cva'] or input_parameters['tia']:
                explanation += f"Because at least one of the issues is reported to be present for the patient, we add 1 point to the score, making the current total {cci} + 1 = {cci + 1}.\n"
                cci += 1
                continue
            else:
                explanation += f"Neither of the issues are reported to be present for the patient and so we add 0 point to the score, keeping the current total at {cci}.\n"
                continue

        if parameter == 'solid_tumor' and parameter not in input_parameters:
            explanation += f"The patient's solid tumor status is not reported and so we assume that it is 'none.' Hence, do not add any points to the score, keeping the current total at {cci}.\n"
            continue
        elif parameter == 'solid_tumor' and parameter in input_parameters and input_parameters[parameter] == 'none':
            explanation += f"The patient's solid tumor is reported to be 'none' and so we do not add any points to the score, keeping the current total at {cci}.\n"
            continue
        elif parameter == 'solid_tumor' and parameter in input_parameters and input_parameters[parameter] == 'localized':
            explanation += f"The patient's solid tumor is reported to be 'localized' and so we add 2 points to the score, making the current total {cci} + 2 = {cci + 2}.\n"
            cci += 2
            continue
        elif parameter =='solid_tumor' and parameter in input_parameters and input_parameters[parameter] == 'metastatic':
            explanation += f"The patient's solid tumor is reported to be 'metastatic' and so we add 6 points to the score, making the current total {cci} + 6 = {cci + 6}.\n"
            cci += 6
            continue

        if parameter == 'liver_diease' and parameter not in input_parameters:
            explanation +=  f"The patient's liver disease status is not reported and so we assume the value to be 'none or diet-controlled.' No points are added to the score, keeping the current total at {cci}.\n"
            continue
        elif parameter == 'liver_disease' and parameter in input_parameters and input_parameters[parameter] == 'none':
            explanation += f"The patient's liver disease is reported to be 'none' and so we do not add any points to the score, keeping the current total at {cci}.\n"
            continue
        elif parameter == 'liver_disease' and parameter in input_parameters and input_parameters[parameter] == 'mild':
            explanation += f"The patient's liver disease is reported to be 'mild' and so we add 1 point to the score, making the current total {cci} + 1 = {cci + 1}.\n"
            cci += 1
            continue
        elif parameter == 'liver_disease' and parameter in input_parameters and input_parameters[parameter] == 'moderate to severe':
            explanation += f"The patient's liver disease is reported to be 'moderate to severe' and so we add 3 points to the score, making the current total {cci} + 3 = {cci + 3}.\n"
            cci += 3
            continue

        if parameter == 'diabetes_mellitus' and 'diabetes_mellitus' not in input_parameters:
            explanation +=  f"The patient's diabetes mellitus status is not reported and so we assume the value to be 'none or diet-controlled.' No points are added to the score, keeping the current total at {cci}.\n"
            continue
        elif parameter == 'diabetes_mellitus' and parameter in input_parameters and input_parameters[parameter] == 'none or diet-controlled':
            explanation +=  f"The patient's diabetes mellitus is reported to be 'none or diet-controlled' and so we add 0 point to the score, keeping the current total at {cci}.\n"
            continue
        elif parameter == 'diabetes_mellitus' and parameter in input_parameters and input_parameters[parameter] == 'uncomplicated':
            explanation += f"The patient's diabetes mellitus is reported to be 'uncomplicated' and so we add 1 point to the score, making the current total {cci} + 1 = {cci + 1}.\n"
            cci += 1
            continue
        elif parameter == 'diabetes_mellitus' and parameter in input_parameters and input_parameters[parameter] == 'end-organ damage':
            explanation += f"The patient's diabetes mellitus is reported to be 'end-organ damage' and so we add 2 points to the score, making the current total {cci} + 2 = {cci + 2}.\n"
            cci += 2    
            continue


        if parameter in two_point_params and parameter in input_parameters and input_parameters[parameter]:
            explanation += f"The issue, '{parameter_to_name[parameter]},' is reported to be present for the patient and so we add 2 points to the score, making the current total {cci} + 2 = {cci + 2}.\n"
            cci += 2
        elif parameter == 'aids' and parameter in input_parameters and input_parameters['aids']:
            explanation += f'AIDS is reported to be present for the patient and so we add 6 points to the score, making the current total at {cci} + 6 = {cci + 6}.\n' 
            cci += 6

        elif parameter not in two_point_params and parameter != 'aids' and parameter in input_parameters and input_parameters[parameter]:
            explanation += f" The issue,'{parameter_to_name[parameter]},' is present for the patient and so we add 1 point to the score, making the current total {cci} + 1 = {cci + 1}.\n"
            cci += 1
        elif parameter in input_parameters and not input_parameters[parameter]:
            explanation += f"The issue, '{parameter_to_name[parameter]},' is reported to be absent for the patient and so we do not add any points to the score, keeping the current total at {cci}.\n"
        elif parameter not in input_parameters:
            explanation += f"The issue, '{parameter_to_name[parameter]},' is reported to be absent for the patient and so we do not add any points to the score, keeping the current total at {cci}.\n"

        explanation += f"The patient's CCI score is {cci} points.\n"

    return {"Explanation": explanation, "Answer": cci}

