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
from camel.toolkits.markdown_memory_toolkit import MarkdownMemoryToolkit
from camel.models.model_factory import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.utils import OpenAITokenCounter
from camel.memories.context_creators.score_based import ScoreBasedContextCreator

"""
This example shows how to use the ChatAgent with automatic context compression enabled.
This is particularely useful when memory gets too bloated and irrelevant, causing a decay
in the model's performance.

When the number of messages or tokens in the memory gets too large, the full history of the
model is saved in a `md` file. The agent will then provide a summary of the key information
about the history. It will then clear the memory and continue the conversation with the
summary.
"""

# set up directory for saving markdown memory files
memory_dir = "./agent_memory"

model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O,
)

# make the agent with automatic context compression enabled
agent = ChatAgent(
    system_message="You are a helpful AI assistant providing brief travel advice. Keep responses concise.",
    model=model,
    agent_id="markdown_agent_001",
    ########## Context Compression ##########
    auto_compress_context=True,
    memory_save_directory=memory_dir,
    compress_message_limit=10, # low number for demonstration
    ########## Context Compression ##########
)

# 1. start a conversation about travel planning
user_input_1 = "Hello my name is John. I'm planning a trip to Japan in spring. What are the best cities to visit?"
response_1 = agent.step(user_input_1)
print(f"User: {user_input_1}")
print(f"Assistant: {response_1.msgs[0].content}\n")
'''
===============================================================================
Hello John! In spring, Japan is beautiful, especially with cherry blossoms. Some of the best cities to visit are:
1. **Tokyo**: Experience vibrant city life, parks like Ueno Park for cherry blossoms, and attractions such as the Tokyo Tower.
2. **Kyoto**: Famous for its historical sites and traditional culture. Don't miss the Arashiyama Bamboo Grove and Kinkaku-ji.
3. **Osaka**: Known for amazing food and lively atmosphere. Visit Osaka Castle and Dotonbori.
4. **Hiroshima**: Visit the Peace Memorial Park and nearby Miyajima Island for its iconic floating torii gate.
5. **Nara**: Known for friendly deer in Nara Park and the impressive Todai-ji Temple.
6. **Fukuoka**: Offers beautiful parks and delicious local cuisine. 
Enjoy your trip!
===============================================================================
'''

# 2. continue with more details  
user_input_2 = "How many days should I spend in Tokyo? I'm interested in culture and food."
response_2 = agent.step(user_input_2)
print(f"User: {user_input_2}")
print(f"Assistant: {response_2.msgs[0].content}\n")
'''
===============================================================================
For a focus on culture and food, spending 4 to 5 days in Tokyo is ideal. This allows you to explore cultural landmarks like Senso-ji Temple, Meiji Shrine, and the traditional Asakusa district. You can also delve into the diverse food scene with visits to Tsukiji Outer Market, Shin-Okubo for Korean food, and various izakayas and street-food spots around Shibuya and Shinjuku. Don't forget to explore different neighborhoods to fully experience the city's cultural and culinary diversity.
===============================================================================
'''

# 3. add more complexity
user_input_3 = "What's the best way to travel between cities in Japan?"
response_3 = agent.step(user_input_3)
print(f"User: {user_input_3}")
print(f"Assistant: {response_3.msgs[0].content}\n")
'''
===============================================================================
The best way to travel between cities in Japan is by using the Shinkansen, or bullet train. It is fast, efficient, and offers a comfortable travel experience with frequent departures. Consider getting a Japan Rail Pass if you plan to visit multiple cities, as it can provide significant savings. Alternatively, for shorter distances or more flexibility, consider highway buses or domestic flights if you're covering long distances, such as from Tokyo to Hokkaido or Okinawa.
===============================================================================
'''

# 4. continue adding context
user_input_4 = "Should I book accommodations in advance?"
response_4 = agent.step(user_input_4)
print(f"User: {user_input_4}")
print(f"Assistant: {response_4.msgs[0].content}\n")
'''
===============================================================================
Yes, it's advisable to book accommodations in advance, especially when traveling during peak seasons like spring, when cherry blossoms attract many tourists. Booking ahead ensures you have a wider selection of options and can often secure better rates. Popular destinations like Tokyo, Kyoto, and Osaka can fill up quickly, so early reservations are recommended to avoid inconvenience.
===============================================================================
'''

# 5. this should trigger the automatic context refresh (threshold=5)
user_input_5 = "What are some essential Japanese phrases for travelers?"
response_5 = agent.step(user_input_5)
print(f"User: {user_input_5}")
print(f"Assistant: {response_5.msgs[0].content}\n")
'''
===============================================================================
Here are some essential Japanese phrases for travelers:

1. **Hello** - こんにちは (Konnichiwa)
2. **Thank you** - ありがとう (Arigatou) or ありがとうございます (Arigatou gozaimasu) for extra politeness
3. **Excuse me / I'm sorry** - すみません (Sumimasen)
4. **Yes** - はい (Hai)
5. **No** - いいえ (Iie)
6. **Do you speak English?** - 英語を話せますか？(Eigo o hanasemasu ka?)
7. **How much is this?** - これはいくらですか？(Kore wa ikura desu ka?)
8. **Where is...?** - ...はどこですか？(...wa doko desu ka?)
9. **Toilet** - トイレ (Toire)
10. **Help!** - 助けて！(Tasukete!)

These phrases can help with basic communication and make your interactions smoother.
===============================================================================
'''

'''
Context now gets compressed. The full history so far is saved in agent_memory/session_07_25_1510/history.md and the summary of the chat so far is returned by the agent and also saved in agent_memory/session_07_25_1510/summary.md:

- **User's main goal**: John is planning a trip to Japan in spring and is seeking travel advice focused on cultural experiences and food.
- **Tasks that were accomplished**: 
  - Recommended cities to visit in Japan during spring (Tokyo, Kyoto, Osaka, Hiroshima, Nara, Fukuoka).
  - Suggested spending 4 to 5 days in Tokyo for cultural and culinary exploration.
  - Advised on the best transportation method between cities (Shinkansen and Japan Rail Pass).
  - Recommended booking accommodations in advance.
  - Provided essential Japanese phrases for travelers.
- **Tools and methods that were used**: Personal travel advice given based on cultural attractions and transportation options in Japan.
- **Key information about the user and their preferences**: John is interested in cultural experiences and food during his trip to Japan. He plans to visit in spring and prefers concise, practical travel advice.
- **Important discoveries or solutions found**: Emphasized the importance of early accommodation booking due to high tourist demand in spring.
- **Technical approaches that worked**: Providing a mix of cultural landmarks, transportation advice, and essential phrases helped address the user's travel planning needs effectively.
'''

# Now the memory is emptied, and the summary is pushed to the memory as the new message.

# 6. continue conversation after context refresh
user_input_6 = "What's the weather like in Japan during spring?"
response_6 = agent.step(user_input_6)
print(f"User: {user_input_6}")
print(f"Assistant: {response_6.msgs[0].content}\n")
'''
===============================================================================
Assistant: In spring, Japan generally experiences mild and pleasant weather. March is cooler with temperatures ranging from 5-15°C (41-59°F). April warms up to around 10-20°C (50-68°F), and May is warmer still, averaging 15-25°C (59-77°F). Rain is possible, especially later in the season, so it's wise to pack a light jacket and an umbrella. Cherry blossoms also bloom during this time, making it an attractive season for travel.
===============================================================================
'''

# 7. ask it to summarize the whole conversation
user_input_7 = "What is my name?"
response_7 = agent.step(user_input_7)
print(f"User: {user_input_7}")
print(f"Assistant: {response_7.msgs[0].content}\n")
'''
===============================================================================
Your name is John.
===============================================================================
'''