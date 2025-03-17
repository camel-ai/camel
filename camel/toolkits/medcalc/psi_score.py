import os
import json 
import unit_converter_new
import age_conversion
import convert_temperature

def psi_score_explanation(input_variables):

    age = age_conversion.age_conversion(input_variables["age"])
    gender = input_variables["sex"]
    pulse = input_variables["heart_rate"][0]
    temperature_exp, temperature = convert_temperature.fahrenheit_to_celsius_explanation(input_variables["temperature"][0], input_variables["temperature"][1])
    pH = input_variables["pH"]
    respiratory_rate = input_variables["respiratory_rate"][0]
    sys_bp = input_variables["sys_bp"][0]
    bun_exp, bun = unit_converter_new.conversion_explanation(input_variables["bun"][0], 'BUN', 28.02, None, input_variables["bun"][1], "mg/dL")
    sodium_exp, sodium = unit_converter_new.conversion_explanation(input_variables["sodium"][0], "sodium", 22.99, None, input_variables["sodium"][1], "mmol/L")
    glucose_exp, glucose = unit_converter_new.conversion_explanation(input_variables["glucose"][0], "glucose", 180.16, None, input_variables["glucose"][1], "mg/dL")
    hemocratit = input_variables["hemocratit"][0]
    partial_pressure_oxygen = input_variables.get("partial_pressure_oxygen")

    explanation = """
    The rules for computing the Pneumonia Severity Index (PSI) are shown below:
    
       1. Age: Enter age in years (age score will be equal to age in years)
       2. Sex: Female = -10 points, Male = 0 points
       3. Nursing home resident: No = 0 points, Yes = +10 points
       4. Neoplastic disease: No = 0 points, Yes = +30 points
       5. Liver disease history: No = 0 points, Yes = +20 points
       6. Congestive heart failure (CHF) history: No = 0 points, Yes = +10 points
       7. Cerebrovascular disease history: No = 0 points, Yes = +10 points
       8. Renal disease history: No = 0 points, Yes = +10 points
       9. Altered mental status: No = 0 points, Yes = +20 points
       10. Respiratory rate ≥30 breaths/min: No = 0 points, Yes = +20 points
       11. Systolic blood pressure <90 mmHg: No = 0 points, Yes = +20 points
       12. Temperature <35°C (95°F) or >39.9°C (103.8°F): No = 0 points, Yes = +15 points
       13. Pulse ≥125 beats/min: No = 0 points, Yes = +10 points
       14. pH <7.35: No = 0 points, Yes = +30 points
       15. BUN ≥30 mg/dL or ≥11 mmol/L: No = 0 points, Yes = +20 points
       16. Sodium <130 mmol/L: No = 0 points, Yes = +20 points
       17. Glucose ≥250 mg/dL or ≥14 mmol/L: No = 0 points, Yes = +10 points
       18. Hematocrit <30%: No = 0 points, Yes = +10 points
       19. Partial pressure of oxygen <60 mmHg or <8 kPa: No = 0 points, Yes = +10 points
       20. Pleural effusion on x-ray: No = 0 points, Yes = +10 points
    
    The total score is calculated by summing the points for each criterion.\n\n
    """


    explanation += f"The current PSI score is 0.\n"
    age_explanation, age = age_conversion.age_conversion_explanation(input_variables["age"])
    explanation += age_explanation
    explanation += f"We add the the number of years of age of the patient to the psi score, making the current total 0 + {age} = {age}.\n"
      
    psi_score = 0

    psi_score += age

    if gender == "Female":
        explanation += f"Because the patient is female, we subtract 10 points from the current total, making the current total {psi_score} - 10 = {psi_score - 10}.\n"
        psi_score -= 10
    else:
        explanation += f"Because the patient is male, no adjustments are made to the score, keeping the current total at {psi_score}.\n"


    parameters = {"nursing_home_resident": ("Nursing Home Resident", 10), "neoplastic_disease": ("Neoplastic disease", 30), 
                  "liver_disease": ("Liver disease history", 20), "chf": ("CHF History", 10), 
                  "cerebrovascular_disease": ("Cerebrovascular disease history", 10), "renal_disease": ("Renal Disease History", 10),
                  "altered_mental_status": ("Altered Mental Status", 20), "pleural_effusion": ("Pleural effusion on x-ray", 10)}
    

    for parameter in parameters:
        
        if parameter == 'nursing_home_resident':
            if parameter not in input_variables:
                explanation += f"Whether patient is a nursing home resident is not reported. Hence, we assume this to be false and so not add any points to the current total keeping it at {psi_score}.\n"
            elif not input_variables[parameter]:
                explanation += f"The patient is not a nursing home resident and so we do not add any points to the current total keeping it at {psi_score}.\n"
            else:
                explanation += f"The patient is reported to be a nursing home resident and so we add 10 points to the score, making the current total {psi_score} + 10 = {psi_score + 10}.\n"
                psi_score += 10
            continue
        
        if parameter not in input_variables:
            explanation += f"{parameters[parameter][0]} is not reported for the patient and so we assume it to be false. Hence, we do not add any points to the current total keeping it at {psi_score}.\n"
        elif not input_variables[parameter]:
            explanation += f"{parameters[parameter][0]} is reported to be false for the patient and so we do not add any points to the current total keeping it at {psi_score}.\n"
        elif input_variables[parameter]:
            points = parameters[parameter][1]
            explanation += f"{parameters[parameter][0]} is reported to be present for the patient and so we add {points} points to the score, making the current total {psi_score} + {points} = {psi_score + points}.\n"
            psi_score += points

    explanation += f"The patient's pulse is {pulse} beats per minute. "

    if pulse >= 125:
        explanation += f"The pulse is greater or equal to than 125 beats per minute, and so we add 10 points to the score, making the current total {psi_score} + 10 = {psi_score + 10}.\n"
        psi_score += 10
    else:
        explanation += f"The pulse is less than 125 beats per minute and so we do not add any points to the score, keeping it at {psi_score}.\n"


    explanation += temperature_exp
    if temperature < 35:
        explanation += f"The patient's temperature is less than 35 degrees celsius, and so we add 15 points to the score, making the current total {psi_score} + 15 = {psi_score + 15}.\n"
        psi_score += 15
    elif temperature > 39.9:
        explanation += f"The patient's temperature is greater than 39.9 degrees celsius and so we add 15 points to the score, making the current total {psi_score} + 15 = {psi_score + 15}.\n"
        psi_score += 15
    else:
        explanation += f"The patient's temperature is greater than 35 degrees celsius and the temperature is less than 39.9 degrees celsius, and so we do not add any points to the score, keeping the total at {psi_score}.\n"


    explanation += f"The patient's pH is {pH}. "

    if pH < 7.35:
        explanation += f"The patient's pH is less than 7.35, and so we add 30 points to the score, making the current total {psi_score} + 30 = {psi_score + 30}.\n"
        psi_score += 30
    else:
        explanation += f"The patient's pH is greater than or equal to 7.35, and so we do not add any points to the score, keeping the current total at {psi_score}.\n"

    explanation += f"The patient's respiratory rate is {respiratory_rate} breaths per minute. "

    if respiratory_rate >= 30:
        explanation += f"The patient's respiratory rate is greater than or equal to 30 breaths per minute and so we add 20 points to the score, making current total {psi_score} + 20 = {psi_score + 20}.\n"
        psi_score += 20
    else:
        explanation += f"The patient's respiratory rate is less than 30 breaths per minute and so we do not add any points to the score, keeping the total score at {psi_score}.\n"
    
    explanation += f"The patient's systolic blood pressure is {sys_bp} mm Hg. "

    if sys_bp < 90:
        explanation += f"The patient's systolic blood pressure is less than 90 mm Hg and so we add 20 points to the score, making current total {psi_score} + 20 = {psi_score + 20}.\n"
        psi_score += 20
    else:
        explanation += f"The patient's systolic blood pressure is greater than or equal to 90 mm Hg and so we do not add any points to the score, keeping the total at {psi_score}.\n"

    explanation += bun_exp

    if bun >= 30:
        explanation += f"The patient's BUN is greater than or equal to 30 mg/dL, and so we add 20 points to the score, making current total {psi_score} + 20 = {psi_score + 20}.\n"
        psi_score += 20
    else:
        explanation += f"The patient's BUN is less than 30 mg/dL, and so we do not add any points to the score, keeping the total at {psi_score}.\n"


    explanation += sodium_exp

    if sodium < 130:
        explanation += f"The patient's sodium is less than 130 mmol/L, and so we add 20 points to the score, making the current total {psi_score} + 20 = {psi_score + 20}.\n"
        psi_score += 20
    else:
        explanation += f"The patient's sodium is greater than or equal to 130 mmol/L, and so we do not add any points to the scor, keeping the total at {psi_score}.\n"

    explanation += glucose_exp

    if glucose >= 250:
        explanation += f"The patient's glucose concentration is greater than 250 mg/dL, and so we add 10 points to the score, making the current total {psi_score} + 10 = {psi_score + 10}.\n"
        psi_score += 10
    else:
        explanation += f"The patient's glucose concentration is less than or equal to than 250 mg/dL, and so we not add any points to the current total, keeping it at {psi_score}.\n"

    explanation += f"The patient's hemocratit is {hemocratit} %. "

    if hemocratit < 30:
        explanation += f"The patient's hemocratit is less than 30%, and so we add 10 points to the score, making the current total {psi_score} + 10 = {psi_score + 10}.\n"
        psi_score += 10
    else:
        explanation += f"The patient's hemocratit is greater than or equal to 30%, and so we not add any points to the current total, keeping it at {psi_score}.\n"


    if partial_pressure_oxygen[1] == "mm Hg":
        explanation += f"The patient's partial pressure of oxygen is {partial_pressure_oxygen[0]} mm Hg. "

        if partial_pressure_oxygen[0] < 60:
            explanation += f"The patient's partial pressure of oxygen is less than 60 mm Hg, and so we add {psi_score} points to the score, making the current total {psi_score} + 10 = {psi_score + 10}.\n"
            psi_score += 10
        else:
            explanation += f"The patient's partial pressure of oxygen is greater than or equal to 60 mm Hg, and so we not add any points to the current total, keeping it at {psi_score}.\n"


    elif partial_pressure_oxygen[1] == "kPa":
        explanation += f"The patient's partial pressure of oxygen is {partial_pressure_oxygen[0]} kPa. "

        
        if partial_pressure_oxygen[0] < 8:
            explanation += f"The patient's partial pressure of oxygen is less than 8 kPa, and so we add {psi_score} points to the score, making the current total {psi_score} + 10 = {psi_score + 10}.\n"
            psi_score += 10
        else:
            explanation += f"The patient's partial pressure of oxygen is greater than or equal to 8 kPa, and so we not add any points to the current total, keeping it at {psi_score}.\n"

    explanation += f"The patient's PSI score is {psi_score}.\n"

    return {"Explanation": explanation, "Answer": psi_score}
