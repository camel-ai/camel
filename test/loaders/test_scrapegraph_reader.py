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

import os
import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest  # type: ignore[import-not-found]

from camel.loaders.scrapegraph_loader import ScrapeGraphAILoader


def _install_fake_scrapegraph_package():
    fake_scrapegraph_module = ModuleType("scrapegraph_py")
    fake_logger_module = ModuleType("scrapegraph_py.logger")
    fake_logger_module.sgai_logger = MagicMock()
    fake_scrapegraph_module.Client = MagicMock()

    return patch.dict(
        sys.modules,
        {
            "scrapegraph_py": fake_scrapegraph_module,
            "scrapegraph_py.logger": fake_logger_module,
        },
    )


@pytest.fixture
def scrapegraph_ai():
    with _install_fake_scrapegraph_package() as fake_modules:
        mock_client = fake_modules["scrapegraph_py"].Client
        mock_client_instance = MagicMock()
        mock_client.return_value = mock_client_instance
        yield ScrapeGraphAILoader(api_key="test_api_key")


def test_init_with_api_key():
    with _install_fake_scrapegraph_package() as fake_modules:
        mock_client = fake_modules["scrapegraph_py"].Client
        ScrapeGraphAILoader(api_key="test_api_key")
        mock_client.assert_called_once_with(api_key="test_api_key")


def test_init_with_env_var():
    with (
        _install_fake_scrapegraph_package() as fake_modules,
        patch.dict(os.environ, {"SCRAPEGRAPH_API_KEY": "env_api_key"}),
    ):
        mock_client = fake_modules["scrapegraph_py"].Client
        ScrapeGraphAILoader()
        mock_client.assert_called_once_with(api_key="env_api_key")


def test_load_success(scrapegraph_ai):
    mock_response = "test answer"
    scrapegraph_ai.client.smartscraper.return_value = mock_response

    result = scrapegraph_ai.load("https://example.com")

    expected_result = {
        "contents": [
            {"content": "test answer", "source": "https://example.com"}
        ]
    }
    assert result == expected_result
    scrapegraph_ai.client.smartscraper.assert_called_once_with(
        website_url="https://example.com",
        user_prompt="Extract the main content from this page.",
    )


def test_load_failure(scrapegraph_ai):
    scrapegraph_ai.client.smartscraper.side_effect = Exception("Scrape failed")

    with pytest.raises(
        RuntimeError, match="Error loading source 1/1: https://example.com"
    ):
        scrapegraph_ai.load("https://example.com")


def test_close(scrapegraph_ai):
    scrapegraph_ai.close()
    scrapegraph_ai.client.close.assert_called_once()
