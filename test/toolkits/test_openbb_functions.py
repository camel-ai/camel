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

import pytest

# Create a mock for the openbb module
mock_openbb_module = MagicMock()
mock_openbb_module.obb = MagicMock()

# Apply the mock to sys.modules
with patch.dict('sys.modules', {'openbb': mock_openbb_module}):
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
    mock_obb.economy = MagicMock()
    mock_obb.economy.indicators = MagicMock()
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
            with patch.dict(os.environ, {'OPENBB_TOKEN': 'test_token'}):
                yield mock_openbb


def test_init_api_keys(mock_dependencies, monkeypatch):
    """Test initialization of API keys from environment variables."""
    # Set environment variables
    test_keys = {
        'OPENBB_TOKEN': 'test_token',
        'FMP_API_KEY': 'test_fmp',
        'POLYGON_API_KEY': 'test_polygon',
        'FRED_API_KEY': 'test_fred',
    }
    for key, value in test_keys.items():
        monkeypatch.setenv(key, value)

    # Initialize toolkit
    OpenBBToolkit()

    # Verify login was called with correct Token
    mock_dependencies.account.login.assert_called_once_with(pat='test_token')


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
        symbol='AAPL', provider='fmp'
    )


def test_get_stock_quote_error(mock_dependencies):
    """Test stock quote error handling."""
    # Setup mock to raise exception
    mock_dependencies.equity.price.quote.side_effect = Exception('API Error')

    # Initialize toolkit and make request
    toolkit = OpenBBToolkit()
    result = toolkit.get_stock_quote('INVALID')

    # Verify error message is returned
    assert isinstance(result, list)
    assert len(result) == 1
    assert 'Failed to get stock quote' in result[0]
    assert 'INVALID' in result[0]


def test_get_income_statement_success(mock_dependencies):
    """Test successful income statement retrieval."""
    mock_data = {
        'date': ['2023-12-31', '2022-12-31'],
        'revenue': [394.3e9, 365.8e9],
        'grossProfit': [170.7e9, 155.8e9],
        'operatingIncome': [109.4e9, 99.8e9],
        'netIncome': [96.1e9, 94.7e9],
    }
    mock_response = MagicMock()
    mock_response.results = mock_data
    mock_dependencies.equity.fundamental.income.return_value = mock_response

    toolkit = OpenBBToolkit()
    result = toolkit.get_financial_statement(
        symbol='AAPL', statement_type='income'
    )

    assert isinstance(result, dict)
    assert result['date'] == ['2023-12-31', '2022-12-31']
    assert result['revenue'] == [394.3e9, 365.8e9]


def test_get_historical_data(mock_dependencies):
    """Test historical data retrieval."""
    mock_data = {
        'date': ['2023-12-01'],
        'open': [190.33],
        'close': [191.24],
        'volume': [45679300],
    }
    mock_response = MagicMock()
    mock_response.results = mock_data
    mock_dependencies.equity.price.historical.return_value = mock_response

    toolkit = OpenBBToolkit()
    result = toolkit.get_historical_data(
        symbol="AAPL",
        start_date="2023-12-01",
        end_date="2023-12-02",
        interval="1d",
    )

    assert isinstance(result, dict)
    assert result == mock_data


def test_get_historical_data_error(mock_dependencies):
    """Test historical data error handling."""
    mock_dependencies.equity.price.historical.side_effect = Exception(
        'API Error'
    )

    toolkit = OpenBBToolkit()
    result = toolkit.get_historical_data(
        symbol="INVALID", start_date="2023-12-01", end_date="2023-12-02"
    )

    assert isinstance(result, list)
    assert len(result) == 1
    assert 'Failed to get historical data' in result[0]
    assert 'INVALID' in result[0]


def test_get_company_profile(mock_dependencies):
    """Test company profile retrieval."""
    mock_data = {
        'name': ['Apple Inc.'],
        'sector': ['Technology'],
        'industry': ['Electronics'],
    }
    mock_response = MagicMock()
    mock_response.results = mock_data
    mock_dependencies.equity.profile.return_value = mock_response

    toolkit = OpenBBToolkit()
    result = toolkit.get_company_profile(symbol="AAPL", provider="fmp")

    assert isinstance(result, dict)
    assert result['name'][0] == 'Apple Inc.'


def test_get_company_profile_error(mock_dependencies):
    """Test company profile error handling."""
    mock_dependencies.equity.profile.side_effect = Exception('API Error')

    toolkit = OpenBBToolkit()
    result = toolkit.get_company_profile(symbol="INVALID", provider="fmp")

    assert isinstance(result, list)
    assert len(result) == 1
    assert 'Failed to get company profile' in result[0]
    assert 'INVALID' in result[0]


def test_get_financial_statement(mock_dependencies):
    """Test financial statement retrieval."""
    mock_data = {'total_assets': [1000000], 'total_equity': [500000]}
    mock_response = MagicMock()
    mock_response.results = mock_data
    mock_dependencies.equity.fundamental.balance.return_value = mock_response
    mock_dependencies.equity.fundamental.income.return_value = mock_response
    mock_dependencies.equity.fundamental.cash.return_value = mock_response

    toolkit = OpenBBToolkit()

    # Test balance sheet
    result = toolkit.get_financial_statement(
        symbol="MSFT", statement_type="balance", period="annual"
    )
    assert isinstance(result, dict)
    assert result['total_assets'][0] == 1000000


def test_get_financial_statement_error(mock_dependencies):
    """Test financial statement error handling."""
    mock_dependencies.equity.fundamental.balance.side_effect = Exception(
        'API Error'
    )
    mock_dependencies.equity.fundamental.income.side_effect = Exception(
        'API Error'
    )
    mock_dependencies.equity.fundamental.cash.side_effect = Exception(
        'API Error'
    )

    toolkit = OpenBBToolkit()
    result = toolkit.get_financial_statement(
        symbol="INVALID", statement_type="balance", period="annual"
    )

    assert isinstance(result, list)
    assert len(result) == 1
    assert 'Failed to get financial statement' in result[0]
    assert 'INVALID' in result[0]
