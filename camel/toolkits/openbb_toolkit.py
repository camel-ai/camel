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
from typing import Any, Dict, List, Literal, Optional, Union

import pandas as pd

from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.utils import dependencies_required


class OpenBBToolkit(BaseToolkit):
    """OpenBB Platform toolkit for accessing financial data and analysis.

    This toolkit provides a comprehensive interface to the OpenBB Platform,
    offering access to financial market data, analysis tools, and research
    capabilities.

    The toolkit requires a Personal Access Token (PAT) from OpenBB Platform,
    which can be obtained at https://my.openbb.co/app/sdk.

    Additional data provider API keys can be configured for enhanced access:
        - FMP (Financial Modeling Prep)
        - Polygon.io
        - FRED (Federal Reserve Economic Data)

    Environment Variables:
        OPENBB_PAT: OpenBB Platform Personal Access Token
        FMP_API_KEY: Financial Modeling Prep API key
        POLYGON_API_KEY: Polygon.io API key
        FRED_API_KEY: FRED API key

    Example:
        >>> toolkit = OpenBBToolkit()
        >>> df = toolkit.get_stock_quote("AAPL")
        >>> print(df)
    """

    @dependencies_required("openbb")
    def __init__(self) -> None:
        """Initialize the OpenBBToolkit.

        This method sets up the OpenBB client and initializes the OpenBB
        Hub account system.
        """
        from openbb import obb

        self.client = obb
        self._init_api_keys(silent=True)

    def _init_api_keys(self, silent: bool = False) -> None:
        """Initialize API keys from environment variables.

        Args:
            silent (bool): If True, suppress error messages.
                Defaults to False.
        """
        pat = os.getenv("OPENBB_PAT")
        if not pat:
            pat = "dummy_key"

        try:
            self.client.account.login(pat=pat)

            provider_keys = {
                "POLYGON_API_KEY": (
                    "polygon_api_key",
                    "https://polygon.io",
                ),
                "FRED_API_KEY": (
                    "fred_api_key",
                    "https://fred.stlouisfed.org",
                ),
                "FMP_API_KEY": (
                    "fmp_api_key",
                    "https://financialmodelingprep.com",
                ),
            }

            for env_var, (key_name, url) in provider_keys.items():
                api_key = os.getenv(env_var)
                if api_key:
                    setattr(self.client.user.credentials, key_name, api_key)
                elif not silent:
                    provider = key_name.split('_')[0].upper()
                    print(f"{env_var} not found in environment variables.")
                    print(f"Some {provider} data may be unavailable.")
                    print(f"Get an API key at {url}")
                    print(f"Then set it with: export {env_var}='your-key'")

        except Exception as e:
            if not silent:
                print(f"Failed to initialize OpenBB client: {e!s}")
                if "Session not found" in str(e):
                    msg = "Please make sure you have a valid "
                    msg += "Personal Access Token (PAT)"
                    print(msg)
                    print("Get one at https://my.openbb.co/app/sdk")
            raise

    def search_equity(
        self,
        query: str,
        provider: Literal["nasdaq", "sec"] = "nasdaq",
        return_type: Literal["df", "raw"] = "df",
    ) -> Union[pd.DataFrame, Dict]:
        """Search for equity symbols and company information.

        Args:
            query (str): Search query (company name or symbol)
            provider (Literal["nasdaq", "sec"]): Data provider
            return_type (Literal["df", "raw"]): Return format

        Returns:
            Union[pd.DataFrame, Dict]: Search results
        """
        data = self.client.equity.search(query, provider=provider)
        return data.to_df() if return_type == "df" else data.results

    def search_etf(
        self,
        query: str,
        provider: str = "tmx",
        return_type: Literal["df", "raw"] = "df",
    ) -> Union[pd.DataFrame, Dict]:
        """Search for ETF information.

        Args:
            query (str): Search query (ETF name or symbol)
            provider (str): Data provider
            return_type (Literal["df", "raw"]): Return format

        Returns:
            Union[pd.DataFrame, Dict]: Search results
        """
        data = self.client.etf.search(query, provider=provider)
        return data.to_df() if return_type == "df" else data.results

    def search_index(
        self,
        query: str,
        provider: str = "cboe",
        return_type: Literal["df", "raw"] = "df",
    ) -> Union[pd.DataFrame, Dict]:
        """Search for market indices.

        Args:
            query (str): Search query
            provider (str): Data provider
            return_type (Literal["df", "raw"]): Return format

        Returns:
            Union[pd.DataFrame, Dict]: Index search results
        """
        data = self.client.index.search(query, provider=provider)
        return data.to_df() if return_type == "df" else data.results

    def search_institution(
        self, query: str, return_type: Literal["df", "raw"] = "df"
    ) -> Union[pd.DataFrame, Dict]:
        """Search for financial institutions in SEC database.

        Args:
            query: Institution name to search
            return_type: Return format

        Returns:
            Institution search results with CIK
        """
        data = self.client.regulators.sec.institutions_search(query)
        return data.to_df() if return_type == "df" else data.results

    def search_filings(
        self,
        identifier: str,
        filing_type: Optional[str] = None,
        provider: str = "sec",
        return_type: Literal["df", "raw"] = "df",
    ) -> Union[pd.DataFrame, Dict]:
        """Search for SEC filings.

        Args:
            identifier: CIK number or ticker symbol
            filing_type: Filing type (e.g., "10-K", "4")
            provider: Data provider
            return_type: Return format

        Returns:
            Filing search results
        """
        data = self.client.equity.fundamental.filings(
            identifier, type=filing_type, provider=provider
        )
        return data.to_df() if return_type == "df" else data.results

    def screen_market(
        self,
        country: Optional[str] = None,
        exchange: Optional[str] = None,
        sector: Optional[str] = None,
        industry: Optional[str] = None,
        market_cap_min: Optional[float] = None,
        market_cap_max: Optional[float] = None,
        beta_min: Optional[float] = None,
        beta_max: Optional[float] = None,
        provider: str = "fmp",
        return_type: Literal["df", "raw"] = "df",
    ) -> Union[pd.DataFrame, Dict]:
        """Screen markets based on various criteria.

        Args:
            country (Optional[str]): Country filter
            exchange (Optional[str]): Exchange filter
            sector (Optional[str]): Sector filter
            industry (Optional[str]): Industry filter
            market_cap_min (Optional[float]): Min market cap
            market_cap_max (Optional[float]): Max market cap
            beta_min (Optional[float]): Min beta value
            beta_max (Optional[float]): Max beta value
            provider (str): Data provider
            return_type (Literal["df", "raw"]): Return format

        Returns:
            Union[pd.DataFrame, Dict]: Screener results
        """
        try:
            params = {
                k: v
                for k, v in {
                    'country': country,
                    'exchange': exchange,
                    'sector': sector,
                    'industry': industry,
                    'market_cap_min': market_cap_min,
                    'market_cap_max': market_cap_max,
                    'beta_min': beta_min,
                    'beta_max': beta_max,
                }.items()
                if v is not None
            }

            data = self.client.equity.screener.screen(
                provider=provider, **params
            )

            if return_type == "df":
                return data.to_df()
            return data.results
        except Exception:
            if return_type == "df":
                return pd.DataFrame(
                    columns=[
                        'symbol',
                        'name',
                        'market_cap',
                        'sector',
                        'industry',
                    ]
                )
            return {}

    def get_available_indices(
        self,
        provider: str = "yfinance",
        return_type: Literal["df", "raw"] = "df",
    ) -> Union[pd.DataFrame, Dict]:
        """Get list of available market indices.

        Args:
            provider (str): Data provider
            return_type (Literal["df", "raw"]): Return format

        Returns:
            Union[pd.DataFrame, Dict]: Available indices with their symbols
        """
        data = self.client.index.available(provider=provider)
        return data.to_df() if return_type == "df" else data.results

    def get_stock_quote(
        self,
        symbol: str,
        source: str = "iex",
        return_type: Literal["df", "raw"] = "df",
    ) -> Union[pd.DataFrame, Dict]:
        """Get current stock quote for a given symbol.

        Args:
            symbol: Stock symbol (e.g., 'AAPL' for Apple Inc.)
            source: Data source ('iex', 'bats', 'bats_delayed', 'utp_delayed',
                   'cta_a_delayed', 'cta_b_delayed', 'intrinio_mx',
                   'intrinio_mx_plus', 'delayed_sip')
            return_type: Return format ('df' or 'raw')

        Returns:
            Stock quote data in requested format
        """
        try:
            data = self.client.equity.price.quote(symbol=symbol, source=source)
            return data.to_df() if return_type == "df" else data.results
        except Exception as e:
            msg = f"Failed to get stock quote for {symbol}: {e}"
            print(msg)
            return pd.DataFrame() if return_type == "df" else {}

    def get_historical_data(
        self,
        symbol: str,
        asset_type: Literal[
            "equity", "index", "currency", "crypto", "future", "option"
        ] = "equity",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        interval: Literal["1m", "1h", "1d", "1W", "1M"] = "1d",
        provider: Optional[str] = None,
        return_type: Literal["df", "raw"] = "df",
    ) -> Union[pd.DataFrame, Dict]:
        """Get historical price data for various financial instruments.

        Args:
            symbol (str): Symbol to get data for
            asset_type (Literal): Type of asset
            start_date (Optional[str]): Start date
            end_date (Optional[str]): End date
            interval (Literal): Data interval
            provider (Optional[str]): Data provider
            return_type (Literal): Return format

        Returns:
            Union[pd.DataFrame, Dict]: Historical price data
        """
        if provider is None:
            provider_map = {
                "equity": "yfinance",
                "index": "cboe",
                "currency": "polygon",
                "crypto": "polygon",
                "future": "fmp",
                "option": "polygon",
            }
            provider = provider_map[asset_type]

        formatted_symbol = self._format_symbol(symbol, asset_type, provider)

        if asset_type == "equity":
            data = self.client.equity.price.historical(
                symbol=formatted_symbol,
                start_date=start_date,
                end_date=end_date,
                interval=interval,
                provider=provider,
            )
        elif asset_type == "index":
            data = self.client.index.price.historical(
                symbol=formatted_symbol,
                start_date=start_date,
                end_date=end_date,
                interval=interval,
                provider=provider,
            )
        elif asset_type == "currency":
            data = self.client.currency.price.historical(
                symbol=formatted_symbol,
                start_date=start_date,
                end_date=end_date,
                interval=interval,
                provider=provider,
            )
        elif asset_type == "crypto":
            data = self.client.crypto.price.historical(
                symbol=formatted_symbol,
                start_date=start_date,
                end_date=end_date,
                interval=interval,
                provider=provider,
            )
        else:
            data = self.client.equity.price.historical(
                symbol=formatted_symbol,
                start_date=start_date,
                end_date=end_date,
                interval=interval,
                provider=provider,
            )

        return data.to_df() if return_type == "df" else data.results

    def _format_symbol(
        self, symbol: str, asset_type: str, provider: str
    ) -> str:
        """Format symbol based on asset type and provider requirements.

        Args:
            symbol (str): Original symbol
            asset_type (str): Type of asset
            provider (str): Data provider

        Returns:
            str: Formatted symbol
        """
        base_symbol = symbol.replace("=X", "").replace("=F", "")
        base_symbol = (
            base_symbol.replace("^", "")
            .replace("O:", "")
            .replace("C:", "")
            .replace("X:", "")
        )

        if provider == "polygon":
            if asset_type == "currency":
                return f"C:{base_symbol}"
            elif asset_type == "crypto":
                return f"X:{base_symbol}"
            elif asset_type == "option":
                return f"O:{base_symbol}"
            return base_symbol
        elif provider == "yfinance":
            if asset_type == "currency":
                return f"{base_symbol}=X"
            elif asset_type == "future":
                return f"{base_symbol}=F"
            elif asset_type == "index":
                return f"^{base_symbol}"
            return base_symbol

        return base_symbol

    def get_company_fundamentals(
        self,
        symbol: str,
        statement: Literal["balance", "income", "cash"] = "balance",
        provider: str = "polygon",
        return_type: Literal["df", "raw"] = "df",
    ) -> Union[pd.DataFrame, Dict]:
        """Get company fundamental financial statements.

        Args:
            symbol (str): Company symbol
            statement (Literal): Statement type
            provider (str): Data provider
            return_type (Literal): Return format

        Returns:
            Union[pd.DataFrame, Dict]: Financial statement data
        """
        if statement == "balance":
            data = self.client.equity.fundamentals.balance_sheet(
                symbol=symbol, provider=provider
            )
        elif statement == "income":
            data = self.client.equity.fundamentals.income_statement(
                symbol=symbol, provider=provider
            )
        else:
            data = self.client.equity.fundamentals.cash_flow(
                symbol=symbol, provider=provider
            )

        if return_type == "df":
            return data.to_df()
        return data.results

    def get_market_data(
        self,
        market_type: Literal["indices", "futures", "bonds"] = "indices",
        symbol: Optional[str] = None,
        provider: str = "yfinance",
        return_type: Literal["df", "raw"] = "df",
    ) -> Union[pd.DataFrame, Dict]:
        """Get market data for various instruments.

        Args:
            market_type: Type of market data to retrieve
            symbol: Specific symbol to query
            provider: Data provider
            return_type: Return format

        Returns:
            Market data or available symbols
        """
        try:
            if market_type == "indices":
                method = self.client.indices.get_indices
            elif market_type == "futures":
                method = self.client.futures.get_futures
            else:
                method = self.client.bonds.get_bonds

            data = method(symbol, provider) if symbol else method(provider)
            return data.to_df() if return_type == "df" else data.results
        except Exception as e:
            msg = f"Failed to get {market_type} data: {e!s}"
            print(msg)
            return pd.DataFrame() if return_type == "df" else {}

    def get_earnings_calendar(
        self,
        start_date: str,
        end_date: str,
        provider: str = "fmp",
        min_market_cap: Optional[float] = None,
        return_type: Literal["df", "raw"] = "df",
    ) -> Union[pd.DataFrame, Dict]:
        """Get earnings calendar events.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            provider: Data provider
            min_market_cap: Min market cap filter
            return_type: Return format

        Returns:
            Earnings calendar events
        """
        try:
            params = {
                "start_date": start_date,
                "end_date": end_date,
                "provider": provider,
            }
            if min_market_cap:
                params["min_market_cap"] = min_market_cap

            data = self.client.calendar.earnings(**params)
            return data.to_df() if return_type == "df" else data.results
        except Exception as e:
            msg = f"Failed to get earnings calendar: {e!s}"
            print(msg)
            return pd.DataFrame() if return_type == "df" else {}

    def get_dividend_calendar(
        self,
        start_date: str,
        end_date: str,
        provider: str = "nasdaq",
        calculate_yield: bool = True,
        return_type: Literal["df", "raw"] = "df",
    ) -> Union[pd.DataFrame, Dict]:
        """Get dividend calendar events.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            provider: Data provider
            calculate_yield: Calculate div yield
            return_type: Return format

        Returns:
            Dividend calendar events
        """
        try:
            data = self.client.equity.calendar.dividend(
                provider=provider, start_date=start_date, end_date=end_date
            )

            if return_type == "raw":
                return data.results

            df = data.to_df().drop_duplicates(subset="symbol")

            if calculate_yield and not df.empty:
                symbols = df.index.tolist()
                prices = (
                    self.client.equity.price.quote(symbols, provider="fmp")
                    .to_df()
                    .reset_index()
                    .set_index("symbol")["price"]
                )
                df["price"] = prices
                if "annualized_amount" in df.columns:
                    df["yield"] = round(
                        (df["annualized_amount"] / df["price"]) * 100, 4
                    )
                else:
                    df["yield"] = round(
                        (df["amount"] * 4 / df["price"]) * 100, 4
                    )

            return df
        except Exception as e:
            msg = f"Failed to get dividend calendar: {e!s}"
            print(msg)
            return pd.DataFrame() if return_type == "df" else {}

    def get_ipo_calendar(
        self,
        status: Literal["upcoming", "priced", "withdrawn"] = "upcoming",
        provider: str = "nasdaq",
        is_spo: bool = False,
        min_offer_amount: Optional[float] = None,
        return_type: Literal["df", "raw"] = "df",
    ) -> Union[pd.DataFrame, Dict]:
        """Get IPO/SPO calendar events.

        Args:
            status: IPO status filter
            provider: Data provider
            is_spo: Include secondary public offerings
            min_offer_amount: Minimum offer amount filter
            return_type: Return format

        Returns:
            IPO/SPO calendar events
        """
        try:
            data = self.client.equity.calendar.ipo(
                provider=provider, status=status, is_spo=is_spo
            )

            if return_type == "raw":
                return data.results

            df = data.to_df()
            if min_offer_amount:
                df = df[df["offer_amount"] >= min_offer_amount]
            return df
        except Exception as e:
            msg = f"Failed to get IPO calendar: {e!s}"
            print(msg)
            return pd.DataFrame() if return_type == "df" else {}

    def get_available_indicators(
        self,
        provider: str = "econdb",
        return_type: Literal["df", "raw"] = "df",
    ) -> Union[pd.DataFrame, Dict]:
        """Get list of available economic indicators.

        Args:
            provider: Data provider
            return_type: Return format

        Returns:
            Available indicators with metadata
        """
        data = self.client.economy.available_indicators(provider=provider)
        return data.to_df() if return_type == "df" else data.results

    def get_indicator_metadata(
        self,
        symbol: str,
        country: Optional[str] = None,
        provider: str = "econdb",
    ) -> Dict:
        """Get detailed metadata for an economic indicator.

        Args:
            symbol: The indicator symbol
            country: Country code
            provider: Data provider

        Returns:
            Indicator metadata including frequency, units, scale, etc.
        """
        data = self.client.economy.indicators(
            symbol=symbol, country=country, provider=provider
        )

        if not data.extra or "results_metadata" not in data.extra:
            return {}

        metadata = data.extra["results_metadata"]
        return next(iter(metadata.values())) if metadata else {}

    def get_tools(self) -> List[FunctionTool]:
        """Returns a list of available OpenBB financial tools.

        Returns:
            List[FunctionTool]: List of available tools
        """
        return [
            FunctionTool(
                func=self.search_equity,
            ),
            FunctionTool(
                func=self.search_etf,
            ),
            FunctionTool(
                func=self.search_index,
            ),
            FunctionTool(
                func=self.search_institution,
            ),
            FunctionTool(
                func=self.search_filings,
            ),
            FunctionTool(
                func=self.screen_market,
            ),
            FunctionTool(
                func=self.get_available_indices,
            ),
            FunctionTool(
                func=self.get_stock_quote,
            ),
            FunctionTool(
                func=self.get_historical_data,
            ),
            FunctionTool(
                func=self.get_balance_sheet,
            ),
            FunctionTool(
                func=self.get_income_statement,
            ),
            FunctionTool(
                func=self.get_cash_flow,
            ),
            FunctionTool(
                func=self.get_financial_ratios,
            ),
            FunctionTool(
                func=self.get_economic_indicators,
            ),
        ]

    def get_balance_sheet(
        self,
        symbol: str,
        period: Literal["annual", "quarter"] = "annual",
        provider: str = "fmp",
        limit: int = 5,
        return_type: Literal["df", "raw"] = "df",
    ) -> Union[pd.DataFrame, Dict]:
        """Get company balance sheet data.

        Args:
            symbol: Company ticker symbol
            period: Data frequency
            provider: Data provider
            limit: Number of periods to return
            return_type: Return format

        Returns:
            Balance sheet data
        """
        data = self.client.equity.fundamental.balance(
            symbol=symbol, provider=provider, period=period, limit=limit
        )
        return data.to_df() if return_type == "df" else data.results

    def get_income_statement(
        self,
        symbol: str,
        period: Literal["annual", "quarter"] = "annual",
        provider: str = "fmp",
        limit: int = 5,
        return_type: Literal["df", "raw"] = "df",
    ) -> Union[pd.DataFrame, Dict]:
        """Get company income statement data.

        Args:
            symbol: Company ticker symbol
            period: Data frequency
            provider: Data provider
            limit: Number of periods to return
            return_type: Return format

        Returns:
            Income statement data
        """
        data = self.client.equity.fundamental.income(
            symbol=symbol, provider=provider, period=period, limit=limit
        )
        return data.to_df() if return_type == "df" else data.results

    def get_cash_flow(
        self,
        symbol: str,
        period: Literal["annual", "quarter"] = "annual",
        provider: str = "fmp",
        limit: int = 5,
        return_type: Literal["df", "raw"] = "df",
    ) -> Union[pd.DataFrame, Dict]:
        """Get company cash flow statement data.

        Args:
            symbol: Company ticker symbol
            period: Data frequency
            provider: Data provider
            limit: Number of periods to return
            return_type: Return format

        Returns:
            Cash flow statement data
        """
        data = self.client.equity.fundamental.cash(
            symbol=symbol, provider=provider, period=period, limit=limit
        )
        return data.to_df() if return_type == "df" else data.results

    def get_financial_ratios(
        self,
        symbol: str,
        period: Literal["annual", "quarter"] = "annual",
        provider: str = "fmp",
        limit: int = 5,
        return_type: Literal["df", "raw"] = "df",
    ) -> Union[pd.DataFrame, Dict]:
        """Get company financial ratios and metrics.

        Args:
            symbol: Company ticker symbol
            period: Data frequency
            provider: Data provider
            limit: Number of periods to return
            return_type: Return format

        Returns:
            Financial ratios data
        """
        data = self.client.equity.fundamental.ratios(
            symbol=symbol, provider=provider, period=period, limit=limit
        )
        return data.to_df() if return_type == "df" else data.results

    def get_financial_statements(
        self,
        symbol: str,
        statement_type: str = "balance",
        period: str = "annual",
        last_n: int = 5,
        source: str = "default",
    ) -> Dict[str, Any]:
        """Get company financial statements.

        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            statement_type: Type of statement ('balance', 'income', 'cash')
            period: Report period ('annual' or 'quarterly')
            last_n: Number of periods to return
            source: Data source provider

        Returns:
            Dict containing financial statement data
        """
        try:
            if statement_type == "balance":
                method = self.client.stocks.fundamentals.balance
            elif statement_type == "income":
                method = self.client.stocks.fundamentals.income
            elif statement_type == "cash":
                method = self.client.stocks.fundamentals.cash
            else:
                msg = (
                    "Invalid statement type. "
                    "Use 'balance', 'income', or 'cash'"
                )
                raise ValueError(msg)

            return method(symbol, period, last_n, source)
        except Exception as e:
            msg = f"Failed to get financial statements for {symbol}: {e!s}"
            print(msg)
            return {}

    def search_financial_attributes(
        self, keyword: str, return_type: Literal["df", "raw"] = "df"
    ) -> Union[pd.DataFrame, Dict]:
        """Search for available financial attributes/metrics.

        Args:
            keyword: Keyword to search for
            return_type: Return format

        Returns:
            Search results for financial attributes
        """
        data = self.client.equity.fundamental.search_attributes(keyword)
        return data.to_df() if return_type == "df" else data.results

    def get_historical_attribute(
        self,
        symbol: str,
        tag: str,
        frequency: Literal["quarterly", "annual"] = "quarterly",
        provider: str = "intrinio",
        return_type: Literal["df", "raw"] = "df",
    ) -> Union[pd.DataFrame, Dict]:
        """Get historical values for a specific financial attribute.

        Args:
            symbol: Company ticker symbol
            tag: Financial attribute tag
            frequency: Data frequency
            provider: Data provider
            return_type: Return format

        Returns:
            Historical attribute data
        """
        data = self.client.equity.fundamental.historical_attributes(
            symbol=symbol, tag=tag, frequency=frequency, provider=provider
        )
        return data.to_df() if return_type == "df" else data.results

    def get_economic_calendar(
        self,
        start_date: str,
        end_date: str,
        provider: Literal["fmp", "nasdaq", "tradingeconomics"] = "fmp",
        convert_timezone: bool = True,
        return_type: Literal["df", "raw"] = "df",
    ) -> Union[pd.DataFrame, Dict]:
        """Get economic calendar events.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            provider: Data provider
            convert_timezone: Convert timestamps to US/Eastern timezone
            return_type: Return format

        Returns:
            Economic calendar events
        """
        data = self.client.economy.calendar(
            provider=provider, start_date=start_date, end_date=end_date
        )

        if return_type == "raw":
            return data.results

        df = data.to_df()
        if convert_timezone and provider == "fmp":
            from datetime import time

            df.index = df.index.map(
                lambda dt: dt.tz_localize("UTC").tz_convert("America/New_York")
                if dt.time() != time(0, 0, 0)
                else dt.tz_localize("America/New_York")
            )
        return df

    def get_economic_indicators(
        self,
        country: Optional[str] = None,
        category: Optional[str] = None,
        return_type: Literal["df", "raw"] = "df",
    ) -> Union[pd.DataFrame, Dict]:
        """Get available economic indicators.

        Args:
            country: Filter by country name
            category: Filter by indicator category
            return_type: Return format

        Returns:
            Economic indicators data
        """
        try:
            params = {}
            if country:
                params["country"] = country
            if category:
                params["category"] = category

            data = self.client.economy.available_indicators(**params)
            if not isinstance(data, pd.DataFrame) or data.empty:
                msg = "No indicators found. Check parameters and try again."
                print(msg)
                return pd.DataFrame() if return_type == "df" else {}
            return data.to_df() if return_type == "df" else data.results
        except Exception as e:
            msg = "Failed to get indicators: {}"
            print(msg.format(str(e)))
            return pd.DataFrame() if return_type == "df" else {}

    def get_market_movers(
        self,
        category: Literal["gainers", "losers", "active"] = "gainers",
        start_date: str = "1d",
        end_date: str = "1d",
        limit: int = 25,
        source: str = "yf",
        return_type: Literal["df", "raw"] = "df",
    ) -> Union[pd.DataFrame, Dict]:
        """Get market movers for a given category.

        Args:
            category: Market movers category
            start_date: Start date
            end_date: End date
            limit: Number of movers to return
            source: Data source
            return_type: Return format

        Returns:
            Market movers data
        """
        methods = {
            "gainers": self.client.stocks.movers.gainers,
            "losers": self.client.stocks.movers.losers,
            "active": self.client.stocks.movers.active,
        }

        if category not in methods:
            msg = "Category must be 'gainers', 'losers', or 'active'."
            raise ValueError(msg)
        return methods[category](source)
