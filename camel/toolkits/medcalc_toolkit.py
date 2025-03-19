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
import sys
from pathlib import Path
# sys.path.append(str(Path(__file__).parent.parent.parent))

from camel.toolkits.medcalc import weight_conversion
from camel.toolkits.medcalc import ideal_body_weight
from camel.toolkits.medcalc.rounding import round_number

def abw_explanation(input_variables):

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


class MedCalcToolkit(BaseToolkit):
    r"""
    A toolkit for performing medical calculations using various clinical formulas.
    This toolkit provides methods to compute specific medical values such as adjusted body weight (ABW),
    albumin-corrected anion gap, and more. Each method includes a step-by-step explanation of the calculation.

    The toolkit is designed to integrate with agent frameworks and expose its methods as tools that can be used
    by agents to perform medical computations in a structured manner.
    """

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
        
    # def adjusted_body_weight(self, input_variables: Dict[str, Any]) -> str:
    #     r"""
    #     Computes the Adjusted Body Weight (ABW) for a patient based on their weight and ideal body weight (IBW).

    #     The ABW is calculated using the formula:
    #     \[
    #     ABW = IBW + 0.4 \times (\text{actual weight} - IBW)
    #     \]

    #     Args:
    #         input_variables (Dict[str, Any]): A dictionary containing the following keys:
    #             - "weight" (float or str): The patient's actual weight, optionally including units.
    #             - "height" (float or str): The patient's height, optionally including units.
    #             - "gender" (str): The patient's gender, either "male" or "female".
    #             - "age" (int): The patient's age in years.

    #     Returns:
    #         str: A JSON string containing the following fields:
    #             - "rationale" (str): A detailed step-by-step explanation of the calculation.
    #             - "final_answer" (str): The computed ABW value as a string.
    #             If an error occurs, the JSON will include:
    #             - "status" (str): Set to `"error"`.
    #             - "message" (str): A description of the error.
    #     """
    #     from camel.toolkits.medcalc_toolkit.adjusted_body_weight import abw_explanation

    #     try:
    #         result = abw_explanation(input_variables)
    #         return json.dumps(
    #             {"rationale": result['Explanation'], "final_answer": str(result['Answer'])}
    #         )
    #     except Exception as e:
    #         return self.handle_exception("abw_explanation", e)

    def adjusted_body_weight(
        self,
        weight: str,   
        height: str,  
        gender: str,   
        age: int      
    ) -> str:
        r"""
        Computes the Adjusted Body Weight (ABW) for a patient based on their weight and ideal body weight (IBW).

        The ABW is calculated using the formula:
        \[
        ABW = IBW + 0.4 \times (\text{actual weight} - IBW)
        \]

        Args:
            input_variables (Dict[str, Any]): A dictionary containing the following keys:
                - "weight" (List): The patient's actual weight, optionally including units. eg. 'weight': [44.0, 'kg']
                - "height" (List): The patient's height, optionally including units. eg. 'height': [154.2, 'cm']
                - "gender" (str): The patient's gender, either "male" or "female". eg. 'sex': 'Female'
                - "age" (int): The patient's age in years.
        Returns:
            str: A JSON string containing the following fields:
                - "rationale" (str): A detailed step-by-step explanation of the calculation.
                - "final_answer" (str): The computed ABW value as a string.
                If an error occurs, the JSON will include:
                - "status" (str): Set to `"error"`.
                - "message" (str): A description of the error.
        """
        input_variables = {
            "weight": weight,
            "height": height,
            "gender": gender,
            "age": int(age)
        }
        input_variables = {'weight': [44.0, 'kg'], 'height': [154.2, 'cm'], 'sex': 'Female', 'age': 30}
        print(input_variables)
        # from camel.toolkits.medcalc.adjusted_body_weight import abw_explanation
        try:
            result = abw_explanation(input_variables)
            return json.dumps({
                "rationale": result['Explanation'],
                "final_answer": str(result['Answer'])
            })
        except Exception as e:
            return self.handle_exception("abw_explanation", e)

    # def albumin_corrected_anion(self, input_parameters) -> str:
    #     r"""
    #     Computes the Albumin-Corrected Anion Gap for a patient based on their anion gap and albumin levels.

    #     The formula for the albumin-corrected anion gap is:
    #     \[
    #     \text{Corrected Anion Gap} = \text{Anion Gap} + 2.5 \times (4 - \text{Albumin (g/dL)})
    #     \]

    #     Args:
    #         input_parameters (dict): A dictionary containing the following keys:
    #             - "anion_gap" (float or str): The patient's anion gap, optionally including units.
    #             - "albumin" (tuple): A tuple containing the albumin value and its unit (e.g., `(3.5, "g/dL")`).

    #     Returns:
    #         str: A JSON string containing the following fields:
    #             - "rationale" (str): A detailed step-by-step explanation of the calculation.
    #             - "final_answer" (str): The computed albumin-corrected anion gap value as a string.
    #             If an error occurs, the JSON will include:
    #             - "status" (str): Set to `"error"`.
    #             - "message" (str): A description of the error.
    #     """
    #     from camel.toolkits.medcalc.albumin_corrected_anion import compute_albumin_corrected_anion_explanation

    #     try:
    #         result = compute_albumin_corrected_anion_explanation(input_parameters)
    #         return json.dumps(
    #             {"rationale": result["Explanation"], "final_answer": str(result["Answer"])}
    #         )
    #     except Exception as e:
    #         return self.handle_exception("expand_expression", e)

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
        
    def get_tools(self) -> List[FunctionTool]:
        r"""Exposes the tool's methods to the agent framework.

        Returns:
            List[FunctionTool]: A list of `FunctionTool` objects representing
                the toolkit's methods, making them accessible to the agent.
        """
        return [
            FunctionTool(self.adjusted_body_weight),
            # FunctionTool(self.adjusted_body_weight),
            # FunctionTool(self.albumin_corrected_anion),
        ]



# class MedCalcToolkit(BaseToolkit):
    
#     def adjusted_body_weight(
#         self,
#         weight: str,    # 带单位的体重（如 "89 kg"）
#         height: str,    # 带单位的身高（如 "163 cm"）
#         gender: str,    # 性别（"male"/"female"）
#         age: int        # 年龄
#     ) -> str:
#         input_variables = {
#             "weight": weight,
#             "height": height,
#             "gender": gender,
#             "age": age
#         }
#         from medcalc.adjusted_body_weight import abw_explanation
#         try:
#             result = abw_explanation(input_variables)
#             return json.dumps({
#                 "rationale": result['Explanation'],
#                 "final_answer": str(result['Answer'])
#             })
#         except Exception as e:
#             return self.handle_exception("abw_explanation", e)

#     # def get_tools(self) -> List[FunctionTool]:
#     #     return [
#     #         FunctionTool(
#     #             func=self.adjusted_body_weight,
#     #             openai_tool_schema={
#     #                 "type": "function",  # 必须明确指定类型
#     #                 "function": {
#     #                     "name": "adjusted_body_weight",
#     #                     "description": "使用调整体重公式计算校正体重",
#     #                     "parameters": {
#     #                         "type": "object",
#     #                         "properties": {
#     #                             "weight": {
#     #                                 "type": "string",
#     #                                 "description": "带单位的实际体重（如 '89 kg'）"
#     #                             },
#     #                             "height": {
#     #                                 "type": "string",
#     #                                 "description": "带单位的身高（如 '163 cm'）"
#     #                             },
#     #                             "gender": {
#     #                                 "type": "string",
#     #                                 "enum": ["male", "female"]
#     #                             },
#     #                             "age": {
#     #                                 "type": "integer"
#     #                             }
#     #                         },
#     #                         "required": ["weight", "height", "gender", "age"],
#     #                         "additionalProperties": False
#     #                     }
#     #                 }
#     #             }
#     #         ),
#     #         # 其他工具...
#     #     ]
        
#     def get_tools(self) -> List[FunctionTool]:
#         r"""Exposes the tool's methods to the agent framework.

#         Returns:
#             List[FunctionTool]: A list of `FunctionTool` objects representing
#                 the toolkit's methods, making them accessible to the agent.
#         """
#         return [
#             FunctionTool(self.adjusted_body_weight),
#         ]
