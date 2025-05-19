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
from camel.configs import QwenConfig
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

model = ModelFactory.create(
    model_platform=ModelPlatformType.QWEN,
    model_type=ModelType.QWEN_2_5_CODER_32B,
    model_config_dict=QwenConfig(temperature=0.2).as_dict(),
)

# Define system message
sys_msg = "You are a helpful assistant."

# Set agent
camel_agent = ChatAgent(system_message=sys_msg, model=model)

user_msg = """give me python code to develop a trading bot"""

# Get response information
response = camel_agent.step(user_msg)
print(response.msgs[0].content)

'''
===============================================================================
Creating a trading bot involves several steps, including data acquisition, 
strategy development, backtesting, and live trading. Below is a simplified 
example of a trading bot using Python. This example will use the `ccxt` 
library to interact with cryptocurrency exchanges and `pandas` for data 
manipulation. The strategy used here is a simple moving average crossover 
strategy.

First, you need to install the required libraries:

```bash
pip install ccxt pandas
```

Here's a basic example of a trading bot:

```python
import ccxt
import pandas as pd
import time

# Initialize the exchange
exchange = ccxt.binance({
    'apiKey': 'YOUR_API_KEY',
    'secret': 'YOUR_SECRET_KEY',
})

# Define the trading parameters
symbol = 'BTC/USDT'
timeframe = '1h'
short_window = 50
long_window = 200
amount_to_trade = 0.001  # Amount of BTC to trade

def fetch_ohlcv(symbol, timeframe):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 
    'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

def calculate_moving_averages(df, short_window, long_window):
    df['short_mavg'] = df['close'].rolling(window=short_window, min_periods=1).
    mean()
    df['long_mavg'] = df['close'].rolling(window=long_window, min_periods=1).
    mean()
    return df

def get_signal(df):
    if df['short_mavg'].iloc[-1] > df['long_mavg'].iloc[-1] and df
    ['short_mavg'].iloc[-2] <= df['long_mavg'].iloc[-2]:
        return 'buy'
    elif df['short_mavg'].iloc[-1] < df['long_mavg'].iloc[-1] and df
    ['short_mavg'].iloc[-2] >= df['long_mavg'].iloc[-2]:
        return 'sell'
    else:
        return 'hold'

def execute_trade(signal, symbol, amount):
    if signal == 'buy':
        order = exchange.create_market_buy_order(symbol, amount)
        print(f"Executed BUY order: {order}")
    elif signal == 'sell':
        order = exchange.create_market_sell_order(symbol, amount)
        print(f"Executed SELL order: {order}")

def main():
    while True:
        try:
            # Fetch OHLCV data
            df = fetch_ohlcv(symbol, timeframe)

            # Calculate moving averages
            df = calculate_moving_averages(df, short_window, long_window)

            # Get trading signal
            signal = get_signal(df)

            # Execute trade based on signal
            execute_trade(signal, symbol, amount_to_trade)

            # Wait for the next candle
            time.sleep(60 * 60)  # Sleep for 1 hour

        except Exception as e:
            print(f"An error occurred: {e}")
            time.sleep(60)  # Sleep for 1 minute before retrying

if __name__ == "__main__":
    main()
```
===============================================================================
'''

model = ModelFactory.create(
    model_platform=ModelPlatformType.QWEN,
    model_type=ModelType.QWEN_PLUS_LATEST,
    model_config_dict=QwenConfig(
        temperature=0.2,
        stream=False,
        # you can set enable_thinking and steam to True to use thinking
        extra_body={"enable_thinking": False, "thinking_budget": 10000},
    ).as_dict(),
)

# Define system message
sys_msg = "You are a helpful assistant."

# Set agent
camel_agent = ChatAgent(system_message=sys_msg, model=model)

user_msg = """give me python code to develop a trading bot"""

# Get response information
response = camel_agent.step(user_msg)
print(response.msgs[0].content)

# ruff: noqa: E501
'''
===============================================================================
Creating a **trading bot in Python** involves several components:

1. **Choosing a Broker/Exchange API**
2. **Fetching Market Data**
3. **Implementing a Trading Strategy**
4. **Placing Trades Automatically**
5. **Risk Management**

Below is a simple example of a **basic trading bot** using the **Binance** exchange and the `python-binance` library.

---

### ✅ Prerequisites

Install required packages:
```bash
pip install python-binance pandas
```

You'll also need:
- A Binance account
- API Key and Secret (from your Binance account)

---

### 📦 Basic Trading Bot Example (Moving Average Crossover Strategy)

```python
import time
import pandas as pd
from binance.client import Client
from binance.enums import *

# Replace with your own API keys
API_KEY = 'your_api_key'
API_SECRET = 'your_api_secret'

client = Client(API_KEY, API_SECRET)

# --- Helper Functions ---
def get_moving_average(symbol, interval, period=20):
    """Get the moving average for a given symbol"""
    klines = client.get_klines(symbol=symbol, interval=interval)
    closes = [float(entry[4]) for entry in klines]
    return sum(closes[-period:]) / period

def place_order(symbol, quantity, side):
    try:
        order = client.create_order(
            symbol=symbol,
            side=side,
            type=ORDER_TYPE_MARKET,
            quantity=quantity
        )
        print(f"Order placed: {order}")
        return order
    except Exception as e:
        print(f"Error placing order: {e}")
        return None

# --- Trading Logic ---
def trading_bot():
    symbol = "BTCUSDT"
    qty = 0.001  # Adjust based on your balance and risk
    fast_ma_period = 10
    slow_ma_period = 20

    print("Starting trading bot...")
    
    while True:
        try:
            fast_ma = get_moving_average(symbol, KLINE_INTERVAL_1MINUTE, fast_ma_period)
            slow_ma = get_moving_average(symbol, KLINE_INTERVAL_1MINUTE, slow_ma_period)

            print(f"Fast MA: {fast_ma}, Slow MA: {slow_ma}")

            # Simple crossover strategy
            if fast_ma > slow_ma:
                print("Going Long")
                place_order(symbol, qty, SIDE_BUY)
            elif fast_ma < slow_ma:
                print("Going Short")
                place_order(symbol, qty, SIDE_SELL)

            # Wait before next check
            time.sleep(60)  # Check every minute

        except KeyboardInterrupt:
            print("Stopping bot...")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(60)

# Run the bot
if __name__ == "__main__":
    trading_bot()
```

---

### 🔐 Important Notes

- **Paper Trading First**: Test your bot with a demo or paper trading account before using real money.
- **Risk Management**: Add stop-loss, take-profit, and position sizing logic.
- **Rate Limits**: Be aware of exchange rate limits to avoid being banned.
- **Logging & Monitoring**: Add logging and alerts (email, Telegram, etc.)
- **Backtesting**: Always backtest your strategy before deploying it live.

---

### 🧠 Want More?

Let me know if you want:
- A **backtester** for strategies
- Integration with **Telegram alerts**
- Use of **TA-Lib** for technical indicators
- **Multi-exchange support**
- **GUI interface**

Would you like help customizing this bot further?
===============================================================================
'''
