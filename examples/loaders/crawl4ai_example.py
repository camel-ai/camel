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

import asyncio

from pydantic import BaseModel, Field

from camel.loaders import Crawl4AI

# Instantiate the Crawl4AI crawler
crawler = Crawl4AI()

URL = "https://toscrape.com/"

# --- Crawling (BFS) ---
crawl_results = asyncio.run(crawler.crawl(URL, max_depth=1))
print(crawl_results[0]["markdown"])
'''
===============================================================================
![](img/zyte.png)

# Web Scraping Sandbox

## Books

A [fictional bookstore](http://books.toscrape.com) that desperately wants to 
be scraped. It's a safe place for beginners learning web scraping and for 
developers validating their scraping technologies as well. 
Available at: [books.toscrape.com](http://books.toscrape.com)

[![](./img/books.png)](http://books.toscrape.com)

Details  
---  
Amount of items | 1000  
Pagination | ✔  
Items per page | max 20  
Requires JavaScript | ✘  
  
## Quotes

[A website](http://quotes.toscrape.com/) that lists quotes from famous people.
It has many endpoints showing the quotes in many different ways, each of them 
including new scraping challenges for you, as described below.

[![](./img/quotes.png)](http://quotes.toscrape.com)

Endpoints  
---  
[Default](http://quotes.toscrape.com/)| Microdata and pagination  
[Scroll](http://quotes.toscrape.com/scroll) | infinite scrolling pagination  
[JavaScript](http://quotes.toscrape.com/js) | JavaScript generated content  
[Delayed](http://quotes.toscrape.com/js-delayed) | Same as JavaScript but with 
    a delay (?delay=10000)  
[Tableful](http://quotes.toscrape.com/tableful) | a table based messed-up 
    layout
[Login](http://quotes.toscrape.com/login) | login with CSRF token 
    (any user/passwd works)  
[ViewState](http://quotes.toscrape.com/search.aspx) | an AJAX based filter 
    form with ViewStates  
[Random](http://quotes.toscrape.com/random) | a single random quote
===============================================================================
'''


# --- Scraping ---
scrape_result = asyncio.run(crawler.scrape(URL))
print(scrape_result)
'''
===============================================================================
{url: 'https://toscrape.com/', 
'raw_result': CrawlResult(url='https://toscrape.com/', markdown=..., 
    cleaned_html=..., links=...),
'markdown': "![](img/zyte.png)\n\n# Web Scraping Sandbox\n\n## Books...", 
'cleaned_html': '\n<div>\n<div>\n<div>\n<img class="logo" height="108" 
    src="img/zyte.png" width="200"/>\n
    <h1>Web Scraping Sandbox</h1>\n...'}
===============================================================================
'''


# --- Structured Scraping ---
class MovieResponse(BaseModel):
    title: str = Field(..., description="The name of the website.")
    year: int = Field(..., description="The amount of items on the bookstore.")
    rating: float = Field(
        ..., description="The names of the endpoints of quotes."
    )


structured_scrape_result = asyncio.run(
    crawler.structured_scrape(
        URL,
        response_format=MovieResponse,
        llm_provider="openai/gpt-4o",
    )
)
print(structured_scrape_result.extracted_content)
