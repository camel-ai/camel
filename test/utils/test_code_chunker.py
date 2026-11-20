# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
from camel.utils.chunker.code_chunker import CodeChunker

# "世" is tokenised into two cl100k_base tokens whose bytes are each half of
# the UTF-8 encoded character, so a token window boundary can fall inside it.
CJK_TEXT = "你好世界" * 3


def test_split_oversized_preserves_multibyte_characters():
    chunker = CodeChunker(chunk_size=3)

    chunks = chunker._split_oversized(CJK_TEXT)

    assert "".join(chunks) == CJK_TEXT
    assert "\ufffd" not in "".join(chunks)


def test_split_oversized_preserves_whitespace():
    line = "def add(a, b):\n    return a + b\n"
    chunker = CodeChunker(chunk_size=3)

    chunks = chunker._split_oversized(line)

    assert "".join(chunks) == line


def test_split_oversized_respects_chunk_size():
    chunker = CodeChunker(chunk_size=4)

    chunks = chunker._split_oversized("abcdef ghij klmno")

    assert len(chunks) > 1
    assert "".join(chunks) == "abcdef ghij klmno"
    assert all(chunker.count_tokens(chunk) <= 4 for chunk in chunks)
