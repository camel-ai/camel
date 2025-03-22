from datetime import datetime, timedelta


def add_40_weeks_explanation(input_data):

    input_date_str = input_data["menstrual_date"]
    cycle_length = input_data["cycle_length"]
    
    explanation = "The patient's estimated due date based on their last period is computed by using Naegele's Rule. "
    explanation += "Using Naegele's Rule, we add 40 weeks to the patient's last menstrual period date. We then add or subtract days from the patient's estimated due date depending on how many more or less days a patient's cycle length is from the standard 28 days. \n"
    explanation += f"The patient's last menstrual period was {input_date_str}. \n"

    input_date = datetime.strptime(input_date_str, "%m/%d/%Y")
    future_date = input_date + timedelta(weeks=40)

    explanation += f"The date after adding 40 weeks to the patient's last menstrual period date is {future_date.strftime('%m/%d/%Y')}. \n"

    if cycle_length == 28:
        explanation += f"Because the patient's cycle length is 28 days, we do not make any changes to the date. Hence, the patient's estimated due date is {future_date.strftime('%m/%d/%Y')}. \n"
    elif cycle_length < 28:
        cycle_length_gap = abs(cycle_length - 28)
        future_date = future_date + timedelta(days=cycle_length_gap)
        explanation += f"Because the patient's cycle length is {abs(cycle_length)} days, this means that we must subtract {cycle_length_gap} days from the patient's estimate due date. Hence, the patient's estimated due date is {future_date.strftime('%m/%d/%Y')}. \n"
    elif cycle_length > 28:
        cycle_length_gap = abs(cycle_length - 28)
        future_date = future_date + timedelta(days=cycle_length_gap)
        explanation += f"Because the patient's cycle length is {cycle_length} days, this means that we must add {cycle_length_gap} days to the patient's estimate due date. Hence, the patient's estimated due date is {future_date.strftime('%m/%d/%Y')}. \n"

    return {"Explanation": explanation, "Answer": future_date.strftime('%m/%d/%Y')}
