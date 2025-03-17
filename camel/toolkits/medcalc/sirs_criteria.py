import unit_converter_new
import convert_temperature

def sirs_criteria_explanation(input_parameters):

    explanation = """
    The rules for SIRS Criteria are listed below:
    
       1. Temperature >38°C (100.4°F) or <36°C (96.8°F): No = 0 points, Yes = +1 point
       2. Heart rate >90: No = 0 points, Yes = +1 point
       3. Respiratory rate >20 or PaCO₂ <32 mm Hg: No = 0 points, Yes = +1 point
       4. White blood cell count (WBC) >12,000/mm³, <4,000/mm³, or >10% bands: No = 0 points, Yes = +1 point
    
    The total number of criteria met is taken by summing the score for each criteria.\n\n
    """


    explanation += "The current count of SIRS criteria met is 0.\n"

    temperature = input_parameters["temperature"]

    temp_exp, temperature = convert_temperature.fahrenheit_to_celsius_explanation(temperature[0], temperature[1])
    heart_rate = input_parameters["heart_rate"][0]
    wbc_exp, wbc = unit_converter_new.convert_to_units_per_liter_explanation(input_parameters["wbc"][0], input_parameters["wbc"][1], "white blood cell", "mm^3")

    criteria_met = 0

    explanation += temp_exp

    if temperature > 38:
        explanation += f"Because the temperature is greater than 38 degrees celsius, we increment the criteria count by 1 making the current total {criteria_met} + 1 = {criteria_met + 1}.\n"
        criteria_met += 1
    elif temperature < 36:
        explanation += f"Because the temperature is less than 36 degrees celsius, we increment the criteria count by 1 making the current total {criteria_met} + 1 = {criteria_met + 1}.\n"
        criteria_met += 1
    else:
        explanation += f"Because the temperature is between 36 and 38 degrees celsius, this does not meet SIRS criteria for temperature, and so the current total remains at {criteria_met}.\n"

    explanation += f"The patient's heart rate is {heart_rate} beats per minute. "

    if heart_rate > 90:
        explanation += f"Because the heart rate is greater than 90 beats per minute, this meets SIRS criteria and so we increment the criteria count by 1 making the current total {criteria_met} + 1 = {criteria_met + 1}.\n"
        criteria_met += 1
    else:
        explanation += f"Because the heart rate is less than 90 beats per minute, this does not meet SIRS criteria for heart rate, and so the current total remains at {criteria_met}.\n"
        criteria_met += 1

    explanation += wbc_exp

    if wbc > 12000:
        explanation += f"Because the white blood cell count is greater than 12000 count per mm^3, we increment the criteria count by 1 making the current total {criteria_met} + 1 = {criteria_met + 1}.\n"
        criteria_met += 1
    elif wbc < 4000:
        explanation += f"Because the white blood cell count is less than 4000 count per mm^3, we increment the criteria count by 1 making the current total {criteria_met} + 1 = {criteria_met + 1}.\n"
        criteria_met += 1
    else:
        explanation += f"Because the white blood cell count is between 4000 and 12000 count per mm^3, this does not meet SIRS criteria for white blood cell count, and so the current total remains at {criteria_met}.\n"

    explanation += "The final SIRS criteria is whether the patient has a respiratory rate of more than 20 breaths per minute or if the patient's PaCO₂ partial pressure is less than 32 mm Hg. "

    if 'respiratory_rate' in input_parameters:
        respiratory_rate = input_parameters['respiratory_rate'][0]
        explanation += f"The patient's respiratory rate is {respiratory_rate} breaths per minute, "
        res = ""

        if respiratory_rate > 20:
            res += f"which is greater than 20 breaths per minute. "
            resp_met = True
        else:
            res += "which is less or equal to than 20 breaths per min. "
            resp_met = False

        explanation += res
    else:
        explanation += "The patient's respiratory rate is not provided and so we assume that the patient's respiratory rate is less than or equal to 20 breaths per minute. "
        resp_met = False

    if 'paco2' in input_parameters:
        paco2 = input_parameters['paco2'][0]
        explanation += f"The patient's PaCO₂ partial pressure is {paco2} mm Hg, "
        res = "" 

        if paco2 < 32:
            res += f"which is less than than 32 mm Hg. "
            paco2_met = True
        elif paco2 > 32:
            res += f"which is greater or equal to than 32 mm Hg. "
            paco2_met = False
        
        explanation += res
    else:
        explanation += "The patient's PaCO₂ partial pressure is not provided and so we assume that the patient's partial pressure is greater than or equal to 32 mm Hg."
        paco2_met = False 

    if resp_met or paco2_met:
        explanation += f"At least one of the criteria is met, and so we increment the criteria count by 1 giving us a total of {criteria_met} + 1 = {criteria_met + 1} criteria met.\n"
        criteria_met += 1
    else:
        explanation += f"Neither criteria met and so keep the current total at {criteria_met}.\n"

    explanation += f"Hence, the the number of SIRS criteria met by the patient is {criteria_met}.\n"

    return {"Explanation": explanation, "Answer": criteria_met}
     
