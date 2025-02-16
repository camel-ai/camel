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
from camel.configs import QwenConfig
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType


# Define Pydantic models
class Student(BaseModel):
    name: str
    age: str
    email: str


class StudentList(BaseModel):
    studentList: list[Student]


# Define Qwen model
qwen_model = ModelFactory.create(
    model_platform=ModelPlatformType.QWEN,
    model_type=ModelType.QWEN_TURBO,
    model_config_dict=QwenConfig().as_dict(),
)

qwen_agent = ChatAgent(
    model=qwen_model,
)

user_msg = """give me 1 student info."""

# Get response information
response0 = qwen_agent.step(user_msg, response_format=None)
print(response0.msgs[0].content)
"""
===============================================================================
Certainly! Below is an example of a student's information:

**Student Name:** Emily Johnson  
**Date of Birth:** March 12, 2005  
**Grade:** 10th Grade  
**School:** Lincoln High School  
**Address:** 456 Oak Street, Springfield, IL 62704  
**Phone Number:** (555) 123-4567  
**Email:** emily.johnson@student.lincolnhs.edu  
**Emergency Contact:** John Johnson (Father) - (555) 987-6543  

Is there anything specific you need or any changes you'd like to make?
===============================================================================
"""

# Get response information
response1 = qwen_agent.step(user_msg, response_format=Student)
print(response1.msgs[0].content)
"""
===============================================================================
{
  "name": "Emily Johnson",
  "age": "18",
  "email": "emily.johnson@student.lincolnhs.edu"
}
===============================================================================
"""
print(response1.msgs[0].parsed)
"""
===============================================================================
name='Emily Johnson' age='18' email='emily.johnson@student.lincolnhs.edu'
===============================================================================
"""
print(type(response1.msgs[0].parsed))
"""
===============================================================================
<class '__main__.Student'>
===============================================================================
"""

user_msg = """give me a list of student infos."""

# Get response information
response2 = qwen_agent.step(user_msg, response_format=StudentList)
print(response2.msgs[0].content)
"""
===============================================================================
{
  "studentList": [
    {
      "name": "Emily Johnson",
      "age": "18",
      "email": "emily.johnson@student.lincolnhs.edu"
    }
  ]
}
===============================================================================
"""

print(response2.msgs[0].parsed)
"""
===============================================================================
studentList=[Student(name='Emily Johnson', age='18', email='emily.johnson@student.lincolnhs.edu')] 
===============================================================================
"""  # noqa: E501

print(type(response2.msgs[0].parsed))
"""
===============================================================================
<class '__main__.StudentList'>
===============================================================================
"""
