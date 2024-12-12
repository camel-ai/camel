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

# Example 1: Stock quotes for multiple companies
print("\nExample 1: Stock quotes for multiple companies")
companies = ["AAPL", "MSFT", "GOOGL"]
for symbol in companies:
    res_quote = openbb_toolkit.OpenBBToolkit().get_stock_quote(
        symbol=symbol, source="iex"
    )
    print(f"\n{symbol} Stock Quote:")
    print(res_quote)
"""
===============================================================================
AAPL Stock Quote:
  symbol        name exchange  last_price  ... shares_outstanding   eps     pe
  earnings_announcement
0   AAPL  Apple Inc.   NASDAQ    246.6579  ...        15115800000  6.07  40.64
2025-01-30 21:00:00+00:00

[1 rows x 22 columns]

MSFT Stock Quote:
  symbol                   name exchange  last_price  ... shares_outstanding
  eps    pe     earnings_announcement
0   MSFT  Microsoft Corporation   NASDAQ      446.85  ...         7434880000
12.11  36.9 2025-01-28 21:00:00+00:00

[1 rows x 22 columns]

GOOGL Stock Quote:
  symbol           name exchange  last_price  ... shares_outstanding   eps  
  pe     earnings_announcement
0  GOOGL  Alphabet Inc.   NASDAQ      175.96  ...        12297382550  7.55  
23.31 2025-01-28 21:00:00+00:00

[1 rows x 22 columns]
===============================================================================
"""

# Example 2: Historical data for Apple stock
print("\nExample 2: Historical data for Apple stock")
res_hist = openbb_toolkit.OpenBBToolkit().get_historical_data(
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
                  open        high         low       close     volume
date                                                                 
2023-12-01  190.330002  191.559998  189.229996  191.240005   45679300
2023-12-04  189.979996  190.050003  187.449997  189.429993   43389500
2023-12-05  190.210007  194.399994  190.179993  193.419998   66628400
2023-12-06  194.449997  194.759995  192.110001  192.320007   41089700
2023-12-07  193.630005  195.000000  193.589996  194.270004   47477700
2023-12-08  194.199997  195.990005  193.669998  195.710007   53377300
2023-12-11  193.110001  193.490005  191.419998  193.179993   60943700
2023-12-12  193.080002  194.720001  191.720001  194.710007   52696900
2023-12-13  195.089996  198.000000  194.850006  197.960007   70404200
2023-12-14  198.020004  199.619995  196.160004  198.110001   66831600
2023-12-15  197.529999  198.399994  197.000000  197.570007  128256700
2023-12-18  196.089996  196.630005  194.389999  195.889999   55751900
2023-12-19  196.160004  196.949997  195.889999  196.940002   40714100
2023-12-20  196.899994  197.679993  194.830002  194.830002   52242800
2023-12-21  196.100006  197.080002  193.500000  194.679993   46482500
2023-12-22  195.179993  195.410004  192.970001  193.600006   37122800
2023-12-26  193.610001  193.889999  192.830002  193.050003   28919300
2023-12-27  192.490005  193.500000  191.089996  193.149994   48087700
2023-12-28  194.139999  194.660004  193.169998  193.580002   34049900
2023-12-29  193.899994  194.399994  191.729996  192.529999   42628800
===============================================================================
"""

# Example 3: Economic indicators
print("\nExample 3: Economic indicators")
toolkit = openbb_toolkit.OpenBBToolkit()

# Show available indicators
print("\nAvailable Economic Indicators:")
available_indicators = toolkit.get_available_indicators()
print("\nIndicators by country:")
country_counts = available_indicators.groupby('country').size()
print(country_counts)

print("\nSample Euro area indicators:")
euro_indicators = available_indicators[
    available_indicators['country'] == 'Euro area'
]
print(euro_indicators[["symbol", "description"]].head())
"""
===============================================================================
Available Economic Indicators:

Indicators by country:
country
Afghanistan     1
Albania        31
Algeria         8
Andorra         1
Angola          4
               ..
Vietnam        32
World          83
Yemen           4
Zambia          1
Zimbabwe        1
Length: 190, dtype: int64

Sample Euro area indicators:
      symbol                description
3    POLIREA   Policy rate - short term
79     CPIEA       Consumer price index
125   COREEA  Core consumer price index
174  Y10YDEA            Long term yield
256   M3YDEA              3 month yield
===============================================================================
"""

# Example with ChatAgent using OpenBB toolkit
agent = ChatAgent(
    system_message="""You are a helpful financial analyst that can use OpenBB 
        toolkit to analyze stocks and market data. When getting stock quotes, 
        always use 'iex' as the data source.""",
    tools=toolkit.get_tools(),
)

usr_msg = (
    "Compare the current stock prices of AAPL and MSFT "
    "with their 10-day moving averages"
)
response = agent.step(input_message=usr_msg)
print("\nAI Analysis:")
print(response.msgs[0].content)

"""
===============================================================================
AI Analysis:
Here are the current stock prices and the 10-day moving averages for Apple Inc.
(AAPL) and Microsoft Corporation (MSFT):

### Current Stock Prices
- **AAPL (Apple Inc.)**
  - Current Price: $246.67
- **MSFT (Microsoft Corporation)**
  - Current Price: $446.375

### 10-Day Moving Averages
To calculate the 10-day moving average, we will take the average of the closing
prices for the last 10 trading days.

#### AAPL Closing Prices (Last 10 Days)
- 10/13: $178.85
- 10/16: $178.72
- 10/17: $177.15
- 10/18: $175.84
- 10/19: $175.46
- 10/20: $172.88
- 10/23: $173.00
- 10/24: $173.44
- 10/25: $171.10
- 10/26: $166.89
- 10/27: $168.22

**10-Day Moving Average for AAPL:**
\[
\text{Average} = \frac{178.85 + 178.72 + 177.15 + 175.84 + 175.46 + 172.88 
+ 173.00 + 173.44 + 171.10 + 166.89 + 168.22}{10} = 174.65
\]

#### MSFT Closing Prices (Last 10 Days)
- 10/13: $327.73
- 10/16: $332.64
- 10/17: $332.06
- 10/18: $330.11
- 10/19: $331.32
- 10/20: $326.67
- 10/23: $329.32
- 10/24: $330.53
- 10/25: $340.67
- 10/26: $327.89
- 10/27: $329.81

**10-Day Moving Average for MSFT:**
\[
\text{Average} = \frac{327.73 + 332.64 + 332.06 + 330.11 + 331.32 + 326.67 
+ 329.32 + 330.53 + 340.67 + 327.89 + 329.81}{10} = 330.43
\]

### Summary
- **AAPL**
  - Current Price: $246.67
  - 10-Day Moving Average: $174.65
- **MSFT**
  - Current Price: $446.375
  - 10-Day Moving Average: $330.43

### Conclusion
- AAPL's current price is significantly above its 10-day moving average.
- MSFT's current price is also above its 10-day moving average.
===============================================================================
"""
