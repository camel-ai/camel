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
from unittest.mock import Mock, patch

import pytest

from camel.loaders import JinaURLReader

SUCCESSFUL_RESP = """Title: Hollow Knight

URL Source: https://en.wikipedia.org/wiki/Hollow_Knight

Published Time: 2017-03-05T15:54:50Z

Markdown Content:
| Hollow Knight |
| --- |
| [![Image 1](https://upload.wikimedia.org/wikipedia/en/thumb/0/04/Hollow_Knight_first_cover_art.webp/220px-Hollow_Knight_first_cover_art.webp.png)](https://en.wikipedia.org/wiki/File:Hollow_Knight_first_cover_art.webp) |
| [Developer(s)](https://en.wikipedia.org/wiki/Video_game_developer "Video game developer") | Team Cherry |
| [Publisher(s)](https://en.wikipedia.org/wiki/Video_game_publisher "Video game publisher") | Team Cherry |
| [Designer(s)](https://en.wikipedia.org/wiki/Video_game_designer "Video game designer") | 
*   Ari Gibson
*   William Pellen



 |
| [Programmer(s)](https://en.wikipedia.org/wiki/Video_game_programmer "Video game programmer") |

*   William Pellen
*   David Kazi
"""  # noqa: E501

FAILED_RESP = r'''{"data":null,"cause":{"name":"TimeoutError"},"code":422,"name":"AssertionFailureError","status":42206,"message":"Failed to goto http://bad_url/: TimeoutError: Navigation timeout of 30000 ms exceeded","readableMessage":"AssertionFailureError: Failed to goto http://bad_url/: TimeoutError: Navigation timeout of 30000 ms exceeded"}
'''  # noqa: E501


@patch("requests.get")
def test_read_content_success(mock_get: Mock):
    mock_get.return_value.text = SUCCESSFUL_RESP
    mock_get.return_value.status_code = 200
    reader = JinaURLReader()
    test_url = "https://en.wikipedia.org/wiki/Hollow_Knight"
    content = reader.read_content(test_url)
    assert "Title: Hollow Knight" in content


@patch("requests.get")
def test_read_content_fail(mock_get: Mock):
    mock_get.return_value.text = FAILED_RESP
    mock_get.return_value.status_code = 422
    mock_get.return_value.raise_for_status.side_effect = Exception(
        "Failed to goto http://bad_url/: TimeoutError: Navigation timeout of "
        "30000 ms exceeded"
    )

    reader = JinaURLReader()
    test_url = "bad_url"
    with pytest.raises(ValueError):
        reader.read_content(test_url)
