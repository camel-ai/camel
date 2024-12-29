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

from camel.agents import ChatAgent
from camel.toolkits import openbb_toolkit

# Initialize OpenBB toolkit with proper credentials
toolkit = openbb_toolkit.OpenBBToolkit()

# Example 1: Stock quotes for multiple companies
print("\nExample 1: Stock quotes for multiple companies")
companies = ["AAPL", "MSFT", "GOOGL"]
for symbol in companies:
    res_quote = toolkit.get_stock_quote(symbol=symbol, source="iex")
    print(f"\n{symbol} Stock Quote:")
    print(res_quote)
"""
===============================================================================
AAPL Stock Quote:
[YFinanceEquityQuoteData(symbol=AAPL, asset_type=EQUITY, name=Apple Inc.,
exchange=NMS, bid=249.26, bid_size=5000, bid_exchange=None, ask=250.02,
ask_size=400, ask_exchange=None, quote_conditions=None, quote_indicators=None,
sales_conditions=None, sequence_number=None, market_center=None,
participant_timestamp=None, trf_timestamp=None, sip_timestamp=None,
last_price=249.79, last_tick=None, last_size=None, last_timestamp=None,
open=247.46, high=251.85, low=247.0949, close=None, volume=58911560,
exchange_volume=None, prev_close=248.05, change=None, change_percent=None,
year_high=254.28, year_low=164.08, ma_50d=234.3126, ma_200d=210.4949,
volume_average=42989052.0, volume_average_10d=44930240.0, currency=USD)]

MSFT Stock Quote:
[YFinanceEquityQuoteData(symbol=MSFT, asset_type=EQUITY,
name=Microsoft Corporation, exchange=NMS, bid=418.95, bid_size=100,
bid_exchange=None, ask=437.26, ask_size=100, ask_exchange=None,
quote_conditions=None, quote_indicators=None, sales_conditions=None,
sequence_number=None, market_center=None, participant_timestamp=None,
trf_timestamp=None, sip_timestamp=None, last_price=437.03, last_tick=None,
last_size=None, last_timestamp=None, open=441.62, high=443.1834, low=436.33,
close=None, volume=21207330, exchange_volume=None, prev_close=437.39,
change=None, change_percent=None, year_high=468.35, year_low=366.5,
ma_50d=426.4474, ma_200d=424.4953, volume_average=20174949.0,
volume_average_10d=21000220.0, currency=USD)]

GOOGL Stock Quote:
[YFinanceEquityQuoteData(symbol=GOOGL, asset_type=EQUITY, name=Alphabet Inc.,
exchange=NMS, bid=188.33, bid_size=300, bid_exchange=None, ask=188.56,
ask_size=200, ask_exchange=None, quote_conditions=None, quote_indicators=None,
sales_conditions=None, sequence_number=None, market_center=None,
participant_timestamp=None, trf_timestamp=None, sip_timestamp=None,
last_price=188.51, last_tick=None, last_size=None, last_timestamp=None,
open=191.625, high=193.03, low=188.38, close=None, volume=31130881,
exchange_volume=None, prev_close=188.4, change=None, change_percent=None,
year_high=201.42, year_low=130.67, ma_50d=173.84, ma_200d=167.58334,
volume_average=27155819.0, volume_average_10d=38432110.0, currency=USD)]
===============================================================================
"""

# Example 2: Historical data for Apple stock
print("\nExample 2: Historical data for Apple stock")
res_hist = toolkit.get_historical_data(
    symbol="AAPL",
    start_date="2023-12-01",
    end_date="2023-12-31",
    interval="1d",
)
print("\nRecent Historical Data for AAPL:")
print(res_hist)
"""
===============================================================================
Recent Historical Data for AAPL:
{'results': [YFinanceEquityHistoricalData(date=2023-12-01,
open=190.3300018310547, high=191.55999755859375, low=189.22999572753906,
close=191.24000549316406, volume=45679300, vwap=None, split_ratio=None,
dividend=None), YFinanceEquityHistoricalData(date=2023-12-04,
open=189.97999572753906, high=190.0500030517578, low=187.4499969482422,
close=189.42999267578125, volume=43389500, vwap=None, split_ratio=None,
dividend=None), YFinanceEquityHistoricalData(date=2023-12-05,
open=190.2100067138672, high=194.39999389648438, low=190.17999267578125,
close=193.4199981689453, volume=66628400, vwap=None, split_ratio=None,
dividend=None), YFinanceEquityHistoricalData(date=2023-12-06,
open=194.4499969482422, high=194.75999450683594, low=192.11000061035156,
close=192.32000732421875, volume=41089700, vwap=None, split_ratio=None,
dividend=None), YFinanceEquityHistoricalData(date=2023-12-07,
open=193.6300048828125, high=195.0, low=193.58999633789062,
close=194.27000427246094, volume=47477700, vwap=None, split_ratio=None,
dividend=None), YFinanceEquityHistoricalData(date=2023-12-08,
open=194.1999969482422, high=195.99000549316406, low=193.6699981689453,
close=195.7100067138672, volume=53377300, vwap=None, split_ratio=None,
dividend=None), YFinanceEquityHistoricalData(date=2023-12-11,
open=193.11000061035156, high=193.49000549316406, low=191.4199981689453,
close=193.17999267578125, volume=60943700, vwap=None, split_ratio=None,
dividend=None), YFinanceEquityHistoricalData(date=2023-12-12,
open=193.0800018310547, high=194.72000122070312, low=191.72000122070312,
close=194.7100067138672, volume=52696900, vwap=None, split_ratio=None,
dividend=None), YFinanceEquityHistoricalData(date=2023-12-13,
open=195.08999633789062, high=198.0, low=194.85000610351562,
close=197.9600067138672, volume=70404200, vwap=None, split_ratio=None,
dividend=None), YFinanceEquityHistoricalData(date=2023-12-14,
open=198.02000427246094, high=199.6199951171875, low=196.16000366210938,
close=198.11000061035156, volume=66831600, vwap=None, split_ratio=None,
dividend=None), YFinanceEquityHistoricalData(date=2023-12-15,
open=197.52999877929688, high=198.39999389648438, low=197.0,
close=197.57000732421875, volume=128256700, vwap=None, split_ratio=None,
dividend=None), YFinanceEquityHistoricalData(date=2023-12-18,
open=196.08999633789062, high=196.6300048828125, low=194.38999938964844,
close=195.88999938964844, volume=55751900, vwap=None, split_ratio=None,
dividend=None), YFinanceEquityHistoricalData(date=2023-12-19,
open=196.16000366210938, high=196.9499969482422, low=195.88999938964844,
close=196.94000244140625, volume=40714100, vwap=None, split_ratio=None,
dividend=None), YFinanceEquityHistoricalData(date=2023-12-20,
open=196.89999389648438, high=197.67999267578125, low=194.8300018310547,
close=194.8300018310547, volume=52242800, vwap=None, split_ratio=None,
dividend=None), YFinanceEquityHistoricalData(date=2023-12-21,
open=196.10000610351562, high=197.0800018310547, low=193.5,
close=194.67999267578125, volume=46482500, vwap=None, split_ratio=None,
dividend=None), YFinanceEquityHistoricalData(date=2023-12-22,
open=195.17999267578125, high=195.41000366210938, low=192.97000122070312,
close=193.60000610351562, volume=37122800, vwap=None, split_ratio=None,
dividend=None), YFinanceEquityHistoricalData(date=2023-12-26,
open=193.61000061035156, high=193.88999938964844, low=192.8300018310547,
close=193.0500030517578, volume=28919300, vwap=None, split_ratio=None,
dividend=None), YFinanceEquityHistoricalData(date=2023-12-27,
open=192.49000549316406, high=193.5, low=191.08999633789062,
close=193.14999389648438, volume=48087700, vwap=None, split_ratio=None,
dividend=None), YFinanceEquityHistoricalData(date=2023-12-28,
open=194.13999938964844, high=194.66000366210938, low=193.1699981689453,
close=193.5800018310547, volume=34049900, vwap=None, split_ratio=None,
dividend=None), YFinanceEquityHistoricalData(date=2023-12-29,
open=193.89999389648438, high=194.39999389648438, low=191.72999572753906,
close=192.52999877929688, volume=42628800, vwap=None, split_ratio=None,
dividend=None)]}
===============================================================================
"""

# Example 3: Company Information
print("\nExample 3: Company Information")
company_info = toolkit.get_company_profile(
    symbol="AAPL", provider="fmp", return_type="df"
)
print("\nApple Inc. Company Information:")
print(company_info)
"""
===============================================================================
Apple Inc. Company Information:
         name      sector industry description
0  Apple Inc.  Technology     None        None
===============================================================================
"""

# Example 4: Financial Statements
print("\nExample 4: Financial Statements")
balance_sheet = toolkit.get_financial_statement(
    symbol="MSFT",
    statement_type="balance",
    period="annual",
    provider="fmp",
    limit=5,
    return_type="df",
)
income_stmt = toolkit.get_financial_statement(
    symbol="MSFT",
    statement_type="income",
    period="annual",
    provider="fmp",
    limit=5,
    return_type="df",
)
cash_flow = toolkit.get_financial_statement(
    symbol="MSFT",
    statement_type="cash",
    period="annual",
    provider="fmp",
    limit=5,
    return_type="df",
)
print("\nMicrosoft Financial Statements Overview:")
print(f"Balance Sheet: {balance_sheet}")
print(f"Income Statement: {income_stmt}")
print(f"Cash Flow Statement: {cash_flow}")
"""
===============================================================================
Microsoft Financial Statements Overview:
Balance Sheet:    period_ending  fiscal_period  fiscal_year  filing_date  ...  
  total_debt      net_debt  link  final_link
0            NaN            NaN         2024          NaN  ...  9.785200e+10  
7.953700e+10   NaN         NaN
1            NaN            NaN         2023          NaN  ...  7.944100e+10  
4.473700e+10   NaN         NaN
2            NaN            NaN         2022          NaN  ...  7.840000e+10  
6.446900e+10   NaN         NaN
3            NaN            NaN         2021          NaN  ...  8.227800e+10  
6.805400e+10   NaN         NaN
4            NaN            NaN         2020          NaN  ...  8.211000e+10  
6.853400e+10   NaN         NaN

[5 rows x 46 columns]
Income Statement:    period_ending  fiscal_period  fiscal_year  ...  
link  final_link  other_expenses
0            NaN            NaN         2024  ...   
NaN         NaN             NaN
1            NaN            NaN         2023  ...   
NaN         NaN    -223000000.0
2            NaN            NaN         2022  ...   
NaN         NaN     -32000000.0
3            NaN            NaN         2021  ...   
NaN         NaN      98000000.0
4            NaN            NaN         2020  ...   
NaN         NaN     -40000000.0

[5 rows x 36 columns]
Cash Flow Statement:    period_ending  fiscal_period  fiscal_year  ...  
free_cash_flow  link  final_link
0            NaN            NaN         2024  ...    
7.407100e+10   NaN         NaN
1            NaN            NaN         2023  ...    
5.947500e+10   NaN         NaN
2            NaN            NaN         2022  ...    
6.514900e+10   NaN         NaN
3            NaN            NaN         2021  ...    
5.611800e+10   NaN         NaN
4            NaN            NaN         2020  ...    
4.523400e+10   NaN         NaN

[5 rows x 38 columns]
===============================================================================
"""

# Example 5: Market Data
print("\nExample 5: Market Data")
market_movers = toolkit.get_market_movers(
    category="gainers", source="fmp", return_type="df"
)
print("\nMarket Overview:")
print(f"Top Gainers: {market_movers}")
"""
===============================================================================
Top Gainers: {'result': [YFGainersData(symbol=KC, name=Kingsoft Cloud Holdings 
Limited, price=11.96, change=1.7600002, percent_change=0.17254905999999998, 
volume=6134763, open=11.76, high=12.84, low=11.6, previous_close=10.2, 
ma50=5.8358, ma200=3.5662, year_high=12.84, year_low=2.02, 
market_cap=2840176896.0, shares_outstanding=237472992.0, book_value=29.014, 
price_to_book=0.4122148, eps_ttm=-1.17, eps_forward=-0.41, 
pe_forward=-29.170732, dividend_yield=0.0, exchange=NMS, 
exchange_timezone=America/New_York, earnings_date=2024-11-19 06:24:15-05:00, 
currency=USD), YFGainersData(symbol=LW, name=Lamb Weston Holdings, Inc., 
price=68.5083, change=3.228302, percent_change=0.04945316, volume=629067, 
open=64.86, high=68.59, low=64.886, previous_close=65.28, ma50=76.2034, 
ma200=77.0976, year_high=111.875, year_low=52.99, market_cap=9772092416.0, 
shares_outstanding=142640992.0, book_value=12.444, price_to_book=5.5053277, 
eps_ttm=2.54, eps_forward=4.98, pe_forward=13.756687, dividend_yield=0.0, 
exchange=NYQ, exchange_timezone=America/New_York, earnings_date=2024-12-19 
06:00:00-05:00, currency=USD), YFGainersData(symbol=GDS, 
name=GDS Holdings Limited, price=21.67, change=1.0200005, 
percent_change=0.0493947, volume=337231, open=20.65, high=21.73, low=20.53, 
previous_close=20.65, ma50=20.8845, ma200=13.93865, year_high=24.74, 
year_low=5.01, market_cap=4094524672.0, shares_outstanding=188948992.0, 
book_value=99.15, price_to_book=0.21855775, eps_ttm=-2.98, eps_forward=-0.6, 
pe_forward=-36.116665, dividend_yield=0.0, exchange=NGM, 
exchange_timezone=America/New_York, earnings_date=2024-11-19 07:00:00-05:00, 
currency=USD), YFGainersData(symbol=AMED, name=Amedisys Inc, price=89.81, 
change=3.8600006, percent_change=0.04492552, volume=982418, open=89.5, 
high=90.0, low=89.355, previous_close=85.95, ma50=90.9384, ma200=94.0375, 
year_high=98.95, year_low=82.15, market_cap=2941681664.0, 
shares_outstanding=32754500.0, book_value=35.045, price_to_book=2.562705, 
eps_ttm=2.52, eps_forward=5.11, pe_forward=17.575342, dividend_yield=0.0, 
exchange=NMS, exchange_timezone=America/New_York, 
earnings_date=2024-11-06 16:30:00-05:00, currency=USD)]}
===============================================================================
"""

# Example 6: Economic Indicators
print("\nExample 6: Economic Indicators\n")

# Get US GDP in USD
gdp_data = toolkit.get_economic_data(
    symbols="GDP",
    country="US",
    transform="tusd",
    start_date="2014-01-10",
)
print("\nUS GDP Data:")
print(gdp_data)

# Get inflation rates for multiple countries
inflation = toolkit.get_economic_data(
    symbols="CPI",
    country=["US", "JP", "DE"],
    transform="toya",  # Year-over-year change
)
print("\nInflation Rates:")
print(inflation)

# Get multiple indicators with transform
data = toolkit.get_economic_data(
    symbols=["CORE", "CPI"], country=["US", "DE", "JP"], transform="toya"
)
print("\nMultiple Economic Indicators:")
print(data)
"""
===============================================================================
...
S~TOYA, country=United States, value=0.03411), 
EconDbEconomicIndicatorsData(date=2024-05-01, symbol_root=CPI, 
symbol=CPIDE~TOYA, country=Germany, value=0.024034), 
EconDbEconomicIndicatorsData(date=2024-05-01, symbol_root=CPI, 
symbol=CPIJP~TOYA, country=Japan, value=0.02854), 
EconDbEconomicIndicatorsData(date=2024-05-01, symbol_root=CPI, 
symbol=CPIUS~TOYA, country=United States, value=0.0325), 
EconDbEconomicIndicatorsData(date=2024-06-01, symbol_root=CORE, 
symbol=COREDE~TOYA, country=Germany, value=0.03291), 
EconDbEconomicIndicatorsData(date=2024-06-01, symbol_root=CORE, 
symbol=COREJP~TOYA, country=Japan, value=0.021072999999999998), 
EconDbEconomicIndicatorsData(date=2024-06-01, symbol_root=CORE, 
symbol=COREUS~TOYA, country=United States, value=0.03277), 
EconDbEconomicIndicatorsData(date=2024-06-01, symbol_root=CPI, 
symbol=CPIDE~TOYA, country=Germany, value=0.02226), 
EconDbEconomicIndicatorsData(date=2024-06-01, symbol_root=CPI, 
symbol=CPIJP~TOYA, country=Japan, value=0.02852), 
EconDbEconomicIndicatorsData(date=2024-06-01, symbol_root=CPI, 
symbol=CPIUS~TOYA, country=United States, value=0.029759999999999998), 
EconDbEconomicIndicatorsData(date=2024-07-01, symbol_root=CORE, 
symbol=COREDE~TOYA, country=Germany, value=0.032690000000000004), 
EconDbEconomicIndicatorsData(date=2024-07-01, symbol_root=CORE, 
symbol=COREJP~TOYA, country=Japan, value=0.019066), 
EconDbEconomicIndicatorsData(date=2024-07-01, symbol_root=CORE, 
symbol=COREUS~TOYA, country=United States, value=0.03213), 
EconDbEconomicIndicatorsData(date=2024-07-01, symbol_root=CPI, 
symbol=CPIDE~TOYA, country=Germany, value=0.023056999999999998), 
EconDbEconomicIndicatorsData(date=2024-07-01, symbol_root=CPI, 
symbol=CPIJP~TOYA, country=Japan, value=0.027440000000000003), 
EconDbEconomicIndicatorsData(date=2024-07-01, symbol_root=CPI, 
symbol=CPIUS~TOYA, country=United States, value=0.02924), 
EconDbEconomicIndicatorsData(date=2024-08-01, symbol_root=CORE, 
symbol=COREDE~TOYA, country=Germany, value=0.03008), 
EconDbEconomicIndicatorsData(date=2024-08-01, symbol_root=CORE, 
symbol=COREJP~TOYA, country=Japan, value=0.020913), 
EconDbEconomicIndicatorsData(date=2024-08-01, symbol_root=CORE, 
symbol=COREUS~TOYA, country=United States, value=0.03266), 
EconDbEconomicIndicatorsData(date=2024-08-01, symbol_root=CPI, 
symbol=CPIDE~TOYA, country=Germany, value=0.018723), 
EconDbEconomicIndicatorsData(date=2024-08-01, symbol_root=CPI, 
symbol=CPIJP~TOYA, country=Japan, value=0.030219999999999997), 
EconDbEconomicIndicatorsData(date=2024-08-01, symbol_root=CPI, 
symbol=CPIUS~TOYA, country=United States, value=0.025910000000000002), 
EconDbEconomicIndicatorsData(date=2024-09-01, symbol_root=CORE, 
symbol=COREDE~TOYA, country=Germany, value=0.03008), 
EconDbEconomicIndicatorsData(date=2024-09-01, symbol_root=CORE, 
symbol=COREJP~TOYA, country=Japan, value=0.019924), 
EconDbEconomicIndicatorsData(date=2024-09-01, symbol_root=CORE, 
symbol=COREUS~TOYA, country=United States, value=0.03259), 
EconDbEconomicIndicatorsData(date=2024-09-01, symbol_root=CPI, 
symbol=CPIDE~TOYA, country=Germany, value=0.016129), 
EconDbEconomicIndicatorsData(date=2024-09-01, symbol_root=CPI, 
symbol=CPIJP~TOYA, country=Japan, value=0.025419999999999998), 
EconDbEconomicIndicatorsData(date=2024-09-01, symbol_root=CPI, 
symbol=CPIUS~TOYA, country=United States, value=0.024075000000000003), 
EconDbEconomicIndicatorsData(date=2024-10-01, symbol_root=CORE, 
symbol=COREDE~TOYA, country=Germany, value=0.03258), 
EconDbEconomicIndicatorsData(date=2024-10-01, symbol_root=CORE, 
symbol=COREJP~TOYA, country=Japan, value=0.021739), 
EconDbEconomicIndicatorsData(date=2024-10-01, symbol_root=CORE, 
symbol=COREUS~TOYA, country=United States, value=0.033), 
EconDbEconomicIndicatorsData(date=2024-10-01, symbol_root=CPI, 
symbol=CPIDE~TOYA, country=Germany, value=0.020373000000000002), 
EconDbEconomicIndicatorsData(date=2024-10-01, symbol_root=CPI, 
symbol=CPIJP~TOYA, country=Japan, value=0.022409), 
EconDbEconomicIndicatorsData(date=2024-10-01, symbol_root=CPI, 
symbol=CPIUS~TOYA, country=United States, value=0.02576), 
EconDbEconomicIndicatorsData(date=2024-11-01, symbol_root=CORE, 
symbol=COREDE~TOYA, country=Germany, value=0.031139999999999998), 
EconDbEconomicIndicatorsData(date=2024-11-01, symbol_root=CORE, 
symbol=COREJP~TOYA, country=Japan, value=0.023607), 
EconDbEconomicIndicatorsData(date=2024-11-01, symbol_root=CORE, 
symbol=COREUS~TOYA, country=United States, value=0.033), 
EconDbEconomicIndicatorsData(date=2024-11-01, symbol_root=CPI, 
symbol=CPIDE~TOYA, country=Germany, value=0.022165), 
EconDbEconomicIndicatorsData(date=2024-11-01, symbol_root=CPI, 
symbol=CPIJP~TOYA, country=Japan, value=0.028999999999999998), 
EconDbEconomicIndicatorsData(date=2024-11-01, symbol_root=CPI, 
symbol=CPIUS~TOYA, country=United States, value=0.02733)]
===============================================================================
"""

# Example 7: Economic Indicator Countries
print("\nExample 7: Economic Indicator Countries")

# Get countries with GDP data
gdp_countries = toolkit.get_indicator_countries(symbol="GDP", return_type="df")
print("\nCountries with GDP data:")
print(gdp_countries)

# Show specific country metadata
if not gdp_countries.empty:
    us_gdp = gdp_countries[gdp_countries["iso"] == "US"]
    if not us_gdp.empty:
        print("\nUS GDP Metadata:")
        print(f"Description: {us_gdp['description'].iloc[0]}")
        print(f"Frequency: {us_gdp['frequency'].iloc[0]}")

# Get countries with inflation data
cpi_countries = toolkit.get_indicator_countries(symbol="CPI", return_type="df")
print("\nCountries with CPI (inflation) data:")
print(cpi_countries)
"""
===============================================================================
Countries with GDP data:
                 country iso             description frequency
0                Albania  AL  Gross domestic product         Q
1              Argentina  AR  Gross domestic product         Q
2              Australia  AU  Gross domestic product         Q
3                Austria  AT  Gross domestic product         Q
4             Azerbaijan  AZ  Gross domestic product         Q
..                   ...  ..                     ...       ...
83  United Arab Emirates  AE  Gross domestic product         Y
84        United Kingdom  UK  Gross domestic product         Q
85         United States  US  Gross domestic product         Q
86            Uzbekistan  UZ  Gross domestic product         Y
87               Vietnam  VN  Gross domestic product         Q

[88 rows x 4 columns]

US GDP Metadata:
Description: Gross domestic product
Frequency: Q

Countries with CPI (inflation) data:
                 country iso           description frequency
0            Afghanistan  AF  Consumer price index         M
1                Albania  AL  Consumer price index         M
2    Antigua And Barbuda  AG  Consumer price index         M
3              Argentina  AR  Consumer price index         M
4                Armenia  AM  Consumer price index         M
..                   ...  ..                   ...       ...
166           Uzbekistan  UZ  Consumer price index         M
167            Venezuela  VE  Consumer price index         M
168              Vietnam  VN  Consumer price index         M
169               Zambia  ZM  Consumer price index         M
170             Zimbabwe  ZW  Consumer price index         M
===============================================================================
"""

# Example 8: Financial Analysis with ChatAgent
print("\nExample 8: Financial Analysis with ChatAgent")

# Initialize agent with toolkit tools
tech_agent = ChatAgent(
    system_message="""You are a financial analysis expert. Analyze the provided
    financial data and provide insights about the company's financial 
    health.""",
    tools=toolkit.get_tools(),
)

# Get company data
symbol = "AAPL"

# Get financial statements using correct provider
balance_sheet = toolkit.get_financial_statement(
    symbol=symbol,
    statement_type="balance",
    period="annual",
    provider="fmp",
    limit=3,
)
print(f"\n{symbol} Balance Sheet:")
print(balance_sheet)

income_stmt = toolkit.get_financial_statement(
    symbol=symbol,
    statement_type="income",
    period="annual",
    provider="fmp",
    limit=3,
)
print(f"\n{symbol} Income Statement:")
print(income_stmt)

# Get financial metrics
metrics = toolkit.get_financial_metrics(
    symbol=symbol, period="annual", provider="fmp", limit=3
)
print(f"\n{symbol} Financial Metrics:")
print(metrics)

# Get company profile
profile = toolkit.get_company_profile(symbol=symbol, provider="fmp")
print(f"\n{symbol} Company Profile:")
print(profile)

# Example analysis prompt
analysis_prompt = f"""
Analyze {symbol}'s financial health based on:
1. Balance sheet strength
2. Profitability trends
3. Key financial metrics
4. Business profile

Provide a concise summary of strengths and potential concerns.
"""

response = tech_agent.step(input_message=analysis_prompt)
print("\nFinancial Analysis:")
print(response.msgs[0].content)
"""
===============================================================================
Financial Analysis:
### Financial Health Analysis of Apple Inc. (AAPL)

#### 1. Balance Sheet Strength
- **Total Debt**: The total debt has shown a decreasing trend from 
approximately $132.48 billion in 2022 to $106.63 billion in 2024. This 
indicates a reduction in leverage and improved financial stability.
- **Net Debt**: Similarly, net debt has decreased from about $108.83 billion 
in 2022 to $76.69 billion in 2024, suggesting that the company is managing its 
debt effectively and has sufficient cash reserves to cover its liabilities.

#### 2. Profitability Trends
- **Revenue Growth**: AAPL has consistently generated significant revenue, 
with a notable increase in profitability over the years. The income statement 
shows a healthy profit margin, indicating effective cost management.
- **Operating Income**: The operating income has remained strong, reflecting 
the company's ability to generate profit from its core operations.
- **Interest Expenses**: Interest expenses have been relatively stable, which 
is a positive sign as it indicates that the company is not over-leveraged.

#### 3. Key Financial Metrics
- **Market Capitalization**: As of 2024, AAPL's market cap is approximately 
$3.50 trillion, making it one of the most valuable companies in the world.
- **P/E Ratio**: The P/E ratio has increased from 24.44 in 2022 to 37.29 in 
2024, indicating that the stock may be overvalued relative to its earnings, 
which could be a concern for investors.
- **Dividend Yield**: The dividend yield has decreased slightly, reflecting a 
focus on reinvesting profits for growth rather than returning cash to 
shareholders.
- **Graham Number**: The Graham number indicates that the stock may be 
overvalued, as the calculated value is negative, suggesting that the stock 
price exceeds its intrinsic value based on earnings and book value.

#### 4. Business Profile
- **Industry Position**: AAPL is a leader in the technology sector, 
particularly in consumer electronics, software, and services. Its strong brand 
loyalty and innovative product offerings contribute to its competitive 
advantage.
- **Growth Potential**: The company continues to invest in research and 
development, positioning itself for future growth in emerging technologies and 
services.

### Summary of Strengths and Potential Concerns
**Strengths:**
- Strong balance sheet with decreasing total and net debt.
- Consistent revenue and operating income growth.
- Leading market capitalization and brand recognition.

**Potential Concerns:**
- Increasing P/E ratio may indicate overvaluation.
- Decreasing dividend yield could concern income-focused investors.
- Negative Graham number suggests potential overvaluation based on intrinsic 
value metrics.

Overall, AAPL demonstrates robust financial health, but investors should be 
cautious of valuation metrics that may indicate a correction in stock price.
===============================================================================
"""

# Example 9: Economic Analysis with ChatAgent
print("\nExample 9: Economic Analysis with ChatAgent")

# Initialize economic analysis agent
econ_agent = ChatAgent(
    system_message="""You are an economic analyst that can use OpenBB toolkit
    to analyze economic indicators and their trends.""",
    tools=toolkit.get_tools(),
)

# Get economic data using get_economic_data instead of get_historical_data
gdp_data = toolkit.get_economic_data(
    symbols="GDP",
    country="US",
    transform="toya",
    start_date="2022-01-01",
    end_date="2023-12-31",
)
print("\nUS GDP Growth Rate:")
print(gdp_data)

cpi_data = toolkit.get_economic_data(
    symbols="CPI",
    country="US",
    transform="toya",
    start_date="2022-01-01",
    end_date="2023-12-31",
)
print("\nUS Inflation Rate (CPI):")
print(cpi_data)

# Economic analysis prompt
econ_prompt = """
Based on the GDP and CPI data:
1. What is the current state of US economic growth?
2. How has inflation trended over the past year?
3. What do these indicators suggest about the overall economic health?
"""

econ_response = econ_agent.step(input_message=econ_prompt)
print("\nEconomic Analysis:")
print(econ_response.msgs[0].content)

# Example 10: Market Research with ChatAgent
print("\nExample 10: Market Research with ChatAgent")
research_agent = ChatAgent(
    system_message="""You are a market research analyst that can use OpenBB
    toolkit to provide comprehensive market insights.""",
    tools=toolkit.get_tools(),
)

research_msg = (
    "Provide an overview of the technology sector, focusing on the top tech "
    "companies (AAPL, MSFT, GOOGL). Include their financial metrics and "
    "market performance."
)
research_response = research_agent.step(input_message=research_msg)
print("\nMarket Research Analysis:")
print(research_response.msgs[0].content)
"""
===============================================================================
Market Research Analysis:
### Overview of the Technology Sector

The technology sector is one of the most dynamic and rapidly evolving sectors 
in the global economy. It encompasses a wide range of industries, including 
software, hardware, telecommunications, and information technology services. 
The sector is characterized by innovation, high growth potential, and 
significant investment in research and development.

#### Top Tech Companies

1. **Apple Inc. (AAPL)**
   - **Market Capitalization**: $3.495 trillion
   - **P/E Ratio**: 37.29
   - **Dividend Yield**: 0.44%
   - **Recent Stock Price**: $255.59
   - **52-Week Range**: $164.08 - $260.10
   - **EPS**: $6.07
   - **Recent Performance**: 
     - Change: -3.43
     - Change Percentage: -1.32%

2. **Microsoft Corporation (MSFT)**
   - **Market Capitalization**: $3.394 trillion
   - **P/E Ratio**: 38.51
   - **Dividend Yield**: 0.64%
   - **Recent Stock Price**: $430.53
   - **52-Week Range**: $366.50 - $468.35
   - **EPS**: $12.13
   - **Recent Performance**: 
     - Change: -7.58
     - Change Percentage: -1.73%

3. **Alphabet Inc. (GOOGL)**
   - **Market Capitalization**: $1.764 trillion
   - **P/E Ratio**: 23.91
   - **Dividend Yield**: 0.00%
   - **Recent Stock Price**: $192.76
   - **52-Week Range**: $130.67 - $201.42
   - **EPS**: $7.54
   - **Recent Performance**: 
     - Change: -2.84
     - Change Percentage: -1.45%

### Summary of Financial Metrics

| Company | Market Cap (Trillions) | P/E Ratio | Dividend Yield | EPS |
| Recent Price | Change | Change (%) |
|---------|------------------------|-----------|----------------|-----|
--------------|--------|------------|
| AAPL    | 3.495                  | 37.29     | 0.44%          | 6.07|
| $255.59      | -3.43  | -1.32%     |
| MSFT    | 3.394                  | 38.51     | 0.64%          | 12.13|
| $430.53     | -7.58  | -1.73%     |
| GOOGL   | 1.764                  | 23.91     | 0.00%          | 7.54|
| $192.76      | -2.84  | -1.45%     |

### Conclusion

The technology sector continues to be a driving force in the global economy, 
with major players like Apple, Microsoft, and Alphabet leading the way. These 
companies demonstrate strong financial metrics, although they have recently 
experienced slight declines in stock prices. Investors remain optimistic about 
the long-term growth potential of these tech giants, given their innovation 
and market leadership.
===============================================================================
"""

# Example 11: ChatAgent using OpenBB toolkit
print("\nExample 11: ChatAgent using OpenBB toolkit")
agent = ChatAgent(
    system_message="""You are a helpful financial analyst that can use
    OpenBB toolkit to analyze stocks and market data. When comparing stock
    prices with moving averages, use the data directly from the stock quotes
    including the volume_average_10d field for accurate analysis.""",
    tools=toolkit.get_tools(),
)

usr_msg = (
    "Compare the current stock prices of AAPL and MSFT with their trading "
    "volumes and 10-day average volumes using the quote data"
)
response = agent.step(input_message=usr_msg)
print("\nAI Analysis:")
print(response.msgs[0].content)
"""
===============================================================================
AI Analysis:
Here is the comparison of the current stock prices, trading volumes,
and 10-day average volumes for Apple Inc. (AAPL) and Microsoft Corporation
(MSFT):

### Apple Inc. (AAPL)
- **Current Price:** $244.75
- **Current Trading Volume:** 44,476,711
- **10-Day Average Volume:** 56,030,030

### Microsoft Corporation (MSFT)
- **Current Price:** $424.63
- **Current Trading Volume:** 20,960,541
- **10-Day Average Volume:** 25,580,240

### Summary
- **AAPL** has a higher current trading volume compared to its 10-day
average volume, indicating increased trading activity.
- **MSFT** has a lower current trading volume than its 10-day average
volume, suggesting less trading activity relative to the past 10 days.

If you need further analysis or details, feel free to ask!
===============================================================================
"""
