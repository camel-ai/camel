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

# Example with ChatAgent using OpenBB toolkit
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
