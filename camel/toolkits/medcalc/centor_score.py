import convert_temperature
import age_conversion

def compute_centor_score_explanation(input_variables):

    explanation = """
    The criteria listed in the Centor Score formula are listed below:
    
       1. Age: 3-14 years = +1 point, 15-44 years = 0 points, ≥45 years = -1 point
       2. Exudate or swelling on tonsils: No = 0 points, Yes = +1 point
       3. Tender/swollen anterior cervical lymph nodes: No = 0 points, Yes = +1 point
       4. Temperature >38°C (100.4°F): No = 0 points, Yes = +1 point
       5. Cough: Cough present = 0 points, Cough absent = +1 point
    
    The Centor score is calculated by summing the points for each criterion.\n\n
    """
   
    centor_score = 0
    age_explanation, age = age_conversion.age_conversion_explanation(input_variables["age"])
    explanation += f"The current Centor score is 0.\n"
    explanation += age_explanation

    if 3 <= age <= 14:
        explanation += f"Because the age is between 3 and 14 years, we add one point to the score making current score {centor_score} + 1 = {centor_score + 1}.\n"
        centor_score += 1
    elif 15 <= age <= 44:
        explanation += f"Because the age is in between 15 and 44 years, the score does not change, keeping the score at {centor_score}.\n"
    elif age >= 45:
        explanation +=  f"Because the age is greater than 44 years, we decrease the score by one point, making the score {centor_score} - 1 = {centor_score - 1}.\n"
        centor_score -= 1

    explanation_temp, temp_val = convert_temperature.fahrenheit_to_celsius_explanation(input_variables["temperature"][0], input_variables["temperature"][1])

    explanation += explanation_temp
    if temp_val > 38:
        explanation += f"The patient's temperature is greater than 38 degrees Celsius, and so we add one point to the score, making the current score {centor_score} + 1 = {centor_score + 1}.\n"
        centor_score += 1
    elif temp_val <= 38:
        explanation += f"The patient's temperature is less than or equal to 38 degrees Celsius, and so we do not make any changes to the score, keeping the score at {centor_score}.\n"

    default_parameters_dict = {"cough_absent": "cough absent", "tender_lymph_nodes": "tender/swollen anterior cervical lymph nodes", "exudate_swelling_tonsils": "exudate or swelling on tonsils"}

    for parameter in default_parameters_dict:

        if parameter not in input_variables:
            explanation += f"The patient note does not mention details about '{default_parameters_dict[parameter]}' and so we assume it to be absent. "
            input_variables[parameter] = False
            explanation += f"Hence, we do not change the score, keeping the current score at {centor_score}.\n"
        elif not input_variables[parameter]:
            explanation += f"The patient note reports '{default_parameters_dict[parameter]}' as absent for the patient. Hence, we do not change the score, keeping the current score at {centor_score}.\n"
        else:
            explanation += f"The patient note reports '{default_parameters_dict[parameter]}' as present for the patient. Hence, we increase the score by 1, making the current score {centor_score} + 1 = {centor_score + 1}.\n"
            centor_score += 1
            

    explanation += f"Hence, the Centor score for the patient is {centor_score}.\n"

    return {"Explanation": explanation, "Answer": centor_score}
