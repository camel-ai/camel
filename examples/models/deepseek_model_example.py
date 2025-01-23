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
    model_type=ModelType.DEEPSEEK_REASONER,
    model_config_dict=DeepSeekConfig(temperature=0.2).as_dict(),
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
The word 'strawberry' is spelled **S-T-R-A-W-B-E-R-R-Y**. Breaking it down:

1. **S**  
2. **T**  
3. **R** (first R)  
4. **A**  
5. **W**  
6. **B**  
7. **E**  
8. **R** (second R)  
9. **R** (third R)  
10. **Y**  

There are **3 Rs** in the word 'strawberry'.
===============================================================================
'''

# If we set the os environment GET_REASONING_CONTENT to "true", we get the reasoning content.

# ruff: noqa: E501
'''
===============================================================================
The word 'strawberry' contains **3 Rs**. Here's the breakdown:

1. **S**  
2. **T**  
3. **R** (1st R)  
4. **A**  
5. **W**  
6. **B**  
7. **E**  
8. **R** (2nd R)  
9. **R** (3rd R)  
10. **Y**  

The Rs appear in the 3rd, 8th, and 9th positions. 🍓

BELOW IS THE REASONING CONTENT:

Okay, let's see. The user is asking how many times the letter 'R' appears in the word 'strawberry'. Hmm, first, I need to make sure I spell the word correctly. Strawberry is S-T-R-A-W-B-E-R-R-Y. Wait, let me break it down letter by letter.

S, T, R, A, W, B, E, R, R, Y. So let's count the Rs. The third letter is R. Then after that, the next letters are A, W, B, E, so the 8th and 9th letters are R and R again. So that's three Rs? Wait, no. Let me check again. S-T-R (1), then later after E, there are two Rs: R and R. So that would be the third letter R and then the two Rs towards the end. Wait, no. Let's list them out step by step:

1. S
2. T
3. R (1st R)
4. A
5. W
6. B
7. E
8. R (2nd R)
9. R (3rd R)
10. Y

Wait, so that's three Rs? But wait, when I spell strawberry, I think it's S-T-R-A-W-B-E-R-R-Y. So after the B, it's E, then R, R, Y. So that's two Rs in a row. So positions 8 and 9. So total Rs would be the one at position 3 and then the two at positions 8 and 9. That makes three Rs. But wait, is that correct? Let me write out the letters with their positions:

1: S
2: T
3: R
4: A
5: W
6: B
7: E
8: R
9: R
10: Y

Yes, that's correct. So there's an R at position 3, and two Rs at positions 8 and 9. So total three Rs. But wait, when I actually think about the spelling of strawberry, I might be making a mistake here. Let me confirm the correct spelling. Strawberry is spelled S-T-R-A-W-B-E-R-R-Y. Yes, that's right. The double R comes after the E. So that's two Rs there. Plus the initial R after T. So total three Rs. But wait, is the first R really there? Let me think. S-T-R-A-W... Yes, the third letter is R. So that's one. Then after the W, B, E, then two Rs. So three total. Hmm, but I might be miscounting. Let me check again. Maybe I added an extra R by mistake. Let's spell it out slowly: S, T, R, A, W, B, E, R, R, Y. That's 10 letters. So the Rs are at positions 3, 8, and 9. So three Rs. But wait, when I say the word out loud, "strawberry," I don't hear three Rs. Maybe I'm overcomplicating. Let me write it down: strawberry. Breaking it down: S T R A W B E R R Y. So R is the third letter, then after B and E, there are two Rs. So total three Rs. But maybe I'm wrong. Let me look it up mentally. The correct spelling of strawberry is S-T-R-A-W-B-E-R-R-Y. Yes, so two Rs at the end before Y. So that's two Rs there. Plus the R in the beginning. So three. But wait, I think I might have confused the spelling with another word. Let me confirm again. Strawberry: S-T-R-A-W-B-E-R-R-Y. So R appears once after T, then again twice after E. So that's three Rs. Wait, but maybe the first R isn't there. Let me check again: S-T-R... yes, that's correct. The word starts with S-T-R, like 'straw', which is S-T-R-A-W. So the third letter is R. Then after that, B-E-R-R-Y. So the Rs are in positions 3, 8, and 9. So three Rs. Hmm, but I'm now doubting because when I think of the pronunciation, "strawberry" has two Rs: the one in 'straw' and the double R in 'berry'. But 'straw' is S-T-R-A-W, so that's one R. Then 'berry' is B-E-R-R-Y, which is two Rs. So total three Rs. But maybe I'm overcomplicating. Alternatively, maybe the correct spelling only has two Rs. Wait, no. The correct spelling of strawberry does have two Rs in the 'berry' part. Let me confirm. Yes, 'berry' is spelled B-E-R-R-Y. So strawberry is S-T-R-A-W-B-E-R-R-Y. Therefore, three Rs: one in 'straw' and two in 'berry'. So the answer should be three. But I want to be absolutely sure. Let me count each letter one by one:

1. S
2. T
3. R (1)
4. A
5. W
6. B
7. E
8. R (2)
9. R (3)
10. Y

Yes, three Rs. So the answer is 3. But wait, I just thought of something. Maybe the user is tricking me. Let me check another way. If I write the word out: strawberry. Let's see: s t r a w b e r r y. So under each letter:

s (1)
t (2)
r (3)
a (4)
w (5)
b (6)
e (7)
r (8)
r (9)
y (10)

Yes, three Rs at positions 3, 8, and 9. So the answer is 3. But wait, sometimes people might misspell it as 'strawbery' with one R. But the correct spelling has two Rs in the 'berry' part. So strawberry has three Rs. Therefore, the answer should be three.
===============================================================================
'''
