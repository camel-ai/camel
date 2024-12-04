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

from typing import List

from pydantic import BaseModel, Field

from camel.loaders import Firecrawl

firecrawl = Firecrawl()

response = firecrawl.crawl(url="https://www.camel-ai.org/about")

print(response["status"])
'''
===============================================================================
completed
===============================================================================
'''

print(response["data"][0]["markdown"])
'''
===============================================================================
...

Camel-AI Team

We are finding the  
scaling law of agent
=========================================

🐫 CAMEL is an open-source library designed for the study of autonomous and 
communicative agents. We believe that studying these agents on a large scale 
offers valuable insights into their behaviors, capabilities, and potential 
risks. To facilitate research in this field, we implement and support various 
types of agents, tasks, prompts, models, and simulated environments.

**We are** always looking for more **contributors** and **collaborators**.  
Contact us to join forces via [Slack](https://join.slack.com/t/camel-kwr1314/
shared_invite/zt-1vy8u9lbo-ZQmhIAyWSEfSwLCl2r2eKA)
 or [Discord](https://discord.gg/CNcNpquyDc)...
===============================================================================
'''


class ArticleSchema(BaseModel):
    title: str
    points: int
    by: str
    commentsURL: str


class TopArticlesSchema(BaseModel):
    top: List[ArticleSchema] = Field(
        ..., max_length=5, description="Top 5 stories"
    )


response = firecrawl.structured_scrape(
    url='https://news.ycombinator.com', response_format=TopArticlesSchema
)

print(response)
'''
===============================================================================
{'top': [{'title': 'Foobar2000', 'points': 69, 'by': 'citruscomputing', 
'commentsURL': 'item?id=41122920'}, {'title': 'How great was the Great 
Oxidation Event?', 'points': 145, 'by': 'Brajeshwar', 'commentsURL': 'item?
id=41119080'}, {'title': 'Launch HN: Martin (YC S23) - Using LLMs to Make a 
Better Siri', 'points': 73, 'by': 'darweenist', 'commentsURL': 'item?
id=41119443'}, {'title': 'macOS in QEMU in Docker', 'points': 488, 'by': 
'lijunhao', 'commentsURL': 'item?id=41116473'}, {'title': 'Crafting 
Interpreters with Rust: On Garbage Collection', 'points': 148, 'by': 
'amalinovic', 'commentsURL': 'item?id=41108662'}]}
===============================================================================
'''

map_result = firecrawl.map_site(url="https://www.camel-ai.org")

print(map_result)
"""
===============================================================================
['https://www.camel-ai.org', 'https://www.camel-ai.org/blog', 'https://www.
camel-ai.org/checkout', 'https://www.camel-ai.org/contact', 'https://www.camel-
ai.org/features', 'https://www.camel-ai.org/order-confirmation', 'https://www.
camel-ai.org/paypal-checkout', 'https://www.camel-ai.org/about', 'https://www.
camel-ai.org/integration', 'https://www.camel-ai.org/search', 'https://www.
camel-ai.org/post/crab', 'https://www.camel-ai.org/post/tool-usage', 'https://
www.camel-ai.org/post/releasenotes-sprint4', 'https://www.camel-ai.org/post/
releasenotes-sprint56']
===============================================================================
"""
