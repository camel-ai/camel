from rounding import round_number

def rautaharju_calculator_explanation(input_variables):
    heart_rate = input_variables["heart_rate"][0]
    qt_interval = input_variables["qt_interval"][0]

    explanation = "The corrected QT interval using the Rautajarju formula is computed as  QTc = QT interval x (120 + HR) / 180, where QT interval is in msec, and HR is the heart rate in beats per minute.\n"

    explanation += f"The QT interval is {qt_interval} msec.\n"
    explanation += f"The patient's heart rate is {heart_rate} beats per minute.\n"

    qt_c = round_number(qt_interval * (120 + heart_rate) / 180)
    
    explanation += f"Hence, plugging in these values, we will get {qt_interval} x (120 + {heart_rate}) / 180 = {qt_c}.\n"
    explanation += f"The patient's corrected QT interval (QTc) is {qt_c} msec.\n"

    return {"Explanation": explanation, "Answer": qt_c}
