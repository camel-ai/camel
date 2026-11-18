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


def _only_missing(module_name: str):
    """Patch is_module_available so only `module_name` is reported missing;
    every other module reports available. Use when a toolkit's __init__
    requires deps not installed in the test env but we want to isolate a
    method-level decorator check."""

    def fake(m):
        return m != module_name

    return patch('camel.utils.commons.is_module_available', side_effect=fake)


def _all_available():
    """Patch is_module_available to report every module as installed. Use
    to bypass __init__ dep decorators in the test env so a method-level
    decorator can be exercised in isolation."""
    return patch(
        'camel.utils.commons.is_module_available', return_value=True
    )


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


def test_excel_toolkit_extract_missing_tabulate():
    from camel.toolkits import ExcelToolkit

    with _all_available():
        toolkit = ExcelToolkit()
    with _only_missing('tabulate'):
        with pytest.raises(ImportError, match="tabulate"):
            toolkit.extract_excel_content("dummy.xlsx")


def test_excel_toolkit_extract_missing_xls2xlsx():
    from camel.toolkits import ExcelToolkit

    with _all_available():
        toolkit = ExcelToolkit()
    with _only_missing('xls2xlsx'):
        with pytest.raises(ImportError, match="xls2xlsx"):
            toolkit.extract_excel_content("dummy.xlsx")


def test_google_scholar_toolkit_get_full_paper_missing_arxiv2text():
    from unittest.mock import MagicMock

    scholarly_mock = MagicMock()
    with patch.dict('sys.modules', {'scholarly': scholarly_mock}):
        from camel.toolkits import GoogleScholarToolkit

        with _all_available():
            toolkit = GoogleScholarToolkit(author_identifier="Test Author")
        with _only_missing('arxiv2text'):
            with pytest.raises(ImportError, match="arxiv2text"):
                toolkit.get_full_paper_content_by_link("http://x/pdf")


def test_reddit_toolkit_sentiment_missing_textblob(monkeypatch):
    from unittest.mock import MagicMock

    monkeypatch.setenv("REDDIT_CLIENT_ID", "x")
    monkeypatch.setenv("REDDIT_CLIENT_SECRET", "x")
    monkeypatch.setenv("REDDIT_USER_AGENT", "x")

    praw_mock = MagicMock()
    with patch.dict('sys.modules', {'praw': praw_mock}):
        from camel.toolkits import RedditToolkit

        with _all_available():
            toolkit = RedditToolkit()
        with _only_missing('textblob'):
            with pytest.raises(ImportError, match="textblob"):
                toolkit.perform_sentiment_analysis([])


def test_weather_toolkit_missing_dependency():
    from camel.toolkits import WeatherToolkit

    toolkit = WeatherToolkit()
    with _mock_missing('pyowm'):
        with pytest.raises(ImportError, match="pyowm"):
            toolkit.get_weather_data("London")


def test_slack_toolkit_missing_dependency():
    from camel.toolkits import SlackToolkit

    with _mock_missing('slack_sdk'):
        with pytest.raises(ImportError, match="slack_sdk"):
            SlackToolkit()


def test_open_api_toolkit_missing_dependency():
    from camel.toolkits import OpenAPIToolkit

    toolkit = OpenAPIToolkit()
    with _mock_missing('prance'):
        with pytest.raises(ImportError, match="prance"):
            toolkit.parse_openapi_file("dummy.yaml")


def test_gmail_toolkit_missing_dependency():
    from camel.toolkits import GmailToolkit

    with _mock_missing('googleapiclient'):
        with pytest.raises(ImportError, match="googleapiclient"):
            GmailToolkit()


def test_earth_science_toolkit_missing_numpy():
    from camel.toolkits import EarthScienceToolkit

    with _mock_missing('numpy'):
        with pytest.raises(ImportError, match="numpy"):
            EarthScienceToolkit()


def test_earth_science_toolkit_missing_rasterio():
    from camel.toolkits import EarthScienceToolkit

    with _mock_missing('rasterio'):
        with pytest.raises(ImportError, match="rasterio"):
            EarthScienceToolkit()


def test_earth_science_toolkit_scipy_method_missing_scipy():
    from camel.toolkits import EarthScienceToolkit

    with _all_available():
        toolkit = EarthScienceToolkit()
    with _only_missing('scipy'):
        with pytest.raises(ImportError, match="scipy"):
            toolkit.mann_kendall_test([1, 2, 3])
