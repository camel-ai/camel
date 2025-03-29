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

usr_msg = """A 16-year-old female adolescent was referred to our hospital with
severe hypertension (systolic pressure 178 mmHg), which was first detected
7 months prior to presentation during a routine annual physical examination.
She complained of intermittent headache for about 1 year, and her previous
blood pressure, measured 1 month prior to her detection of hypertension,
had been normal. She showed mild hypokalemia (3.4 mmol/L) in a routine
blood test, and an additional workup considering secondary hypertension
was planned. Despite taking amlodipine (0.1 mg/kg twice a day),
her blood pressure remained uncontrolled.\nUpon admission to our hospital,
her systolic and diastolic blood pressures were 155 mmHg (>99th percentile)
and 111 mmHg (>99th percentile) respectively. She was 162.8 cm tal
l (50th to 75th percentile) and weighed 55 kg (50th to 75th percentile).
Physical examination including ophthalmological examination revealed
no abnormality other than hypertension, and her family history was
negative for hypertension or renal diseases. Laboratory examination
revealed normal levels of hemoglobin (14.4 g/dL), serum creatinine
(0.57 mg/dL), serum total cholesterol (144 mg/dL), and normal urinalysis.
Serum sodium, potassium, chloride, and total carbon dioxide levels were
134 mmol/L, 3.4 mmol/L, 102 mmol/L, and 27 mmol/L, respectively.
Plasma renin activity was 9.83 ng/mL/hr (normal, 0.5 to 3.3 ng/mL/hr),
and serum aldosterone level was 77.3 ng/dL (normal, 4 to 48 ng/dL).
Urinary levels of vanillylmandelic acid, epinephrine, norepinephrine,
dopamine, metanephrine, and normetanephrine were normal, and plasma
levels of epinephrine, norepinephrine, and dopamine were also normal.
Chest radiography, electrocardiography, and echocardiography showed
normal findings. Renal Doppler ultrasonography revealed an avascular
bilobed cyst in the lower pole of the right kidney (). Abdominal
computed tomography (CT) angiography showed bilaterally normal
renal arteries and an eccentric soft tissue component at the
peripheral aspect of the cystic lesion (). The mass remained
unenhanced during the arterial phase, and its margin was indistinguishable
from the surrounding tissue (). During the delayed phase, its eccentric
capsule showed enhancement, and an intact mass could be observed (),
consistent with CT findings of JGC tumors.\nA right partial nephrectomy
was performed, and a clear resection margin was identified.
The well-encapsulated mass measured 2.5 cm * 2.2 cm * 2.0 cm in
size with a partially cystic-appearing cut surface. Microscopic
examination revealed sheets of polygonal tumor cells with amphophilic
cytoplasm. Immunohistochemical examination showed that the tumor cells
stained positive for CD34 and focally positive for CD117 (C-Kit) and smooth
muscle actin. ()\nPostoperatively, her blood pressure returned to normal
(105/63 mmHg) without using any antihypertensive medication. On the 3rd
postoperative day, the plasma renin activity (0.52 ng/mL/hr), serum
aldosterone (3.9 ng/dL), and serum potassium (3.6 mmol/L) levels
returned to normal. Her blood pressure and laboratory findings
remained within the reference range over the next 3 years postoperatively
until her last follow-up. What is the patient's Creatinine Clearance using
the Cockroft-Gault Equation in terms of mL/min? You should use the patient's
adjusted body weight in kg instead of the patient's actual body weight
if the patient is overweight or obese based on their BMI. If the patient's
BMI's normal, set their adjusted body weight to the minimum of the ideal
body and actual weight. If the patient is underweight, please set their
adjusted body weight to their actual body weight."""

# Get response information
response = camel_agent.step(usr_msg)
print(response.info["tool_calls"])
"""
===============================================================================
[ToolCallingRecord(tool_name='adjusted_body_weight', args={'weight_value': 89,
'weight_unit': 'kg', 'height_value': 163, 'height_unit': 'cm', 'sex': 'Female',
'age': 30}, result='{"rationale": "The patient\'s gender is Female.\\n
The patient\'s height is 163.0 cm,
which is 163.0 cm * 0.393701 in/cm = 64.173 in.
\\nFor females, the ideal body weight (IBW) is calculated as follows:\\n
IBW = 45.5 kg + 2.3 kg * (height (in inches) - 60)\\nPlugging in the values
gives us 45.5 kg + 2.3 kg * (64.173 (in inches) - 60) = 55.098 kg.\\nHence,
the patient\'s IBW is 55.098 kg.The patient\'s weight is 89.0 kg.
To compute the ABW value, apply the following formula:
ABW = IBW + 0.4 * (weight (in kg) - IBW (in kg)). ABW = 55.098 kg
+ 0.4 * (89.0 kg  - 55.098 kg) = 68.659 kg.
The patient\'s adjusted body weight is 68.659 kg.\\n", "final_answer": "68.659"
}', tool_call_id='call_5IJD6Us7RfkVP21zx9G5JGyf')]
===============================================================================
"""
