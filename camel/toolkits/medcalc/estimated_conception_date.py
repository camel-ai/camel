from datetime import datetime, timedelta

def add_2_weeks_explanation(input_data):

    input_date_str = input_data["menstrual_date"]
    cycle_length = input_data["cycle_length"]
    
    explanation = "The patient's estimated date of conception based on their last period is computed by adding to 2 weeks to the patient's last menstrual period date. "
    explanation += f"The patient's last menstrual period was {input_date_str}. \n"

    input_date = datetime.strptime(input_date_str, "%m/%d/%Y")
    future_date = input_date + timedelta(weeks=2)

    explanation += f"Hence, the estimated date of conception after adding 2 weeks to the patient's last menstrual period date is {future_date.strftime('%m/%d/%Y')}. \n"

    return {"Explanation": explanation, "Answer": future_date.strftime('%m/%d/%Y')}
