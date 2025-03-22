import unit_converter_new

def compute_child_pugh_score_explanation(input_variables):

    cp_score = 0

    explanation =  """
    The criteria for the Child-Pugh Score are listed below:

    1. Bilirubin (Total): <2 mg/dL (<34.2 μmol/L) = +1 point, 2-3 mg/dL (34.2-51.3 μmol/L) = +2 points, >3 mg/dL (>51.3 μmol/L) = +3 points
    2. Albumin: >3.5 g/dL (>35 g/L) = +1 point, 2.8-3.5 g/dL (28-35 g/L) = +2 points, <2.8 g/dL (<28 g/L) = +3 points
    3. INR: <1.7 = +1 point, 1.7-2.3 = +2 points, >2.3 = +3 points
    4. Ascites: Absent = +1 point, Slight = +2 points, Moderate = +3 points
    5. Encephalopathy: No Encephalopathy = +1 point, Grade 1-2 = +2 points, Grade 3-4 = +3 points

    The Child-Pugh Score is calculated by summing the points for each criterion.\n\n
    """

    explanation += "The current child pugh score is 0.\n"

    inr = input_variables['inr']

    ascites_state = input_variables.get('ascites', 'Absent')
    encephalopathy_state = input_variables.get('encephalopathy', 'No Encephalopathy')

    explanation += f"The patient's INR is {inr}. "
    bilirubin_exp, bilirubin = unit_converter_new.conversion_explanation(input_variables['bilirubin'][0], 'bilirubin', 548.66, None, input_variables['bilirubin'][1], "mg/dL")
    albumin_exp, albumin = unit_converter_new.conversion_explanation(input_variables['albumin'][0], 'albumin', 66500, None, input_variables['albumin'][1], "g/dL")


    # INR score calculation
    if inr < 1.7: 
        explanation += f"Because the INR is less than 1.7, we add 1 to the score, making the current total {cp_score} + 1 = {cp_score + 1}.\n"
        cp_score += 1
    elif 1.7 <= inr <= 2.3:
        explanation += f"Because the INR is between 1.7 and 2.3, we add two to the score, making the current total {cp_score} + 2 = {cp_score + 2}.\n"
        cp_score += 2
    elif inr > 2.3:
        explanation +=  f"Because the INR is greater than 2.3, we add three to the score, making the current total {cp_score} + 3 = {cp_score + 3}.\n"
        cp_score += 3

    explanation += bilirubin_exp

    # Bilirubin score calculation
    if bilirubin < 2: 
        explanation += f"Because the Bilirubin concentration is less than 2 mg/dL, we add 1 to the score, making the current total {cp_score} + 1 = {cp_score + 1}.\n"
        cp_score += 1
    elif 2 < bilirubin < 3:
        explanation += f"Because the Bilirubin concentration is between 2 mg/dL and 3 mg/dL, we add 2 to the score, making the current total {cp_score} + 2 = {cp_score + 2}.\n"
        cp_score += 2
    elif bilirubin >= 3:
        explanation += f"Because the Bilirubin concentration is greater than 3 mg/dL, we add 3 to the score, making the current total {cp_score} + 3 = {cp_score + 3}.\n"
        cp_score += 3

    explanation += albumin_exp

    # Albumin score calculation
    if albumin > 3.5: 
        explanation += f"Because the Albumin concentration is greater than 3.5 g/dL, we add 1 to the score, making the current total {cp_score} + 1 = {cp_score + 1}.\n"
        cp_score += 1
    elif 2.8 < albumin <= 3.5:
        explanation += f"Because the Albumin concentration is between 2.8 g/dL and 3.5 g/dL, we add 2 to the score, making the current total {cp_score} + 2 = {cp_score + 2}.\n"
        cp_score += 2 
    elif albumin <= 2.8:
        explanation += f"Because the Albumin concentration is less than 2.8 g/dL, we add 3 to the score, making the current total {cp_score} + 3 = {cp_score + 3}.\n"
        cp_score += 3

    # Ascites score calculation
    if 'ascites' in input_variables:

        if input_variables['ascites'] == 'Absent':
            explanation += f"Ascites is reported to be 'absent' and so we add 1 point to the score, making the current total {cp_score} + 1 = {cp_score + 1}.\n"
            cp_score += 1
        elif ascites_state == 'Slight':
            explanation += f"Ascites is reported to be 'slight' and so we add 2 points to the score, making the current total {cp_score} + 2 = {cp_score + 2}.\n"
            cp_score += 2
        elif ascites_state == 'Moderate':
            explanation += f"Ascites is reported to be 'moderate' and so we add 3 points to the score, making the current total {cp_score} + 3 = {cp_score + 3}.\n"
            cp_score += 3
    else:
        explanation += f"The Ascites state not specified, assuming and so we will assume it to be absent. This means we add 1 point to the score, making the current total {cp_score} + 1 = {cp_score + 1}.\n"
        cp_score += 1

    if 'encephalopathy' in input_variables:
        # Encephalopathy score calculation
        if encephalopathy_state == 'No Encephalopathy':
            explanation +=  f"Encephalopathy state is reported to be 'no encephalopathy' and so we add one point to the score, making the current total {cp_score} + 1 = {cp_score + 1}.\n"
            cp_score += 1
        elif encephalopathy_state == 'Grade 1-2':
            explanation += f"Encephalopathy state is 'Grade 1-2 encephalopathy' and so we add two points to the score, making the current total {cp_score} + 2 = {cp_score + 2}.\n"
            cp_score += 2
        elif encephalopathy_state == 'Grade 3-4':
            explanation += f"Encephalopathy state is 'Grade 3-4 encephalopathy' and so we add three points to the score, making the current total {cp_score} + 3 = {cp_score + 3}.\n"
            cp_score += 3
    else:
        explanation += f"Encephalopathy state is not specified, and so we assume it's value to be 'no encephalopathy.' We add one point to the score, making the current total {cp_score} + 1 = {cp_score + 1}.\n"
        cp_score += 1

    explanation += f"The patient's child pugh score is {cp_score}.\n"

    return {"Explanation": explanation, "Answer": cp_score}


