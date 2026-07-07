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
"""
Test that the following decorators are correctly applied to camel.loaders:
@api_keys_required - should raise ValueError if value is missing
@dependencies_required - should raise ImportError if package/module is missing
"""

from io import BytesIO
from unittest.mock import patch

import pytest

fake_api_key = "fake_api_key"


def _mock_missing(module_name: str):
    """Patch is_module_available to return False for a specific module."""
    original = __import__(
        'camel.utils.commons', fromlist=['is_module_available']
    ).is_module_available

    def fake(m):
        if m == module_name:
            return False
        return original(m)

    return patch('camel.utils.commons.is_module_available', side_effect=fake)


def test_crawl4ai_missing_dependency():
    from camel.loaders import Crawl4AI

    with _mock_missing('crawl4ai'):
        with pytest.raises(ImportError, match="crawl4ai"):
            Crawl4AI()


def test_firecrawl_missing_dependency():
    from camel.loaders import Firecrawl

    with _mock_missing('firecrawl'):
        with pytest.raises(ImportError, match="firecrawl"):
            Firecrawl(api_key=fake_api_key)


def test_markitdown_missing_dependency():
    from camel.loaders import MarkItDownLoader

    with _mock_missing('markitdown'):
        with pytest.raises(ImportError, match="markitdown"):
            MarkItDownLoader()


def test_scrapegraph_missing_dependency():
    from camel.loaders import ScrapeGraphAI

    with _mock_missing('scrapegraph_py'):
        with pytest.raises(ImportError, match="scrapegraph_py"):
            ScrapeGraphAI(api_key=fake_api_key)


def test_scrapegraph_missing_api_key():
    from camel.loaders import ScrapeGraphAI

    with patch('camel.utils.commons.is_module_available', return_value=True):
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="SCRAPEGRAPH_API_KEY"):
                ScrapeGraphAI()


def test_base_io_missing_dependencies():
    from camel.loaders.base_io import HtmlFile, PdfFile

    with _mock_missing('fitz'):
        with pytest.raises(ImportError, match="fitz"):
            PdfFile.from_bytes(BytesIO(b"pdf"), "test.pdf")

    with _mock_missing('bs4'):
        with pytest.raises(ImportError, match="bs4"):
            HtmlFile.from_bytes(BytesIO(b"<html></html>"), "test.html")


def test_unstructured_io_missing_dependency():
    from camel.loaders import UnstructuredIO

    with _mock_missing('unstructured'):
        with pytest.raises(ImportError, match="unstructured"):
            UnstructuredIO.create_element_from_text(text="test")

    with _mock_missing('unstructured'):
        with pytest.raises(ImportError, match="unstructured"):
            UnstructuredIO.parse_file_or_url(input_path="test.txt")

    with _mock_missing('unstructured'):
        with pytest.raises(ImportError, match="unstructured"):
            UnstructuredIO.parse_bytes(file=BytesIO(b"test"))

    with _mock_missing('unstructured'):
        with pytest.raises(ImportError, match="unstructured"):
            UnstructuredIO.clean_text_data(text="test")

    with _mock_missing('unstructured'):
        with pytest.raises(ImportError, match="unstructured"):
            UnstructuredIO.extract_data_from_text(
                text="test@example.com",
                extract_type="extract_email_address",
            )

    with _mock_missing('unstructured'):
        with pytest.raises(ImportError, match="unstructured"):
            UnstructuredIO.stage_elements(
                elements=[],
                stage_type="convert_to_dict",
            )

    with _mock_missing('unstructured'):
        with pytest.raises(ImportError, match="unstructured"):
            UnstructuredIO.chunk_elements(
                elements=[],
                chunk_type="chunk_by_title",
            )
