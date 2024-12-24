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

import os
import sys
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from camel.toolkits import OpenBBToolkit


@pytest.fixture
def mock_openbb():
    """Create a mock OpenBB client with all required attributes."""
    mock_obb = MagicMock()
    mock_obb.account = MagicMock()
    mock_obb.account.login = MagicMock()
    mock_obb.equity = MagicMock()
    mock_obb.equity.price = MagicMock()
    mock_obb.equity.screener = MagicMock()
    mock_obb.equity.fundamental = MagicMock()
    return mock_obb


@pytest.fixture
def mock_dependencies(mock_openbb):
    """Mock dependencies and environment for OpenBBToolkit."""
    openbb_module = MagicMock()
    openbb_module.obb = mock_openbb
    with patch.dict(sys.modules, {'openbb': openbb_module}):
        with patch(
            'camel.utils.commons.is_module_available', return_value=True
        ):
            with patch.dict(os.environ, {'OPENBB_PAT': 'test_pat'}):
                yield mock_openbb


def test_init_api_keys(mock_dependencies, monkeypatch):
    """Test initialization of API keys from environment variables."""
    # Set environment variables
    test_keys = {
        'OPENBB_PAT': 'test_pat',
        'FMP_API_KEY': 'test_fmp',
        'POLYGON_API_KEY': 'test_polygon',
        'FRED_API_KEY': 'test_fred',
    }
    for key, value in test_keys.items():
        monkeypatch.setenv(key, value)

    # Initialize toolkit
    OpenBBToolkit()

    # Verify login was called with correct PAT
    mock_dependencies.account.login.assert_called_once_with(pat='test_pat')


def test_get_stock_quote_success(mock_dependencies):
    """Test successful stock quote retrieval."""
    # Setup mock response
    mock_data = {
        'symbol': ['AAPL'],
        'asset_type': ['EQUITY'],
        'name': ['Apple Inc.'],
        'exchange': ['NMS'],
        'bid': [245.17],
        'ma_50d': [230.3884],
        'ma_200d': [207.31],
        'volume_average': [47881519.0],
        'volume_average_10d': [44455510.0],
        'currency': ['USD'],
    }
    mock_response = MagicMock()
    mock_response.results = mock_data
    mock_dependencies.equity.price.quote.return_value = mock_response

    # Initialize toolkit and make request
    toolkit = OpenBBToolkit()
    result = toolkit.get_stock_quote('AAPL')

    # Verify the result
    assert isinstance(result, dict)
    assert result['symbol'] == ['AAPL']
    assert result['name'] == ['Apple Inc.']
    assert result['bid'] == [245.17]

    # Verify the API was called correctly
    mock_dependencies.equity.price.quote.assert_called_with(
        symbol='AAPL', source='iex'
    )


def test_get_stock_quote_error(mock_dependencies):
    """Test stock quote error handling."""
    # Setup mock to raise exception
    mock_dependencies.equity.price.quote.side_effect = Exception('API Error')

    # Initialize toolkit and make request
    toolkit = OpenBBToolkit()
    result = toolkit.get_stock_quote('INVALID')

    # Verify empty dict is returned
    assert isinstance(result, dict)
    assert len(result) == 0


def test_screen_market_success(mock_dependencies):
    """Test successful market screening."""
    # Setup mock response
    mock_data = {
        'symbol': ['AAPL', 'MSFT'],
        'name': ['Apple Inc.', 'Microsoft Corporation'],
        'sector': ['Technology', 'Technology'],
        'industry': ['Consumer Electronics', 'Software'],
        'market_cap': [2.5e12, 2.1e12],
        'beta': [1.2, 1.1],
    }
    mock_response = MagicMock()
    mock_response.results = mock_data
    mock_dependencies.equity.screener.screen.return_value = mock_response

    # Initialize toolkit and make request
    toolkit = OpenBBToolkit()
    result = toolkit.screen_market(
        sector='Technology',
        market_cap_min=1e12,
        return_type='raw',
    )

    # Verify the result
    assert isinstance(result, dict)
    assert len(result['symbol']) == 2
    assert all(s == 'Technology' for s in result['sector'])
    assert all(mc >= 1e12 for mc in result['market_cap'])

    # Verify the API was called correctly
    mock_dependencies.equity.screener.screen.assert_called_once()


def test_screen_market_error(mock_dependencies):
    """Test market screening error handling."""
    # Setup mock to raise exception
    mock_dependencies.equity.screener.screen.side_effect = Exception(
        'API Error'
    )

    # Initialize toolkit and make request
    toolkit = OpenBBToolkit()
    result = toolkit.screen_market(sector='Invalid')

    # Verify empty dict is returned
    assert isinstance(result, dict)
    assert len(result) == 0


def test_get_income_statement_success(mock_dependencies):
    """Test successful income statement retrieval."""
    # Setup mock response
    mock_data = pd.DataFrame(
        {
            'date': ['2023-12-31', '2022-12-31'],
            'revenue': [394.3e9, 365.8e9],
            'grossProfit': [170.7e9, 155.8e9],
            'operatingIncome': [109.4e9, 99.8e9],
            'netIncome': [96.1e9, 94.7e9],
        }
    )
    mock_dependencies.equity.fundamental.income.return_value = mock_data

    # Initialize toolkit and make request
    toolkit = OpenBBToolkit()
    result = toolkit.get_income_statement('AAPL', return_type='raw')

    # Verify the result
    assert isinstance(result, dict)
    assert 'date' in result
    assert 'revenue' in result
    assert 'netIncome' in result
    assert len(result['date']) == 2

    # Verify the API was called correctly
    mock_dependencies.equity.fundamental.income.assert_called_once()
