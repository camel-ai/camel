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
from camel.configs import SiliconFlowConfig
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

"""
please set the below os environment:
export SILICONFLOW_API_KEY=""
export GET_REASONING_CONTENT="true"
"""

model = ModelFactory.create(
    model_platform=ModelPlatformType.SILICONFLOW,
    model_type=ModelType.SILICONFLOW_DEEPSEEK_R1,
    model_config_dict=SiliconFlowConfig(temperature=0.2).as_dict(),
)

# Define system message
sys_msg = "You are a helpful assistant."

# Set agent
camel_agent = ChatAgent(system_message=sys_msg, model=model)

user_msg = """How many Rs are there in the word 'strawberry'?"""

# Get response information
response = camel_agent.step(user_msg)
print(response.msgs[0].content)

'''
===============================================================================
The word 'strawberry' contains **3 Rs**. Breaking it down:
- **S-T-R** (1st R)
- **B-E-R-R** (2nd and 3rd Rs)

So, the letters R appear at the 3rd, 8th, and 9th positions. 🍓
===============================================================================
'''

# If we set the os environment GET_REASONING_CONTENT to "true", we get the reasoning content.
'''
===============================================================================
Okay, let's see. The user is asking how many times the letter 'R' appears in the word 'strawberry'. Hmm, first I need to make sure I spell the word correctly. Strawberry. Let me break it down letter by letter.

S-T-R-A-W-B-E-R-R-Y. Wait, let me write that out: S, T, R, A, W, B, E, R, R, Y. Let me count the Rs. The third letter is R, then after that, the eighth and ninth letters are R and R again. Wait, no, let me check the spelling again. Maybe I'm splitting the syllables wrong. Straw-berry. So 'straw' is S-T-R-A-W, then 'berry' is B-E-R-R-Y. So in 'straw', there's one R (the third letter), and in 'berry', there are two Rs (the third and fourth letters). So total Rs would be 1 + 2 = 3? Wait, but when I spelled it out earlier, I had S-T-R-A-W-B-E-R-R-Y. Let's count the positions:

1. S
2. T
3. R
4. A
5. W
6. B
7. E
8. R
9. R
10. Y

So positions 3, 8, and 9 are Rs. That's three Rs. But wait, sometimes people might misspell strawberry. Let me confirm the correct spelling. Yes, strawberry is spelled S-T-R-A-W-B-E-R-R-Y. So two Rs in 'berry' part and one in 'straw' part? Wait, no. Wait, 'straw' is S-T-R-A-W, so that's one R. Then 'berry' is B-E-R-R-Y, which is two Rs. So total three Rs. But when I count the letters in the full word, it's S-T-R-A-W-B-E-R-R-Y. Let's list them:

1. S
2. T
3. R
4. A
5. W
6. B
7. E
8. R
9. R
10. Y

Yes, letters 3, 8, and 9 are R. So three Rs. Wait, but I think I might have made a mistake here. Let me check again. Maybe the 'straw' part doesn't have an R? No, 'straw' is S-T-R-A-W. So yes, the third letter is R. Then 'berry' is B-E-R-R-Y. So two Rs there. So total three. But when I look at the word 'strawberry', sometimes people might think it's spelled with one R in the first part. Wait, no, the correct spelling is with R in 'straw' and two Rs in 'berry'. So the answer should be three Rs. Let me confirm with another method. Maybe write the word out and underline each R: s t r a w b e r r y. So R at position 3, then two Rs at positions 8 and 9. So three Rs total. Therefore, the answer is 3.
</think>
The word 'strawberry' contains **3 Rs**. Breaking it down:
- **S-T-R** (1st R)
- **B-E-R-R** (2nd and 3rd Rs)

So, the letters R appear at the 3rd, 8th, and 9th positions. 🍓
===============================================================================
'''
