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

from camel.toolkits import AskNewsToolkit

ask_news = AskNewsToolkit()

news_output = ask_news.get_news(query="President of United States")
print(news_output[:1000])

"""
===============================================================================
<doc>
[1]:
Title: Can Elon Musk Become President of the United States?
Summary: Elon Musk, the American billionaire, has been appointed to lead the 
Department of Government Efficiency in Donald Trump's upcoming administration, 
sparking speculation about his potential presidential ambitions. However, 
according to the US Constitution, the President must be a natural-born citizen 
of the United States. As Musk was born in South Africa and became a Canadian 
citizen through his mother, he does not meet this requirement. While he 
acquired US citizenship in 2002, this does not make him a natural-born 
citizen. Additionally, the Constitution requires the President to be at least 
35 years old and a resident of the United States for at least 14 years. Musk 
can, however, hold other government positions, as the requirement of being a 
natural-born citizen only applies to the President and Vice President. Many 
non-US-born citizens have held prominent government positions in the past, 
including Henry
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

finance_output = ask_news.query_finance(asset="bitcoin")
print(finance_output)
