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

gpt_4_5_preview_model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4_5_PREVIEW,
    model_config_dict=ChatGPTConfig().as_dict(),
)

# Set agent
camel_agent = ChatAgent(model=gpt_4_5_preview_model)

# Set user message
user_msg = """Please write inspirational poems 
that make people feel hopeful and enthusiastic about life"""

# Get response information
response = camel_agent.step(user_msg)
print(response.msgs[0].content)
'''
===============================================================================

### Poem 1: Embrace the Dawn

Awaken now, the dawn is near,  
A fresh new day, release your fear.  
Yesterday's shadows fade away,  
Hope blooms bright, embrace today.

Rise with courage, dreams in sight,  
Your heart ablaze, your spirit bright.  
Each step forward, strength you find,  
A brighter future, yours to bind.

Believe in you, your path is clear,  
Trust your journey, hold it dear.  
Life's beauty shines, a guiding star,  
You're stronger now than ever you are.

---

### Poem 2: The Power Within

Within your heart, a spark resides,
A strength that never truly hides.
Through storms and trials, you will rise,
With hope and courage in your eyes.

Your dreams are seeds, plant them deep,
Nurture faith, your promise keep.
Life's journey vast, adventure grand,
Hold tight to hope, take life's hand.

Enthusiasm fuels your way,
Brightens every single day.
Believe, persist, your spirit free,
The power within—your destiny.

---

### Poem 3: A New Beginning

Each sunrise brings a fresh new start,
A chance to heal, renew your heart.
Let go of doubts, embrace the light,
Your future shines, forever bright.

Life's canvas blank, your colors bold,
Paint your dreams, let joy unfold.
Hope whispers softly, "You can soar,"
Open wide life's wondrous door.

Enthusiasm fills your soul,
Guiding you toward your goal.
With hope alive, your spirit strong,
Life's melody—your hopeful song.
===============================================================================
'''
