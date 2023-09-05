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
import requests


def test_google_api():
    # Check the google search api

    # https://developers.google.com/custom-search/v1/overview
    GOOGLE_API_KEY = "AIzaSyAFATycX7C9SgqpeL5ciCZ7dFBsqIqLhtY"
    # https://cse.google.com/cse/all
    SEARCH_ENGINE_ID = "50393d7ebc1ef4bf9"

    url = f"https://www.googleapis.com/customsearch/v1?" \
          f"key={GOOGLE_API_KEY}&cx={SEARCH_ENGINE_ID}&q=any"
    result = requests.get(url)

    assert result.status_code == 200
