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
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from camel.toolkits import OpenBBToolkit


@pytest.fixture
def mock_obb():
    """Mock OpenBB client fixture."""
    with patch('openbb.obb') as mock:
        mock.account.login = MagicMock()
        yield mock


@pytest.fixture
def openbb_toolkit(mock_obb):
    """Create OpenBBToolkit instance with mocked OpenBB client."""
    with patch.dict(
        os.environ,
        {
            'OPENBB_PAT': 'dummy_pat',
            'FMP_API_KEY': 'dummy_fmp',
            'POLYGON_API_KEY': 'dummy_polygon',
            'FRED_API_KEY': 'dummy_fred',
        },
    ):
        toolkit = OpenBBToolkit()
        return toolkit


def test_init_api_keys(monkeypatch):
    """Test initialization of API keys from environment variables."""
    with patch('openbb.obb') as mock_obb:
        mock_obb.account.login = MagicMock()

        test_keys = {
            'OPENBB_PAT': 'test_pat',
            'FMP_API_KEY': 'test_fmp',
            'POLYGON_API_KEY': 'test_polygon',
            'FRED_API_KEY': 'test_fred',
        }
        for key, value in test_keys.items():
            monkeypatch.setenv(key, value)

        OpenBBToolkit()
        mock_obb.account.login.assert_called_once_with(pat='test_pat')


def test_get_stock_quote_success(openbb_toolkit, mock_obb):
    """Test successful stock quote retrieval."""
    mock_df = pd.DataFrame(
        {
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
    )

    mock_response = MagicMock()
    mock_response.to_df.return_value = mock_df
    mock_obb.equity.price.quote.return_value = mock_response

    df_result = openbb_toolkit.get_stock_quote('AAPL')
    assert isinstance(df_result, pd.DataFrame)
    assert not df_result.empty
    assert df_result.iloc[0]['symbol'] == 'AAPL'
    assert df_result.iloc[0]['name'] == 'Apple Inc.'
    assert df_result.iloc[0]['bid'] == 245.17

    mock_obb.equity.price.quote.assert_called_with(symbol='AAPL', source='iex')


def test_get_stock_quote_error(openbb_toolkit, mock_obb):
    """Test stock quote error handling."""
    mock_obb.equity.price.quote.side_effect = Exception('API Error')

    empty_df = pd.DataFrame(columns=['symbol', 'name', 'price'])
    mock_response = MagicMock()
    mock_response.to_df.return_value = empty_df

    df_result = openbb_toolkit.get_stock_quote('INVALID')
    assert isinstance(df_result, pd.DataFrame)
    assert df_result.empty


def test_screen_market_success(openbb_toolkit, mock_obb):
    """Test successful market screening."""
    mock_df = pd.DataFrame(
        {
            'symbol': ['AAPL', 'MSFT', 'NVDA'],
            'name': [
                'Apple Inc.',
                'Microsoft Corporation',
                'NVIDIA Corporation',
            ],
            'market_cap': [3707148438420, 3309265088000, 3388681300000],
            'is_etf': [False, False, False],
            'actively_trading': [True, True, True],
            'isFund': [False, False, False],
        }
    )

    mock_response = MagicMock()
    mock_response.to_df.return_value = mock_df
    mock_obb.equity.screener.screen.return_value = mock_response

    df_result = openbb_toolkit.screen_market(
        sector='technology', market_cap_min=100000000000, provider='fmp'
    )

    assert isinstance(df_result, pd.DataFrame)
    assert not df_result.empty
    assert len(df_result) == 3
    assert all(
        col in df_result.columns for col in ['symbol', 'name', 'market_cap']
    )
    assert all(df_result['market_cap'] >= 100000000000)

    mock_obb.equity.screener.screen.assert_called_with(
        sector='technology', market_cap_min=100000000000, provider='fmp'
    )


def test_screen_market_error(openbb_toolkit, mock_obb):
    """Test market screening error handling."""
    mock_obb.equity.screener.screen.side_effect = Exception('API Error')

    empty_df = pd.DataFrame(columns=['symbol', 'name', 'market_cap'])
    mock_response = MagicMock()
    mock_response.to_df.return_value = empty_df

    df_result = openbb_toolkit.screen_market(sector='invalid')
    assert isinstance(df_result, pd.DataFrame)
    assert df_result.empty


def test_get_income_statement_success(openbb_toolkit, mock_obb):
    """Test successful income statement retrieval."""
    mock_df = pd.DataFrame(
        {
            'period_ending': ['2024-06-30', '2023-06-30'],
            'fiscal_period': ['FY', 'FY'],
            'revenue': [245122000000.0, 211915000000.0],
            'operating_income': [109433000000.0, 88523000000.0],
            'net_income': [88136000000.0, 72361000000.0],
        }
    )

    mock_response = MagicMock()
    mock_response.to_df.return_value = mock_df
    mock_obb.equity.fundamental.income.return_value = mock_response

    df_result = openbb_toolkit.get_income_statement(
        symbol='MSFT', period='annual', limit=2
    )

    assert isinstance(df_result, pd.DataFrame)
    assert not df_result.empty
    assert len(df_result) == 2
    assert all(
        col in df_result.columns
        for col in ['revenue', 'operating_income', 'net_income']
    )

    mock_obb.equity.fundamental.income.assert_called_with(
        symbol='MSFT', period='annual', provider='fmp', limit=2
    )
