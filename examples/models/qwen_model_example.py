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
    model_type=ModelType.QWEN_3_CODER_PLUS,
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
Here's a basic Python trading bot framework using the ccxt library for cryptocurrency trading. This example includes key components like data fetching, strategy implementation, and order execution:

```python
import ccxt
import pandas as pd
import numpy as np
import time
from datetime import datetime

class SimpleTradingBot:
    def __init__(self, exchange_id, api_key, secret, symbol, timeframe='1h', short_window=10, long_window=50):
        # Initialize exchange connection
        self.exchange = getattr(ccxt, exchange_id)({
            'apiKey': api_key,
            'secret': secret,
            'enableRateLimit': True,
        })
        
        self.symbol = symbol
        self.timeframe = timeframe
        self.short_window = short_window
        self.long_window = long_window
        self.position = None  # 'long', 'short', or None
        
    def fetch_ohlcv(self, limit=100):
        """Fetch OHLCV data from exchange"""
        raw_data = self.exchange.fetch_ohlcv(self.symbol, self.timeframe, limit=limit)
        df = pd.DataFrame(raw_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    
    def calculate_indicators(self, df):
        """Calculate moving averages"""
        df['sma_short'] = df['close'].rolling(window=self.short_window).mean()
        df['sma_long'] = df['close'].rolling(window=self.long_window).mean()
        return df
    
    def generate_signal(self, df):
        """Generate buy/sell signals based on moving average crossover"""
        if len(df) < self.long_window:
            return 'HOLD'
            
        # Get last two values for crossover detection
        short_current = df['sma_short'].iloc[-1]
        short_prev = df['sma_short'].iloc[-2]
        long_current = df['sma_long'].iloc[-1]
        long_prev = df['sma_long'].iloc[-2]
        
        # Bullish crossover
        if short_prev <= long_prev and short_current > long_current:
            return 'BUY'
        # Bearish crossover
        elif short_prev >= long_prev and short_current < long_current:
            return 'SELL'
        else:
            return 'HOLD'
    
    def execute_order(self, signal, amount=0.001):  # Default small amount for safety
        """Execute buy/sell orders"""
        try:
            if signal == 'BUY' and self.position != 'long':
                print(f"[{datetime.now()}] BUY signal. Executing order...")
                order = self.exchange.create_market_buy_order(self.symbol, amount)
                self.position = 'long'
                print(f"Order executed: {order}")
                
            elif signal == 'SELL' and self.position != 'short':
                print(f"[{datetime.now()}] SELL signal. Executing order...")
                order = self.exchange.create_market_sell_order(self.symbol, amount)
                self.position = 'short'
                print(f"Order executed: {order}")
                
        except Exception as e:
            print(f"Order execution failed: {e}")
    
    def run(self):
        """Main bot loop"""
        print(f"Starting bot for {self.symbol} on {self.exchange.id}")
        while True:
            try:
                # Fetch market data
                df = self.fetch_ohlcv()
                df = self.calculate_indicators(df)
                
                # Generate trading signal
                signal = self.generate_signal(df)
                print(f"[{datetime.now()}] Signal: {signal} | Price: {df['close'].iloc[-1]}")
                
                # Execute order if signal is strong
                if signal in ['BUY', 'SELL']:
                    self.execute_order(signal)
                
                # Wait before next iteration
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(60)

# Example usage (replace with your exchange credentials)
if __name__ == "__main__":
    # WARNING: Never share your API keys
    # Use environment variables or secure storage in production
    bot = SimpleTradingBot(
        exchange_id='binance',  # Change to your exchange
        api_key='YOUR_API_KEY',
        secret='YOUR_SECRET_KEY',
        symbol='BTC/USDT',
        timeframe='1h',
        short_window=10,
        long_window=50
    )
    
    # Run the bot (WARNING: This will execute real trades)
    # bot.run()  # Uncomment to run live
```

### Key Features:
1. **Moving Average Crossover Strategy**: Buys when short-term MA crosses above long-term MA, sells when it crosses below
2. **Exchange Integration**: Uses CCXT library for connecting to various exchanges
3. **Risk Management**: Position tracking to avoid duplicate orders
4. **Error Handling**: Basic exception handling and rate limiting

### Setup Instructions:
1. Install required packages:
```bash
pip install ccxt pandas numpy
```

2. Get API keys from your exchange (enable trading permissions)
3. Replace placeholder keys with your actual keys
4. Adjust trading parameters (symbol, timeframes, windows)

### Important Safety Notes:
⚠️ **This is a basic example for educational purposes only**
- Start with paper trading/simulation
- Use small amounts for initial testing
- Add proper risk management before using with real funds
- Implement stop-losses and position sizing
- Test thoroughly in sandbox environments
- Monitor the bot continuously during operation

### Possible Enhancements:
1. Add more sophisticated strategies (RSI, MACD, Bollinger Bands)
2. Implement backtesting capabilities
3. Add database logging for trades
4. Include Telegram/email notifications
5. Add portfolio management features
6. Implement proper configuration management
7. Add web dashboard for monitoring

Remember to comply with your exchange's API usage policies and trading regulations in your jurisdiction.
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
