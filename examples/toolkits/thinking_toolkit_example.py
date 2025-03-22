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
from camel.toolkits import ThinkingToolkit
from camel.types import ModelPlatformType, ModelType

# Create a Model
model_config_dict = ChatGPTConfig(temperature=0.0).as_dict()
model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
    model_config_dict=model_config_dict,
)

# Initialize the ThinkingToolkit
thinking_toolkit = ThinkingToolkit()
tools = thinking_toolkit.get_tools()

# Set up the ChatAgent with thinking capabilities
sys_msg = (
    "You are an assistant that can break down complex problems and think "
    "through solutions step by step. Use the thinking toolkit to organize "
    "your thoughts and approach problems systematically."
)

agent = ChatAgent(
    system_message=sys_msg,
    model=model,
    tools=tools,
)

# Example 1: Complex problem solving
print("\nExample 1: Complex problem solving")
print("=" * 80)

usr_msg = """
Help me solve this problem:
A train travels at 60 mph between two cities that are 300 miles apart. 
If it stops for 30 minutes at each of 3 stations along the way, 
how long will the entire journey take?
"""

response = agent.step(usr_msg)
print(response.msgs[0].content)
print("Tool calls:", response.info['tool_calls'])

"""
===============================================================================
The entire journey will take **6.5 hours**. 

Here's a summary of the calculations:
1. Travel time without stops: \( \frac{300 \text{ miles}}{60 \text{ mph}} = 5 
   \text{ hours} \)
2. Total stopping time: \( 3 \text{ stops} \times 30 \text{ minutes/stop} = 90 
   \text{ minutes} = 1.5 \text{ hours} \)
3. Total journey time: \( 5 \text{ hours} + 1.5 \text{ hours} = 6.5 \text{ 
   hours} \)
Tool calls: [ToolCallingRecord(tool_name='think', args={'thought': 'First, I 
need to calculate the time it takes for the train to travel the 300 miles 
without any stops. The speed of the train is 60 mph.'}, result='Thoughts:\n- 
First, I need to calculate the time it takes for the train to travel the 300 
miles without any stops. The speed of the train is 60 mph.', tool_call_id=
'call_0VV53KPnOUmdomeYKczd9nuz'), ToolCallingRecord(tool_name='think', args={
'thought': 'To find the travel time, I can use the formula: time = distance / 
speed. Here, distance = 300 miles and speed = 60 mph.'}, result='Thoughts:\n- 
First, I need to calculate the time it takes for the train to travel the 300 
miles without any stops. The speed of the train is 60 mph.\n- To find the 
travel time, I can use the formula: time = distance / speed. Here, distance = 
300 miles and speed = 60 mph.', tool_call_id='call_W9aNgb9BV42nfCajQ5jOf54M'),
ToolCallingRecord(tool_name='think', args={'thought': 'Calculating the travel 
time: time = 300 miles / 60 mph = 5 hours.'}, result='Thoughts:\n- First, I 
need to calculate the time it takes for the train to travel the 300 miles 
without any stops. The speed of the train is 60 mph.\n- To find the travel 
time, I can use the formula: time = distance / speed. Here, distance = 300 
miles and speed = 60 mph.\n- Calculating the travel time: time = 300 miles / 60
mph = 5 hours.', tool_call_id='call_D6eWMKiNqQvQMC90G2lnyaqR'), 
ToolCallingRecord(tool_name='think', args={'thought': 'Next, I need to account 
for the stops. The train stops for 30 minutes at each of the 3 stations. 
Therefore, the total stopping time is 3 stops * 30 minutes/stop.'}, result=
'Thoughts:\n- First, I need to calculate the time it takes for the train to 
travel the 300 miles without any stops. The speed of the train is 60 mph.\n- To
find the travel time, I can use the formula: time = distance / speed. Here, 
distance = 300 miles and speed = 60 mph.\n- Calculating the travel time: time =
300 miles / 60 mph = 5 hours.\n- Next, I need to account for the stops. The 
train stops for 30 minutes at each of the 3 stations. Therefore, the total 
stopping time is 3 stops * 30 minutes/stop.', tool_call_id='call_eJRZkM5Fk1d9F7
qLRulivRvH'), ToolCallingRecord(tool_name='think', args={'thought': 
'Calculating the total stopping time: 3 stops * 30 minutes = 90 minutes. Since 
90 minutes is 1.5 hours, I will add this to the travel time.'}, result=
'Thoughts:\n- First, I need to calculate the time it takes for the train to 
travel the 300 miles without any stops. The speed of the train is 60 mph.\n- To
find the travel time, I can use the formula: time = distance / speed. Here, 
distance = 300 miles and speed = 60 mph.\n- Calculating the travel time: time =
300 miles / 60 mph = 5 hours.\n- Next, I need to account for the stops. The 
train stops for 30 minutes at each of the 3 stations. Therefore, the total 
stopping time is 3 stops * 30 minutes/stop.\n- Calculating the total stopping 
time: 3 stops * 30 minutes = 90 minutes. Since 90 minutes is 1.5 hours, I will 
add this to the travel time.', tool_call_id='call_sEcIUy9Hz1IwBEvWJenlPJOU'), 
ToolCallingRecord(tool_name='think', args={'thought': 'Now, I will add the 
travel time and the stopping time: 5 hours + 1.5 hours = 6.5 hours.'}, result=
'Thoughts:\n- First, I need to calculate the time it takes for the train to 
travel the 300 miles without any stops. The speed of the train is 60 mph.\n- To
find the travel time, I can use the formula: time = distance / speed. Here, 
distance = 300 miles and speed = 60 mph.\n- Calculating the travel time: time =
300 miles / 60 mph = 5 hours.\n- Next, I need to account for the stops. The 
train stops for 30 minutes at each of the 3 stations. Therefore, the total 
stopping time is 3 stops * 30 minutes/stop.\n- Calculating the total stopping 
time: 3 stops * 30 minutes = 90 minutes. Since 90 minutes is 1.5 hours, I will 
add this to the travel time.\n- Now, I will add the travel time and the 
stopping time: 5 hours + 1.5 hours = 6.5 hours.', tool_call_id='call_rjDAMoHbW7
tpD5YIactAYeSL'), ToolCallingRecord(tool_name='think', args={'thought': 'The 
entire journey will take 6.5 hours.'}, result='Thoughts:\n- First, I need to 
calculate the time it takes for the train to travel the 300 miles without any 
stops. The speed of the train is 60 mph.\n- To find the travel time, I can use 
the formula: time = distance / speed. Here, distance = 300 miles and speed = 60
mph.\n- Calculating the travel time: time = 300 miles / 60 mph = 5 hours.\n- 
Next, I need to account for the stops. The train stops for 30 minutes at each 
of the 3 stations. Therefore, the total stopping time is 3 stops * 30 minutes/
stop.\n- Calculating the total stopping time: 3 stops * 30 minutes = 90 minutes
Since 90 minutes is 1.5 hours, I will add this to the travel time.\n- Now, I 
will add the travel time and the stopping time: 5 hours + 1.5 hours = 6.5 hours
.\n- The entire journey will take 6.5 hours.', tool_call_id='call_bi58ef9JWVo7p
TbcEJ8yaPLq'), ToolCallingRecord(tool_name='get_thought_history', args={}, 
result='Thought History:\n- First, I need to calculate the time it takes for 
the train to travel the 300 miles without any stops. The speed of the train is
60 mph.\n- To find the travel time, I can use the formula: time = distance / 
speed. Here, distance = 300 miles and speed = 60 mph.\n- Calculating the travel
time: time = 300 miles / 60 mph = 5 hours.\n- Next, I need to account for the 
stops. The train stops for 30 minutes at each of the 3 stations. Therefore, the
total stopping time is 3 stops * 30 minutes/stop.\n- Calculating the total 
stopping time: 3 stops * 30 minutes = 90 minutes. Since 90 minutes is 1.5 hours
, I will add this to the travel time.\n- Now, I will add the travel time and 
the stopping time: 5 hours + 1.5 hours = 6.5 hours.\n- The entire journey will 
take 6.5 hours.', tool_call_id='call_TIUEw9Eph
mQY8eGg53e1HlVP')]
===============================================================================
"""

# Example 2: Decision making analysis
print("\nExample 2: Decision making analysis")
print("=" * 80)

usr_msg = """
Help me decide whether to buy a hybrid or electric car, considering:
- Daily commute: 30 miles
- Budget: $35,000
- Living in an apartment without home charging
"""

response = agent.step(usr_msg)
print(response.msgs[0].content)
print("Tool calls:", response.info['tool_calls'])

"""
===============================================================================
Here's a breakdown of the considerations for deciding between a hybrid and an 
electric car based on your situation:

1. **Daily Commute**: 
- Your daily commute is 30 miles, which is manageable for both hybrid and 
    electric cars. Most electric cars have a range of 100-300 miles on a full 
    charge, so they can easily handle your daily needs.

2. **Home Charging**:
- Living in an apartment without home charging is a significant factor. 
    Electric cars are most convenient when you can charge them at home. Without
    this, you would need to rely on public charging stations, which may not 
    always be available or convenient.

3. **Public Charging Availability**:
- Check the availability of public charging stations near your apartment and 
    along your commute. If there are sufficient charging options, an electric 
    car could still be feasible. However, if charging stations are scarce, it 
    may be more challenging to own an electric vehicle.

4. **Cost Considerations**:
- **Hybrid Cars**: Generally have lower upfront costs and can be refueled at 
  gas stations, making them convenient without home charging. They offer 
  better fuel efficiency than gas cars.
- **Electric Cars**: Higher upfront costs but lower operating costs and tax 
  incentives. Public charging fees can add up without home charging access.

5. **Budget**:
- $35,000 budget allows for both hybrid and electric options. Research 
  specific models to find best fit.

### Conclusion:
- If convenience and charging access are priorities, a **hybrid car** may be 
  better.
- If public charging is available and long-term savings matter, an **electric 
  car** works but needs more charging planning.

The final choice depends on charging availability and your convenience/cost 
priorities.
Tool calls: [ToolCallingRecord(tool_name='think', args={'thought': 'First, I 
need to consider the daily commute of 30 miles. I should evaluate if a hybrid 
or electric car can accommodate this distance without needing frequent 
charging.'}, result='Thoughts:\n- First, I need to calculate the time it takes 
for the train to travel the 300 miles without any stops. The speed of the 
train is 60 mph.\n- To find the travel time, I can use the formula: time = 
distance / speed. Here, distance = 300 miles and speed = 60 mph.\n- 
Calculating the travel time: time = 300 miles / 60 mph = 5 hours.\n- Next, I 
need to account for the stops. The train stops for 30 minutes at each of the 3 
stations. Therefore, the total stopping time is 3 stops * 30 minutes/stop.\n- 
Calculating the total stopping time: 3 stops * 30 minutes = 90 minutes. Since 
90 minutes is 1.5 hours, I will add this to the travel time.\n- Now, I will 
add the travel time and the stopping time: 5 hours + 1.5 hours = 6.5 hours.\n- 
The entire journey will take 6.5 hours.\n- First, I need to consider the daily 
commute of 30 miles. I should evaluate if a hybrid or electric car can 
accommodate this distance without needing frequent charging.', tool_call_id=
'call_th5SPiU99yrdSnoS0WPXsjH8'), ToolCallingRecord(tool_name='think', args=
{'thought': 'For electric cars, I need to check the range. Many electric cars 
have a range of 100-300 miles on a full charge. A 30-mile daily commute is 
manageable for most electric cars.'}, result='Thoughts:\n- First, I need to 
calculate the time it takes for the train to travel the 300 miles without any 
stops. The speed of the train is 60 mph.\n- To find the travel time, I can use 
the formula: time = distance / speed. Here, distance = 300 miles and speed = 
60 mph.\n- Calculating the travel time: time = 300 miles / 60 mph = 5 hours.
\n- Next, I need to account for the stops. The train stops for 30 minutes 
at each of the 3 stations. Therefore, the total stopping time is 3 
stops * 30 minutes/stop.\n- Calculating the total stopping time: 
3 stops * 30 minutes = 90 minutes. Since 90 minutes is 1.5 hours, I will 
add this to the travel time.\n- Now, I will add the travel time and 
the stopping time: 5 hours + 1.5 hours = 6.5 hours.\n- The entire 
journey will take 6.5 hours.\n- First, I need to consider the daily commute 
of 30 miles. I should evaluate if a hybrid or electric car can accommodate 
this distance without needing frequent charging.\n- For electric cars, I 
need to check the range. Many electric cars have a range of 100-300 miles 
on a full charge. A 30-mile daily commute is manageable for 
most electric cars.', tool_call_id='call_soKX6KKHp0FHAft4swzPCEer'), 
ToolCallingRecord(tool_name='think', args={'thought': 'Next, I need to 
consider the lack of home charging. This could be a significant factor for an 
electric car, as charging at home is often more convenient and cost-
effective.'}, result='Thoughts:\n- First, I need to calculate the time it  
for the train to travel the 300 miles without any stops. The speed of the 
train is 60 mph.\n- To find the travel time, I can use the formula: time = 
distance / speed. Here, distance = 300 miles and speed = 60 mph.\n- 
Calculating the travel time: time = 300 miles / 60 mph = 5 hours.\n- Next, I 
need to account for the stops. The train stops for 30 minutes at each of the 3 
stations. Therefore, the total stopping time is 3 stops * 30 minutes/stop.\n- 
Calculating the total stopping time: 3 stops * 30 minutes = 90 minutes. Since 
90 minutes is 1.5 hours, I will add this to the travel time.\n- Now, I will 
add the travel time and the stopping time: 5 hours + 1.5 hours = 6.5 hours.\n- 
The entire journey will take 6.5 hours.\n- First, I need to consider the daily 
commute of 30 miles. I should evaluate if a hybrid or electric car can 
accommodate this distance without needing frequent charging.\n- For electric 
cars, I need to check the range. Many electric cars have a range of 100-300 
miles on a full charge. A 30-mile daily commute is manageable for most 
electric cars.\n- Next, I need to consider the lack of home charging. This 
could be a significant factor for an electric car, as charging at home is  
more convenient and cost-effective.', tool_call_id=
'call_good1QDuvMmb4pVL0SyLVwn4'), ToolCallingRecord(tool_name='think', args=
{'thought': 'I should also consider the availability of public charging 
stations. If there are enough charging stations near the apartment or along  
commute, it may make owning an electric car feasible.'}, result='Thoughts:\n- 
First, I need to calculate the time it takes for the train to travel the 300 
miles without any stops. The speed of the train is 60 mph.\n- To find the 
travel time, I can use the formula: time = distance / speed. Here, distance = 
300 miles and speed = 60 mph.\n- Calculating the travel time: time = 300 miles 
/ 60 mph = 5 hours.\n- Next, I need to account for the stops. The train stops 
for 30 minutes at each of the 3 stations. Therefore, the total stopping time  
3 stops * 30 minutes/stop.\n- Calculating the total stopping time: 3 stops*30 
minutes = 90 minutes. Since 90 minutes is 1.5 hours, I will add this to the 
travel time.\n- Now, I will add the travel time and the stopping time: 5 hours 
+ 1.5 hours = 6.5 hours.\n- The entire journey will take 6.5 hours.\n- First, 
I need to consider the daily commute of 30 miles. I should evaluate if hybrid 
or electric car can accommodate this distance without needing frequent 
charging.\n- For electric cars, I need to check the range. Many electric cars 
have a range of 100-300 miles on a full charge. A 30-mile daily commute is 
manageable for most electric cars.\n- Next, I need to consider the lack of 
home charging. This could be a significant factor for an electric car, as 
charging at home is often more convenient and cost-effective.\n- I should also 
consider the availability of public charging stations. If there are enough 
charging stations near the apartment or along the commute, it may make owning 
an electric car feasible.', tool_call_id='call_bsYgiDs9ptfjoZY3l1235v6N'), 
ToolCallingRecord(tool_name='think', args={'thought': 'Finally, I need to 
compare the costs of ownership for both options. Hybrids generally have lower 
upfront costs and can be refueled at gas stations, while electric cars may 
have lower operating costs but could incur higher charging costs if public 
charging is used frequently.'}, result='Thoughts:\n- First, I need to 
calculate the time it takes for the train to travel the 300 miles without any 
stops. The speed of the train is 60 mph.\n- To find the travel time, I can use 
the formula: time = distance / speed. Here, distance = 300 miles and speed=60 
mph.\n- Calculating the travel time: time = 300 miles / 60 mph = 5 hours.\n- 
Next, I need to account for the stops. The train stops for 30 minutes at each 
of the 3 stations. Therefore, the total stopping time is 3 stops * 30 
minutes/stop.\n- Calculating the total stopping time: 3 stops * 30 minutes=90 
minutes. Since 90 minutes is 1.5 hours, I will add this to the travel time.\n- 
Now, I will add the travel time and the stopping time: 5 hours + 1.5 hours = 
6.5 hours.\n- The entire journey will take 6.5 hours.\n- First, I need to 
consider the daily commute of 30 miles. I should evaluate if a hybrid or 
electric car can accommodate this distance without needing frequent charge.\n- 
For electric cars, I need to check the range. Many electric cars have a range 
of 100-300 miles on a full charge. A 30-mile daily commute is manageable for 
most electric cars.\n- Next, I need to consider the lack of home charging.This 
could be a significant factor for electric car, as charging at home is often 
more convenient and cost-effective.\n- I should also consider the availability 
of public charging stations. If there are enough charging stations near the 
apartment or along the commute, it may make owning electric car feasible.\n- 
Finally, I need to compare the costs of ownership for both options. Hybrids 
generally have lower upfront costs and can be refueled at gas stations, while 
electric cars may have lower operating costs but could incur higher charging 
costs if public charging is used frequently.', tool_call_id=
'call_OFrapo3h30EQ0HhJnMQ3TssR')]
===============================================================================
"""
