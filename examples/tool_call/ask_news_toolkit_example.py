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

from camel.toolkits import AskNewsToolkit

ask_news = AskNewsToolkit()

# news_output = ask_news.get_news(query="camel-ai")
# print(news_output[:1000])

"""
===============================================================================
<doc>
[1]:
Title: Robot Creates Painting of Alan Turing for $130,000 to $195,000 Auction
Summary: A robot named 'Ai-Da' created a painting of Alan Turing, a British 
mathematician and father of modern computer science, using artificial 
intelligence technology. The painting is part of an online auction that will 
take place from October 31 to November 7, and is estimated to be worth between 
$130,000 and $195,000. Ai-Da is a highly advanced robot that has arms and a 
face that resembles a human, complete with brown hair. The robot was created 
in 2019 by a team led by Aidan Meller, an art dealer and founder of Ai-Da 
Robot Studio, in collaboration with experts in artificial intelligence from 
the universities of Oxford and Birmingham. Ai-Da uses AI to create paintings 
or sculptures, and has cameras in its eyes and electronic arms. According to 
Ai-Da, 'Through my works on Alan Turing, I celebrate his achievements and 
contributions to the development of computing and artificial intelligence.' T
===============================================================================
"""

story_output = ask_news.get_stories(
    query="camel-ai", categories=["Technology"]
)
print(story_output)

web_search_output = ask_news.get_web_search(queries=["camel-ai"])
print(web_search_output)

reddit_output = ask_news.search_reddit(keywords=["camel-ai", "multi-agent"])
print(reddit_output)

finance_output = ask_news.finance_query(asset="bitcoin")
print(finance_output)
