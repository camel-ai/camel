from datetime import datetime

def compute_gestational_age_explanation(input_parameters):

    date2 = input_parameters["current_date"]
    date1 = input_parameters["menstrual_date"]

    explanation = "To compute the estimated gestational age, we compute the number of weeks and days apart today's date is from the patient's last menstrual period date. "
    explanation += f"The current date is {date2} and the patient's last menstrual period date was {date1}. "

    datetime1 = datetime.strptime(date1, "%m/%d/%Y")
    datetime2 = datetime.strptime(date2, "%m/%d/%Y")

    delta = abs(datetime2 - datetime1)

    weeks = delta.days // 7
    days = delta.days % 7

    if weeks == 0:
        explanation += f"The gap between these two dates is {days} days. Hence, the estimated gestational age is {days} days. "
    elif days == 0:
        explanation += f"The gap between these two dates is {weeks} weeks. Hence, the estimated gestational age is {weeks} weeks. "
    else:
        explanation += f"The gap between these two dates is {weeks} weeks and {days} days. Hence, the estimated gestational age is {weeks} weeks and {days} days. "


    return {"Explanation": explanation, "Answer": (f"{weeks} weeks", f"{days} days")}
