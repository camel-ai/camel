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
import pytest

from camel.loaders import JinaURLReader


@pytest.fixture
def jina_default_reader():
    return JinaURLReader(timeout=100)


def test_read_content_default(jina_default_reader: JinaURLReader):
    test_url = "https://www.ign.com/articles/the-best-reviewed-games-of-2024"
    content = jina_default_reader.read_content(test_url)
    assert content is not None
    print(content)


def test_read_content_no_protocol():
    # use the default return format
    default_reader = JinaURLReader()
    content = default_reader.read_content("www.example.com")
    print(content)


def test_read_content_invalid_url():
    # use the default return format
    default_reader = JinaURLReader()
    content = default_reader.read_content("https://www.example.com")
    print(content)


def test_read_content_timeout():
    default_reader = JinaURLReader(timeout=10)
    slow_url = "https://httpbin.org/delay/5"
    content = default_reader.read_content(slow_url)
    print(content)
