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
from camel.toolkits import OpenBBToolkit

# Initialize OpenBB toolkit with proper credentials
toolkit = OpenBBToolkit()

# Example 1: Stock quotes for multiple companies
print("\nExample 1: Stock quotes for multiple companies")
companies = ["AAPL", "MSFT", "GOOGL"]
for symbol in companies:
    res_quote = toolkit.get_stock_quote(symbol=symbol)
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
company_info = toolkit.get_company_profile(symbol="AAPL", provider="fmp")
print("\nApple Inc. Company Information:")
print(company_info)
"""
===============================================================================
Apple Inc. Company Information:
[FMPEquityProfileData(symbol=AAPL, name=Apple Inc., cik=0000320193, 
cusip=037833100, isin=US0378331005, lei=None, legal_name=None, 
stock_exchange=NASDAQ Global Select, sic=None, short_description=None, 
long_description=Apple Inc. designs, manufactures, and markets smartphones, 
personal computers, tablets, wearables, and accessories worldwide. The company 
offers iPhone, a line of smartphones; Mac, a line of personal computers; iPad, 
a line of multi-purpose tablets; and wearables, home, and accessories 
comprising AirPods, Apple TV, Apple Watch, Beats products, and HomePod. It 
also provides AppleCare support and cloud services; and operates various 
platforms, including the App Store that allow customers to discover and 
download applications and digital content, such as books, music, video, games, 
and podcasts. In addition, the company offers various services, such as Apple 
Arcade, a game subscription service; Apple Fitness+, a personalized fitness 
service; Apple Music, which offers users a curated listening experience with 
on-demand radio stations; Apple News+, a subscription news and magazine 
service; Apple TV+, which offers exclusive original content; Apple Card, a 
co-branded credit card; and Apple Pay, a cashless payment service, as well as 
licenses its intellectual property. The company serves consumers, and small 
and mid-sized businesses; and the education, enterprise, and government 
markets. It distributes third-party applications for its products through the 
App Store. The company also sells its products through its retail and online 
stores, and direct sales force; and third-party cellular network carriers, 
wholesalers, retailers, and resellers. Apple Inc. was founded in 1976 and is 
headquartered in Cupertino, California., ceo=Mr. Timothy D. Cook, 
company_url=https://www.apple.com, business_address=None, 
mailing_address=None, business_phone_no=408 996 1010, hq_address1=One Apple 
Park Way, hq_address2=None, hq_address_city=Cupertino, 
hq_address_postal_code=95014, hq_state=CA, hq_country=US, inc_state=None, 
inc_country=None, employees=164000, entity_legal_form=None, 
entity_status=None, latest_filing_date=None, irs_number=None, 
sector=Technology, industry_category=Consumer Electronics, 
industry_group=None, template=None, standardized_active=None, 
first_fundamental_date=None, last_fundamental_date=None, 
first_stock_price_date=1980-12-12, last_stock_price_date=None, is_etf=False, 
is_actively_trading=True, is_adr=False, is_fund=False, image=https://images.
financialmodelingprep.com/symbol/AAPL.png, currency=USD, 
market_cap=3785298636000, last_price=250.42, year_high=260.1, year_low=164.08, 
volume_avg=43821504, annualized_dividend_amount=0.99, beta=1.24)]
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
)
income_stmt = toolkit.get_financial_statement(
    symbol="MSFT",
    statement_type="income",
    period="annual",
    provider="fmp",
    limit=5,
)
cash_flow = toolkit.get_financial_statement(
    symbol="MSFT",
    statement_type="cash",
    period="annual",
    provider="fmp",
    limit=5,
)
print("\nMicrosoft Financial Statements Overview:")
print(f"Balance Sheet: {balance_sheet}")
print(f"Income Statement: {income_stmt}")
print(f"Cash Flow Statement: {cash_flow}")
"""
===============================================================================
Microsoft Financial Statements Overview:
Balance Sheet: [FMPBalanceSheetData(period_ending=2024-06-30, 
fiscal_period=FY, fiscal_year=2024, filing_date=2024-07-30, 
accepted_date=2024-07-30 16:06:22, reported_currency=USD, 
cash_and_cash_equivalents=18315000000.0, short_term_investments=57216000000.0, 
cash_and_short_term_investments=75531000000.0, net_receivables=56924000000.0, 
inventory=1246000000.0, other_current_assets=26033000000.0, 
total_current_assets=159734000000.0, plant_property_equipment_net=154552000000.
0, goodwill=119220000000.0, intangible_assets=27597000000.0, 
goodwill_and_intangible_assets=146817000000.0, 
long_term_investments=14600000000.0, tax_assets=None, 
other_non_current_assets=36460000000.0, non_current_assets=352429000000.0, ..
===============================================================================
"""

# Example 5: Financial Analysis with ChatAgent
print("\nExample 5: Financial Analysis with ChatAgent")

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

# Example 6: ChatAgent using OpenBB toolkit
print("\nExample 6: ChatAgent using OpenBB toolkit")
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
