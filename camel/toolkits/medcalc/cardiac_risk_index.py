import json 
import unit_converter_new

def compute_cardiac_index_explanation(input_variables):
    # List of parameters and their default values
    parameters = {
        'elevated_risk_surgery': "elevated risk surgery",
        'ischemetic_heart_disease': "ischemetic heart disease",
        'congestive_heart_failure': "congestive heart failure", 
        'cerebrovascular_disease': "cerebrovascular disease",
        'pre_operative_insulin_treatment': "pre-operative insulin treatment",
        'pre_operative_creatinine': "pre-operative creatinine" 
    }

    output = """
    The criteria for the Revised Cardiac Risk Index (RCRI) are listed below:
    
       1. Elevated-risk surgery (intraperitoneal, intrathoracic, or suprainguinal vascular): No = 0 points, Yes = +1 point
       2. History of ischemic heart disease (history of myocardial infarction, positive exercise test, current chest pain due to myocardial ischemia, use of nitrate therapy, or ECG with pathological Q waves): No = 0 points, Yes = +1 point
       3. History of congestive heart failure (pulmonary edema, bilateral rales or S3 gallop, paroxysmal nocturnal dyspnea, or chest x-ray showing pulmonary vascular redistribution): No = 0 points, Yes = +1 point
       4. History of cerebrovascular disease (prior transient ischemic attack or stroke): No = 0 points, Yes = +1 point
       5. Pre-operative treatment with insulin: No = 0 points, Yes = +1 point
       6. Pre-operative creatinine >2 mg/dL (176.8 μmol/L): No = 0 points, Yes = +1 point
    
    The total score is calculated by summing the points for each criterion.\n\n
    """

    # Initializing scores and output explanation
    cri = 0
    output += "The current cardiac risk index is 0.\n"
    #output += "Total Score = elevated_risk_surgery_score + ischemetic_heart_disease_score + congestive_heart_failure_score + cerebrovascular_disease_score + pre_operative_insulin_treatment_score + pre_operative_creatinine_score.\n\n"    

    for param_name, full_name in parameters.items():
        param_value = input_variables.get(param_name)

        # If parameter is missing, assume it as False
        if param_value is None:
            output += f"The patient note does not mention about {full_name} and is assumed to be absent. "
            input_variables[param_name] = False
            param_value = False
        elif param_name != 'pre_operative_creatinine':
            value = 'absent' if not param_value else 'present'
            output += f"The patient note reports {full_name} as '{value}' for the patient. "
        elif param_name == 'pre_operative_creatinine':
            explanation, param_value = unit_converter_new.conversion_explanation(param_value[0], "Pre-Operative Creatinine", 113.12, None, param_value[1], "mg/dL" )
            input_variables['pre_operative_creatinine'] = [param_value, "mg/dL"]
            output += explanation
          
        if param_name == 'pre_operative_creatinine':

            if param_value > 2: 
                output += f"The patient has pre-operative creatinine > 2 mg/dL, so we increment the score by one and the current total will be {cri} + 1 = {cri + 1}.\n"
                cri += 1
            else:
                output += f"The patient has pre-operative creatinine <= 2 mg/dL, so we keep the score the same at {cri}.\n"
            continue

        if param_value:
            output += f"This means that we increment the score by one and the current total will be {cri} + 1 = {cri + 1}.\n"
            cri += 1
        else:
            output += f"This means that the total score remains unchanged at {cri}.\n"


    output += f"\nThe cardiac risk index score is {cri}.\n"

    return {"Explanation": output, "Answer": cri}

