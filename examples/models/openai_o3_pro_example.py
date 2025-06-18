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
from camel.configs import ChatGPTConfig
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

# Instantiate the O3_PRO reasoning model
o3_pro_model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.O3_PRO,
    model_config_dict=ChatGPTConfig().as_dict(),
)

# Set up the chat agent with the O3_PRO model
camel_agent = ChatAgent(model=o3_pro_model)

# Example user message (multi-step reasoning/logic problem)
user_msg = (
    "A farmer has a 3-liter jug and a 5-liter jug. Neither jug has any "
    "measurement marks on it. How can the farmer measure exactly 4 liters of "
    "water using just these two jugs and unlimited water supply? "
    "Explain the steps."
)

# Get response from the agent
response = camel_agent.step(user_msg)
print(response.msgs[0].content)

'''
===============================================================================
Sample Output (O3_PRO Reasoning Model):

To measure exactly 4 liters with a 3-liter and a 5-liter jug:

1. Fill the 5-liter jug completely (5 liters).
2. Pour from the 5-liter jug into the 3-liter jug until the 3-liter jug is
   full.
   - Now, 5-liter jug has 2 liters left; 3-liter jug has 3 liters.
3. Empty the 3-liter jug.
   - Now, 5-liter jug has 2 liters; 3-liter jug is empty.
4. Pour the remaining 2 liters from the 5-liter jug into the 3-liter jug.
   - Now, 5-liter jug is empty; 3-liter jug has 2 liters.
5. Fill the 5-liter jug again (5 liters).
6. Pour from the 5-liter jug into the 3-liter jug until the 3-liter jug is
   full.
   - The 3-liter jug already has 2 liters, so you can add only 1 more liter.
   - Now, 5-liter jug has 4 liters left; 3-liter jug is full (3 liters).

**Result:** The 5-liter jug now contains exactly 4 liters of water.
===============================================================================
'''
