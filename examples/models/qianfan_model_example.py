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
from camel.configs import QianfanConfig
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

model = ModelFactory.create(
    model_platform=ModelPlatformType.QIANFAN,
    model_type=ModelType.QIANFAN_ERNIE_X1_TURBO_32K,
    model_config_dict=QianfanConfig(temperature=0.2).as_dict(),
)

# Define system message
sys_msg = "You are a helpful assistant."

# Set agent
camel_agent = ChatAgent(system_message=sys_msg, model=model)

user_msg = """how many 'r' in the word 'strawberry?'"""

# Get response information
response = camel_agent.step(user_msg)
print(response.msgs[0].content)
'''
===============================================================================
The word 'strawberry' is spelled **S-T-R-A-W-B-E-R-R-Y**.  

Breaking it down letter by letter:  
1. S  
2. T  
3. **R**  
4. A  
5. W  
6. B  
7. E  
8. **R**  
9. **R**  
10. Y  

There are **3 instances of the letter 'r'** in 'strawberry'.
===============================================================================

'''
