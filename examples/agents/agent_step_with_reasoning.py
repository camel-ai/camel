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
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

sys_msg = "You are a helpful assistant."
usr_msg = """Who is the best basketball player in the world? 
Tell about his career.
"""

openai_model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
)

openai_agent = ChatAgent(
    system_message=sys_msg,
    model=openai_model,
)


# 1st run: the ordinary response

response = openai_agent.step(usr_msg)
print(response.msgs[0].content)
# flake8: noqa: E501
"""
===============================================================================
Determining the "best" basketball player in the world is subjective and often depends on personal preferences, criteria, and the specific time frame being considered. As of the latest NBA season, players like LeBron James, Kevin Durant, Giannis Antetokounmpo, Stephen Curry, and Nikola Jokić are frequently mentioned in discussions about the best players due to their exceptional skills, achievements, and impact on the game. Each of these players brings unique strengths to the court, and opinions on who is the best can vary widely among fans and analysts.
===============================================================================
"""

# 2nd run: the response with thinking (agent choose the best candidate above the threshold)

response_with_think = openai_agent.step(
    usr_msg,
    reason_params=dict(
        choices=3,
        threshold=0.33,
    ),
)
print(response_with_think.msgs[0].content)
# flake8: noqa: E501
"""
===============================================================================
Let's start by identifying three potential candidates for the title of the best basketball player in the world. Here are three top candidates:

1. **LeBron James**: Known for his versatility, basketball IQ, and leadership on and off the court. LeBron has won multiple NBA championships and MVP awards.

2. **Kevin Durant**: Renowned for his scoring ability, shooting accuracy, and clutch performances. Durant has also won multiple NBA championships and MVP awards.

3. **Giannis Antetokounmpo**: Known for his athleticism, defensive prowess, and ability to dominate games. Giannis has won NBA championships and MVP awards as well.

Now, let's assign probabilities/credibilities to each choice:

- LeBron James: 0.4
- Kevin Durant: 0.3
- Giannis Antetokounmpo: 0.3

Since LeBron James has a probability/credibility greater than 0.33, I will continue with him.

### LeBron James' Career Overview

LeBron James, often regarded as one of the greatest basketball players of all time, began his NBA career in 2003 when he was drafted as the first overall pick by the Cleveland Cavaliers. Known for his exceptional athleticism, court vision, and versatility, LeBron quickly made an impact in the league.

Throughout his career, LeBron has played for the Cleveland Cavaliers, Miami Heat, and Los Angeles Lakers. He has won four NBA championships (two with the Miami Heat, one with the Cleveland Cavaliers, and one with the Los Angeles Lakers) and has been named NBA Finals MVP four times. LeBron is also a four-time NBA Most Valuable Player (MVP).

LeBron is known for his ability to play and defend multiple positions, his leadership on and off the court, and his contributions to the game beyond just scoring. He is also recognized for his philanthropic efforts and influence in social justice issues.

LeBron continues to play at a high level, consistently being a key player for his team and a significant figure in the NBA.
===============================================================================
"""

# 3rd run: the response with thinking (agent fails to choose the best candidate above the threshold, let the user decide)

response_with_think_2 = openai_agent.step(
    usr_msg,
    reason_params=dict(
        choices=3,
        threshold=0.5,
    ),
)

print(response_with_think_2.msgs[0].content)
# flake8: noqa: E501
"""
===============================================================================
Question: Who do you think is the best basketball player in the world? Here are the candidates and their probabilities: 
1. LeBron James (0.4): Known for his versatility, leadership, and consistent performance over the years. Multiple NBA championships and MVP awards.
2. Giannis Antetokounmpo (0.3): Known as the "Greek Freak," celebrated for his athleticism, defensive skills, and recent NBA championship win. Multiple MVP awards.
3. Stephen Curry (0.3): Renowned for his exceptional shooting ability, revolutionized the game with his three-point shooting. Multiple NBA championships and MVP awards.
Please choose one to continue with.
Your reply: 3
The user has chosen Stephen Curry as the best basketball player in the world. Let's talk about his career.

Stephen Curry, born on March 14, 1988, is an American professional basketball player for the Golden State Warriors of the National Basketball Association (NBA). Widely regarded as one of the greatest shooters in NBA history, Curry is credited with revolutionizing the game of basketball by inspiring teams to regularly utilize the three-point shot.

### Career Highlights:

1. **Early Life and College:**
   - Stephen Curry is the son of former NBA player Dell Curry. He played college basketball for the Davidson Wildcats, where he gained national attention for leading his team to the NCAA Tournament's Elite Eight in 2008.

2. **NBA Draft and Early Years:**
   - Curry was selected by the Golden State Warriors with the seventh overall pick in the 2009 NBA Draft. He quickly became known for his shooting prowess and playmaking ability.

3. **Rise to Stardom:**
   - Curry's breakout season came in 2014-2015 when he won his first NBA Most Valuable Player (MVP) award and led the Warriors to their first NBA Championship in 40 years.

4. **Record-Breaking Achievements:**
   - He set the record for most three-pointers made in a single season, a record he has broken multiple times. Curry's shooting range and accuracy have made him a central figure in the Warriors' success.

5. **Championships and MVP Awards:**
   - Stephen Curry has won four NBA Championships with the Warriors (2015, 2017, 2018, and 2022). He has been named NBA MVP twice (2015 and 2016), with the 2016 award being the first unanimous MVP in league history.

6. **Impact on the Game:**
   - Curry's influence extends beyond his statistics. He has changed how the game is played, with teams placing a greater emphasis on three-point shooting. His style of play has inspired a new generation of players.

7. **Continued Excellence:**
   - Even as he progresses in his career, Curry continues to perform at an elite level, contributing significantly to his team's success and maintaining his status as one of the top players in the league.

Stephen Curry's combination of skill, leadership, and impact on the game makes him a strong candidate for the best basketball player in the world today.
===============================================================================
"""
