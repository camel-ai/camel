from camel.toolkits.medcalc.rounding import round_number

def weight_conversion_explanation(weight_info):
    """
    将患者的体重从不同单位（磅、克或千克）转换为千克，并生成解释性文本。

    参数:
        weight_info (tuple): 一个包含两个元素的元组：
            - 第一个元素 (float): 患者的体重数值。
            - 第二个元素 (str): 体重的单位，可以是以下之一：
                - "lbs" 表示磅（pounds）。
                - "g" 表示克（grams）。
                - "kg" 表示千克（kilograms）。

    返回值:
        tuple: 包含两个元素：
            - 第一个元素 (str): 解释性文本，说明体重的转换过程和结果。
            - 第二个元素 (float): 转换后的体重值（以千克为单位）。

    注意:
        - 使用 `round_number` 函数对结果进行四舍五入处理。
        - 如果输入的单位不是 "lbs"、"g" 或 "kg"，函数默认返回输入值作为千克。
    """

    weight = weight_info[0]
    weight_label = weight_info[1]

    answer = round_number(weight * 0.453592)

    if weight_label == "lbs":
        return f"The patient's weight is {weight} lbs so this converts to {weight} lbs * 0.453592 kg/lbs = {answer} kg. ", answer
    elif weight_label == "g":
        return f"The patient's weight is {weight} g so this converts to {weight} lbs * kg/1000 g = {round_number(weight/1000)} kg. ", weight/1000
    else:
        return f"The patient's weight is {weight} kg. ", weight
    
    
if __name__ == "__main__":
    # 定义测试案例
    test_cases = [
        (150, "lbs"),  # 磅转千克
        (5000, "g"),   # 克转千克
        (70, "kg"),    # 已经是千克
        (80, "ton")    # 无效单位，默认视为千克
    ]

    # 遍历测试案例并打印结果
    for i, weight_info in enumerate(test_cases, 1):
        print(f"Test Case {i}: Input = {weight_info}")
        explanation, result = weight_conversion_explanation(weight_info)
        print("Explanation:", explanation)
        print("Result (kg):", result)
        print("-" * 50)
