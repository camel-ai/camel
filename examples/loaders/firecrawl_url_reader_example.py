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
import json
import time
from typing import List

from pydantic import BaseModel, Field

from camel.loaders import FireCrawlURLReader

firecrawl = FireCrawlURLReader()

job_id = firecrawl.crawl(
    url="https://www.camel-ai.org/about",
    wait_until_done=False,
    max_depth=0,
    only_main_content=True,
)

print(job_id)

'''
===============================================================================
99d5d324-410a-4232-904d-be0310ea5f21
===============================================================================
'''

response = firecrawl.check_crawl_job_status(job_id)

print(response["status"])
'''
===============================================================================
active
===============================================================================
'''

while response["status"] == "active":
    time.sleep(5)
    response = firecrawl.check_crawl_job_status(job_id)

if response["status"] == "completed":
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
 or [Discord](https://discord.gg/CNcNpquyDc)
 ...
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


response = firecrawl.scrape_with_llm(
    url='https://news.ycombinator.com',
    extraction_schema=TopArticlesSchema,
)

print(json.dumps(response, indent=2))
'''
===============================================================================
{
  "top": [
    {
      "title": "Structured Outputs in the API",
      "points": 401,
      "by": "davidbarker",
      "commentsURL": "item?id=41173223"
    },
    {
      "title": "Why is 'Left Stick to Sprint' so unpleasant in games?",
      "points": 15,
      "by": "todsacerdoti",
      "commentsURL": "item?id=41176466"
    },
    {
      "title": "Tracking supermarket prices with Playwright",
      "points": 157,
      "by": "sakisv",
      "commentsURL": "item?id=41173335"
    },
    {
      "title": "Show HN: 1-FPS encrypted screen sharing for introverts",
      "points": 203,
      "by": "RomanPushkin",
      "commentsURL": "item?id=41173161"
    },
    {
      "title": 
      "Full text search over Postgres: Elasticsearch vs. alternatives",
      "points": 134,
      "by": "philippemnoel",
      "commentsURL": "item?id=41173288"
    }
  ]
}
===============================================================================
'''
