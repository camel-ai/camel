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
from camel.toolkits import SearchToolkit

# This example demonstrates how to use the SearchToolkit to
# perform a Google search while excluding certain domains from the results.

# Google search API Key and Search Engine ID are required to run this example
# API Key: https://developers.google.com/custom-search/v1/overview
# Search Engine ID: https://cse.google.com/cse/all


toolkit = SearchToolkit()
search_result = toolkit.search_google(
    query="Python Wikipedia", number_of_result_pages=3
)
print("Search results for 'Python Wikipedia':\n")
for result in search_result:
    print(result['url'])
toolkit = SearchToolkit(
    exclude_domains=[
        "wikipedia.org",
    ],
)
search_result = toolkit.search_google(
    query="Python Wikipedia", number_of_result_pages=3
)
print("\nExcluding specified domains related to wikipedia:\n")
for result in search_result:
    print(result['url'])

"""
Search results for 'Python Wikipedia':
https://en.wikipedia.org/wiki/Python_(programming_language)
https://wiki.python.org/moin/FrontPage
https://pypi.org/project/wikipedia/

Excluding specified domains related to wikipedia:


https://pypi.org/project/wikipedia/
https://wiki.python.org/moin/FrontPage
https://www.reddit.com/r/Python/comments/3tn216/scraping_wikipedia/
"""
