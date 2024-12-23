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
from typing import Any, Dict, List, Literal, Optional, Protocol, Union

import pandas as pd

from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.utils import api_keys_required, dependencies_required


class OpenBBBaseProtocol(Protocol):
    r"""Protocol defining the base interface for OpenBB SDK functionality.
    This protocol specifies the required attributes and methods for interacting
    with the OpenBB Platform SDK.

    Args:
        account (Any): Authentication and account management interface
        user (Any): User settings and credentials management
        equity (Any): Stock market data and analysis interface
        etf (Any): Exchange-Traded Funds data interface
        index (Any): Market indices data interface
        regulators (Any): Regulatory data access interface
        stocks (Any): Stock market operations interface
        calendar (Any): Market events data interface
        economy (Any): Economic indicators interface
        currency (Any): Currency exchange data interface
        crypto (Any): Cryptocurrency data interface
        indices (Any): Market indices interface
        futures (Any): Futures market data interface
        bonds (Any): Bond market data interface
        to_df (Any): Convert query results to DataFrame
        results (Any): Access raw query results
        to_dict (Any): Convert query results to dictionary
    """

    account: Any
    user: Any
    equity: Any
    etf: Any
    index: Any
    regulators: Any
    stocks: Any
    calendar: Any
    economy: Any
    currency: Any
    crypto: Any
    indices: Any
    futures: Any
    bonds: Any
    to_df: Any
    results: Any
    to_dict: Any


class OpenBBClient:
    """Type class for OpenBB client implementation."""

    def __init__(self) -> None:
        """Initialize the OpenBB client type."""
        self.account: Any = None
        self.user: Any = None
        self.equity: Any = None
        self.etf: Any = None
        self.index: Any = None
        self.regulators: Any = None
        self.stocks: Any = None
        self.calendar: Any = None
        self.economy: Any = None
        self.currency: Any = None
        self.crypto: Any = None
        self.indices: Any = None
        self.futures: Any = None
        self.bonds: Any = None
        self.to_df: Any = None
        self.results: Any = None
        self.to_dict: Any = None


OpenBBType = Union[OpenBBBaseProtocol, OpenBBClient]


class OpenBBToolkit(BaseToolkit):
    r"""A toolkit for accessing financial data and analysis through OpenBB
    Platform.

    This toolkit provides methods for retrieving and analyzing financial market
    data, including stocks, ETFs, cryptocurrencies, economic indicators, and
    more through the OpenBB Platform SDK.

    Args:
        None: Initialization requires environment variables for authentication.

    Environment Variables:
        OPENBB_PAT: OpenBB Platform Personal Access Token
            Get one at https://my.openbb.co/app/sdk
        FMP_API_KEY: Financial Modeling Prep API key (optional)
        POLYGON_API_KEY: Polygon.io API key (optional)
        FRED_API_KEY: Federal Reserve Economic Data API key (optional)
    """

    @dependencies_required("openbb")
    @api_keys_required("OPENBB_PAT")
    def __init__(self) -> None:
        """Initialize the OpenBBToolkit.

        This method sets up the OpenBB client and initializes the OpenBB
        Hub account system.
        """
        from typing import cast

        from openbb import obb

        self.client = cast(OpenBBType, obb)

    def _format_return(
        self,
        data: Union[pd.DataFrame, Dict, Any],
        return_type: Literal["df", "raw"],
    ) -> Union[pd.DataFrame, Dict]:
        """Format data based on return type.

        Args:
            data: Data to format
            return_type: Desired return format

        Returns:
            Union[pd.DataFrame, Dict]: Formatted data
        """
        if return_type == "df":
            return (
                pd.DataFrame(data)
                if not isinstance(data, pd.DataFrame)
                else data
            )

        # Convert to dict with string keys
        if isinstance(data, pd.DataFrame):
            return {str(k): v for k, v in data.to_dict().items()}
        if isinstance(data, dict):
            return {str(k): v for k, v in data.items()}
        return {}

    def search_equity(
        self,
        query: str,
        provider: Literal[
            "nasdaq", "sec", "intrinio", "tmx", "cboe", "tradier"
        ] = "nasdaq",
        return_type: Literal["df", "raw"] = "raw",
    ) -> Union[pd.DataFrame, Dict]:
        """Search for equity symbols and company information.

        For more details on available providers, see:
        https://docs.openbb.co/platform/reference/equity/search

        Args:
            query (str): Search query (company name or symbol)
            provider (Literal): Data provider. Available options:
                - nasdaq: NASDAQ Stock Market
                - sec: SEC EDGAR Database
                - intrinio: Intrinio Financial Data
                - tmx: Toronto Stock Exchange
                - cboe: Chicago Board Options Exchange
                - tradier: Tradier Brokerage
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
        return_type: Literal["df", "raw"] = "raw",
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
        return_type: Literal["df", "raw"] = "raw",
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
        self, query: str, return_type: Literal["df", "raw"] = "raw"
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
        return_type: Literal["df", "raw"] = "raw",
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
        return_type: Literal["df", "raw"] = "raw",
    ) -> Union[pd.DataFrame, Dict]:
        """Screens stocks based on market and fundamental criteria using the
        OpenBB Platform.

        Args:
            country: Two-letter ISO country code for filtering stocks.
                Example: 'US' for United States stocks.
            exchange: Stock exchange code for filtering listings.
                Example: 'NYSE', 'NASDAQ'. Format varies by provider.
            sector: Global Industry Classification Standard (GICS) sector.
                Example: 'Technology', 'Healthcare'. Case sensitive.
            industry: GICS industry within the specified sector.
                Example: 'Software', 'Biotechnology'. Case sensitive.
            market_cap_min: Minimum market capitalization filter in USD.
                Example: 1e9 for $1 billion minimum.
            market_cap_max: Maximum market capitalization filter in USD.
                Example: 10e9 for $10 billion maximum.
            beta_min: Minimum beta value for volatility filtering.
                Example: 0.8 for low volatility stocks.
            beta_max: Maximum beta value for volatility filtering.
                Example: 1.2 for moderate volatility stocks.
            provider: Data provider to use for screening.
                Currently supported: 'fmp' (Financial Modeling Prep).
            return_type: Format for the returned data.
                'df' for pandas DataFrame, 'raw' for JSON response.

        Returns:
            Union[pd.DataFrame, Dict]: Screened stocks matching criteria.
                DataFrame columns: symbol, name, exchange, sector,
                industry, market_cap, beta (provider dependent).
        """
        logger = logging.getLogger(__name__)
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

            return self._format_return(data, return_type)

        except Exception as e:
            logger.warning(
                "Market screening failed with params: %s, "
                "provider: %s. Error: %s",
                params,
                provider,
                str(e),
            )
            return self._format_return({}, return_type)

    def get_available_indices(
        self,
        provider: str = "yfinance",
        return_type: Literal["df", "raw"] = "raw",
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
        return_type: Literal["df", "raw"] = "raw",
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
            logger = logging.getLogger(__name__)
            msg = f"Failed to get stock quote for {symbol}: {e}"
            logger.error(msg)
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
        return_type: Literal["df", "raw"] = "raw",
    ) -> Union[pd.DataFrame, Dict]:
        """Retrieves historical market data from OpenBB Platform providers.

        Args:
            symbol: Asset identifier based on type:
                equity: Ticker symbol (e.g., 'AAPL')
                index: Index symbol (e.g., '^SPX')
                currency: Currency pair (e.g., 'EURUSD')
                crypto: Crypto pair (e.g., 'BTC-USD')
                future: Future contract (e.g., 'CL=F')
                option: Option contract (e.g., 'SPY251219P00400000')
            asset_type: Type of financial instrument.
                One of: equity, index, currency, crypto, future, option.
            start_date: Start date in YYYY-MM-DD format.
                If None, uses provider's default lookback.
            end_date: End date in YYYY-MM-DD format.
                If None, uses current date.
            interval: Data frequency/timeframe.
                1m=minute, 1h=hour, 1d=day, 1W=week, 1M=month.
                Note: 1m has limited history availability.
            provider: Data provider override.
                If None, uses default provider for asset_type.
            return_type: Format for returned data.
                'df' for pandas DataFrame, 'raw' for JSON response.

        Returns:
            Union[pd.DataFrame, Dict]: Historical market data.
                DataFrame columns: date, open, high, low, close,
                volume, adjusted (equities only).
        """
        if provider is None:
            provider = (
                "yfinance"  # Use yfinance as default for all asset types
            )

        try:
            if asset_type == "currency":
                response = self.client.currency.price.historical(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    interval=interval,
                    provider=provider,
                )
            elif asset_type == "crypto":
                response = self.client.crypto.price.historical(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    interval=interval,
                    provider=provider,
                )
            else:  # equity, index, option, future
                response = self.client.equity.price.historical(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    interval=interval,
                    provider=provider,
                )

            if return_type == "df":
                if hasattr(response, "results") and response.results:
                    return pd.DataFrame(response.results)
                return pd.DataFrame()
            else:
                if hasattr(response, "results"):
                    return {"results": response.results}
                return {}
        except Exception as e:
            logger = logging.getLogger(__name__)
            msg = f"Failed to get historical data for {symbol}: {e}"
            logger.error(msg)
            return pd.DataFrame() if return_type == "df" else {}

    def get_company_fundamentals(
        self,
        symbol: str,
        provider: str = "fmp",
        return_type: Literal["df", "raw"] = "raw",
    ) -> Union[pd.DataFrame, Dict]:
        """Get company fundamental data.

        Args:
            symbol: Company stock ticker symbol
            provider: Data provider to use
            return_type: Format for returned data

        Returns:
            Union[pd.DataFrame, Dict]: Company fundamental data
        """
        try:
            data = self.client.equity.fundamentals.profile(
                symbol=symbol,
                provider=provider,
            )
            return self._format_return(data, return_type)
        except Exception as e:
            logger = logging.getLogger(__name__)
            msg = f"Failed to get fundamentals for {symbol}: {e}"
            logger.error(msg)
            return self._format_return({}, return_type)

    def get_market_data(
        self,
        category: Literal["gainers", "losers", "active"] = "active",
        source: str = "yfinance",
        return_type: Literal["df", "raw"] = "raw",
    ) -> Union[pd.DataFrame, Dict]:
        """Get market movers data.

        Args:
            category: Type of market data.
                'gainers', 'losers', or 'active'.
            source: Data source to use.
                Default is 'yfinance'.
            return_type: Format for returned data.
                'df' for DataFrame, 'raw' for JSON.

        Returns:
            Union[pd.DataFrame, Dict]: Market movers data
        """
        methods = {
            "gainers": self.client.equity.discovery.gainers,
            "losers": self.client.equity.discovery.losers,
            "active": self.client.equity.discovery.most_active,
        }

        if category in methods:
            try:
                data = methods[category](source)
                return self._format_return(data, return_type)
            except Exception as e:
                logger = logging.getLogger(__name__)
                msg = f"Failed to get {category} data: {e}"
                logger.error(msg)
                return self._format_return({}, return_type)

        msg = "Category must be 'gainers', 'losers', or 'active'."
        raise ValueError(msg)

    def get_earnings_calendar(
        self,
        start_date: str,
        end_date: str,
        provider: str = "fmp",
        min_market_cap: Optional[float] = None,
        return_type: Literal["df", "raw"] = "raw",
    ) -> Union[pd.DataFrame, Dict[str, Any]]:
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
                params["min_market_cap"] = str(min_market_cap)

            data = self.client.calendar.earnings(**params)
            if return_type == "df":
                return data.to_df()
            else:
                if isinstance(data, pd.DataFrame):
                    return {str(k): v for k, v in data.to_dict().items()}
                return (
                    {str(k): v for k, v in data.items()}
                    if isinstance(data, dict)
                    else {}
                )
        except Exception as e:
            logger = logging.getLogger(__name__)
            msg = f"Failed to get earnings calendar: {e}"
            logger.error(msg)
            return pd.DataFrame() if return_type == "df" else {}

    def get_dividend_calendar(
        self,
        start_date: str,
        end_date: str,
        provider: str = "nasdaq",
        calculate_yield: bool = True,
        return_type: Literal["df", "raw"] = "raw",
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
            logger = logging.getLogger(__name__)
            msg = f"Failed to get dividend calendar: {e}"
            logger.error(msg)
            return pd.DataFrame() if return_type == "df" else {}

    def get_ipo_calendar(
        self,
        status: Literal["upcoming", "priced", "withdrawn"] = "upcoming",
        provider: str = "nasdaq",
        is_spo: bool = False,
        min_offer_amount: Optional[float] = None,
        return_type: Literal["df", "raw"] = "raw",
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
            logger = logging.getLogger(__name__)
            msg = f"Failed to get IPO calendar: {e}"
            logger.error(msg)
            return pd.DataFrame() if return_type == "df" else {}

    def get_available_indicators(
        self,
        provider: str = "econdb",
        return_type: Literal["df", "raw"] = "raw",
    ) -> Union[pd.DataFrame, Dict]:
        """Get list of available economic indicators.

        Args:
            provider: Data provider
            return_type: Return format

        Returns:
            Available indicators with metadata
        """
        data = self.client.economy.available_indicators(provider=provider)
        if return_type == "df":
            return data.to_df()
        else:
            if isinstance(data, pd.DataFrame):
                return {str(k): v for k, v in data.to_dict().items()}
            return (
                {str(k): v for k, v in data.items()}
                if isinstance(data, dict)
                else {}
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
        return_type: Literal["df", "raw"] = "raw",
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
        if return_type == "df":
            return data.to_df()
        else:
            if isinstance(data, pd.DataFrame):
                return {str(k): v for k, v in data.to_dict().items()}
            return (
                {str(k): v for k, v in data.items()}
                if isinstance(data, dict)
                else {}
            )

    def get_income_statement(
        self,
        symbol: str,
        period: Literal["annual", "quarter"] = "annual",
        provider: str = "fmp",
        limit: int = 5,
        return_type: Literal["df", "raw"] = "raw",
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
        if return_type == "df":
            return data.to_df()
        else:
            if isinstance(data, pd.DataFrame):
                return {str(k): v for k, v in data.to_dict().items()}
            return (
                {str(k): v for k, v in data.items()}
                if isinstance(data, dict)
                else {}
            )

    def get_cash_flow(
        self,
        symbol: str,
        period: Literal["annual", "quarter"] = "annual",
        provider: str = "fmp",
        limit: int = 5,
        return_type: Literal["df", "raw"] = "raw",
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
        if return_type == "df":
            return data.to_df()
        else:
            if isinstance(data, pd.DataFrame):
                return {str(k): v for k, v in data.to_dict().items()}
            return (
                {str(k): v for k, v in data.items()}
                if isinstance(data, dict)
                else {}
            )

    def get_financial_ratios(
        self,
        symbol: str,
        period: Literal["annual", "quarter"] = "annual",
        provider: str = "fmp",
        limit: int = 5,
        return_type: Literal["df", "raw"] = "raw",
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
        if return_type == "df":
            return data.to_df()
        else:
            if isinstance(data, pd.DataFrame):
                return {str(k): v for k, v in data.to_dict().items()}
            return (
                {str(k): v for k, v in data.items()}
                if isinstance(data, dict)
                else {}
            )

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
            logger = logging.getLogger(__name__)
            msg = f"Failed to get financial statements for {symbol}: {e}"
            logger.error(msg)
            return {}

    def search_financial_attributes(
        self, keyword: str, return_type: Literal["df", "raw"] = "raw"
    ) -> Union[pd.DataFrame, Dict]:
        """Search for available financial attributes/metrics.

        Args:
            keyword: Keyword to search for
            return_type: Return format

        Returns:
            Search results for financial attributes
        """
        data = self.client.equity.fundamental.search_attributes(keyword)
        if return_type == "df":
            return data.to_df()
        else:
            if isinstance(data, pd.DataFrame):
                return {str(k): v for k, v in data.to_dict().items()}
            return (
                {str(k): v for k, v in data.items()}
                if isinstance(data, dict)
                else {}
            )

    def get_historical_attribute(
        self,
        symbol: str,
        tag: str,
        frequency: Literal["quarterly", "annual"] = "quarterly",
        provider: str = "intrinio",
        return_type: Literal["df", "raw"] = "raw",
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
        if return_type == "df":
            return data.to_df()
        else:
            if isinstance(data, pd.DataFrame):
                return {str(k): v for k, v in data.to_dict().items()}
            return (
                {str(k): v for k, v in data.items()}
                if isinstance(data, dict)
                else {}
            )

    def get_economic_calendar(
        self,
        start_date: str,
        end_date: str,
        provider: Literal["fmp", "nasdaq", "tradingeconomics"] = "fmp",
        convert_timezone: bool = True,
        return_type: Literal["df", "raw"] = "raw",
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

            data = self.client.economy.available_indicators(**params)
            if not isinstance(data, pd.DataFrame) or data.empty:
                logger = logging.getLogger(__name__)
                msg = "No indicators found. Check parameters and try again."
                logger.warning(msg)
                return pd.DataFrame() if return_type == "df" else {}
            if return_type == "df":
                return (
                    data
                    if isinstance(data, pd.DataFrame)
                    else pd.DataFrame(data)
                )
            else:
                if return_type == "df":
                    return (
                        data
                        if isinstance(data, pd.DataFrame)
                        else pd.DataFrame(data)
                    )
                else:
                    if isinstance(data, pd.DataFrame):
                        result_dict = data.to_dict()
                        return {str(k): v for k, v in result_dict.items()}
                    if isinstance(data, dict):
                        return {str(k): v for k, v in data.items()}
                    return {}
        except Exception as e:
            logger = logging.getLogger(__name__)
            msg = "Failed to get indicators: {}"
            logger.error(msg.format(str(e)))
            return pd.DataFrame() if return_type == "df" else {}

    def get_market_movers(
        self,
        category: Literal["gainers", "losers", "active"] = "gainers",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None,
        source: str = "yf",
        return_type: Literal["df", "raw"] = "raw",
    ) -> Union[pd.DataFrame, Dict]:
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
            return_type: Format of returned data:
                - 'raw': Original JSON response
                - 'df': Pandas DataFrame with columns:
                    [symbol, name, price, change, change_pct, volume]

        Returns:
            Union[pd.DataFrame, Dict]: Market movers data in specified format.
                Empty dict/DataFrame if error occurs.
        """
        methods = {
            "gainers": self.client.stocks.movers.gainers,
            "losers": self.client.stocks.movers.losers,
            "active": self.client.stocks.movers.active,
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

            return self._format_return(response, return_type)

        except Exception as e:
            logger = logging.getLogger(__name__)
            msg = f"Failed to get {category} data: {e}"
            logger.error(msg)
            return self._format_return({}, return_type)
