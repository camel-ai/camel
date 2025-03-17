import age_conversion


param_full_name = { 
                    "surgery_type": "type of surgery",
                    "major_surgery": ("major surgery in the last month", 1),
                    "chf": ("congestive heart failure in the last month", 1),
                    "sepsis": ("sepsis in the last month", 1),
                    "pneumonia": ("pneumonia in the last month", 1),
                    "immobilizing_plaster_case": ("immobilizing plaster cast in the last month", 2),
                    "hip_pelvis_leg_fracture": ("hip, pelvis, or leg fracture in the last month", 5),
                    "stroke": ("stroke in the last month", 5),
                    "multiple trauma": ("multiple trauma in the last month", 5),
                    "acute_spinal_chord_injury": ("acute spinal cord injury causing paralysis in the last month",  5),
                    "varicose_veins": ("varicose veins", 1),
                    "current_swollen_legs": ("current swollen legs", 1),
                    "current_central_venuous": ("current central venuous access", 2),
                    "previous_dvt": ('previous DVT documented', 3),
                    "previous_pe": ('previous pulmonary embolism documented', 3),
                    "family_history_thrombosis": ("family history of thrombosis", 3),
                    "positive_factor_v": ("Positive Factor V Leiden", 3),
                    "positive_prothrombin": ("Positive prothrombin 20210A", 3),
                    "serum_homocysteine": ("elevated serum homocysteine", 3),
                    "positive_lupus_anticoagulant": ("positive lupus anticoagulant", 3),
                    "elevated_anticardiolipin_antibody": ("elevated anticardiolipin antibody", 3),
                    "heparin_induced_thrombocytopenia": ("heparin-induced thrombocytopenia", 3),
                    "congenital_acquired_thrombophilia": ("Other congenital or acquired thrombophilia", 3),
                    "mobility": "mobility",
                    "inflammatory_bowel_disease": ("history of inflammatory bowel disease", 1),
                    "acute_myocardial_infarction": ("acute Myocardial infarction", 1),
                    "copd": ("chronic Obstructive Pulmonary Disease", 1),
                    "malignancy": ("malignancy", 2),
                    "bmi": "bmi"
                }

surgery_type = {"none": 0, "minor": 1, "major": 2,  "laparoscopic": 2, "arthroscopic": 2, "elective major lower extremity arthroplasty": 5}
mobility = {"normal": 0, "on bed rest": 1, "confined to bed >72 hours": 2}



def caprini_score_explanation(input_parameters):


    explanation = """
    The criteria for the Caprini Score are listed below:
  
     1. Age, years: ≤40 = 0 points, 41-60 = +1 point, 61-74 = +2 points, ≥75 = +3 points
     2. Sex: Male = 0 points, Female = +1 point
     3. Type of surgery: None = 0 points, Minor = +1 point, Major >45 min (laparoscopic or arthroscopic) = +2 points, Elective major lower extremity arthroplasty = +5 points
     4. Recent (≤1 month) event: Major surgery = +1 point, Congestive heart failure (CHF) = +1 point, Sepsis = +1 point, Pneumonia = +1 point, Immobilizing plaster cast = +1 point, Hip, pelvis, or leg fracture = +5 points, Stroke = +5 points, Multiple trauma = +5 points, Acute spinal cord injury causing paralysis = +5 points
     5. Venous disease or clotting disorder: Varicose veins = +1 point, Current swollen legs = +1 point, Current central venous access = +2 points, History of deep vein thrombosis (DVT) or pulmonary embolism (PE) = +3 points, Family history of thrombosis = +3 points, Positive Factor V Leiden = +3 points, Positive prothrombin 20210A = +3 points, Elevated serum homocysteine = +3 points
     6. Other congenital or acquired thrombophilia: Positive lupus anticoagulant = +3 points, Elevated anticardiolipin antibody = +3 points, Heparin-induced thrombocytopenia = +3 points
     7. Mobility: Normal, out of bed = 0 points, Medical patient currently on bed rest = +1 point, Patient confined to bed >72 hours = +2 points
     8. Other present and past history: History of inflammatory bowel disease = +1 point, BMI ≥25 = +1 point, Acute myocardial infarction = +1 point, Chronic obstructive pulmonary disease (COPD) = +1 point, Present or previous malignancy = +2 points
  
    The total Caprini Score is calculated by summing the points for each criterion.\n\n
    """


    explanation += "The patient's current caprini score is 0.\n"
    score = 0

    gender = input_parameters["sex"]

    explanation += f"The patient's gender is {gender}.\n"

    age_exp, age = age_conversion.age_conversion_explanation(input_parameters["age"])
    explanation += age_exp

    if age <= 40:
        explanation += f"Because the patient's age is less or equal to 40, we do not add any points to the total, keeping the current total at {score}.\n"
    elif 41 <= age <= 60:
        explanation += f"Because the patient's age is between 61 and 74, we add one point to the current total, making the current total, {score} + 1 = {score + 1}.\n"
        score += 1
    elif 61 <= age <= 74:
        explanation += f"Because the patient's age is between 61 and 74, we add two points to the current total, making the current total, {score} + 2 = {score + 2}.\n"
        score += 2
    elif age >= 75:
        explanation += f"Because the patient's age at least 75, we add three points to the current total, making the current total, {score} + 3 = {score + 3}.\n"
        score += 3

    for param, value in param_full_name.items():
        
        if param not in input_parameters:
            explanation += f"The patient does not report anything about {param_full_name[param][0]} and so we assume this to be false. Hence, 0 points are added to the score, keeping the total at {score}. "

        elif param == "mobility":
            value = input_parameters[param]

            explanation += f"The patient's mobility status is '{value}'. Hence, we add {mobility[value]} points to the total, making the current total {mobility[value]} + {score} = {mobility[value] + score}.\n "
            score += mobility[value]

        elif param == "surgery_type":
            value = input_parameters[param]
            explanation += f"The patient's surgery type is reported to be '{value}'. Hence, we add {surgery_type[value]} points to the total, making the current total {surgery_type[value]} + {score} = {surgery_type[value] + score}.\n "
            score += surgery_type[value]

        elif param == "bmi":
        
            if input_parameters["bmi"][0] > 25:
                explanation += f"The patient's BMI is {input_parameters['bmi'][0]} kg/m^2 which is greater than 25 kg/m^2, and so we add 2 points to the total, making the current total {score} + 2 = {score + 2}.\n"
                score += 2
            else:
                explanation += f"The patient's BMI is {input_parameters['bmi'][0]} kg/m^2 which is less than 25 kg/m^2, and so we add 0 points to the total, keeping the total at {score}.\n"

        elif input_parameters[param]:
            points = param_full_name[param][1]
            explanation += f"The patient's has {param_full_name[param][0]}. Hence, we add {points} to the total, making the current total {points} + {score} = {points + score}.\n "

        elif not input_parameters[param]:
            points = param_full_name[param][1]
            explanation += f"The patient's has does not have {param_full_name[param][0]}. Hence, 0 points are added to the score, keeping the total at {score}.\n"
    
    return {"Explanation": explanation, "Answer": score}



    
