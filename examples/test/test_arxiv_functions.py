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

from unittest.mock import MagicMock, patch

from camel.toolkits import ArxivToolkit

# We need to mock the entire praw module
praw_mock = MagicMock()
praw_mock.Reddit = MagicMock()

def test_search_paper():
    arxivToolkit = ArxivToolkit()
    query = "attention is all you need"
    searched_results = arxivToolkit.search_paper(query, 1)
    print(searched_results)
    assert len(searched_results) == 1

def test_get_tools(arxiv_toolkit):
    from camel.toolkits import OpenAIFunction

    tools = arxiv_toolkit.get_tools()
    assert len(tools) == 2
    assert all(isinstance(tool, OpenAIFunction) for tool in tools)

def test_download_papers():
    arxivToolkit = ArxivToolkit()
    query1 = "attention is all you need"
    result = arxivToolkit.download_papers(pdf_urls=["https://arxiv.org/pdf/1706.03762", "http://arxiv.org/pdf/2409.03757v1"])
    print(result)
test_download_papers()