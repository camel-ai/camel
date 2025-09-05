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
from camel.models.model_factory import ModelFactory
from camel.toolkits.context_summarizer_toolkit import ContextSummarizerToolkit
from camel.types import ModelPlatformType, ModelType

"""
This example demonstrates the ContextSummarizerToolkit, which provides
intelligent context summarization and memory management capabilities for
ChatAgent. The toolkit enables agents to:
1. Manually save conversation memory when context becomes cluttered
2. Load previous context summaries 
3. Search through conversation history using text search
4. Get information about current memory state
5. Check if context should be compressed based on message/token limits

The toolkit is particularly useful when you want the agent to have control over
when to save/refresh memory, rather than relying on automatic thresholds.
"""

# Set up directory for saving context files
memory_dir = "./agent_context_toolkit"

model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
)

# Create agent without auto-compression - we'll use the toolkit for manual
# control
agent = ChatAgent(
    system_message="""You are a helpful AI assistant providing travel """
    """advice.""",
    model=model,
    agent_id="context_toolkit_agent_001",
)

# Initialize the context summarizer toolkit
context_toolkit = ContextSummarizerToolkit(
    agent=agent,
    working_directory=memory_dir,
)

# Add toolkit to agent
agent.add_tools(context_toolkit.get_tools())

print("=== ContextSummarizerToolkit Example ===\n")

# 1. Start conversation about travel planning
user_input_1 = (
    "Hello my name is John. I'm planning a trip to Japan in "
    "spring. What are the best cities to visit?"
)
response_1 = agent.step(user_input_1)
print(f"User: {user_input_1}")
print(f"Assistant: {response_1.msgs[0].content}\n")

'''
===============================================================================
Assistant: In spring, Japan is especially beautiful with cherry blossoms in 
full bloom. Here are some of the best cities to visit:

1. **Tokyo**: The bustling capital offers a mix of modern life and 
traditional culture. Don't miss Ueno Park and Shinjuku Gyoen for 
cherry blossom viewing.

2. **Kyoto**: Known for its classical Buddhist temples, beautiful gardens, 
and traditional wooden houses. The Philosopher's Path is lined with 
hundreds of cherry trees.

3. **Osaka**: A lively city known for modern architecture, vibrant 
nightlife, and delicious street food. Osaka Castle is a great spot 
for hanami.

4. **Nara**: Home to free-roaming deer and the impressive Todaiji Temple. 
Nara Park is another great place for cherry blossoms.

5. **Hiroshima**: Visit the Peace Memorial Park and Museum. Nearby 
Miyajima Island is famous for its floating torii gate and beautiful 
cherry blossoms.

6. **Sapporo**: Sapporo in Hokkaido is known for its late-blooming 
cherry blossoms, and offers a different perspective from mainland Japan.

7. **Kanazawa**: Known for its well-preserved Edo-era districts, art 
museums, and beautiful gardens like Kenrokuen.

8. **Fukuoka**: Offers a mix of modern city life and historical sites. 
Fukuoka Castle ruins are surrounded by cherry blossoms in Maizuru Park.

These cities provide a mix of modern attractions and historical sites, all 
enhanced by the seasonal beauty of cherry blossoms. Let me know if you need 
more details on any specific city or travel tips!
===============================================================================
'''

# 2. Continue with more details
user_input_2 = (
    "How many days should I spend in Tokyo? I'm interested in "
    "culture and food."
)
response_2 = agent.step(user_input_2)
print(f"User: {user_input_2}")
print(f"Assistant: {response_2.msgs[0].content}\n")

'''
===============================================================================
Assistant: To fully experience Tokyo's rich culture and diverse food scene, 
I recommend spending at least 4 to 5 days in the city. Here's a suggested 
breakdown to make the most of your stay:

**Day 1: Explore Traditional Tokyo**
- Visit Asakusa for Senso-ji Temple and traditional shopping streets.
- Explore the historic Tokyo Imperial Palace and its surrounding gardens.
- Enjoy dinner at a traditional izakaya (Japanese pub) in the area.

**Day 2: Discover Modern Tokyo**
- Spend time in Shibuya and Shinjuku to see the bustling city life.
- Explore Harajuku's trendy fashion and unique cafes.
- Visit the observation deck at Tokyo Metropolitan Government Building 
  for a panoramic city view.
- Enjoy modern Japanese cuisine or sushi at a renowned Tokyo restaurant.

**Day 3: Dive into Tokyo's Art and History**
- Visit Ueno Park and museums like the Tokyo National Museum and Ueno Zoo.
- Explore Akihabara for electronics, anime, and manga culture.
- Taste local dishes like monjayaki or okonomiyaki.

**Day 4: Experience Tokyo's Culinary Scene**
- Join a food tour to explore Tsukiji Outer Market for fresh seafood.
- Wander through different neighborhoods to try ramen, tempura, and 
  more street food.
- Visit Ginza for upscale shopping and dining.

**Day 5 (Optional): Day Trip or Special Interest**
- Consider a day trip to nearby Nikko or Kamakura for historical exploration.
- Enjoy a themed cafe experience or attend a cultural workshop 
  (e.g., tea ceremony).

This itinerary gives you a balanced mix of cultural, historical, and 
culinary experiences, highlighting the dynamic and diverse facets of Tokyo.
===============================================================================
'''

# 3. Add more complexity
user_input_3 = "What's the best way to travel between cities in Japan?"
response_3 = agent.step(user_input_3)
print(f"User: {user_input_3}")
print(f"Assistant: {response_3.msgs[0].content}\n")

'''
===============================================================================
Assistant: The best way to travel between cities in Japan is by using the 
country's efficient and reliable train system. Here are some of the most 
popular options:

1. **Shinkansen (Bullet Train)**: 
   - The Shinkansen is the fastest and most convenient way to travel 
     between major cities such as Tokyo, Kyoto, Osaka, Hiroshima, and more.
   - It's known for its punctuality and comfort. You can reserve seats in 
     advance for longer journeys, which is often recommended during busy 
     travel seasons.
   - Consider purchasing a Japan Rail Pass (JR Pass) if you plan to travel 
     extensively by train. It offers unlimited rides on most Shinkansen lines 
     and JR trains for a set period (7, 14, or 21 days), which can be very 
     cost-effective.

2. **Limited Express Trains**:
   - For routes not covered by the Shinkansen, Limited Express trains run 
     frequently and are also comfortable.
   - These are ideal for shorter distances or routes within certain regions.

3. **Local Trains**:
   - Local trains are available for shorter distances and are often more 
     economical, but they might take longer.

4. **Domestic Flights**:
   - For distant cities, like traveling from Tokyo to Sapporo or Okinawa, 
     domestic flights might be more convenient.
   - Low-cost carriers and domestic airlines offer frequent flights between 
     major airports.

5. **Bus Services**: 
   - Highway buses are a cost-effective alternative to trains for 
     long-distance travel. They might take longer but are suitable for 
     overnight travel.

6. **Car Rental**:
   - Renting a car is an option if you want to explore more rural or remote 
     areas. However, navigating cities like Tokyo can be challenging due to 
     traffic and parking limitations.

Each mode of transportation has its benefits depending on your itinerary, 
budget, and preferences. Using a mix of these options can help optimize your 
travel experience in Japan.
===============================================================================
'''

# 4. Continue building context
user_input_4 = "Should I book accommodations in advance?"
response_4 = agent.step(user_input_4)
print(f"User: {user_input_4}")
print(f"Assistant: {response_4.msgs[0].content}\n")

'''
===============================================================================
Assistant: Yes, it is generally advisable to book accommodations in advance, 
especially when traveling to popular destinations like Tokyo, Kyoto, and 
Osaka during peak tourist seasons. Here are some reasons why booking ahead 
is a good idea:

1. **Availability**: Popular hotels and unique accommodations (like ryokans, 
traditional Japanese inns) can fill up quickly, especially during cherry 
blossom season in spring or autumn for the fall foliage.

2. **Cost**: Booking early often allows you to take advantage of early bird 
rates and promotions. Prices can increase significantly as your travel dates 
approach, particularly in popular areas.

3. **Choice**: You'll have a wider selection of accommodations to choose 
from, ensuring that you can find a place that fits your preferences for 
comfort, location, and amenities.

4. **Peace of Mind**: Having your accommodations sorted in advance adds 
convenience and reduces stress, allowing you to focus on planning other 
aspects of your trip.

5. **Flexibility**: Many hotels and booking platforms offer flexible 
cancellation policies, so you can often make changes if needed.

To ensure a smooth and enjoyable experience, consider researching and 
booking your accommodations a few months in advance, especially if you have 
specific places or experiences you'd like to include in your itinerary.
===============================================================================
'''

# 5. Add more topics - this will make context more complex
user_input_5 = "What are some essential Japanese phrases for travelers?"
response_5 = agent.step(user_input_5)
print(f"User: {user_input_5}")
print(f"Assistant: {response_5.msgs[0].content}\n")

'''
===============================================================================
Assistant: Learning a few essential Japanese phrases can greatly enhance your 
travel experience in Japan, as it shows respect for the local culture and 
can help in communication. Here are some helpful phrases:

1. **Basic Greetings:**
   - Hello: こんにちは (Konnichiwa)
   - Good morning: おはようございます (Ohayou gozaimasu)
   - Good evening: こんばんは (Konbanwa)
   - Goodbye: さようなら (Sayonara)

2. **Polite Expressions:**
   - Thank you: ありがとう (Arigatou) / 
     ありがとうございます (Arigatou gozaimasu)
   - Please: お願いします (Onegaishimasu)
   - Excuse me / I'm sorry: すみません (Sumimasen)

3. **Common Questions:**
   - Do you speak English?: 英語を話せますか?(Eigo o hanasemasu ka?)
   - How much is this?: これはいくらですか?(Kore wa ikura desu ka?)
   - Where is the bathroom?: トイレはどこですか?(Toire wa doko desu ka?)
   - Can you help me?: 手伝ってくれますか?(Tetsudatte kuremasu ka?)

4. **Dining:**
   - I would like this: これをお願いします (Kore o onegaishimasu)
   - Delicious: おいしい (Oishii)
   - Check, please: お会計をお願いします (O-kaikei o onegaishimasu)

5. **Travel:**
   - Where is the train station?: 駅はどこですか?(Eki wa doko desu ka?)
   - I need a taxi: タクシーをお願いします (Takushii o onegaishimasu)
   - A ticket to [destination], please: [目的地]行きのチケットを
     お願いします ([Mokutekichi] yuki no chiketto o onegaishimasu)

6. **Emergency:**
   - Help!: 助けて!(Tasukete!)
   - Call a doctor: 医者を呼んでください (Isha o yonde kudasai)

These phrases cover a variety of situations you might encounter during your 
trip. It's also helpful to have a translation app or phrasebook on hand for 
more complex conversations.
===============================================================================
'''

print("=== Asking agent to check memory status ===")
# 6. Ask agent to check memory status
user_input_6 = "Can you check our current memory status using your tools?"
response_6 = agent.step(user_input_6)
print(f"User: {user_input_6}")
print(f"Assistant: {response_6.msgs[0].content}\n")

'''
===============================================================================
Assistant: Our current memory status has 12 messages in memory, and there are 
no summary or history files saved yet. We can store summaries or history of 
our conversations, and you can also perform text searches within these 
sessions if needed. If you have any specific requirements or need a summary, 
feel free to let me know!
===============================================================================
'''

print("=== Suggesting agent save memory ===")
# 7. Suggest agent save memory as conversation is getting complex
user_input_7 = (
    "We've covered a lot of ground on Japan travel. Maybe you "
    "should save our conversation memory to keep things "
    "organized?"
)
response_7 = agent.step(user_input_7)
print(f"User: {user_input_7}")
print(f"Assistant: {response_7.msgs[0].content}\n")

'''
===============================================================================
Assistant: I've cleared some of the previous conversation for a fresh start. 
How can I assist you with your travel plans today?
===============================================================================
'''

print("=== Starting new topic after memory save ===")
# 8. Start a new topic to test context refresh
user_input_8 = (
    "Now I want to ask about something completely different - can "
    "you help me plan a workout routine?"
)
response_8 = agent.step(user_input_8)
print(f"User: {user_input_8}")
print(f"Assistant: {response_8.msgs[0].content}\n")

'''
===============================================================================
Assistant: Sure, I can help you plan a workout routine! Could you tell me a 
bit about your fitness goals and any preferences or limitations you have?
===============================================================================
'''

print("=== Testing memory recall ===")
# 9. Test if agent can recall previous context when needed
user_input_9 = (
    "Wait, let me go back to my Japan trip. What was my name "
    "again, and what did we discuss about Tokyo?"
)
response_9 = agent.step(user_input_9)
print(f"User: {user_input_9}")
print(f"Assistant: {response_9.msgs[0].content}\n")

'''
===============================================================================
Assistant: Your name is John, and we discussed your trip to Japan. 
Specifically about Tokyo, we talked about its modern attractions and 
traditional sites, like visiting Shinjuku Gyoen Park for cherry blossoms, 
and exploring areas such as Shibuya and Akihabara. Is there anything more 
you'd like to know or plan regarding your visit to Tokyo?
===============================================================================
'''

print("=== Testing text search ===")
# 10. Test text search functionality
user_input_10 = (
    "Can you search our conversation history for information "
    "about transportation in Japan?"
)
response_10 = agent.step(user_input_10)
print(f"User: {user_input_10}")
print(f"Assistant: {response_10.msgs[0].content}\n")

'''
===============================================================================
Assistant: We discussed various transportation options in Japan, particularly 
focusing on the train system. Here are some key points:

1. **Shinkansen (Bullet Train)**: The fastest and most convenient way to 
travel between major cities like Tokyo, Kyoto, and Osaka. It's punctual and 
comfortable. If you plan to use trains extensively, a Japan Rail Pass is 
recommended.

2. **Limited Express Trains**: These are suitable for routes not covered by 
the Shinkansen and are ideal for shorter distances within certain regions.

3. **Local Trains**: More economical but slower, ideal for shorter distances.

4. **Domestic Flights**: Useful for traveling to distant cities like 
Sapporo or Okinawa.

5. **Bus Services**: A cost-effective alternative to trains, suitable for 
long-distance travel including overnight trips.

6. **Car Rental**: An option if exploring rural areas, but navigating cities 
like Tokyo might be challenging.

Each transportation mode has its benefits depending on your itinerary and 
preferences. Is there anything more specific you'd like to know?
===============================================================================
'''

print("=== Final memory check ===")
# 11. Final memory status check
user_input_11 = (
    "Can you give me a final status of our memory management for this session?"
)
response_11 = agent.step(user_input_11)
print(f"User: {user_input_11}")
print(f"Assistant: {response_11.msgs[0].content}\n")

'''
===============================================================================
Assistant: Currently, we have 16 messages in memory, and a summary of our 
conversation is available with 1,544 characters. The full conversation history 
file contains 11,212 characters. Our memory management utilizes a lightweight 
file-based text search, and there are 8 searchable sessions. Is there anything 
else you need help with regarding our session or your trip planning?
===============================================================================
'''

print("\n=== Example Complete ===")
