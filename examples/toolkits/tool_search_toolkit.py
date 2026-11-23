# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
from typing import Any, Dict

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import ToolSearchToolkit, tool
from camel.types import ModelPlatformType, ModelType

# BM25 requires: pip install "camel-ai[rag]"
# Example tools return fixed demo data. ChatAgent needs model credentials.


@tool()
def get_weather_forecast(city: str, days: int = 1) -> Dict[str, Any]:
    r"""Retrieves current weather forecast for a specified city.

    Args:
        city (str): Name of the city (e.g., 'San Francisco', 'Beijing').
        days (int): Number of forecast days. (default: 1)

    Returns:
        Dict[str, Any]: Temperature, conditions, and humidity.
    """
    return {
        "city": city,
        "temperature_celsius": 22.5,
        "condition": "Sunny with light breeze",
        "days": days,
    }


@tool()
def query_stock_price(ticker: str) -> Dict[str, Any]:
    r"""Fetches real-time equity stock quote and market cap.

    Args:
        ticker (str): Stock ticker symbol (e.g. 'AAPL', 'NVDA').

    Returns:
        Dict[str, Any]: Current stock price, currency, and daily change.
    """
    return {
        "ticker": ticker.upper(),
        "price": 234.50,
        "currency": "USD",
        "change_percent": "+1.85%",
    }


@tool()
def calculate_compound_interest(
    principal: float, rate: float, time_years: int
) -> Dict[str, Any]:
    r"""Calculates total future compound interest and balance.

    Args:
        principal (float): Initial amount invested.
        rate (float): Annual interest rate as decimal (e.g., 0.05 for 5%).
        time_years (int): Duration of investment in years.

    Returns:
        Dict[str, Any]: Total future value and interest earned.
    """
    amount = principal * ((1 + rate) ** time_years)
    return {
        "principal": principal,
        "total_future_value": round(amount, 2),
        "interest_earned": round(amount - principal, 2),
    }


@tool()
def inspect_database_latency(
    cluster_id: str, threshold_ms: int = 100
) -> Dict[str, Any]:
    r"""Queries PostgreSQL cluster slow query logs and p99 query latency.

    Args:
        cluster_id (str): Database cluster identifier.
        threshold_ms (int): Latency alert threshold in milliseconds.

    Returns:
        Dict[str, Any]: Diagnostic report with slow query count and p99.
    """
    return {
        "cluster_id": cluster_id,
        "p99_latency_ms": 142,
        "slow_queries_detected": 3,
        "slowest_query": "SELECT * FROM orders WHERE status = 'pending'",
    }


@tool()
def send_slack_notification(channel: str, message: str) -> Dict[str, Any]:
    r"""Sends an urgent operational alert or notification message to Slack.

    Args:
        channel (str): Slack channel name with # prefix (e.g., '#ops-alerts').
        message (str): Plain text notification message.

    Returns:
        Dict[str, Any]: Delivery status confirmation.
    """
    return {"status": "sent", "channel": channel, "delivered": True}


def main():
    # Initialize ToolSearchToolkit with all candidate tools
    search_toolkit = ToolSearchToolkit(
        tools=[
            get_weather_forecast,
            query_stock_price,
            calculate_compound_interest,
            inspect_database_latency,
            send_slack_notification,
        ],
        top_k=2,
    )

    # Example 1: Search and filter tools with BM25 backend
    query = "Check how much AAPL shares cost right now"
    matched_tools = search_toolkit.filter_tools(query=query, top_k=1)
    print(f"Query: {query}")
    if matched_tools:
        print(f"Top matched tool: {matched_tools[0].get_function_name()}")
    else:
        print("No matching tools found.")
    '''
    ===============================================================================
    Query: Check how much AAPL shares cost right now
    Top matched tool: query_stock_price
    ===============================================================================
    '''

    # Example 2: Static pre-filtering with ChatAgent execution
    user_query = "What is the weather forecast for Tokyo for the next 3 days?"
    active_tools = search_toolkit.filter_tools(query=user_query, top_k=1)
    if not active_tools:
        print("No weather tool found.")
        return

    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
    )

    agent = ChatAgent(
        system_message="You are a helpful assistant. Always use tools to "
        "answer user questions.",
        model=model,
        tools=active_tools,
    )

    response = agent.step(user_query)
    print(str(response.info['tool_calls'])[:1000])
    '''
    ===============================================================================
    [ToolCallingRecord(tool_name='get_weather_forecast', args={'city': 'Tokyo',
    'days': 3}, result={'city': 'Tokyo', 'temperature_celsius': 22.5,
    'condition': 'Sunny with light breeze', 'days': 3},
    tool_call_id='call_01')]
    ===============================================================================
    '''
    print(response.msgs[0].content)
    '''
    ===============================================================================
    The weather forecast for Tokyo for the next 3 days is as follows:
    - Temperature: 22.5°C
    - Condition: Sunny with a light breeze
    ===============================================================================
    '''


if __name__ == "__main__":
    main()
