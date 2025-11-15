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

import logging
from typing import List, Literal, Optional

from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.utils import (
    MCPServer,
    api_keys_required,
    dependencies_required,
)


@MCPServer()
class OpenBBToolkit(BaseToolkit):
    r"""A toolkit for accessing financial data and analysis through OpenBB
    Platform.

    This toolkit provides methods for retrieving and analyzing financial market
    data, including stocks, ETFs, cryptocurrencies, economic indicators, and
    more through the OpenBB Platform SDK. For credential configuration, please
    refer to the OpenBB documentation
    https://my.openbb.co/app/platform/credentials .
    """

    @dependencies_required("openbb")
    @api_keys_required(
        [
            (None, "OPENBB_TOKEN"),
        ]
    )
    def __init__(self, timeout: Optional[float] = None) -> None:
        r"""Initialize the OpenBBToolkit.

        This method sets up the OpenBB client and initializes the OpenBB
        Hub account system.
        """
        super().__init__(timeout=timeout)
        import os

        from openbb import obb  # type: ignore[import-not-found]

        self.client = obb
        # Initialize OpenBB Hub account with access token
        token = os.getenv("OPENBB_TOKEN")
        self.client.account.login(pat=token)  # type: ignore[union-attr]

    def _handle_api_error(
        self,
        error: Exception,
        operation: str,
        log_level: str = "warning",
        **format_args,
    ) -> List:
        r"""Handle API operation errors consistently.

        Args:
            error (Exception): The caught exception.
            operation (str): Description of the failed operation
                (e.g., "get_historical_data").
            log_level (str): Logging level to use ("warning" or "error").
            format_args: Additional format arguments for the error message  .

        Returns:
            List: List with error message.
        """
        logger = logging.getLogger(__name__)
        log_func = getattr(logger, log_level)

        error_msg = f"Failed to {operation}"
        if format_args:
            error_msg += ": " + ", ".join(
                f"{k}={v}" for k, v in format_args.items()
            )
        error_msg += f". Error: {error!s}"

        log_func(error_msg)
        return [error_msg]

    def search_equity(
        self,
        query: str,
        provider: Literal["intrinio", "sec"] = "sec",
    ) -> List:
        r"""Search for equity symbols and company information.

        For SEC provider, an empty query ("") returns the complete list of
        companies sorted by market cap.

        Args:
            query (str): Search query (company name or symbol), use "" for
                complete SEC list.
            provider (Literal["intrinio", "sec"]): Data provider. Available
                options:
                - sec: SEC EDGAR Database (sorted by market cap)
                - intrinio: Intrinio Financial Data

        Returns:
            List: Search results.
        """
        try:
            data = self.client.equity.search(query, provider=provider)  # type: ignore[union-attr]

            return data.results

        except Exception as e:
            return self._handle_api_error(
                error=e,
                operation="search equity",
                log_level="warning",
                query=query,
                provider=provider,
            )

    def search_institution(self, query: str) -> List:
        r"""Search for financial institutions in SEC database.

        Args:
            query (str): Institution name to search (e.g., "Berkshire
                Hathaway").

        Returns:
            List: Institution search results.
        """
        try:
            data = self.client.regulators.sec.institutions_search(query)  # type: ignore[union-attr]

            return data.results

        except Exception as e:
            return self._handle_api_error(
                error=e,
                operation="search institution",
                log_level="warning",
                query=query,
            )

    def search_filings(
        self,
        symbol: str,
        provider: Literal["fmp", "intrinio", "sec"] = "sec",
        form_type: Optional[str] = None,
    ) -> List:
        r"""Search for SEC filings by CIK or ticker symbol.

        Args:
            symbol (str): Symbol to get data for (e.g., "MAXD").
            provider (Literal["fmp", "intrinio", "sec"]): Data provider.
                (default: :obj:`sec`)
            form_type (Optional[str]): Filter by form type. Check the data
                provider for available types. Multiple comma separated items
                allowed for provider(s): sec. (default: :obj:`None`)

        Returns:
            List: Filing search results.
        """
        try:
            data = self.client.equity.fundamental.filings(  # type: ignore[union-attr]
                symbol=symbol,
                form_type=form_type,
                provider=provider,
            )

            return data.results

        except Exception as e:
            return self._handle_api_error(
                error=e,
                operation="search filings",
                log_level="warning",
                symbol=symbol,
                form_type=form_type,
                provider=provider,
            )

    def search_etf(
        self,
        query: str,
        provider: Literal["fmp", "intrinio"] = "fmp",
    ) -> List:
        r"""Search for ETF information.

        Args:
            query (str): Search query (ETF name or symbol).
            provider (Literal["fmp", "intrinio"]): Data provider. (default:
                :obj:`fmp`)

        Returns:
            List: ETF search results.
        """
        try:
            data = self.client.etf.search(query, provider=provider)  # type: ignore[union-attr]
            return data.results

        except Exception as e:
            return self._handle_api_error(
                error=e,
                operation="search ETF",
                log_level="warning",
                query=query,
                provider=provider,
            )

    def screen_market(
        self,
        provider: Literal["fmp", "yfinance"] = "fmp",
        country: Optional[str] = None,
        exchange: Optional[str] = None,
        sector: Optional[str] = None,
        industry: Optional[str] = None,
        mktcap_min: Optional[float] = None,
        mktcap_max: Optional[float] = None,
        beta_min: Optional[float] = None,
        beta_max: Optional[float] = None,
    ) -> List:
        r"""Screen stocks based on market and fundamental criteria.

        Args:
            provider (Literal["fmp", "yfinance"]): Data provider.
                (default: :obj:`fmp`)
            country (Optional[str]): Two-letter ISO country code (e.g., 'US',
                'IN', 'CN'). (default: :obj:`None`)
            exchange(Optional[str]) : Stock exchange code (e.g., 'NYSE',
                'AMEX', 'NSE'). (default: :obj:`None`)
            sector (Optional[str]): Market sector (e.g., 'Financial Services',
                'Healthcare). (default: :obj:`None`)
            industry (Optional[str]): Industry within sector (e.g.,
                'Banks—Regional','Drug Manufacturers'). (default: :obj:`None`)
            mktcap_min (Optional[float]): Minimum market cap in USD.
                (default: :obj:`None`)
            mktcap_max (Optional[float]): Maximum market cap in USD.
                (default: :obj:`None`)
            beta_min (Optional[float]): Minimum beta value.
                (default: :obj:`None`)
            beta_max (Optional[float]): Maximum beta value.
                (default: :obj:`None`)

        Returns:
            List: Screened stocks.
        """
        try:
            params = {
                k: v
                for k, v in {
                    'country': country,
                    'exchange': exchange,
                    'sector': sector,
                    'industry': industry,
                    'mktcap_min': mktcap_min,
                    'mktcap_max': mktcap_max,
                    'beta_min': beta_min,
                    'beta_max': beta_max,
                }.items()
                if v is not None
            }

            data = self.client.equity.screener(provider=provider, **params)  # type: ignore[union-attr]

            return data.results

        except Exception as e:
            return self._handle_api_error(
                error=e,
                operation="screen market",
                log_level="warning",
                provider=provider,
            )

    def get_available_indices(
        self,
        provider: Literal['fmp', 'yfinance'] = 'fmp',
    ) -> List:
        r"""Get list of available market indices.

        Args:
            provider (Literal["fmp", "yfinance"]): Data provider.
                (default: :obj:`fmp`)

        Returns:
            List: Available indices.
        """
        try:
            data = self.client.index.available(provider=provider)  # type: ignore[union-attr]

            return data.results

        except Exception as e:
            return self._handle_api_error(
                error=e,
                operation="get available indices",
                log_level="warning",
                provider=provider,
            )

    def get_stock_quote(
        self,
        symbol: str,
        provider: Literal['fmp', 'intrinio', 'yfinance'] = "fmp",
    ) -> List:
        r"""Get current stock quote for a given symbol.

        Args:
            symbol (str): Stock symbol (e.g., 'AAPL' for Apple Inc.)
            provider (Literal["fmp", "intrinio", "yfinance"]): Data source.
                (default: :obj:`fmp`)

        Returns:
            List: Stock quote data in requested format
        """
        try:
            data = self.client.equity.price.quote(  # type: ignore[union-attr]
                symbol=symbol, provider=provider
            )

            return data.results

        except Exception as e:
            return self._handle_api_error(
                error=e,
                operation="get stock quote",
                log_level="error",
                symbol=symbol,
            )

    def get_historical_data(
        self,
        symbol: str,
        provider: Literal['fmp', 'polygon', 'tiingo', 'yfinance'] = "fmp",
        asset_type: Literal[
            "equity",
            "currency",
            "crypto",
        ] = "equity",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        interval: Literal["1m", "5m", "15m", "30m", "1h", "4h", "1d"] = "1d",
    ) -> List:
        r"""Retrieves historical market data from OpenBB Platform providers.

        Args:
            symbol (str): Stock symbol (e.g., 'AAPL' for Apple Inc.).
            provider (Literal["fmp", "polygon", "tiingo", "yfinance"]): Data
                source. (default: :obj:`fmp`)
            asset_type (Literal["equity", "currency", "crypto"]): Asset type.
                (default: :obj:`equity`)
            start_date: Start date in YYYY-MM-DD format. If None, uses
                provider's default lookback. (default: :obj:`None`)
            end_date: End date in YYYY-MM-DD format. If None, uses current
                date. (default: :obj:`None`)
            interval: Data frequency/timeframe. (default: :obj:`1d`)

        Returns:
            List: Historical market data.
        """
        try:
            if asset_type == "currency":
                response = self.client.currency.price.historical(  # type: ignore[union-attr]
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    interval=interval,
                    provider=provider,
                )
            elif asset_type == "crypto":
                response = self.client.crypto.price.historical(  # type: ignore[union-attr]
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    interval=interval,
                    provider=provider,
                )
            else:  # equity
                response = self.client.equity.price.historical(  # type: ignore[union-attr]
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    interval=interval,
                    provider=provider,
                )

            return response.results
        except Exception as e:
            return self._handle_api_error(
                error=e,
                operation="get historical data",
                log_level="error",
                symbol=symbol,
            )

    def get_market_data(
        self,
        category: Literal["gainers", "losers", "active"] = "active",
    ) -> List:
        r"""Get market movers data.

        Args:
            category(Literal["gainers", "losers", "active"]): Type of market
                data. Must be 'gainers', 'losers', or 'active'. (default:
                :obj:`active`)

        Returns:
            List: Market movers data.
        """
        try:
            if category == "gainers":
                response = self.client.equity.discovery.gainers()  # type: ignore[union-attr]
            elif category == "losers":
                response = self.client.equity.discovery.losers()  # type: ignore[union-attr]
            else:  # active
                response = self.client.equity.discovery.active()  # type: ignore[union-attr]

            return response.results

        except Exception as e:
            return self._handle_api_error(
                error=e,
                operation="get market data",
                log_level="error",
                category=category,
            )

    def get_earnings_calendar(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List:
        r"""Get company earnings calendar with filtering and sorting options.

        Args:
            start_date (Optional[str]): Start date in YYYY-MM-DD format.
                (default: :obj:`None`)
            end_date (Optional[str]): End date in YYYY-MM-DD format. (default:
                :obj:`None`)

        Returns:
            List: Earnings calendar.
        """
        try:
            response = self.client.equity.calendar.earnings(  # type: ignore[union-attr]
                start_date=start_date, end_date=end_date
            )

            return response.results

        except Exception as e:
            return self._handle_api_error(
                error=e,
                operation="get earnings calendar",
                log_level="warning",
            )

    def get_dividend_calendar(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List:
        r"""Get dividend calendar with optional yield calculations.

        Args:
            start_date (Optional[str]): Start date in YYYY-MM-DD format.
                (default: :obj:`None`)
            end_date (Optional[str]): End date in YYYY-MM-DD format. (default:
                :obj:`None`)

        Returns:
            List: Dividend calendar.
        """
        try:
            response = self.client.equity.calendar.dividend(  # type: ignore[union-attr]
                start_date=start_date, end_date=end_date
            )

            return response.results

        except Exception as e:
            return self._handle_api_error(
                error=e,
                operation="get dividend calendar",
                log_level="warning",
            )

    def get_ipo_calendar(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List:
        r"""Get IPO/SPO calendar with comprehensive filtering options.

        Args:
            start_date (Optional[str]): Start date in YYYY-MM-DD format.
                (default: :obj:`None`)
            end_date (Optional[str]): End date in YYYY-MM-DD format. (default:
                :obj:`None`)

        Returns:
            List: IPO/SPO calendar.
        """
        try:
            response = self.client.equity.calendar.ipo(  # type: ignore[union-attr]
                start_date=start_date, end_date=end_date
            )

            return response.results

        except Exception as e:
            return self._handle_api_error(
                error=e,
                operation="get IPO calendar",
                log_level="warning",
            )

    def get_available_indicators(
        self,
        provider: Literal["econdb", "imf"] = "econdb",
    ) -> List:
        r"""Get list of available economic indicators.

        Args:
            provider (Literal["econdb", "imf"]): Data provider.
                (default: :obj:`econdb`)

        Returns:
            List: Available indicators.
        """
        try:
            response = self.client.economy.available_indicators(  # type: ignore[union-attr]
                provider=provider
            )

            return response.results

        except Exception as e:
            return self._handle_api_error(
                error=e,
                operation="get available indicators",
                log_level="warning",
                provider=provider,
            )

    def get_indicator_data(
        self,
        symbol: str,
        country: str,
        provider: Literal["econdb", "imf"] = "econdb",
    ) -> List:
        r"""Get detailed metadata for an economic indicator.

        Args:
            symbol (str): Stock symbol (e.g., 'AAPL' for Apple Inc.).
            country (str): Country code (e.g., 'US' for United States).
            provider (Literal["econdb", "imf"]): Data provider. (default:
                :obj:`econdb`)

        Returns:
            List: Indicator data.
        """
        try:
            response = self.client.economy.indicators(  # type: ignore[union-attr]
                country=country, provider=provider, symbol=symbol
            )
            return response.results

        except Exception as e:
            return self._handle_api_error(
                error=e,
                operation="get indicator data",
                log_level="warning",
                symbol=symbol,
                country=country,
                provider=provider,
            )

    def get_financial_metrics(
        self,
        symbol: str,
        provider: Literal['fmp', 'intrinio', 'yfinance'] = "fmp",
        period: Literal["annual", "quarter"] = "annual",
        limit: int = 5,
    ) -> List:
        r"""Get company financial metrics and ratios.

        Args:
            symbol (str): Stock symbol (e.g., 'AAPL' for Apple Inc.).
            provider (Literal["fmp", "intrinio", "yfinance"]): Data source.
                (default: :obj:`fmp`)
            period (Literal["annual", "quarter"]): Reporting period, "annual":
                Annual metrics, "quarter": Quarterly metrics. (default:
                :obj:`annual`)
            limit (int): Number of periods to return. (default: :obj:`5`)

        Returns:
            List: Financial metric.
        """
        try:
            response = self.client.equity.fundamental.metrics(  # type: ignore[union-attr]
                symbol=symbol, period=period, provider=provider, limit=limit
            )

            return response.results

        except Exception as e:
            return self._handle_api_error(
                error=e,
                operation="get financial metrics",
                log_level="warning",
                symbol=symbol,
                provider=provider,
            )

    def get_company_profile(
        self,
        symbol: str,
        provider: Literal["fmp", "intrinio", "yfinance"] = "fmp",
    ) -> List:
        r"""Get company profile information.

        Args:
            symbol (str): Stock symbol (e.g., 'AAPL' for Apple Inc.).
            provider (Literal["fmp", "intrinio", "yfinance"]): Data provider.
                (default: :obj:`fmp`)

        Returns:
            List: Company profile.
        """
        try:
            response = self.client.equity.profile(  # type: ignore[union-attr]
                symbol=symbol, provider=provider
            )

            return response.results

        except Exception as e:
            return self._handle_api_error(
                error=e,
                operation="get company profile",
                log_level="warning",
                symbol=symbol,
                provider=provider,
            )

    def get_financial_statement(
        self,
        symbol: str,
        provider: Literal["fmp", "intrinio", "polygon", "yfinance"] = "fmp",
        statement_type: Literal["balance", "income", "cash"] = "balance",
        period: Literal["annual", "quarter"] = "annual",
        limit: int = 5,
    ) -> List:
        r"""Get company financial statements.

        Access balance sheet, income statement, or cash flow statement data.
        Data availability and field names vary by provider and company type.

        Args:
            symbol (str): Stock symbol (e.g., 'AAPL' for Apple Inc.).
            provider (Literal["fmp", "intrinio", "polygon", "yfinance"]): Data
                provider. (default: :obj:`fmp`)
            statement_type (Literal["balance", "income", "cash"]): Type of
                financial statement, "balance": Balance sheet, "income":
                Income statement, "cash": Cash flow statement. (default:
                :obj:`balance`)
            period (Literal["annual", "quarter"]): Reporting period, "annual":
                Annual reports, "quarter": Quarterly reports. (default:
                :obj:`annual`)
            limit (int): Number of periods to return. (default: :obj:`5`)

        Returns:
            List: Financial statement data.
        """
        try:
            # Map statement type to client endpoint
            endpoint_map = {
                "balance": self.client.equity.fundamental.balance,  # type: ignore[union-attr]
                "income": self.client.equity.fundamental.income,  # type: ignore[union-attr]
                "cash": self.client.equity.fundamental.cash,  # type: ignore[union-attr]
            }

            endpoint = endpoint_map.get(statement_type)
            if not endpoint:
                raise ValueError(f"Invalid statement_type: {statement_type}")

            response = endpoint(
                symbol=symbol, period=period, provider=provider, limit=limit
            )

            return response.results

        except Exception as e:
            return self._handle_api_error(
                error=e,
                operation="get financial statement",
                log_level="warning",
                symbol=symbol,
                provider=provider,
            )

    def get_financial_attributes(
        self,
        symbol: str,
        tag: str,
        frequency: Literal[
            "daily", "weekly", "monthly", "quarterly", "yearly"
        ] = "yearly",
    ) -> List:
        r"""Get historical values for a specific financial attribute.

        Args:
            symbol (str): Stock symbol (e.g., 'AAPL' for Apple Inc.).
            tag (str): Financial attribute tag (use
                search_financial_attributes to find tags).
            frequency (Literal["daily", "weekly", "monthly", "quarterly",
                "yearly"]): Data frequency, "daily", "weekly", "monthly",
                "quarterly", "yearly". (default: :obj:`yearly`)

        Returns:
            List: Historical values.
        """
        try:
            response = self.client.equity.fundamental.historical_attributes(  # type: ignore[union-attr]
                symbol=symbol, tag=tag, frequency=frequency
            )

            return response.results

        except Exception as e:
            return self._handle_api_error(
                error=e,
                operation="get financial attribute",
                log_level="warning",
                symbol=symbol,
                tag=tag,
            )

    def search_financial_attributes(
        self,
        query: str,
    ) -> List:
        r"""Search for available financial attributes/tags.

        Args:
            query (str): Search term (e.g., "marketcap", "revenue", "assets").

        Returns:
            List: Matching attributes.
        """
        try:
            response = self.client.equity.fundamental.search_attributes(  # type: ignore[union-attr]
                query=query
            )

            return response.results

        except Exception as e:
            return self._handle_api_error(
                error=e,
                operation="search financial attributes",
                log_level="warning",
                query=query,
            )

    def get_economic_calendar(
        self,
        provider: Literal["fmp", "tradingeconomics"] = "fmp",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List:
        r"""Get economic calendar events.

        Args:
            provider (Literal["fmp", "tradingeconomics"]): Data provider.
                (default: :obj:`fmp`)
            start_date (Optional[str]): Start date in YYYY-MM-DD format.
                (default: :obj:`None`)
            end_date (Optional[str]): End date in YYYY-MM-DD format. (default:
                :obj:`None`)

        Returns:
            List: Economic calendar.
        """
        try:
            response = self.client.economy.calendar(  # type: ignore[union-attr]
                start_date=start_date, end_date=end_date, provider=provider
            )

            return response.results

        except Exception as e:
            return self._handle_api_error(
                error=e,
                operation="get economic calendar",
                log_level="warning",
                provider=provider,
            )

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of available OpenBB financial tools.

        Returns:
            List[FunctionTool]: List of available tools.
        """
        return [
            FunctionTool(
                func=self.search_equity,
            ),
            FunctionTool(
                func=self.search_etf,
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
                func=self.get_market_data,
            ),
            FunctionTool(
                func=self.get_earnings_calendar,
            ),
            FunctionTool(
                func=self.get_dividend_calendar,
            ),
            FunctionTool(
                func=self.get_ipo_calendar,
            ),
            FunctionTool(
                func=self.get_available_indicators,
            ),
            FunctionTool(
                func=self.get_indicator_data,
            ),
            FunctionTool(
                func=self.get_financial_metrics,
            ),
            FunctionTool(
                func=self.get_company_profile,
            ),
            FunctionTool(
                func=self.get_financial_statement,
            ),
            FunctionTool(
                func=self.get_financial_attributes,
            ),
            FunctionTool(
                func=self.search_financial_attributes,
            ),
            FunctionTool(
                func=self.get_economic_calendar,
            ),
        ]
