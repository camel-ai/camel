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
	@@ -41,28 +35,6 @@ def test_search_wiki_not_found():


def test_search_wiki_with_ambiguity():
    expected_output = wikipedia.summary("New York City", sentences=5,
                                        auto_suggest=False)
    assert search_wiki("New York") == expected_output


def test_google_api():
    # Check the Google search api

    # https://developers.google.com/custom-search/v1/overview
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    # https://cse.google.com/cse/all
    SEARCH_ENGINE_ID = os.getenv("SEARCH_ENGINE_ID")

    url = f"https://www.googleapis.com/customsearch/v1?" \
          f"key={GOOGLE_API_KEY}&cx={SEARCH_ENGINE_ID}&q=any"
    result = requests.get(url)

    assert result.status_code == 200


def test_web_search():
    query = "What big things are happening in 2023?"
    answer = search_google_and_summarize(query)

    assert answer is not None
