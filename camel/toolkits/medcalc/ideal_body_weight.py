from camel.toolkits.medcalc.height_conversion import height_conversion_explanation_in
from camel.toolkits.medcalc.rounding import round_number

def ibw_explanation(input_variables):
    """
    计算患者的理想体重（Ideal Body Weight, IBW），并生成详细的解释性文本。

    参数:
        input_variables (dict): 一个包含以下键值对的字典：
            - "height" (tuple): 患者的身高信息，格式为 (数值, 单位)。
                - 数值 (float): 身高的具体数值。
                - 单位 (str): 身高的单位，可以是 "cm"（厘米）、"in"（英寸）或其他支持的单位。
            - "sex" (str): 患者的性别，可以是 "Male"（男性）或 "Female"（女性）。

    返回值:
        dict: 包含两个键值对：
            - "Explanation" (str): 详细的计算过程和解释性文本。
            - "Answer" (float): 患者的理想体重量（以千克为单位）。

    注意:
        - 使用 `height_conversion_explanation_in` 函数将身高转换为英寸。
        - 使用 `round_number` 函数对结果进行四舍五入处理。
        - 如果输入的性别不是 "Male" 或 "Female"，函数不会计算 IBW。
    """

    height = input_variables["height"]
    gender = input_variables["sex"]

    explanation = ""

    height_explanation, height = height_conversion_explanation_in(input_variables["height"])

    explanation += f"The patient's gender is {gender}.\n"
    explanation += f"{height_explanation}\n"

    if gender == "Male":
        ibw = round_number(50 + 2.3 * (height - 60))
        explanation += (f"For males, the ideal body weight (IBW) is calculated as follows:\n"
                       f"IBW = 50 kg + 2.3 kg * (height (in inches) - 60)\n"
                       f"Plugging in the values gives us 50 kg + 2.3 kg * ({height} (in inches) - 60) = {ibw} kg.\n")
                   
    elif gender == "Female":
        ibw = round_number(45.5 + 2.3 * (height - 60))
        explanation += (f"For females, the ideal body weight (IBW) is calculated as follows:\n"
                       f"IBW = 45.5 kg + 2.3 kg * (height (in inches) - 60)\n"
                       f"Plugging in the values gives us 45.5 kg + 2.3 kg * ({height} (in inches) - 60) = {ibw} kg.\n")
        
    explanation += f"Hence, the patient's IBW is {ibw} kg."
    
    return {"Explanation": explanation, "Answer": ibw}



if __name__ == "__main__":
    # 定义测试案例
    test_cases = [
        {"height": (170, "cm"), "sex": "Male"},   # 身高 170 厘米，男性
        {"height": (68, "in"), "sex": "Female"},  # 身高 68 英寸，女性
        {"height": (160, "cm"), "sex": "Female"}, # 身高 160 厘米，女性
        {"height": (72, "in"), "sex": "Male"}     # 身高 72 英寸，男性
    ]

    # 遍历测试案例并打印结果
    for i, input_variables in enumerate(test_cases, 1):
        print(f"Test Case {i}: Input = {input_variables}")
        result = ibw_explanation(input_variables)
        print("Explanation:")
        print(result["Explanation"])
        print("Answer (kg):", result["Answer"])
        print("-" * 50)