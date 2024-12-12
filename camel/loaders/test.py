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
from firecrawl import FirecrawlApp

app = FirecrawlApp(
    api_url="https://firecrawl.testprd.eigent.ai",
)
try:
    crawl_response = app.crawl_url(
        url="https://docs.camel-ai.org/", params={'formats': ['markdown']}
    )
    print("Crawl Response:", crawl_response)
except Exception as e:
    print("Error occurred:", str(e))