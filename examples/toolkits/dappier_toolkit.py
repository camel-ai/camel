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
from camel.toolkits import DappierToolkit, FunctionTool

real_time_data_response = DappierToolkit().search_real_time_data(
    query="camel-ai"
)

print(real_time_data_response)
"""
===============================================================================
CAMEL-AI is pretty cool! It's the first LLM (Large Language Model) multi-agent 
framework and an open-source community focused on exploring the scaling laws 
of agents. 🌟

Here are some highlights:

- **Purpose**: It aims to create highly customizable intelligent agents and 
    build multi-agent systems for real-world applications.
- **Features**: CAMEL provides a role-playing approach and inception prompting
    to help chat agents complete tasks aligned with human intentions.
- **Use Cases**: You can turn your database into an AI-powered data analyst,
    allowing you to ask questions in plain English and get instant insights.
    📊🤖
- **Community**: It's an open-source initiative, so developers can contribute
    and collaborate on building and using LLM-based agents.

If you want to dive deeper, check out their website:
[CAMEL-AI.org](https://www.camel-ai.org) 🚀!
===============================================================================
"""

# Use a different AI model which has access to real-time financial news.
real_time_data_response = DappierToolkit().search_real_time_data(
    query="Could you please provide the stock price for Google on 05/03/24?",
    ai_model_id="am_01j749h8pbf7ns8r1bq9s2evrh",
)
print(real_time_data_response)
"""
===============================================================================
The stock price for Google (GOOGL) on May 3rd, 2024, was $167.10.
===============================================================================
"""

# Example with ChatAgent using the Real Time Search.
agent = ChatAgent(
    system_message="""You are a helpful assistant that can use brave search 
        engine to answer questions.""",
    tools=[FunctionTool(DappierToolkit().search_real_time_data)],
)

usr_msg = "What is the temperature in Tokyo?"

response = agent.step(input_message=usr_msg, response_format=None)

print(response.msgs[0].content)
"""
===============================================================================
The current temperature in Tokyo is 50°F (about 10°C). It's a bit chilly, 
so you might want to grab a jacket! 🧥🌬️
===============================================================================
"""

ai_recommendations_response = DappierToolkit().get_ai_recommendations(
    query="latest sports news",
    data_model_id="dm_01j0pb465keqmatq9k83dthx34",
    similarity_top_k=3,
    ref="sportsnaut.com",
    num_articles_ref=2,
    search_algorithm="most_recent",
)
print(ai_recommendations_response)
"""
===============================================================================
{'author': 'Andrew Buller-Russ', 
'image_url': 'https://images.dappier.com/dm_01j0pb465keqmatq9k83dthx34/
Syndication-Detroit-Free-Press-25087075_.jpg?width=428&height=321', 
'pubdate': 'Thu, 02 Jan 2025 03:12:06 +0000', 
'source_url': 'https://sportsnaut.com/nick-bosa-detroit-lions-trade-rumors-49ers/', 
'summary': 'In a thrilling Monday night game, the Detroit Lions triumphed 
over the San Francisco 49ers 40-34, solidifying their status as a top NFL 
team. Despite a strong performance from Nick Bosa, who recorded eight tackles 
and two sacks, the 49ers\' playoff hopes were dashed. Bosa praised the Lions\' 
competitive spirit and resilience under Coach Dan Campbell, sparking 
about his interest in joining the team, although he remains under contract 
with the 49ers for four more seasons. Bosa\'s admiration for the Lions 
highlights the stark contrast between the two franchises\' fortunes, 
with the Lions celebrating a significant victory while the 49ers struggle.
Having experienced playoff success with the 49ers, Bosa values strong 
leadership from both Campbell and his own coach, Kyle Shanahan. His comments 
reflect a broader sentiment in the NFL about the importance of winning and 
the positive environment it fosters for players.', 
'title': 'Nick Bosa gushes about Detroit Lions, sparking 49ers trade rumors'}

{'author': 'Andrew Buller-Russ', 
'image_url': 'https://images.dappier.com/dm_01j0pb465keqmatq9k83dthx34/
Baseball-World-Baseball-Classic-Semifinal-Japan-vs-Mexico-20279015_.jpg?width=428&height=321', 
'pubdate': 'Thu, 02 Jan 2025 02:43:38 +0000', 
'source_url': 'https://www.lafbnetwork.com/los-angeles-dodgers/
los-angeles-dodgers-news/los-angeles-dodgers-meeting-roki-sasaki/', 
'summary': 'Roki Sasaki, a talented 23-year-old Japanese pitcher, is 
approaching a decision on his MLB free agency, with the Los Angeles Dodgers 
among the frontrunners to sign him. They are competing against teams like 
the Chicago Cubs, New York Mets, and others. The Dodgers are set to meet 
with Sasaki, emphasizing his signing as a top priority despite facing 
competition from around 20 other teams. Sasaki\'s status as a minor-league 
posting player may allow him to be signed at a more affordable price, 
increasing his appeal. As he gathers information and prepares for a second
round of meetings, the Dodgers are keen to secure him before the posting 
window closes on January 24, with the international signing period beginning 
on January 15.', 'title': 'Los Angeles Dodgers Take Another Step Toward 
Signing Roki Sasaki'}

{'author': 'Andrew Buller-Russ', 
'image_url': 'https://images.dappier.com/dm_01j0pb465keqmatq9k83dthx34/
NFL-Detroit-Lions-at-Kansas-City-Chiefs-24020812_.jpg?width=428&height=321', 
'pubdate': 'Thu, 02 Jan 2025 02:08:34 +0000', 
'source_url': 'https://sportsnaut.com/detroit-lions-cut-jamal-adams/', 
'summary': 'The Detroit Lions, with a strong 14-2 record, have released 
former All-Pro safety Jamal Adams from their practice squad ahead of a crucial 
Week 18 game against the Minnesota Vikings. Adams, who joined the Lions on 
December 1, 2024, played in two games but recorded only three tackles in 
20 defensive snaps, representing a mere 17% of the team\'s defensive plays. 
This marks Adams\' second release this season, having previously been cut 
by the Tennessee Titans after three appearances. The Lions\' decision to part 
ways with Adams comes as they focus on their playoff positioning for the 
upcoming game.', 
'title': 'Detroit Lions cut bait with All-Pro ahead of Week 18 matchup with 
Vikings'}
===============================================================================
"""
