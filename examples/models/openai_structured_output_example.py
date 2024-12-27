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
from pydantic import BaseModel

from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.models import ModelFactory
from camel.toolkits import FunctionTool, MathToolkit, SearchToolkit
from camel.types import ModelPlatformType, ModelType


class Student(BaseModel):
    name: str
    age: str


class StudentList(BaseModel):
    studentList: list[Student]


openai_model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O_MINI,
    model_config_dict=ChatGPTConfig(temperature=0.0).as_dict(),
)

# Set agent
camel_agent = ChatAgent(
    model=openai_model,
    tools=[
        *MathToolkit().get_tools(),
        FunctionTool(SearchToolkit().search_duckduckgo),
    ],
)

# Set user message
user_msg = """give me some student infos, use 2024 minus 1996 as their age
"""

user_msg_2 = """give me some student infos, use 2024 minus 1996 as their age, 
search internet to get the most famous peoples in 2024 as their name"""

# Get response information
response = camel_agent.step(user_msg, response_format=StudentList)
print(response.msgs[0].content)
print(response.msgs[0].parsed)
'''
===============================================================================
{"studentLlst":[{"name":"Alice Johnson","age":"20"},{"name":"Brian Smith",
"age":"22"},{"name":"Catherine Lee","age":"19"},{"name":"David Brown",
"age":"21"},{"name":"Eva White","age":"20"}]}

studentList=[Student(name='Alice Johnson', age='20'), Student(name=
'Brian Smith', age='22'), Student(name='Catherine Lee', age='19'),
Student(name='David Brown', age='21'), Student(name='Eva White', age='23')]
===============================================================================
'''
