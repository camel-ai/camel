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
from camel.configs import PPIOConfig
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

"""
please set the below os environment:
export PPIO_API_KEY=""
"""

# deepseek r1
model_R1 = ModelFactory.create(
    model_platform=ModelPlatformType.PPIO,
    model_type=ModelType.PPIO_DEEPSEEK_R1,
    model_config_dict=PPIOConfig(temperature=0.2).as_dict(),
)

# Define system message
sys_msg = "You are a helpful assistant."

# Set agent
camel_agent = ChatAgent(system_message=sys_msg, model=model_R1)

user_msg = """Say hi to CAMEL AI, one open-source community 
    dedicated to the study of autonomous and communicative agents."""

# Get response information
response = camel_agent.step(user_msg)
print(response.msgs[0].content)

'''
===============================================================================
Hello CAMEL AI! 👋 A warm welcome to the open-source community pushing the 
boundaries of autonomous and communicative agents! Your work in exploring 
multi-agent systems, human-AI collaboration, and self-improving AI 
architectures is incredibly exciting. By fostering transparency and 
collaboration, you're empowering researchers and developers to tackle 
challenges like agent coordination, ethical alignment, and real-world 
deployment—critical steps toward responsible AI advancement.

If anyone's curious, CAMEL AI's projects often dive into simulations where AI 
agents role-play scenarios (like a negotiation between a "seller" and "buyer" 
bot), testing how they communicate, adapt, and solve problems autonomously. 
 This hands-on approach helps uncover insights into emergent behaviors and 
 scalable solutions.

Keep innovating! 🌟 The future of AI is brighter with communities like yours 
driving open, creative research.
===============================================================================
'''

# deepseek prover v2 671b
model_prover = ModelFactory.create(
    model_platform=ModelPlatformType.PPIO,
    model_type=ModelType.PPIO_DEEPSEEK_PROVER_V2_671B,
    model_config_dict=PPIOConfig(temperature=0.2).as_dict(),
)

# Define system message
sys_msg = "You are an exceptionally skilled mathematics professor in teaching."

# Set agent
camel_agent = ChatAgent(system_message=sys_msg, model=model_prover)

user_msg = """Find the sum of all integer bases $ b > 9 $ for which $ 17_b $ is a divisor of $ 97_b $."""

# Get response information
response = camel_agent.step(user_msg)
print(response.msgs[0].content)

# ruff: noqa: E501
'''
===============================================================================
First, we need to understand what the notation $ 17_b $ and $ 97_b $ means. The subscript $ b $ indicates that the number is in base $ b $. 

1. **Convert $ 17_b $ to base 10:**
   \[
   17_b = 1 \cdot b + 7 = b + 7
   \]

2. **Convert $ 97_b $ to base 10:**
   \[
   97_b = 9 \cdot b + 7 = 9b + 7
   \]

The problem states that $ 17_b $ divides $ 97_b $ in base 10, i.e., $ b + 7 $ divides $ 9b + 7 $.

### Step 1: Set up the divisibility condition
We can write the divisibility condition as:
\[
b + 7 \mid 9b + 7
\]

### Step 2: Perform polynomial division or find a relationship
We can express $ 9b + 7 $ in terms of $ b + 7 $:
\[
9b + 7 = 9(b + 7) - 56
\]
This means:
\[
b + 7 \mid 9(b + 7) - 56 \implies b + 7 \mid 56
\]
because $ b + 7 $ divides $ 9(b + 7) $.

### Step 3: Find all divisors of 56
The positive divisors of 56 are:
\[
1, 2, 4, 7, 8, 14, 28, 56
\]

Since $ b > 9 $ and $ b $ is an integer, $ b + 7 > 16 $. The corresponding values of $ b + 7 $ that are divisors of 56 and satisfy $ b + 7 > 16 $ are:
\[
28, 56
\]

### Step 4: Solve for $ b $
1. For $ b + 7 = 28 $:
   \[
   b = 21
   \]
2. For $ b + 7 = 56 $:
   \[
   b = 49
   \]

### Step 5: Verify the solutions
1. For $ b = 21 $:
   - $ 17_{21} = 21 + 7 = 28 $
   - $ 97_{21} = 9 \cdot 21 + 7 = 189 + 7 = 196 $
   - Check if $ 28 \mid 196 $: $ 196 / 28 = 7 $, which is true.
2. For $ b = 49 $:
   - $ 17_{49} = 49 + 7 = 56 $
   - $ 97_{49} = 9 \cdot 49 + 7 = 441 + 7 = 448 $
   - Check if $ 56 \mid 448 $: $ 448 / 56 = 8 $, which is true.

Both values of $ b $ are valid.

### Step 6: Sum the valid bases
The valid bases are $ 21 $ and $ 49 $. Their sum is:
\[
21 + 49 = 70
\]

### Final Answer
\boxed{70}
===============================================================================
'''
