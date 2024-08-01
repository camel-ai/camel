import json
import pytest
from camel.loaders import FireCrawlURLReader
from pydantic import BaseModel, Field
from typing import List

def test_scrape():
    test_url = "https://www.camel-ai.org/"
    resp = FireCrawlURLReader().scrape(test_url)
    assert type(resp) is str


def test_scrape_with_llm():
    test_url = "https://www.camel-ai.org/"

    class ArticleSchema(BaseModel):
        title: str
        points: int
        by: str
        commentsURL: str

    class TopArticlesSchema(BaseModel):
        top: List[ArticleSchema] = Field(..., description="Top 5 stories")
    resp = FireCrawlURLReader().scrape_with_llm(test_url, extraction_schema=TopArticlesSchema.model_json_schema())
    assert type(resp) is dict
    print(json.dumps(resp, indent=2))
