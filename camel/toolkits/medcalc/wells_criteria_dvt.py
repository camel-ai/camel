def compute_wells_criteria_dvt_explanation(input_parameters):
    # List of parameters and their default values
    parameters = [
        ('active_cancer', "active cancer"),
        ('bedridden_for_atleast_3_days', "bedridden recently >3 days"),
        ('major_surgery_in_last_12_weeks', "major surgery within 12 weeks"), 
        ('calf_swelling_3cm', "calf swelling >3 cm compared to the other leg"),
        ('collateral_superficial_veins', "collateral (nonvaricose) superficial veins present"),
        ('leg_swollen', "entire leg swollen"),
        ('localized_tenderness_on_deep_venuous_system', "localized tenderness along the deep venous system"),
        ('pitting_edema_on_symptomatic_leg', "pitting edema, confined to symptomatic leg"), 
        ('paralysis_paresis_immobilization_in_lower_extreme', "paralysis, paresis, or recent plaster immobilization of the lower extremity"), 
        ('previous_dvt', 'previously documented DVT'),
        ('alternative_to_dvt_diagnosis', "alternative diagnosis to DVT as likely or more likely")
    ]

    output = """
    The criteria for the Wells' Criteria for Deep Vein Thrombosis (DVT) score are listed below:

       1. Active cancer (treatment or palliation within 6 months): No = 0 points, Yes = +1 point
       2. Bedridden recently >3 days or major surgery within 12 weeks: No = 0 points, Yes = +1 point
       3. Calf swelling >3 cm compared to the other leg (measured 10 cm below tibial tuberosity): No = 0 points, Yes = +1 point
       4. Collateral (nonvaricose) superficial veins present: No = 0 points, Yes = +1 point
       5. Entire leg swollen: No = 0 points, Yes = +1 point
       6. Localized tenderness along the deep venous system: No = 0 points, Yes = +1 point
       7. Pitting edema, confined to symptomatic leg: No = 0 points, Yes = +1 point
       8. Paralysis, paresis, or recent plaster immobilization of the lower extremity: No = 0 points, Yes = +1 point
       9. Previously documented DVT: No = 0 points, Yes = +1 point
       10. Alternative diagnosis to DVT as likely or more likely: No = 0 points, Yes = -2 points
    
    The total score is calculated by summing the points for each criterion.\n\n
    """

    # Initializing points and output explanation
    score = 0
    output += "The current Well's DVT Score is 0.\n"

    count = 0 

    while count < len(parameters):

        param_name = parameters[count][0]

        param_value = input_parameters.get(param_name)
        
        # If parameter is missing, assume it as False
        if param_value is None:
            output += f"The issue,'{parameters[count][1]},' is missing from the patient note and so the value is assumed to be absent from the patient. "
            input_parameters[param_name] = False
            param_value = False

        else:
            param_value_name = 'absent' if not param_value else 'present'    
            output += f"From the patient's note, the issue, '{parameters[count][1]},' is {param_value_name}. "
        

        if param_name == 'bedridden_for_atleast_3_days':
            count += 1
            continue
        if param_name == 'major_surgery_in_last_12_weeks':
            if (input_parameters['bedridden_for_atleast_3_days'] or input_parameters['major_surgery_in_last_12_weeks']):
                output += f"Based on the Well's DVT rule, at least one of the issues, 'bedridden recently >3 days' or 'major surgery within 12 weeks' must be true for this criteria to be met for the score to increase by 1. Because this is the case, we incease the score by one making the total {score} + 1 = {score + 1}.\n"
                score += 1
            else:
                output += f"Based on the Well's DVT rule, at least one of the issues, 'bedridden recently >3 days' or 'major surgery within 12 weeks' must be true for this criteria to be met for the score to increase by 1. This is not the case for this patient, and so the score remains unchanged at {score}.\n"
            count += 1
            continue


        # Score calculation
        if param_value:
            if param_name == 'alternative_to_dvt_diagnosis':
                output += f"By the Well's DVT rule, we decrease the score by 2 and so total is {score} - 2 = {score - 2}.\n"
                score -= 2
                count += 1
                continue 
            else:
                output += f"By Well's DVT rule, a point should be given, and so we increment the score by one, making the the total {score} + 1 =  {score + 1}.\n"
                score += 1
        elif param_value is False:
            output += f"By the Well's DVT rule, a point should not be given, and so the score remains unchanged and so total remains at {score}.\n"

        count += 1

    output += f"The Well's DVT score for the patient is {score}.\n"

    return {"Explanation": output, "Answer": score}


