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
Tests that @dependencies_required and @api_keys_required are correctly applied
to toolkit classes. When a required package is unavailable, calling __init__
should raise ImportError. When required env vars are missing, it should raise
ValueError.
"""

from unittest.mock import patch

import pytest


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


def test_sympy_toolkit_missing_dependency():
    from camel.toolkits import SymPyToolkit

    with _mock_missing('sympy'):
        with pytest.raises(ImportError, match="sympy"):
            SymPyToolkit()


def test_networkx_toolkit_missing_dependency():
    from camel.toolkits import NetworkXToolkit

    with _mock_missing('networkx'):
        with pytest.raises(ImportError, match="networkx"):
            NetworkXToolkit()


def test_crawl4ai_toolkit_missing_dependency():
    from camel.toolkits import Crawl4AIToolkit

    with _mock_missing('crawl4ai'):
        with pytest.raises(ImportError, match="crawl4ai"):
            Crawl4AIToolkit()


def test_excel_toolkit_missing_pandas():
    from camel.toolkits import ExcelToolkit

    with _mock_missing('pandas'):
        with pytest.raises(ImportError, match="pandas"):
            ExcelToolkit()


def test_excel_toolkit_missing_openpyxl():
    from camel.toolkits import ExcelToolkit

    with _mock_missing('openpyxl'):
        with pytest.raises(ImportError, match="openpyxl"):
            ExcelToolkit()


def test_google_scholar_toolkit_missing_dependency():
    from camel.toolkits import GoogleScholarToolkit

    with _mock_missing('scholarly'):
        with pytest.raises(ImportError, match="scholarly"):
            GoogleScholarToolkit(author_identifier="Test Author")


def test_reddit_toolkit_missing_dependency():
    from camel.toolkits import RedditToolkit

    with _mock_missing('praw'):
        with pytest.raises(ImportError, match="praw"):
            RedditToolkit()


def test_reddit_toolkit_missing_api_keys(monkeypatch):
    from unittest.mock import MagicMock

    monkeypatch.delenv("REDDIT_CLIENT_ID", raising=False)
    monkeypatch.delenv("REDDIT_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("REDDIT_USER_AGENT", raising=False)

    praw_mock = MagicMock()
    with patch.dict('sys.modules', {'praw': praw_mock}):
        from camel.toolkits import RedditToolkit

        with pytest.raises(ValueError, match="REDDIT_CLIENT_ID"):
            RedditToolkit()
