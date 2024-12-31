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
    more through the OpenBB Platform SDK.

    Args:
        None: Initialization requires environment variables for authentication.

    Environment Variables:
        OPENBB_TOKEN: OpenBB Platform Personal Access Token
            Get one at https://my.openbb.co/app/sdk
        FMP_API_KEY: Financial Modeling Prep API key (optional)
        POLYGON_API_KEY: Polygon.io API key (optional)
        FRED_API_KEY: Federal Reserve Economic Data API key (optional)
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

    @staticmethod
    def _ensure_columns_exist(
        df: pd.DataFrame, expected_columns: List[str]
    ) -> pd.DataFrame:
        """Ensure that the DataFrame has all expected columns, filling missing
        ones with None.

        Args:
            df (pd.DataFrame): Input DataFrame
            expected_columns (List[str]): List of column names that should
            exist

        Returns:
            pd.DataFrame: DataFrame with all expected columns
        """
        for col in expected_columns:
            if col not in df.columns:
                df[col] = None
        return df

    @staticmethod
    def _convert_numeric_columns(
        df: pd.DataFrame, numeric_cols: List[str]
    ) -> pd.DataFrame:
        """Convert specified columns to numeric type, coercing errors to NaN.

        Args:
            df (pd.DataFrame): Input DataFrame
            numeric_cols (List[str]): List of column names to convert

        Returns:
            pd.DataFrame: DataFrame with converted numeric columns
        """
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        return df

    def _format_return(
        self,
        data: Union[pd.DataFrame, Dict, Any],
        return_type: Literal["df", "raw"],
    ) -> Union[pd.DataFrame, Dict[str, Any]]:
        """Format data based on return type.

        Args:
            data: Data to format
            return_type: Desired return format

        Returns:
            Union[pd.DataFrame, Dict]: Formatted data
        """
        if hasattr(data, "results"):
            data = data.results
        if isinstance(data, pd.Series):
            data = data.to_frame()
        if isinstance(data, pd.DataFrame):
            if return_type == "df":
                return data
            return {str(k): v for k, v in data.to_dict().items()}
        if isinstance(data, dict):
            if return_type == "df":
                return pd.DataFrame.from_dict(data)
            return {str(k): v for k, v in data.items()}
        # For any other type, convert to dict
        return {"result": data}

    def _handle_api_error(
        self,
        error: Exception,
        operation: str,
        return_type: str = "df",
        log_level: str = "warning",
        **format_args,
    ) -> Union[pd.DataFrame, Dict]:
        """Handle API operation errors consistently.

        Args:
            error (Exception): The caught exception
            operation (str): Description of the failed operation
            (e.g., "get_historical_data")
            return_type (str): Return type ("df" or "dict")
            log_level (str): Logging level to use ("warning" or "error")
            format_args: Additional format arguments for the error message

        Returns:
            Union[pd.DataFrame, Dict]: Empty DataFrame or dict based on
            return_type
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
        return pd.DataFrame() if return_type == "df" else {}

    def search_equity(
        self,
        query: str,
        provider: Literal[
            "nasdaq", "sec", "intrinio", "tmx", "cboe", "tradier"
        ] = "nasdaq",
        return_type: Literal["df", "raw"] = "raw",
        limit: Optional[int] = None,
    ) -> Union[pd.DataFrame, Dict]:
        """Search for equity symbols and company information.

        For SEC provider, an empty query ("") returns the complete list of
        companies sorted by market cap.

        Args:
            query: Search query (company name or symbol). Use "" for complete
            SEC list.
            provider: Data provider. Available options:
                - nasdaq: NASDAQ Stock Market
                - sec: SEC EDGAR Database (sorted by market cap)
                - intrinio: Intrinio Financial Data
                - tmx: Toronto Stock Exchange
                - cboe: Chicago Board Options Exchange
                - tradier: Tradier Brokerage
            return_type: Return format ('df' for DataFrame, 'raw' for
            dictionary)
            limit: Maximum number of results to return (None for all)

        Returns:
            Union[pd.DataFrame, Dict]: Search results with columns varying by
            provider.
            For SEC provider:
                - symbol: Ticker symbol
                - name: Company name
                - cik: SEC Central Index Key
        """
        try:
            data = self.client.equity.search(query, provider=provider)  # type: ignore[union-attr]

            if return_type == "df":
                df = data.to_df()

                expected_columns = ["symbol", "name", "cik"]
                # Add missing columns with None values
                df = self._ensure_columns_exist(df, expected_columns)

                # Convert CIK to string and ensure proper formatting
                if 'cik' in df.columns:
                    df['cik'] = df['cik'].astype(str).str.zfill(10)

                if limit is not None:
                    df = df.head(limit)

                return df[expected_columns]

            return data.results

        except Exception as e:
            return self._handle_api_error(
                error=e,
                operation="search equity",
                return_type=return_type,
                log_level="warning",
                query=query,
                provider=provider,
            )

    def search_institution(
        self, query: str, return_type: Literal["df", "raw"] = "raw"
    ) -> Union[pd.DataFrame, Dict]:
        """Search for financial institutions in SEC database.

        Args:
            query: Institution name to search (e.g., "Berkshire Hathaway")
            return_type: Return format ('df' for DataFrame, 'raw' for
            dictionary)

        Returns:
            Union[pd.DataFrame, Dict]: Institution search results with columns:
                - name: Institution name
                - cik: SEC Central Index Key (10-digit format)
        """
        try:
            data = self.client.regulators.sec.institutions_search(query)  # type: ignore[union-attr]

            if return_type == "df":
                df = data.to_df()

                expected_columns = ["name", "cik"]
                # Add missing columns with None values
                df = self._ensure_columns_exist(df, expected_columns)

                # Convert CIK to string and ensure proper formatting
                if 'cik' in df.columns:
                    df['cik'] = df['cik'].astype(str).str.zfill(10)

                return df[expected_columns]

            return data.results

        except Exception as e:
            return self._handle_api_error(
                error=e,
                operation="search institution",
                return_type=return_type,
                log_level="warning",
                query=query,
            )

    def search_filings(
        self,
        identifier: str,
        filing_type: Optional[str] = None,
        provider: str = "sec",
        return_type: Literal["df", "raw"] = "raw",
    ) -> Union[pd.DataFrame, Dict]:
        """Search for SEC filings by CIK or ticker symbol.

        Args:
            identifier: CIK number or ticker symbol
            filing_type: Filing type (e.g., "4", "13F-NT", None for all types)
            provider: Data provider (default: "sec")
            return_type: Return format ('df' for DataFrame, 'raw' for
            dictionary)

        Returns:
            Union[pd.DataFrame, Dict]: Filing search results with columns:
                - type: Filing type (e.g., "4", "13F-NT")
                - link: Direct link to the filing
                - report_date: Date of the report
                - accepted_date: Date and time the filing was accepted
                - act: Securities Act reference
                - primary_doc_description: Description of primary document
                - primary_doc: Primary document filename
                - accession_number: SEC accession number
                - file_number: SEC file number
                - film_number: SEC film number
                - is_inline_xbrl: XBRL inline flag
                - is_xbrl: XBRL flag
                - size: File size
                - complete_submission_url: Complete submission URL
                - filing_detail_url: Filing detail page URL
        """
        try:
            data = self.client.equity.fundamental.filings(  # type: ignore[union-attr]
                identifier,
                type=filing_type,
                provider=provider,
            )

            if return_type == "df":
                df = data.to_df()

                expected_columns = [
                    "type",
                    "link",
                    "report_date",
                    "accepted_date",
                    "act",
                    "primary_doc_description",
                    "primary_doc",
                    "accession_number",
                    "file_number",
                    "film_number",
                    "is_inline_xbrl",
                    "is_xbrl",
                    "size",
                    "complete_submission_url",
                    "filing_detail_url",
                ]

                # Add missing columns with None values
                df = self._ensure_columns_exist(df, expected_columns)

                # Convert date columns
                date_columns = ["report_date", "accepted_date"]
                for col in date_columns:
                    if col in df.columns and df[col].notna().any():
                        df[col] = pd.to_datetime(df[col])

                # Convert boolean columns
                bool_columns = ["is_inline_xbrl", "is_xbrl"]
                for col in bool_columns:
                    if col in df.columns:
                        df[col] = df[col].astype(int)

                # Convert size to integer
                if "size" in df.columns:
                    df["size"] = pd.to_numeric(
                        df["size"], errors="coerce"
                    ).astype("Int64")

                return df[expected_columns]

            return data.results

        except Exception as e:
            return self._handle_api_error(
                error=e,
                operation="search filings",
                return_type=return_type,
                log_level="warning",
                identifier=identifier,
                filing_type=filing_type,
                provider=provider,
            )

    def search_etf(
        self,
        query: str,
        provider: str = "tmx",
        return_type: Literal["df", "raw"] = "raw",
        limit: Optional[int] = None,
    ) -> Union[pd.DataFrame, Dict]:
        """Search for ETF information.

        Args:
            query: Search query (ETF name or symbol)
            provider: Data provider (default: "tmx")
            return_type: Return format ('df' for DataFrame, 'raw' for
            dictionary)
            limit: Maximum number of results to return (None for all)

        Returns:
            Union[pd.DataFrame, Dict]: ETF search results with columns:
                - name: Full ETF name
                - short_name: Abbreviated ETF name
                - inception_date: Fund inception date
                - issuer: ETF issuer/provider
                - investment_style: Investment strategy
                - esg: ESG compliance flag
                - currency: Trading currency
                - unit_price: Current unit price
                - close: Last closing price
                - prev_close: Previous day's closing price
                - return_1m: 1-month return
                - return_3m: 3-month return
                - return_6m: 6-month return
                - return_ytd: Year-to-date return
                - return_1y: 1-year return
                - beta_1y: 1-year beta
                - return_3y: 3-year return
                - beta_3y: 3-year beta
                - return_5y: 5-year return
                - beta_5y: 5-year beta
                - return_10y: 10-year return
                - beta_10y: 10-year beta
                - beta_15y: 15-year beta
                - return_from_inception: Return since inception
                - avg_volume: Average daily volume
                - avg_volume_30d: 30-day average volume
                - aum: Assets under management
                - pe_ratio: Price-to-earnings ratio
                - pb_ratio: Price-to-book ratio
                - management_fee: Management fee
                - mer: Management expense ratio
                - distribution_yield: Distribution yield
                - dividend_frequency: Dividend payment frequency
                - beta_20y: 20-year beta
        """
        try:
            data = self.client.etf.search(query, provider=provider)  # type: ignore[union-attr]

            if return_type == "df":
                df = data.to_df()

                # Ensure consistent column order and names
                expected_columns = [
                    "name",
                    "short_name",
                    "inception_date",
                    "issuer",
                    "investment_style",
                    "esg",
                    "currency",
                    "unit_price",
                    "close",
                    "prev_close",
                    "return_1m",
                    "return_3m",
                    "return_6m",
                    "return_ytd",
                    "return_1y",
                    "beta_1y",
                    "return_3y",
                    "beta_3y",
                    "return_5y",
                    "beta_5y",
                    "return_10y",
                    "beta_10y",
                    "beta_15y",
                    "return_from_inception",
                    "avg_volume",
                    "avg_volume_30d",
                    "aum",
                    "pe_ratio",
                    "pb_ratio",
                    "management_fee",
                    "mer",
                    "distribution_yield",
                    "dividend_frequency",
                    "beta_20y",
                ]

                # Add missing columns with None values
                df = self._ensure_columns_exist(df, expected_columns)

                # Convert date columns
                if 'inception_date' in df.columns:
                    df['inception_date'] = pd.to_datetime(
                        df['inception_date']
                    ).dt.strftime('%Y-%m-%d')

                # Convert numeric columns
                numeric_cols = [
                    'unit_price',
                    'close',
                    'prev_close',
                    'return_1m',
                    'return_3m',
                    'return_6m',
                    'return_ytd',
                    'return_1y',
                    'beta_1y',
                    'return_3y',
                    'beta_3y',
                    'return_5y',
                    'beta_5y',
                    'return_10y',
                    'beta_10y',
                    'beta_15y',
                    'return_from_inception',
                    'avg_volume',
                    'avg_volume_30d',
                    'aum',
                    'pe_ratio',
                    'pb_ratio',
                    'management_fee',
                    'mer',
                    'distribution_yield',
                    'beta_20y',
                ]

                df = self._convert_numeric_columns(df, numeric_cols)

                # Convert boolean columns
                if 'esg' in df.columns:
                    df['esg'] = df['esg'].astype(bool)

                # Apply limit if specified
                if limit is not None:
                    df = df.head(limit)

                return df[expected_columns]

            return data.results

        except Exception as e:
            return self._handle_api_error(
                error=e,
                operation="search ETF",
                return_type=return_type,
                log_level="warning",
                query=query,
                provider=provider,
            )

    def screen_market(
        self,
        country: Optional[str] = None,
        exchange: Optional[str] = None,
        sector: Optional[str] = None,
        industry: Optional[str] = None,
        mktcap_min: Optional[float] = None,
        mktcap_max: Optional[float] = None,
        beta_min: Optional[float] = None,
        beta_max: Optional[float] = None,
        provider: str = "fmp",
        return_type: Literal["df", "raw"] = "raw",
    ) -> Union[pd.DataFrame, Dict]:
        """Screen stocks based on market and fundamental criteria.

        Args:
            country: Two-letter ISO country code (e.g., 'US', 'IN', 'CN')
            exchange: Stock exchange code (e.g., 'NYSE', 'AMEX', 'NSE')
            sector: Market sector (e.g., 'Financial Services', 'Healthcare')
            industry: Industry within sector (e.g., 'Banks—Regional',
            'Drug Manufacturers')
            mktcap_min: Minimum market cap in USD
            mktcap_max: Maximum market cap in USD
            beta_min: Minimum beta value
            beta_max: Maximum beta value
            provider: Data provider (default: 'fmp' for Financial Modeling
            Prep)
            return_type: Return format ('df' for DataFrame, 'raw' for
            dictionary)

        Returns:
            Union[pd.DataFrame, Dict]: Screened stocks with columns:
                - symbol: Stock symbol with exchange suffix
                - name: Company name
                - market_cap: Market capitalization in USD
                - sector: Market sector
                - industry: Industry classification
                - beta: Beta value
                - price: Current price
                - last_annual_dividend: Last annual dividend amount
                - volume: Trading volume
                - exchange: Exchange code
                - exchange_name: Full exchange name
                - country: Country code
                - is_etf: ETF flag
                - actively_trading: Active trading status
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

            if return_type == "df":
                df = data.to_df()

                # Ensure consistent column order and names
                expected_columns = [
                    "symbol",
                    "name",
                    "market_cap",
                    "sector",
                    "industry",
                    "beta",
                    "price",
                    "last_annual_dividend",
                    "volume",
                    "exchange",
                    "exchange_name",
                    "country",
                    "is_etf",
                    "actively_trading",
                ]

                # Add missing columns with None values
                df = self._ensure_columns_exist(df, expected_columns)

                numeric_cols = [
                    "market_cap",
                    "beta",
                    "price",
                    "last_annual_dividend",
                    "volume",
                ]
                df = self._convert_numeric_columns(df, numeric_cols)

                # Convert boolean columns
                bool_cols = ["is_etf", "actively_trading"]
                for col in bool_cols:
                    if col in df.columns:
                        df[col] = df[col].astype(bool)

                # Ensure country codes are uppercase
                if "country" in df.columns:
                    df["country"] = df["country"].str.upper()

                return df[expected_columns]

            return data.results

        except Exception as e:
            return self._handle_api_error(
                error=e,
                operation="screen market",
                return_type=return_type,
                log_level="warning",
                provider=provider,
            )

    def get_available_indices(
        self,
        provider: str = "yfinance",
        return_type: Literal["df", "raw"] = "raw",
    ) -> Union[pd.DataFrame, Dict]:
        """Get list of available market indices.

        With the openbb-yfinance extension, index time series can be loaded
        using either:
        - Ticker symbol (e.g., '^AXJO' for S&P/ASX 200)
        - Short code (e.g., 'au_asx200' for S&P/ASX 200)
        Non-American indices have codes beginning with two-letter country code.

        Args:
            provider: Data provider (default: "yfinance")
            return_type: Return format ('df' for DataFrame, 'raw' for
            dictionary)

        Returns:
            Union[pd.DataFrame, Dict]: Available indices with columns:
                - name: Full index name with currency
                - code: Short code (country_index format)
                - symbol: Ticker symbol (e.g., '^AXJO')
        """
        try:
            data = self.client.index.available(provider=provider)  # type: ignore[union-attr]

            if return_type == "df":
                df = data.to_df()

                # Ensure consistent column order and names
                expected_columns = ["name", "code", "symbol"]

                # Add missing columns with None values
                df = self._ensure_columns_exist(df, expected_columns)

                # Clean up index codes
                if "code" in df.columns:
                    # Ensure codes are lowercase and use underscores
                    df["code"] = df["code"].str.lower().str.replace("-", "_")
                    # Add country prefix if missing
                    mask = ~df["code"].str.contains("^[a-z]{2}_", na=False)
                    df.loc[mask, "code"] = "us_" + df.loc[mask, "code"]

                # Clean up symbols
                if "symbol" in df.columns:
                    # Add '^' prefix if missing for index symbols
                    mask = ~df["symbol"].str.startswith("^", na=False)
                    df.loc[mask, "symbol"] = "^" + df.loc[mask, "symbol"]

                return df[expected_columns]

            return data.results

        except Exception as e:
            return self._handle_api_error(
                error=e,
                operation="get available indices",
                return_type=return_type,
                log_level="warning",
                provider=provider,
            )

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
            data = self.client.equity.price.quote(symbol=symbol, source=source)  # type: ignore[union-attr]
            return self._format_return(data, return_type)
        except Exception as e:
            return self._handle_api_error(
                error=e,
                operation="get stock quote",
                return_type=return_type,
                log_level="error",
                symbol=symbol,
            )

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
            else:  # equity, index, option, future
                response = self.client.equity.price.historical(  # type: ignore[union-attr]
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
            return self._handle_api_error(
                error=e,
                operation="get historical data",
                return_type=return_type,
                log_level="error",
                symbol=symbol,
            )

    def get_historical_prices(
        self,
        symbol: str,
        asset_type: Literal[
            "equity", "index", "currency", "crypto", "future", "option"
        ] = "equity",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        interval: Literal["1m", "1h", "1d", "1W", "1M"] = "1d",
        provider: str = "yfinance",
        return_type: Literal["df", "raw"] = "raw",
    ) -> Union[pd.DataFrame, Dict]:
        r"""Get historical OHLC+V price data for a symbol.

        Supports various symbol types and formats depending on the provider:

        1. Share Classes:
           - Period: "BRK.A", "BRK.B"
           - Hyphen: "BRK-A", "BRK-B"
           - Slash: "BRK/A", "BRK/B"
           - No separator for domestic markets: Fourth/fifth letter indicates
           class

        2. Regional Identifiers:
           - Suffix format: "RELIANCE.NS" (YahooFinance)
           - Composite format: "SPY:US" (TMX)
           - No identifier for domestic markets: "CNQ" (TMX-Canada)

        3. Indices:
           - YahooFinance/FMP/CBOE: "^RUT", "^GSPC"
           - Polygon: "I:NDX"
           Note: For dedicated index data, use obb.index.price.historical()

        4. Currencies:
           - YahooFinance: "EURUSD=X"
           - Polygon: "C:EURUSD"
           - AlphaVantage/FMP: "EURUSD"
           Note: For dedicated FX data, use obb.currency.price.historical()

        5. Crypto:
           - YahooFinance: "BTC-USD"
           - Polygon: "X:BTCUSD"
           - AlphaVantage/FMP: "BTCUSD"
           Note: For dedicated crypto data, use obb.crypto.price.historical()

        6. Futures:
           - Continuous front-month: "CL=F"
           - Specific contracts: "CLZ24.NYM", "CLH24.NYM"
           Note: Contract venues include ["NYM", "NYB", "CME", "CBT"]

        7. Options:
           - YahooFinance: "SPY241220P00400000"
           - Polygon: "O:SPY241220P00400000"

        Args:
            symbol: Trading symbol in provider-specific format
            asset_type: Type of financial instrument.
                One of: equity, index, currency, crypto, future, option.
            start_date: Start date in YYYY-MM-DD format (default:
            provider-dependent)
            end_date: End date in YYYY-MM-DD format (default: today)
            interval: Data granularity. One of:
                - "1m": One minute
                - "1h": One hour
                - "1d": One day (default)
                - "1W": One week
                - "1M": One month
            provider: Data provider (default: "yfinance")
            return_type: Return format ('df' for DataFrame, 'raw' for
            dictionary)

        Returns:
            Union[pd.DataFrame, Dict]: Historical price data with columns:
                - date: Timestamp for the period
                - open: Opening price
                - high: Highest price
                - low: Lowest price
                - close: Closing price
                - volume: Trading volume
                Additional columns by provider:
                - YahooFinance: dividends, stock_splits
                - FMP: vwap, label, adj_close, change, change_percent
                - Polygon: vwap, transactions
        """
        try:
            # Build parameters dict
            params = {"symbol": symbol, "provider": provider}
            if start_date:
                params["start_date"] = start_date
            if end_date:
                params["end_date"] = end_date
            if interval:
                params["interval"] = interval

            data = self.client.equity.price.historical(**params)  # type: ignore[union-attr]

            if return_type == "df":
                df = data.to_df()

                # Ensure consistent column order and names
                base_columns = [
                    "date",
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                ]
                provider_columns = {
                    "yfinance": ["dividends", "stock_splits"],
                    "fmp": [
                        "vwap",
                        "label",
                        "adj_close",
                        "change",
                        "change_percent",
                    ],
                    "polygon": ["vwap", "transactions"],
                }

                # Add missing base columns with None values
                df = self._ensure_columns_exist(df, base_columns)

                numeric_cols = [
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                    "vwap",
                ]
                df = self._convert_numeric_columns(df, numeric_cols)

                # Convert date column to datetime if present
                if "date" in df.columns:
                    df["date"] = pd.to_datetime(df["date"])
                    df.set_index("date", inplace=True)

                # Order columns: base columns first, then provider-specific
                # columns
                extra_cols = provider_columns.get(provider, [])
                available_cols = base_columns[1:] + [
                    col for col in extra_cols if col in df.columns
                ]
                return df[available_cols]

            return data.results

        except Exception as e:
            return self._handle_api_error(
                error=e,
                operation="get historical prices",
                return_type=return_type,
                log_level="warning",
                symbol=symbol,
                provider=provider,
            )

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
            "gainers": self.client.equity.discovery.gainers,  # type: ignore[union-attr]
            "losers": self.client.equity.discovery.losers,  # type: ignore[union-attr]
            "active": self.client.equity.discovery.active,  # type: ignore[union-attr]
        }

        if category in methods:
            try:
                data = methods[category](source)
                return self._format_return(data, return_type)
            except Exception as e:
                return self._handle_api_error(
                    error=e,
                    operation="get market data",
                    return_type=return_type,
                    log_level="error",
                    category=category,
                    source=source,
                )

        msg = "Category must be 'gainers', 'losers', or 'active'."
        raise ValueError(msg)

    def get_earnings_calendar(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        provider: str = "fmp",
        filter_estimates: bool = False,
        sort_by: Optional[str] = None,
        ascending: bool = False,
        limit: Optional[int] = None,
        return_type: Literal["df", "raw"] = "raw",
    ) -> Union[pd.DataFrame, Dict]:
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
            Union[pd.DataFrame, Dict]: Earnings calendar with columns:
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

            if return_type == "df":
                df = data.to_df()

                # Convert dates to datetime
                date_cols = ["report_date", "period_ending", "updated_date"]
                for col in date_cols:
                    if col in df.columns:
                        df[col] = pd.to_datetime(df[col])

                # Set report_date as index
                if "report_date" in df.columns:
                    df.set_index("report_date", inplace=True)

                numeric_cols = [
                    "eps_consensus",
                    "actual_eps",
                    "revenue_consensus",
                    "actual_revenue",
                ]
                df = self._convert_numeric_columns(df, numeric_cols)

                # Filter for entries with estimates
                if filter_estimates:
                    df = df[
                        df["eps_consensus"].notnull()
                        & df["revenue_consensus"].notnull()
                    ]

                # Sort if requested
                if sort_by and sort_by in df.columns:
                    df = df.sort_values(by=sort_by, ascending=ascending)

                # Limit results if requested
                if limit is not None:
                    df = df.head(limit)

                return df

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
        calculate_yield: bool = False,
        sort_by: Optional[str] = None,
        ascending: bool = False,
        limit: Optional[int] = None,
        return_type: Literal["df", "raw"] = "raw",
    ) -> Union[pd.DataFrame, Dict]:
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
            Union[pd.DataFrame, Dict]: Dividend calendar with columns:
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

            if return_type == "df":
                df = data.to_df()

                # Convert dates to datetime
                date_cols = [
                    "ex_dividend_date",
                    "record_date",
                    "payment_date",
                    "declaration_date",
                ]
                for col in date_cols:
                    if col in df.columns:
                        df[col] = pd.to_datetime(df[col])

                # Set ex_dividend_date as index
                if "ex_dividend_date" in df.columns:
                    df.set_index("ex_dividend_date", inplace=True)

                numeric_cols = ["amount", "annualized_amount"]
                df = self._convert_numeric_columns(df, numeric_cols)

                # Calculate annualized amount if not provided
                if (
                    "annualized_amount" not in df.columns
                    and "frequency" in df.columns
                ):
                    frequency_map = {
                        "monthly": 12,
                        "quarterly": 4,
                        "semi-annual": 2,
                        "annual": 1,
                    }
                    df["annualized_amount"] = df.apply(
                        lambda row: row["amount"]
                        * frequency_map.get(
                            row.get("frequency", "").lower(),
                            4,  # Default to quarterly if unknown
                        ),
                        axis=1,
                    )

                # Add yield calculations if requested
                if calculate_yield:
                    try:
                        # Get current prices
                        symbols = df.index.tolist()
                        prices = self.client.equity.price.quote(  # type: ignore[union-attr]
                            symbols,
                            provider="fmp",  # FMP has good global coverage
                        ).to_df()

                        # Add price and yield columns
                        df["price"] = prices["price"]
                        df["yield"] = round(
                            (df["annualized_amount"] / df["price"]) * 100, 4
                        )

                    except Exception as e:
                        logger = logging.getLogger(__name__)
                        logger.warning(
                            f"""Failed to calculate dividend yields. Error: {
                                e!s}"""
                        )

                # Sort if requested
                if sort_by and sort_by in df.columns:
                    df = df.sort_values(by=sort_by, ascending=ascending)

                # Limit results if requested
                if limit is not None:
                    df = df.head(limit)

                return df

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
    ) -> Union[pd.DataFrame, Dict]:
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
            Union[pd.DataFrame, Dict]: IPO/SPO calendar with columns:
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

            if return_type == "df":
                df = data.to_df()

                # Convert dates to datetime
                date_cols = [
                    "ipo_date",
                    "expected_price_date",
                    "withdraw_date",
                    "filed_date",
                ]
                for col in date_cols:
                    if col in df.columns:
                        df[col] = pd.to_datetime(df[col])

                # Set appropriate date column as index based on status
                if (
                    status == "upcoming"
                    and "expected_price_date" in df.columns
                ):
                    df.set_index("expected_price_date", inplace=True)
                elif status == "priced" and "ipo_date" in df.columns:
                    df.set_index("ipo_date", inplace=True)
                elif status == "withdrawn" and "withdraw_date" in df.columns:
                    df.set_index("withdraw_date", inplace=True)

                numeric_cols = ["offer_amount", "share_count"]
                df = self._convert_numeric_columns(df, numeric_cols)

                # Handle share price ranges
                if "share_price" in df.columns:
                    # Keep as string to preserve ranges like "5.75-6.75"
                    df["share_price"] = df["share_price"].astype(str)

                # Sort if requested
                if sort_by and sort_by in df.columns:
                    df = df.sort_values(by=sort_by, ascending=ascending)

                # Limit results if requested
                if limit is not None:
                    df = df.head(limit)

                return df

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
    ) -> Union[pd.DataFrame, Dict]:
        """Get list of available economic indicators.

        Args:
            provider: Data provider (default: "econdb")
            return_type: Return format ('df' for DataFrame, 'raw' for
            dictionary)

        Returns:
            Union[pd.DataFrame, Dict]: Available indicators with columns:
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

            if return_type == "df":
                df = data.to_df()

                # Convert dates to datetime
                date_cols = [
                    "first_date",
                    "last_date",
                    "last_insert_timestamp",
                ]
                for col in date_cols:
                    if col in df.columns:
                        df[col] = pd.to_datetime(df[col])

                return df

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
    ) -> Union[pd.DataFrame, Dict]:
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
            Union[pd.DataFrame, Dict]: Economic data with columns:
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

            if return_type == "df":
                df = data.to_df()

                # Convert dates to datetime
                if "date" in df.columns:
                    df["date"] = pd.to_datetime(df["date"])
                    df.set_index("date", inplace=True)

                # Convert numeric values
                if "value" in df.columns:
                    df["value"] = pd.to_numeric(df["value"], errors='coerce')

                # Add metadata as DataFrame attributes if requested
                if include_metadata and hasattr(data, 'extra'):
                    metadata = data.extra.get("results_metadata", {})
                    if metadata:
                        df.attrs["metadata"] = metadata

                return df

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
                if isinstance(data, pd.DataFrame):
                    result_dict = data.to_dict()
                    return {str(k): v for k, v in result_dict.items()}
                if isinstance(data, dict):
                    return {str(k): v for k, v in data.items()}
                return {}

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
            return_type: Format for returned data:
                - 'raw': Original JSON response
                - 'df': Pandas DataFrame with columns:
                    [symbol, name, price, change, change_pct, volume]

        Returns:
            Union[pd.DataFrame, Dict]: Market movers data in specified format.
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

            return self._format_return(response, return_type)

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
    ) -> Union[pd.DataFrame, Dict]:
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
            Union[pd.DataFrame, Dict]: Financial metrics with common fields:
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

            if return_type == "df":
                df = data.to_df()

                # Convert calendar_year to index if present
                if "calendar_year" in df.columns:
                    df["calendar_year"] = pd.to_numeric(df["calendar_year"])
                    df.set_index("calendar_year", inplace=True)
                    df.sort_index(ascending=False, inplace=True)
                elif "date" in df.columns:
                    df["date"] = pd.to_datetime(df["date"])
                    df.set_index("date", inplace=True)

                numeric_cols = [
                    "quick_ratio",
                    "current_ratio",
                    "debt_to_equity",
                    "gross_margin",
                    "operating_margin",
                    "net_margin",
                    "free_cash_flow_yield",
                    "pe_ratio",
                    "pb_ratio",
                    "ps_ratio",
                    "ev_to_ebitda",
                ]

                df = self._convert_numeric_columns(df, numeric_cols)

                return df

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
    ) -> Union[pd.DataFrame, Dict]:
        """Get company profile information.

        Args:
            symbol: Company ticker symbol
            provider: Data provider (default: "fmp")
            return_type: Return format ('df' for DataFrame, 'raw' for
            dictionary)

        Returns:
            Union[pd.DataFrame, Dict]: Company profile with fields:
                - name: Company name
                - sector: Industry sector
                - industry: Specific industry
                - description: Business description
                Additional fields vary by provider
        """
        try:
            data = self.client.equity.profile(symbol=symbol, provider=provider)  # type: ignore[union-attr]

            if return_type == "df":
                df = data.to_df()

                # Ensure consistent column order
                expected_columns = [
                    "name",
                    "sector",
                    "industry",
                    "description",
                ]

                # Add missing columns with None values
                df = self._ensure_columns_exist(df, expected_columns)

                return df[expected_columns]

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
    ) -> Union[pd.DataFrame, Dict]:
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
            Union[pd.DataFrame, Dict]: Available countries with columns:
                - country: Country name
                - iso: Two-letter ISO country code
                - description: Indicator description
                - frequency: Data frequency (D/W/M/Q/Y)
        """
        try:
            # Get all available indicators
            data = self.client.economy.available_indicators(provider=provider)  # type: ignore[union-attr]

            if return_type == "df":
                df = data.to_df()

                # Filter for the requested symbol
                df = df[df["symbol_root"] == symbol]

                # Select relevant columns and drop duplicates
                columns = ["country", "iso", "description", "frequency"]
                result = df[columns].drop_duplicates()

                # Sort by country name
                result = result.sort_values("country").reset_index(drop=True)

                return result

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
    ) -> Union[pd.DataFrame, Dict]:
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
            Union[pd.DataFrame, Dict]: Financial statement data.
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

            if return_type == "df":
                df = data.to_df()

                # Convert date column to datetime if present
                if "date" in df.columns:
                    df["date"] = pd.to_datetime(df["date"])
                    df.set_index("date", inplace=True)

                df = self._convert_numeric_columns(df, df.columns)

                return df

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
    ) -> Union[pd.DataFrame, Dict]:
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
            Union[pd.DataFrame, Dict]: Historical values for the attribute with
             columns:
                - date: Timestamp for the period
                - value: Attribute value
        """
        try:
            data = self.client.equity.fundamental.historical_attributes(  # type: ignore[union-attr]
                symbol=symbol, tag=tag, frequency=frequency, provider=provider
            )

            if return_type == "df":
                df = data.to_df()

                # Convert date column to datetime if present
                if "date" in df.columns:
                    df["date"] = pd.to_datetime(df["date"])
                    df.set_index("date", inplace=True)

                # Convert value column to numeric
                if "value" in df.columns:
                    df["value"] = pd.to_numeric(df["value"], errors='coerce')

                return df

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
    ) -> Union[pd.DataFrame, Dict]:
        """Search for available financial attributes/tags.

        Args:
            query: Search term (e.g., "marketcap", "revenue", "assets")
            provider: Data provider (default: "intrinio")
            return_type: Return format ('df' for DataFrame, 'raw' for
            dictionary)

        Returns:
            Union[pd.DataFrame, Dict]: Matching attributes with columns:
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

            if return_type == "df":
                df = data.to_df()

                # Ensure consistent column order
                expected_columns = [
                    "id",
                    "name",
                    "tag",
                    "statement_code",
                    "statement_type",
                    "parent_name",
                    "sequence",
                    "factor",
                    "transaction",
                    "type",
                    "unit",
                ]

                # Add missing columns with None values
                df = self._ensure_columns_exist(df, expected_columns)

                return df[expected_columns]

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
    ) -> Union[pd.DataFrame, Dict]:
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
            Union[pd.DataFrame, Dict]: Economic calendar with columns:
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

            if return_type == "df":
                df = data.to_df()

                # Convert timestamps to datetime
                if "date" in df.columns:
                    df["date"] = pd.to_datetime(df["date"])
                    df.set_index("date", inplace=True)

                # Convert timezone if requested
                if convert_timezone and not df.index.empty:
                    from datetime import time

                    # Handle timezone conversion based on provider
                    if provider in ["fmp", "tradingeconomics"]:
                        df.index = df.index.map(
                            lambda dt: dt.tz_localize("UTC").tz_convert(
                                "America/New_York"
                            )
                            if dt.time() != time(0, 0, 0)
                            else dt.tz_localize("America/New_York")
                        )
                    elif provider == "nasdaq":
                        df.index = df.index.map(
                            lambda dt: dt.tz_localize("America/New_York")
                            if dt.time() != time(0, 0, 0)
                            else dt
                        )

                numeric_cols = [
                    "actual",
                    "previous",
                    "consensus",
                    "change",
                    "change_percent",
                ]
                df = self._convert_numeric_columns(df, numeric_cols)

                return df

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
    ) -> Union[pd.DataFrame, Dict]:
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
            Union[pd.DataFrame, Dict]: Calendar events with type-specific
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

            if return_type == "df":
                df = data.to_df()

                # Convert date columns to datetime
                date_cols = ["date", "ex_date", "payment_date", "record_date"]
                for col in date_cols:
                    if col in df.columns:
                        df[col] = pd.to_datetime(df[col])
                        if col == "date":  # Set primary date column as index
                            df.set_index(col, inplace=True)

                # Convert numeric columns based on calendar type
                if calendar_type == "earnings":
                    numeric_cols = [
                        "eps_estimate",
                        "actual_eps",
                        "revenue_estimate",
                        "actual_revenue",
                    ]
                elif calendar_type == "dividends":
                    numeric_cols = ["amount"]
                elif calendar_type == "splits":
                    numeric_cols = ["from_factor", "to_factor"]
                elif calendar_type == "ipo":
                    numeric_cols = ["shares", "price"]
                    # Handle price range separately
                    if "price_range" in df.columns:
                        df["price_range"] = df["price_range"].astype(str)

                df = self._convert_numeric_columns(df, numeric_cols)

                return df

            return data.results

        except Exception as e:
            return self._handle_api_error(
                error=e,
                operation="get market calendar",
                return_type=return_type,
                log_level="warning",
                provider=provider,
            )
