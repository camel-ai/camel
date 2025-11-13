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
from camel.configs import DeepSeekConfig
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

"""
please set the below os environment:
export DEEPSEEK_API_KEY=""
"""

model = ModelFactory.create(
    model_platform=ModelPlatformType.DEEPSEEK,
    model_type=ModelType.DEEPSEEK_CHAT,
    model_config_dict=DeepSeekConfig(temperature=0.2).as_dict(),
)

# Define system message
sys_msg = "You are a helpful assistant."

# Set agent
camel_agent = ChatAgent(system_message=sys_msg, model=model)

user_msg = """How many Rs are there in the word 'strawberry'?"""

# Get response information
response = camel_agent.step(user_msg)
print(response.msgs[0].reasoning_content)
print(response.msgs[0].content)

# ruff: noqa: E501
'''
### Step 1: Understanding the Problem

Before jumping into counting, it's essential to understand what's being asked. The question is: **"How many Rs are there in the word 'strawberry'?"** This means I need to look at the word "strawberry" and count how many times the letter 'R' appears in it.

### Step 2: Writing Down the Word

To avoid missing any letters, I'll write down the word clearly:

**S T R A W B E R R Y**

Breaking it down like this helps me visualize each letter individually.

### Step 3: Identifying Each Letter

Now, I'll go through each letter one by one to identify if it's an 'R':

1. **S** - Not an 'R'.
2. **T** - Not an 'R'.
3. **R** - This is an 'R'. (First 'R' found)
4. **A** - Not an 'R'.
5. **W** - Not an 'R'.
6. **B** - Not an 'R'.
7. **E** - Not an 'R'.
8. **R** - This is an 'R'. (Second 'R' found)
9. **R** - This is another 'R'. (Third 'R' found)
10. **Y** - Not an 'R'.

### Step 4: Counting the Rs

From the above identification:

- The first 'R' is the 3rd letter.
- The second 'R' is the 8th letter.
- The third 'R' is the 9th letter.

So, there are **three** instances of the letter 'R' in "strawberry."

### Step 5: Double-Checking

To ensure accuracy, I'll recount:

1. **S** - Not 'R'.
2. **T** - Not 'R'.
3. **R** - 1st 'R'.
4. **A** - Not 'R'.
5. **W** - Not 'R'.
6. **B** - Not 'R'.
7. **E** - Not 'R'.
8. **R** - 2nd 'R'.
9. **R** - 3rd 'R'.
10. **Y** - Not 'R'.

Yes, the count remains consistent at three 'R's.

### Step 6: Considering Pronunciation

Sometimes, pronunciation can be misleading. In "strawberry," the 'R's are pronounced, but that doesn't affect the count. Whether silent or pronounced, each 'R' is still a distinct letter in the spelling.

### Step 7: Final Answer

After carefully analyzing and recounting, I conclude that there are **three** 'R's in the word "strawberry."

---

**Final Answer:** There are **three** 'R's in the word "strawberry."
'''
