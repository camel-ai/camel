# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========

import json
from typing import List, Optional

from camel.logger import get_logger
from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit
from typing import Dict, Any

logger = get_logger(__name__)


# class MedCalcToolkit(BaseToolkit):
#     r"""
#     A toolkit for performing medical calculations using various clinical formulas.
#     This toolkit provides methods to compute specific medical values such as adjusted body weight (ABW),
#     albumin-corrected anion gap, and more. Each method includes a step-by-step explanation of the calculation.

#     The toolkit is designed to integrate with agent frameworks and expose its methods as tools that can be used
#     by agents to perform medical computations in a structured manner.
#     """

#     def __init__(
#         self,
#         default_variable: str = 'x',
#         timeout: Optional[float] = None,
#     ):
#         r"""
#         Initializes the toolkit with a default variable and optional timeout.

#         Args:
#             default_variable (str): The default variable used in symbolic computations (default: :obj:`x`).
#             timeout (Optional[float]): The maximum time allowed for each computation (in seconds). If `None`,
#                 no timeout is enforced.
#         """
#         super().__init__(timeout=timeout)
#         self.default_variable = default_variable
#         logger.info(f"Default variable set to: {self.default_variable}")
    
#     def adjusted_body_weight(self, input_variables) -> str:
#         print(input_variables)
#         """
#         计算患者的调整体重（Adjusted Body Weight, ABW），并生成详细的解释性文本。

#         参数:
#             input_variables (dict): 一个包含以下键值对的字典：
#                 - "weight" (tuple): 患者的体重信息，格式为 (数值, 单位)。
#                     - 数值 (float): 体重的具体数值。
#                     - 单位 (str): 体重的单位，可以是以下之一：
#                         - "lbs" 表示磅（pounds）。
#                         - "g" 表示克（grams）。
#                         - "kg" 表示千克（kilograms）。
#                 - "height" (tuple): 患者的身高信息，格式为 (数值, 单位)。
#                     - 数值 (float): 身高的具体数值。
#                     - 单位 (str): 身高的单位，可以是以下之一：
#                         - "cm" 表示厘米（centimeters）。
#                         - "in" 表示英寸（inches）。
#                 - "sex" (str): 患者的性别，可以是以下之一：
#                     - "Male" 表示男性。
#                     - "Female" 表示女性。

#         返回值:
#             dict: 包含三个键值对：
#                 - "Explanation" (str): 详细的计算过程和解释性文本，包括 IBW 和 ABW 的计算。
#                 - "ABW" (str): ABW 的具体计算公式和结果。
#                 - "Answer" (float): 患者的调整体重量（以千克为单位）。

#         注意:
#             - 使用 `weight_conversion.weight_conversion_explanation` 函数将体重转换为千克。
#             - 使用 `ideal_body_weight.ibw_explanation` 函数计算理想体重（IBW）。
#             - 使用 `round_number` 函数对结果进行四舍五入处理。
#             - 如果输入的性别不是 "Male" 或 "Female"，函数不会计算 IBW 和 ABW。
#             - 如果输入的单位无效，默认将体重视为千克，身高视为英寸。
#         """
#         from camel.toolkits.medcalc.adjusted_body_weight import abw_explanation
#         try:
#             result = abw_explanation(input_variables)
#             return json.dumps({
#                 "rationale": result['Explanation'],
#                 "final_answer": str(result['Answer'])
#             })
#         except Exception as e:
#             return self.handle_exception("abw_explanation", e)
    
#     def handle_exception(self, func_name: str, error: Exception) -> str:
#         r"""
#         Handles exceptions by logging the error and returning a standardized error message.

#         Args:
#             func_name (str): The name of the function where the exception occurred.
#             error (Exception): The exception object containing details about the error.

#         Returns:
#             str: A JSON string containing the following fields:
#                 - "status" (str): Always set to `"error"`.
#                 - "message" (str): A human-readable description of the error.
#         """
#         logger.error(f"Error in {func_name}: {error}")
#         return json.dumps(
#             {"status": "error", "message": f"Error in {func_name}: {error}"},
#             ensure_ascii=False,
#         )
        
#     def get_tools(self) -> List[FunctionTool]:
#         r"""Exposes the tool's methods to the agent framework.

#         Returns:
#             List[FunctionTool]: A list of `FunctionTool` objects representing
#                 the toolkit's methods, making them accessible to the agent.
#         """
#         return [
#             FunctionTool(self.adjusted_body_weight),
#             # FunctionTool(self.albumin_corrected_anion),
#         ]



class MedCalcToolkit(BaseToolkit):
    def __init__(
        self,
        default_variable: str = 'x',
        timeout: Optional[float] = None,
    ):
        r"""
        Initializes the toolkit with a default variable and optional timeout.

        Args:
            default_variable (str): The default variable used in symbolic computations (default: :obj:`x`).
            timeout (Optional[float]): The maximum time allowed for each computation (in seconds). If `None`,
                no timeout is enforced.
        """
        super().__init__(timeout=timeout)
        self.default_variable = default_variable
        logger.info(f"Default variable set to: {self.default_variable}")
    
    def adjusted_body_weight(
            self,
            weight_value: float,  # Numeric part of the weight (e.g., 89)
            weight_unit: str,     # Unit of the weight (e.g., "kg")
            height_value: float,  # Numeric part of the height (e.g., 163)
            height_unit: str,     # Unit of the height (e.g., "cm")
            sex: str,             # Gender ("male"/"female")
            age: int              # Age
        ) -> str:
        """
        Calculate the patient's Adjusted Body Weight (ABW) and generate a detailed explanatory text.

        Parameters:
            weight_value (float): The numeric value of the patient's weight.
            weight_unit (str): The unit of the patient's weight, one of the following:
                - "lbs" for pounds.
                - "g" for grams.
                - "kg" for kilograms.
            height_value (float): The numeric value of the patient's height.
            height_unit (str): The unit of the patient's height, one of the following:
                - "cm" for centimeters.
                - "in" for inches.
            sex (str): The patient's gender, one of the following:
                - "Male" for male.
                - "Female" for female.
            age (int): The patient's age (integer). Currently unused but may be used for future extensions.

        Returns:
            str: A JSON string containing the calculation process and result, formatted as follows:
                {
                    "rationale": "Detailed calculation process and explanatory text",
                    "final_answer": "Adjusted body weight in kilograms (string format)"
                }
                If an exception occurs, return an error message generated by the `handle_exception` method.

        Notes:
            - The `abw_explanation` function is used to calculate the adjusted body weight.
            - The `json.dumps` function is used to serialize the result into a JSON string.
            - If the input gender is not "male" or "female", the function will not calculate IBW and ABW.
        """
        # Construct the input variables dictionary
        input_variables = {
            "weight": (float(weight_value), str(weight_unit)),  # Weight: (value, unit)
            "height": (float(height_value), str(height_unit)),  # Height: (value, unit)
            "sex": str(sex),                      # Gender
            "age": int(age)                       # Age
        }
        print(input_variables)
        from camel.toolkits.medcalc.adjusted_body_weight import abw_explanation

        try:
            # Call the ABW calculation function
            result = abw_explanation(input_variables)

            # Return the result as a JSON string
            return json.dumps({
                "rationale": result['Explanation'],       # Detailed explanation
                "final_answer": str(result['Answer'])     # Final answer (string format)
            })

        except Exception as e:
            # Catch exceptions and return an error message
            return self.handle_exception("abw_explanation", e)
            
    def handle_exception(self, func_name: str, error: Exception) -> str:
        r"""
        Handles exceptions by logging the error and returning a standardized error message.

        Args:
            func_name (str): The name of the function where the exception occurred.
            error (Exception): The exception object containing details about the error.

        Returns:
            str: A JSON string containing the following fields:
                - "status" (str): Always set to `"error"`.
                - "message" (str): A human-readable description of the error.
        """
        logger.error(f"Error in {func_name}: {error}")
        return json.dumps(
            {"status": "error", "message": f"Error in {func_name}: {error}"},
            ensure_ascii=False,
        )
    
    # def get_tools(self) -> List[FunctionTool]:
    #     return [
    #         FunctionTool(
    #             func=self.adjusted_body_weight,
    #             openai_tool_schema={
    #                 "type": "function",  # 必须明确指定类型
    #                 "function": {
    #                     "name": "adjusted_body_weight",
    #                     "description": "使用调整体重公式计算校正体重",
    #                     "parameters": {
    #                         "type": "object",
    #                         "properties": {
    #                             "weight": {
    #                                 "type": "tuple",
    #                                 "description": "带单位的实际体重（如 '(89, kg)'）"
    #                             },
    #                             "height": {
    #                                 "type": "tuple",
    #                                 "description": "带单位的身高（如 '163, cm'）"
    #                             },
    #                             "gender": {
    #                                 "type": "string",
    #                                 "enum": ["male", "female"]
    #                             },
    #                             "age": {
    #                                 "type": "integer"
    #                             }
    #                         },
    #                         "required": ["weight", "height", "gender", "age"],
    #                         "additionalProperties": False
    #                     }
    #                 }
    #             }
    #         ),
    #         # 其他工具...
    #     ]
        
    def get_tools(self) -> List[FunctionTool]:
        r"""Exposes the tool's methods to the agent framework.

        Returns:
            List[FunctionTool]: A list of `FunctionTool` objects representing
                the toolkit's methods, making them accessible to the agent.
        """
        return [
            FunctionTool(self.adjusted_body_weight),
        ]
