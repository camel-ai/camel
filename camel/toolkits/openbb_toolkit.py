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
from typing import Any, Dict, List, Literal, Optional, Union

import pandas as pd

from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.utils import api_keys_required, dependencies_required


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
    def __init__(self) -> None:
        r"""Initialize the OpenBBToolkit.

        This method sets up the OpenBB client and initializes the OpenBB
        Hub account system.
        """
        import os

        from openbb import obb

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
            List: Empty list.
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
        return []

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

    # TODO: Continue refactoring
    def get_earnings_calendar(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        provider: str = "fmp",
        return_type: Literal["df", "raw"] = "raw",
    ) -> List:
        """Get company earnings calendar with filtering and sorting options.

        Note: EPS values are reported in the currency of the exchange listing
        price.
        Use convert_currency=True for USD-normalized comparisons.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            provider: Data provider (default: "fmp")
            filter_estimates: Only include entries with analyst estimates
            (default: False)
            sort_by: Column to sort by (e.g., "eps_consensus",
            "revenue_consensus")
            ascending: Sort order (default: False for descending)
            limit: Maximum number of results to return
            return_type: Return format ('df' for DataFrame, 'raw' for
            dictionary)

        Returns:
            List: Earnings calendar with columns:
                - report_date: Earnings announcement date
                - symbol: Company symbol
                - eps_consensus: Expected EPS
                - actual_eps: Reported EPS (if available)
                - revenue_consensus: Expected revenue
                - actual_revenue: Reported revenue (if available)
                - period_ending: Fiscal period end date
                - reporting_time: Time of day (bmo: before market open,
                                amc: after market close)
                - updated_date: Last update date
                - currency: Listing currency (if available)
        """
        try:
            # Get base calendar data
            params = {"provider": provider}
            if start_date:
                params["start_date"] = start_date
            if end_date:
                params["end_date"] = end_date

            data = self.client.equity.calendar.earnings(**params)  # type: ignore[union-attr]

            return data.results

        except Exception as e:
            return self._handle_api_error(
                error=e,
                operation="get earnings calendar",
                return_type=return_type,
                log_level="warning",
                provider=provider,
            )

    def get_dividend_calendar(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        provider: str = "nasdaq",
        return_type: Literal["df", "raw"] = "raw",
    ) -> List:
        """Get dividend calendar with optional yield calculations.

        Note: Ex-dividend date is when stock begins trading without dividend
        rights.
        T+2 settlement means purchase must occur 2 days before record date for
        eligibility.

        Args:
            start_date: Start date in YYYY-MM-DD format (optional)
            end_date: End date in YYYY-MM-DD format (optional)
            provider: Data provider (default: "nasdaq")
                - nasdaq: US-only data with annualized amounts
                - fmp: Global coverage
            calculate_yield: Add current yield calculations (default: False)
                Requires additional price data query
            sort_by: Column to sort by
            ascending: Sort order (default: False for descending)
            limit: Maximum number of results to return
            return_type: Return format ('df' for DataFrame, 'raw' for
            dictionary)

        Returns:
            List: Dividend calendar with columns:
                - symbol: Company symbol
                - ex_dividend_date: Date stock trades ex-dividend
                - record_date: Date of record for eligibility
                - payment_date: Date dividend is paid
                - amount: Dividend payment amount
                - frequency: Payment frequency (if available)
                - annualized_amount: Annual dividend (Nasdaq only)
                If calculate_yield is True, additional columns:
                - price: Current stock price
                - yield: Annualized dividend yield (%)
        """
        try:
            # Get base calendar data
            params = {"provider": provider}
            if start_date:
                params["start_date"] = start_date
            if end_date:
                params["end_date"] = end_date

            data = self.client.equity.calendar.dividend(**params)  # type: ignore[union-attr]

            return data.results

        except Exception as e:
            return self._handle_api_error(
                error=e,
                operation="get dividend calendar",
                return_type=return_type,
                log_level="warning",
                provider=provider,
            )

    def get_ipo_calendar(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        provider: str = "nasdaq",
        status: Optional[Literal["upcoming", "priced", "withdrawn"]] = None,
        is_spo: bool = False,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        sort_by: Optional[str] = None,
        ascending: bool = False,
        limit: Optional[int] = None,
        return_type: Literal["df", "raw"] = "raw",
    ) -> List:
        """Get IPO/SPO calendar with comprehensive filtering options.

        Note: Data from Nasdaq and Intrinio is US-only, sourced from SEC
        filings.

        Args:
            start_date: Start date in YYYY-MM-DD format (optional)
            end_date: End date in YYYY-MM-DD format (optional)
            provider: Data provider (default: "nasdaq")
                Available: ["nasdaq", "intrinio"]
            status: Filter by offering status:
                - "upcoming": Confirmed future offerings
                - "priced": Completed offerings
                - "withdrawn": Cancelled offerings
            is_spo: Include secondary public offerings (default: False)
                SPOs are existing shares sold by investors
                Only available with Nasdaq provider
            min_amount: Minimum offering amount in USD
                Only available with Intrinio provider
            max_amount: Maximum offering amount in USD
                Only available with Intrinio provider
            sort_by: Column to sort by
            ascending: Sort order (default: False for descending)
            limit: Maximum number of results to return
            return_type: Return format ('df' for DataFrame, 'raw' for
            dictionary)

        Returns:
            List: IPO/SPO calendar with columns:
                Common fields:
                - symbol: Trading symbol (if assigned)
                - name: Company name
                - offer_amount: Total offering value
                - share_count: Number of shares offered
                - share_price: Offering price or range
                Status-specific fields:
                - Upcoming:
                    - expected_price_date: Expected offering date
                    - exchange: Target exchange
                - Priced:
                    - ipo_date: Actual offering date
                    - deal_status: Final status
                - Withdrawn:
                    - withdraw_date: Cancellation date
                    - filed_date: Original filing date
        """
        try:
            # Build parameters dict
            params = {"provider": provider}
            if start_date:
                params["start_date"] = start_date
            if end_date:
                params["end_date"] = end_date
            if status:
                params["status"] = status
            if provider == "nasdaq" and is_spo:
                params["is_spo"] = str(is_spo)
            if provider == "intrinio":
                if min_amount:
                    params["min_amount"] = str(min_amount)
                if max_amount:
                    params["max_amount"] = str(max_amount)

            data = self.client.equity.calendar.ipo(**params)  # type: ignore[union-attr]

            return data.results

        except Exception as e:
            return self._handle_api_error(
                error=e,
                operation="get IPO calendar",
                return_type=return_type,
                log_level="warning",
                provider=provider,
            )

    def get_available_indicators(
        self,
        provider: str = "econdb",
        return_type: Literal["df", "raw"] = "raw",
    ) -> List:
        """Get list of available economic indicators.

        Args:
            provider: Data provider (default: "econdb")
            return_type: Return format ('df' for DataFrame, 'raw' for
            dictionary)

        Returns:
            List: Available indicators with columns:
                - symbol_root: Base indicator symbol
                - symbol: Full indicator symbol with country
                - country: Country name
                - iso: Country ISO code
                - description: Indicator description
                - frequency: Data frequency (D/W/M/Q/Y)
                - currency: Value currency or unit
                - scale: Value scale
                - multiplier: Value multiplier
                - transformation: Applied transformations
                - source: Data source
                - first_date: First available date
                - last_date: Last available date
                - last_insert_timestamp: Last update time
        """
        try:
            data = self.client.economy.available_indicators(provider=provider)  # type: ignore[union-attr]

            return data.results

        except Exception as e:
            return self._handle_api_error(
                error=e,
                operation="get available indicators",
                return_type=return_type,
                log_level="warning",
                provider=provider,
            )

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
        data = self.client.economy.indicators(  # type: ignore[union-attr]
            symbol=symbol, country=country, provider=provider
        )

        if not data.extra or "results_metadata" not in data.extra:
            return {}

        metadata = data.extra["results_metadata"]
        return next(iter(metadata.values())) if metadata else {}

    def get_economic_data(
        self,
        symbols: Union[str, List[str]],
        country: Optional[Union[str, List[str]]] = None,
        transform: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        provider: str = "econdb",
        include_metadata: bool = True,
        return_type: Literal["df", "raw"] = "raw",
    ) -> List:
        r"""Get economic indicators from EconDB.

        Note: Requires API key for full access. Without key, uses temporary
        token
        with limited functionality. Data is provided AS IS without warranty.

        Args:
            symbols: Single indicator symbol or list of symbols (e.g., "GDP",
            ["CPI", "URATE"])
            country: Single country code/name or list (e.g., "US", ["US", "JP",
             "DE"])
            transform: Optional transformation to apply:
                - tpop: Percent change from previous period
                - toya: Percent change from year ago
                - tusd: Values as US dollars
                - tpgp: Values as a percent of GDP
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            provider: Data provider (default: "econdb")
            include_metadata: Include indicator metadata (default: True)
            return_type: Return format ('df' for DataFrame, 'raw' for
            dictionary)

        Returns:
            List: Economic data with columns:
                - date: Observation date
                - symbol_root: Base indicator symbol
                - symbol: Full indicator symbol with country/transform
                - country: Country name
                - value: Indicator value
        """
        try:
            # Handle single string inputs
            if isinstance(symbols, str):
                symbols = [symbols]
            if isinstance(country, str):
                country = [country]

            # Build parameters dict
            params = {"provider": provider}
            if country:
                params["country"] = ", ".join(country)
            if transform:
                params["transform"] = (
                    transform if isinstance(transform, str) else transform[0]
                )  # Ensure string type
            if start_date:
                params["start_date"] = start_date
            if end_date:
                params["end_date"] = end_date

            data = self.client.economy.indicators(symbol=symbols, **params)  # type: ignore[union-attr]

            return data.results

        except Exception as e:
            return self._handle_api_error(
                error=e,
                operation="get economic data",
                return_type=return_type,
                log_level="error",
                symbols=symbols,
                provider=provider,
            )

    def get_economic_indicators(
        self,
        country: Optional[str] = None,
        category: Optional[str] = None,
        return_type: Literal["df", "raw"] = "raw",
    ) -> Union[pd.DataFrame, Dict[str, Any]]:
        """Get available economic indicators.

        Args:
            country: Filter by country name
            category: Filter by indicator category
            return_type: Return format

        Returns:
            Economic indicators data
        """
        try:
            params: Dict[str, Any] = {}
            if country:
                params["country"] = country
            if category:
                params["category"] = category

            data = self.client.economy.available_indicators(**params)  # type: ignore[union-attr]

            return data.results

        except Exception as e:
            return self._handle_api_error(
                error=e,
                operation="get economic indicators",
                return_type=return_type,
                log_level="error",
            )

    def get_market_movers(
        self,
        category: Literal["gainers", "losers", "active"] = "gainers",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None,
        source: str = "yf",
        return_type: Literal["df", "raw"] = "raw",
    ) -> List:
        """Get market movers (gainers, losers, most active) data from various
        sources.

        Args:
            category: Type of market movers to retrieve:
                - 'gainers': Stocks with highest % gain
                - 'losers': Stocks with highest % loss
                - 'active': Most actively traded stocks
            start_date: Start date for historical comparison (YYYY-MM-DD).
                Defaults to None (uses source's default).
            end_date: End date for historical comparison (YYYY-MM-DD).
                Defaults to None (uses source's default).
            limit: Maximum number of stocks to return.
                Defaults to None (uses source's default).
            source: Data source provider. Available options:
                - 'yf': Yahoo Finance
                - 'fmp': Financial Modeling Prep
                - 'av': Alpha Vantage
            return_type: Format for returned data:
                - 'raw': Original JSON response
                - 'df': Pandas DataFrame with columns:
                    [symbol, name, price, change, change_pct, volume]

        Returns:
            List: Market movers data in specified format.
                Empty dict/DataFrame if error occurs.
        """
        methods = {
            "gainers": self.client.equity.discovery.gainers,  # type: ignore[union-attr]
            "losers": self.client.equity.discovery.losers,  # type: ignore[union-attr]
            "active": self.client.equity.discovery.active,  # type: ignore[union-attr]
        }

        if category not in methods:
            msg = "Category must be 'gainers', 'losers', or 'active'."
            raise ValueError(msg)

        try:
            params = {
                "source": source,
                "start_date": start_date,
                "end_date": end_date,
                "limit": limit,
            }
            params = {k: v for k, v in params.items() if v is not None}

            response = methods[category](**params)

            return response.results

        except Exception as e:
            return self._handle_api_error(
                error=e,
                operation="get market movers",
                return_type=return_type,
                log_level="error",
                category=category,
                source=source,
            )

    def get_financial_metrics(
        self,
        symbol: str,
        period: Literal["annual", "quarter"] = "annual",
        provider: str = "fmp",
        limit: int = 5,
        return_type: Literal["df", "raw"] = "raw",
    ) -> List:
        """Get company financial metrics and ratios.

        Provides derived metrics from financial statements, including:
        - Valuation ratios (P/E, P/B, EV/EBITDA)
        - Profitability ratios (ROE, ROA, margins)
        - Liquidity ratios (current ratio, quick ratio)
        - Efficiency ratios (asset turnover, inventory turnover)
        - Per share metrics (EPS, FCF per share)
        - Growth metrics (revenue growth, EPS growth)

        Args:
            symbol: Company ticker symbol
            period: Reporting period:
                - "annual": Annual metrics
                - "quarter": Quarterly metrics
            provider: Data provider (default: "fmp")
            limit: Number of periods to return (default: 5)
            return_type: Return format ('df' for DataFrame, 'raw' for
            dictionary)

        Returns:
            List: Financial metrics with common fields:
                - calendar_year: Reporting year
                - quick_ratio: (Current Assets - Inventory) / Current
                Liabilities
                - current_ratio: Current Assets / Current Liabilities
                - debt_to_equity: Total Debt / Total Equity
                - gross_margin: Gross Profit / Revenue
                - operating_margin: Operating Income / Revenue
                - net_margin: Net Income / Revenue
                - free_cash_flow_yield: FCF per Share / Share Price
                Additional fields vary by provider
        """
        try:
            data = self.client.equity.fundamental.metrics(  # type: ignore[union-attr]
                symbol=symbol, period=period, provider=provider, limit=limit
            )

            return data.results

        except Exception as e:
            return self._handle_api_error(
                error=e,
                operation="get financial metrics",
                return_type=return_type,
                log_level="warning",
                symbol=symbol,
                provider=provider,
            )

    def get_company_profile(
        self,
        symbol: str,
        provider: str = "fmp",
        return_type: Literal["df", "raw"] = "raw",
    ) -> List:
        """Get company profile information.

        Args:
            symbol: Company ticker symbol
            provider: Data provider (default: "fmp")
            return_type: Return format ('df' for DataFrame, 'raw' for
            dictionary)

        Returns:
            List: Company profile with fields:
                - name: Company name
                - sector: Industry sector
                - industry: Specific industry
                - description: Business description
                Additional fields vary by provider
        """
        try:
            data = self.client.equity.profile(symbol=symbol, provider=provider)  # type: ignore[union-attr]

            return data.results

        except Exception as e:
            return self._handle_api_error(
                error=e,
                operation="get company profile",
                return_type=return_type,
                log_level="warning",
                symbol=symbol,
                provider=provider,
            )

    def get_indicator_countries(
        self,
        symbol: str,
        provider: str = "econdb",
        return_type: Literal["df", "raw"] = "raw",
    ) -> Dict:
        """Get list of countries available for a specific indicator.

        Note: Requires API key for full access. Without key, uses temporary
        token
        with limited functionality. You can set the API key via:
            toolkit.client.user.credentials.econdb_api_key = "YOUR_KEY"

        Args:
            symbol: Indicator symbol (e.g., "GDPPC" for GDP per capita)
            provider: Data provider (default: "econdb")
            return_type: Return format ('df' for DataFrame, 'raw' for
            dictionary)

        Returns:
            List: Available countries with columns:
                - country: Country name
                - iso: Two-letter ISO country code
                - description: Indicator description
                - frequency: Data frequency (D/W/M/Q/Y)
        """
        try:
            # Get all available indicators
            data = self.client.economy.available_indicators(provider=provider)  # type: ignore[union-attr]

            # For raw return, filter and format the data
            results = []
            for item in data.results:
                if item.get("symbol_root") == symbol:
                    country_info = {
                        "country": item.get("country"),
                        "iso": item.get("iso"),
                        "description": item.get("description"),
                        "frequency": item.get("frequency"),
                    }
                    if country_info not in results:
                        results.append(country_info)

            return {"results": sorted(results, key=lambda x: x["country"])}

        except Exception as e:
            return self._handle_api_error(
                error=e,
                operation="get indicator countries",
                return_type=return_type,
                log_level="warning",
                symbol=symbol,
                provider=provider,
            )

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of available OpenBB financial tools.

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
                func=self.get_financial_statement,
            ),
            FunctionTool(
                func=self.get_financial_metrics,
            ),
        ]

    def get_financial_statement(
        self,
        symbol: str,
        statement_type: Literal["balance", "income", "cash"] = "balance",
        period: Literal["annual", "quarter"] = "annual",
        provider: str = "fmp",
        limit: int = 5,
        return_type: Literal["df", "raw"] = "raw",
    ) -> List:
        """Get company financial statements.

        Access balance sheet, income statement, or cash flow statement data.
        Data availability and field names vary by provider and company type.

        Args:
            symbol: Company ticker symbol
            statement_type: Type of financial statement:
                - "balance": Balance sheet
                - "income": Income statement
                - "cash": Cash flow statement
            period: Reporting period:
                - "annual": Annual reports
                - "quarter": Quarterly reports
            provider: Data provider (e.g., "fmp", "yfinance", "intrinio",
            "polygon")
            limit: Number of periods to return (default: 5)
                Note: Up to 150 periods (~35 years) available from some
                providers
            return_type: Return format ('df' for DataFrame, 'raw' for
            dictionary)

        Returns:
            List: Financial statement data.
            Note: Field names and dates may vary by provider:
                - Field names use provider-specific terminology
                - Dates may be period start/end or reporting date
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

            data = endpoint(
                symbol=symbol, period=period, provider=provider, limit=limit
            )

            return data.results

        except Exception as e:
            return self._handle_api_error(
                error=e,
                operation="get financial statement",
                return_type=return_type,
                log_level="warning",
                symbol=symbol,
                provider=provider,
            )

    def get_financial_attributes(
        self,
        symbol: str,
        tag: str,
        frequency: Literal["quarterly", "annual"] = "quarterly",
        provider: str = "intrinio",
        return_type: Literal["df", "raw"] = "raw",
    ) -> List:
        """Get historical values for a specific financial attribute.

        Args:
            symbol: Company ticker symbol
            tag: Financial attribute tag (use search_financial_attributes to
            find tags)
            frequency: Data frequency:
                - "quarterly": Quarterly values
                - "annual": Annual values
            provider: Data provider (default: "intrinio")
            return_type: Return format ('df' for DataFrame, 'raw' for
            dictionary)

        Returns:
            List: Historical values for the attribute with
             columns:
                - date: Timestamp for the period
                - value: Attribute value
        """
        try:
            data = self.client.equity.fundamental.historical_attributes(  # type: ignore[union-attr]
                symbol=symbol, tag=tag, frequency=frequency, provider=provider
            )

            return data.results

        except Exception as e:
            return self._handle_api_error(
                error=e,
                operation="get financial attribute",
                return_type=return_type,
                log_level="warning",
                symbol=symbol,
                provider=provider,
            )

    def search_financial_attributes(
        self,
        query: str,
        provider: str = "intrinio",
        return_type: Literal["df", "raw"] = "raw",
    ) -> List:
        """Search for available financial attributes/tags.

        Args:
            query: Search term (e.g., "marketcap", "revenue", "assets")
            provider: Data provider (default: "intrinio")
            return_type: Return format ('df' for DataFrame, 'raw' for
            dictionary)

        Returns:
            List: Matching attributes with columns:
                - id: Unique identifier
                - name: Human-readable name
                - tag: Tag to use with get_financial_attributes
                - statement_code: Related financial statement
                - statement_type: Industry classification
                - parent_name: Parent category
                - sequence: Display order
                - factor: Scaling factor
                - transaction: Transaction type
                - type: Data type
                - unit: Measurement unit
        """
        try:
            data = self.client.equity.fundamental.search_attributes(  # type: ignore[union-attr]
                query=query, provider=provider
            )

            return data.results

        except Exception as e:
            return self._handle_api_error(
                error=e,
                operation="search financial attributes",
                return_type=return_type,
                log_level="warning",
                query=query,
                provider=provider,
            )

    def get_economic_calendar(
        self,
        start_date: str,
        end_date: str,
        provider: Literal["fmp", "nasdaq", "tradingeconomics"] = "fmp",
        convert_timezone: bool = True,
        return_type: Literal["df", "raw"] = "raw",
    ) -> List:
        """Get economic calendar events.

        Note: Do not rely on this calendar for real-time updates. Times posted
        are
        scheduled estimates which may not reflect actual release times.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            provider: Data provider (default: "fmp")
                Available: ["fmp", "nasdaq", "tradingeconomics"]
            convert_timezone: Convert timestamps to US/Eastern (default: True)
                Note: Provider differences:
                - FMP/TradingEconomics: UTC-0
                - Nasdaq: US/Eastern
                - Only TradingEconomics provides TZ-aware timestamps
            return_type: Return format ('df' for DataFrame, 'raw' for
            dictionary)

        Returns:
            List: Economic calendar with columns:
                - date: Event timestamp
                - country: Country code
                - event: Event name/description
                - actual: Actual value if released
                - previous: Previous period value
                - consensus: Expected value
                Additional fields by provider:
                - FMP: importance, currency, change, change_percent
                - Nasdaq: description
                - TradingEconomics: category
        """
        try:
            data = self.client.economy.calendar(  # type: ignore[union-attr]
                start_date=start_date, end_date=end_date, provider=provider
            )

            return data.results

        except Exception as e:
            return self._handle_api_error(
                error=e,
                operation="get economic calendar",
                return_type=return_type,
                log_level="warning",
                provider=provider,
            )

    def get_market_calendar(
        self,
        calendar_type: Literal[
            "earnings", "dividends", "splits", "ipo"
        ] = "earnings",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        provider: str = "fmp",
        return_type: Literal["df", "raw"] = "raw",
    ) -> List:
        """Get market calendar events (earnings, dividends, splits, IPOs).

        Args:
            calendar_type: Type of calendar:
                - "earnings": Earnings announcements
                - "dividends": Dividend schedules
                - "splits": Stock splits
                - "ipo": IPO/SPO offerings
            start_date: Start date in YYYY-MM-DD format (optional)
            end_date: End date in YYYY-MM-DD format (optional)
            provider: Data provider (default: "fmp")
            return_type: Return format ('df' for DataFrame, 'raw' for
            dictionary)

        Returns:
            List: Calendar events with type-specific
            columns:
                Earnings:
                    - date: Announcement date
                    - symbol: Company symbol
                    - eps_estimate: Expected EPS
                    - actual_eps: Reported EPS (if available)
                    - revenue_estimate: Expected revenue
                    - actual_revenue: Reported revenue (if available)
                Dividends:
                    - ex_date: Ex-dividend date
                    - payment_date: Payment date
                    - record_date: Record date
                    - amount: Dividend amount
                    - frequency: Payment frequency
                Splits:
                    - date: Split date
                    - from_factor: Original shares
                    - to_factor: New shares
                IPO:
                    - date: Offering date
                    - exchange: Listing exchange
                    - shares: Shares offered
                    - price_range: Expected price range
                    - price: Final price
        """
        try:
            # Map calendar type to client endpoint
            endpoint_map = {
                "earnings": self.client.equity.calendar.earnings,  # type: ignore[union-attr]
                "dividend": self.client.equity.calendar.dividend,  # type: ignore[union-attr]
                "splits": self.client.equity.calendar.splits,  # type: ignore[union-attr]
                "ipo": self.client.equity.calendar.ipo,  # type: ignore[union-attr]
            }

            endpoint = endpoint_map.get(calendar_type)
            if not endpoint:
                raise ValueError(f"Invalid calendar_type: {calendar_type}")

            # Build parameters dict
            params = {"provider": provider}
            if start_date:
                params["start_date"] = start_date
            if end_date:
                params["end_date"] = end_date

            data = endpoint(**params)

            return data.results

        except Exception as e:
            return self._handle_api_error(
                error=e,
                operation="get market calendar",
                return_type=return_type,
                log_level="warning",
                provider=provider,
            )
