import age_conversion

def generate_cha2ds2_vasc_explanation(params):

    score = 0

    output = """
    The criteria for the CHA2DS2-VASc score are listed below:

    1. Age: < 65 years = 0 points, 65-74 years = +1 point, ≥ 75 years = +2 points
    2. Sex: Female = +1 point, Male = 0 points
    3. Congestive Heart Failure (CHF) history: No = 0 points, Yes = +1 point
    4. Hypertension history: No = 0 points, Yes = +1 point
    5. Stroke, Transient Ischemic Attack (TIA), or Thromboembolism history: No = 0 points, Yes = +2 points
    6. Vascular disease history (previous myocardial infarction, peripheral artery disease, or aortic plaque): No = 0 points, Yes = +1 point
    7. Diabetes history: No = 0 points, Yes = +1 point

    The CHA2DS2-VASc score is calculated by summing the points for each criterion.\n\n
    """
   
    output += "The current CHA2DS2-VASc score is 0.\n"

    text, age = age_conversion.age_conversion_explanation(params['age'])
    output += text

      # Age
    if age >= 75:
        output += f"Because the age is greater than 74, two points added to the score, making the current total {score} + 2 = {score + 2}.\n"
        score += 2
    elif age >= 65:
        output += f"Because the age is between 65 and 74, one point added to the score, making the current total {score} + 1 = {score + 1}.\n"
        score += 1
    else:
        output += f"Because the age is less than 65 years, no points are added to the current total, keeping the total at {score}.\n"

    sex = params['sex']  # Sex of the patient (Male/Female)

    output += f"The patient's gender is {sex.lower()} "

    if sex.lower() == 'female':
        output += f"and so one point is added to the score, making the current total {score} + 1 = {score + 1}.\n"
        score += 1
    else:
        output += f"and so no points are added to the current total, keeping the total at {score}.\n"

    # Congestive Heart Failure
    if 'chf' in params:
        chf = params['chf']
        output += f"The patient history for congestive heart failure is {'present' if chf else 'absent'}. "
    else:
        chf = False
        output += f"Because the congestive heart failure history is not specified in the patient note, we assume it is absent from the patient. "

    # Congestive Heart Failure (CHF)
    if chf:
        output += f"Because the patient has congestive heart failure, one point is added to the score, making the current total {score} + 1 = {score + 1}.\n"
        score += 1
    else:
        output += f"Because the patient does not have congestive heart failure, no points are added to the current total, keeping the total at {score}.\n"


    # Hypertension
    if 'hypertension' in params:
        hypertension = params['hypertension']
        output += f"The patient history for hypertension is {'present' if hypertension else 'absent'}. "
    else:
        hypertension = False
        output += f"Because hypertension history is not specified in the patient note, we assume that it is absent from the patient. "

     # Congestive Heart Failure (CHF)
    if hypertension:
        output += f"Because the patient has hypertension, one point is added to the score, making the current total {score} + 1 = {score + 1}.\n"
        score += 1
    else:
        output += f"Because the patient does not have hypertension, no points are added to the current total, keeping the total at {score}.\n"
   
    output += f"One criteria of the CHA2DS2-VASc score is to check if the patient has had any history of stroke, transient ischemic attacks (TIA), or thromboembolism. "    

    if 'stroke' in params:
        stroke = params['stroke']
        output += f"Based on the patient note, the patient history for stroke is {'present' if stroke else 'absent'}. "
    else:
        stroke = False
        output += f"Because stroke history is not specified in the patient note, we assume that it is absent from the patient. "

    if 'tia' in params:
        tia = params['tia']
        output += f"Based on the patient note, the patient history for tia is {'present' if tia else 'absent'}. "
    else:
        tia = False
        output += f"Because tia history is not specified in the patient note, we assume that it is absent from the patient. "

    if 'thromboembolism' in params:
        thromboembolism = params['thromboembolism']
        output += f"Based on the patient note, the patient history for thromboembolism is {'present' if thromboembolism else 'absent'}. "
    else:
        thromboembolism = False
        output += f"Because thromboembolism history is not specified in the patient note, we assume it to be absent. "

    # Stroke / TIA / Thromboembolism
    if stroke or tia or thromboembolism:
        output += f"Because at least one of stroke, tia, or thromboembolism is present, two points are added to the score, making the current total {score} + 2 = {score + 2}.\n"
        score += 2
    else:
        output += f"Because all of stroke, tia, or thromboembolism are absent, no points are added to score, keeping the score at {score}.\n"

    if 'vascular_disease' in params:
        vascular_disease = params['vascular_disease']
        output += f"Based on the patient note, the patient history for vascular disease is {'present' if vascular_disease else 'absent'}. "
    else:
        vascular_disease = False
        output += f"Because vascular disease history is not specified in the patient note, we assume it to be absent.\n"

    if vascular_disease:
        output += f"Because the patient has vascular disease, one point is added to the score, making the current total {score} + 1 = {score + 1}. "
        score += 1
    else:
        output += f"Because the patient does not have vascular disease, no points are added to score, keeping the score at {score}. "

    if 'diabetes' in params:
        diabetes = params['diabetes']
        output += f"Based on the patient note, the patient history for diabetes is {'present' if diabetes else 'absent'}. "
    else:
        diabetes = False
        output += f"Because diabetes history is not specified in the patient note, we assume it's value as 'absent'. "

    if diabetes:
        output += f"Because the patient has diabetes, one point is added to the score, making the current total {score} + 1 = {score + 1}.\n"
        score += 1
    else:
        output += f"Because the patient does not have diabetes, no points are added to score, keeping the score at {score}.\n"

    output += f"The patient's CHA2DS2-VASc Score is {score}.\n"

    return {"Explanation": output, "Answer": score}

