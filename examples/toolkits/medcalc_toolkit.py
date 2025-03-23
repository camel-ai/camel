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

from camel.agents import ChatAgent
from camel.configs.openai_config import ChatGPTConfig
from camel.models import ModelFactory
from camel.toolkits import MedCalcToolkit
from camel.types import ModelPlatformType, ModelType

import json
import os

os.environ["OPENAI_API_KEY"] = ""

# Define system message
sys_msg = """You are a helpful assistant."""

# Set model config
tools = MedCalcToolkit().get_tools()
print(tools)
model_config_dict = ChatGPTConfig(
    temperature=0.0,
).as_dict()

model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
    model_config_dict=model_config_dict,
)

# Set agent
camel_agent = ChatAgent(
    system_message=sys_msg,
    model=model,
    tools=tools,
)
camel_agent.reset()

# Specify the file path
file_path = './examples/toolkits/medcalc_samples.json'

# Load the JSON file
with open(file_path, 'r') as file:
    data = json.load(file)

# Specify the Calculator in camel/toolkits/medcalc_bench
# OPTION(eg): adjusted_body_weight, anion_gap, bmi_calculator, calcium_correction, homa_ir, mean_arterial_pressure, sOsm
calculator_name = "sOsm"

# Extract the "usr_msg" and "Ground Truth Answer" that match the criteria
target_entry = None 
for entry in data:
    if "File Path" in entry:
        file_name = os.path.basename(entry["File Path"]).split(".")[0]  # Extract the file name (remove path and extension)
        if file_name == calculator_name:
            target_entry = entry
            break
        
usr_msg = target_entry["Usr Msg"]
gt =  target_entry["Ground Truth Answer"]

# Get response information
response = camel_agent.step(usr_msg)
print(response.info['tool_calls'])
print("Ground Truth", gt)

'''
===============================================================================
[ToolCallingRecord(tool_name='adjusted_body_weight', args={'weight_value': 89, 
'weight_unit': 'kg', 'height_value': 163, 'height_unit': 'cm', 'sex': 'Female', 
'age': 30}, result='{"rationale": "The patient\'s gender is Female.\\n
The patient\'s height is 163.0 cm, which is 163.0 cm * 0.393701 in/cm = 64.173 in. 
\\nFor females, the ideal body weight (IBW) is calculated as follows:\\n
IBW = 45.5 kg + 2.3 kg * (height (in inches) - 60)\\nPlugging in the values 
gives us 45.5 kg + 2.3 kg * (64.173 (in inches) - 60) = 55.098 kg.\\nHence, 
the patient\'s IBW is 55.098 kg.The patient\'s weight is 89.0 kg. 
To compute the ABW value, apply the following formula: 
ABW = IBW + 0.4 * (weight (in kg) - IBW (in kg)). ABW = 55.098 kg + 0.4 * (89.0 kg  - 55.098 kg) = 68.659 kg. 
The patient\'s adjusted body weight is 68.659 kg.\\n", "final_answer": "68.659"}', tool_call_id='call_5IJD6Us7RfkVP21zx9G5JGyf')]
===============================================================================
'''
