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
import os

import requests
import wikipedia

from camel.functions.search_functions import (
    search_google_and_summarize,
    search_wiki,
)


def test_search_wiki_normal():
    expected_output = (
        "Erygia sigillata is a species of moth in the family Erebidae found "
        "in Himachal Pradesh, Northern India. The moth was officially "
        "recognized and classified in 1892.")

    assert search_wiki("Erygia sigillata") == expected_output


def test_search_wiki_not_found():
    search_output = search_output = search_wiki(
        "South Africa Women Football Team")
    assert search_output.startswith(
        "There is no page in Wikipedia corresponding to entity South Africa "
        "Women Football Team, please specify another word to describe the "
        "entity to be searched.")


def test_search_wiki_with_ambiguity():
    expected_output = wikipedia.summary("Google", sentences=5,
                                        auto_suggest=False)
    assert search_wiki("Google LLC") == expected_output


def test_duckduckgo_api():
    # Check the Google search api

    # https://pypi.org/project/duckduckgo-search/
    DUCKDUCKGO_API_KEY = os.getenv("DUCKDUCKGO_API_KEY")
    # https://cse.google.com/cse/all
    SEARCH_ENGINE_ID = os.getenv("SEARCH_ENGINE_ID")

    url = f"https://pypi.org/project/duckduckgo-search/" \
          f"key={DUCKDUCKGO_API_KEY}&cx={SEARCH_ENGINE_ID}&q=any"
    result = requests.get(url)

    assert result.status_code == 200


def test_web_search():
    query = "What big things are happening in 2023?"
    answer = search_google_and_summarize(query)

    assert answer is not None
