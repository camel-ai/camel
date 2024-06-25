# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========

from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

model = ModelFactory.create(
    model_platform=ModelPlatformType.ZHIPU,
    model_type=ModelType.GLM_4,
    model_config_dict=ChatGPTConfig(temperature=0.2).__dict__,
)

# Define system message
sys_msg = BaseMessage.make_assistant_message(
    role_name="Assistant",
    content="You are a helpful assistant.",
)

# Set agent
camel_agent = ChatAgent(system_message=sys_msg, model=model)

user_msg = BaseMessage.make_user_message(
    role_name="User",
    content="I want to practice my legs today."
    "Help me make a fitness and diet plan",
)

# Get response information
response = camel_agent.step(user_msg)
print(response.msgs[0].content)
'''
===============================================================================
Certainly! Focusing on leg workouts can help improve strength, endurance, and 
overall lower-body fitness. Here's a sample fitness 
and diet plan for leg training:

**Fitness Plan:**

1. **Warm-Up:**
   - 5-10 minutes of light cardio (jogging, cycling, or jumping jacks)
   - Leg swings (forward and backward)
   - Hip circles

2. **Strength Training:**
   - Squats: 3 sets of 8-12 reps
   - Deadlifts: 3 sets of 8-12 reps
   - Lunges: 3 sets of 10-12 reps per leg
   - Leg press: 3 sets of 10-12 reps
   - Calf raises: 3 sets of 15-20 reps

3. **Cardio:**
   - Hill sprints: 5-8 reps of 30-second sprints
   - Cycling or stationary biking: 20-30 minutes at moderate intensity

4. **Cool Down:**
   - Stretching (focus on the legs, hip flexors, and hamstrings)
   - Foam rolling (optional)

**Diet Plan:**

1. **Breakfast:**
   - Greek yogurt with mixed berries and a tablespoon of chia seeds
   - Whole-grain toast with avocado

2. **Snack:**
   - A banana with a tablespoon of natural peanut butter

3. **Lunch:**
   - Grilled chicken breast with quinoa and steamed vegetables
   - A side of mixed greens with a light vinaigrette

4. **Snack:**
   - A serving of mixed nuts and dried fruits

5. **Dinner:**
   - Baked salmon with sweet potato and roasted asparagus
   - A side of lentil soup or a bean salad

6. **Post-Workout Snack:**
   - A protein shake or a serving of cottage cheese with fruit

7. **Hydration:**
   - Drink plenty of water throughout the day to 
   stay hydrated, especially after workouts.

**Tips:**

- Ensure you get enough rest and recovery, as leg workouts 
can be demanding on the body.
- Listen to your body and adjust the weights and reps 
according to your fitness level.
- Make sure to include a variety of nutrients in your diet to 
support muscle recovery and overall health.
- Consult a fitness professional or trainer if you need personalized 
guidance or have any pre-existing health conditions.

Remember, consistency is key to seeing results, so stick to 
your plan and modify it as needed to suit your goals and progress.
===============================================================================
'''
