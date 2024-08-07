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
from camel.loaders import FireCrawlURLReader
from pydantic import BaseModel, Field
from typing import List


def test_scrape():
    test_url = "https://www.camel-ai.org/"
    resp = FireCrawlURLReader().scrape(test_url)
    assert type(resp) is str
    print(resp)


def test_scrape_with_llm_with_pydanctic():
    test_url = "https://www.camel-ai.org/"

    class ArticleSchema(BaseModel):
        title: str
        points: int
        by: str
        commentsURL: str

    class TopArticlesSchema(BaseModel):
        top: List[ArticleSchema] = Field(..., description="Top 5 stories")
    print(json.dumps(TopArticlesSchema.schema(), indent=2))
    print("\n\n\n\n")
    resp = FireCrawlURLReader().scrape_with_llm(test_url, extraction_schema=TopArticlesSchema.model_json_schema())
    assert type(resp) is dict
    print(json.dumps(resp, indent=2))


def test_scrape_with_llm_with_json():
    test_url = "https://www.camel-ai.org/"
    extraction_schema = {
      "$defs": {
        "ArticleSchema": {
          "properties": {
            "title": {
              "title": "Title",
              "type": "string"
            },
            "points": {
              "title": "Points",
              "type": "integer"
            },
            "by": {
              "title": "By",
              "type": "string"
            },
            "commentsURL": {
              "title": "Commentsurl",
              "type": "string"
            }
          },
          "required": [
            "title",
            "points",
            "by",
            "commentsURL"
          ],
          "title": "ArticleSchema",
          "type": "object"
        }
      },
      "properties": {
        "top": {
          "description": "Top 5 stories",
          "items": {
            "$ref": "#/$defs/ArticleSchema"
          },
          "title": "Top",
          "type": "array"
        }
      },
      "required": [
        "top"
      ],
      "title": "TopArticlesSchema",
      "type": "object"
    }
    resp = FireCrawlURLReader().scrape_with_llm(test_url, extraction_schema=extraction_schema)
    assert type(resp) is dict
    print(json.dumps(resp, indent=2))


def test_crawl():
    test_url = "https://www.camel-ai.org/"
    resp = FireCrawlURLReader().crawl(test_url, max_depth=1)
    assert type(resp) is list
    print(json.dumps(resp, indent=2))


def test_crawl_jobid():
    test_url = "https://www.camel-ai.org/"
    reader = FireCrawlURLReader()
    jobid = reader.crawl(test_url, max_depth=0, wait_until_done=False)
    assert type(jobid) is str
    resp = reader.check_crawl_job_status(jobid)
    assert type(resp) is dict

