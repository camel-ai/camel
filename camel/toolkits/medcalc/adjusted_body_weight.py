# import weight_conversion
# import ideal_body_weight
# from rounding import round_number

from camel.toolkits.medcalc import weight_conversion
from camel.toolkits.medcalc import ideal_body_weight
from camel.toolkits.medcalc.rounding import round_number


def abw_explanation(input_variables):
    """
    计算患者的调整体重（Adjusted Body Weight, ABW），并生成详细的解释性文本。

    参数:
        input_variables (dict): 一个包含以下键值对的字典：
            - "weight" (tuple): 患者的体重信息，格式为 (数值, 单位)。
                - 数值 (float): 体重的具体数值。
                - 单位 (str): 体重的单位，可以是 "lbs"（磅）、"g"（克）、"kg"（千克）。
            - "height" (tuple): 患者的身高信息，格式为 (数值, 单位)。
                - 数值 (float): 身高的具体数值。
                - 单位 (str): 身高的单位，可以是 "cm"（厘米）、"in"（英寸）。
            - "sex" (str): 患者的性别，可以是 "Male"（男性）或 "Female"（女性）。

    返回值:
        dict: 包含三个键值对：
            - "Explanation" (str): 详细的计算过程和解释性文本，包括 IBW 和 ABW 的计算。
            - "ABW" (str): ABW 的具体计算公式和结果。
            - "Answer" (float): 患者的调整体重量（以千克为单位）。

    注意:
        - 使用 `weight_conversion.weight_conversion_explanation` 函数将体重转换为千克。
        - 使用 `ideal_body_weight.ibw_explanation` 函数计算理想体重（IBW）。
        - 使用 `round_number` 函数对结果进行四舍五入处理。
    """

    weight_explanation, weight = weight_conversion.weight_conversion_explanation(input_variables["weight"])
    ibw_explanation =  ideal_body_weight.ibw_explanation(input_variables)

    explanation = f"{ibw_explanation['Explanation']}"
    explanation += f"{weight_explanation}"
   

    ibw = ibw_explanation["Answer"]
        
    abw = round_number(ibw + 0.4 * (weight - ibw))
    abw_explanation_string = ""
    abw_explanation_string += f"To compute the ABW value, apply the following formula: "
    abw_explanation_string += f"ABW = IBW + 0.4 * (weight (in kg) - IBW (in kg)). "
    abw_explanation_string += f"ABW = {ibw} kg + 0.4 * ({weight} kg  - {ibw} kg) = {abw} kg. "
    abw_explanation_string += f"The patient's adjusted body weight is {abw} kg.\n"

    explanation += abw_explanation_string

    return {"Explanation": explanation, "ABW": abw_explanation_string, "Answer": abw}


if __name__ == "__main__":
    # 定义测试案例
    test_cases = [
        {
            "weight": (150, "lbs"),  # 体重 150 磅
            "height": (170, "cm"),  # 身高 170 厘米
            "sex": "Male"           # 性别 男性
        },
        {
            "weight": (68, "kg"),   # 体重 68 千克
            "height": (68, "in"),   # 身高 68 英寸
            "sex": "Female"         # 性别 女性
        },
        {
            "weight": (7000, "g"),  # 体重 7000 克
            "height": (160, "cm"),  # 身高 160 厘米
            "sex": "Female"         # 性别 女性
        }
    ]

    # 遍历测试案例并打印结果
    for i, input_variables in enumerate(test_cases, 1):
        print(f"Test Case {i}: Input = {input_variables}")
        result = abw_explanation(input_variables)
        print("Explanation:")
        print(result["Explanation"])
        print("ABW Calculation:", result["ABW"])
        print("Answer (kg):", result["Answer"])
        print("-" * 50)
