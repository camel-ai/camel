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

"""
Anthropic structured output + tool use example for CAMEL.

Required environment variable:
    export ANTHROPIC_API_KEY="<your-anthropic-api-key>"

Optional environment variables:
    export ANTHROPIC_API_BASE_URL="<your-anthropic-compatible-base-url>"
    export ANTHROPIC_MODEL="<your-anthropic-model>"

Run:
    python3 examples/models/anthropic_structured_output_example.py
"""

import json
import os

from pydantic import BaseModel, Field

from camel.agents import ChatAgent
from camel.models import AnthropicModel
from camel.types import ModelType
from camel.utils import OpenAITokenCounter


class TripDecision(BaseModel):
    recommended_area: str = Field(
        description="Best Kyoto area for a first-time weekend visitor"
    )
    estimated_total_budget_rmb: int = Field(
        description="Estimated total budget in RMB"
    )
    must_visit_spot: str = Field(
        description="One attraction selected using tool-backed context"
    )
    transport_tip: str = Field(description="Short practical transport advice")


def lookup_kyoto_area(area: str) -> dict[str, str]:
    """Look up concise travel notes for a Kyoto area.

    Args:
        area: Kyoto area name such as "Higashiyama", "Arashiyama", or
            "Downtown Kyoto".

    Returns:
        Structured area information for itinerary decisions.
    """
    area_db = {
        "Higashiyama": {
            "must_visit_spot": "Kiyomizu-dera",
            "transport_tip": "Take a bus or taxi early in the morning.",
        },
        "Arashiyama": {
            "must_visit_spot": "Arashiyama Bamboo Grove",
            "transport_tip": "Use JR or local rail and arrive before 9 AM.",
        },
        "Downtown Kyoto": {
            "must_visit_spot": "Nishiki Market",
            "transport_tip": (
                "Stay near Karasuma or Kawaramachi for transfers."
            ),
        },
    }
    return area_db.get(
        area,
        {
            "must_visit_spot": "Kyoto Station area",
            "transport_tip": "Use Kyoto Station as the central transfer hub.",
        },
    )


def estimate_kyoto_budget(days: int, hotel_tier: str) -> dict[str, int]:
    """Estimate a simple Kyoto travel budget in RMB.

    Args:
        days: Number of travel days.
        hotel_tier: One of "budget", "midrange", or "premium".

    Returns:
        Budget breakdown in RMB.
    """
    hotel_per_day = {
        "budget": 260,
        "midrange": 460,
        "premium": 900,
    }.get(hotel_tier, 260)
    food_per_day = 140
    attraction_per_day = 110
    transport_total = 80

    total = (
        days * hotel_per_day
        + days * food_per_day
        + days * attraction_per_day
        + transport_total
    )
    return {"total_budget_rmb": total}


def build_anthropic_model() -> AnthropicModel:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Missing ANTHROPIC_API_KEY. "
            "Please export it before running this example."
        )

    base_url = os.environ.get("ANTHROPIC_API_BASE_URL")
    model_type = os.environ.get("ANTHROPIC_MODEL") or (
        ModelType.CLAUDE_SONNET_4_5
    )

    return AnthropicModel(
        model_type=model_type,
        api_key=api_key,
        url=base_url,
        # Third-party Anthropic-compatible platforms may require a local
        # fallback token counter instead of Anthropic's count_tokens API.
        token_counter=OpenAITokenCounter(ModelType.GPT_4O_MINI),
        model_config_dict={"max_tokens": 800},
    )


def main() -> None:
    agent = ChatAgent(
        system_message=(
            "You are a helpful assistant. "
            "Use tools first, then return concise structured data."
        ),
        model=build_anthropic_model(),
        tools=[lookup_kyoto_area, estimate_kyoto_budget],
    )

    response = agent.step(
        (
            "Plan a first-time 2-day Kyoto weekend for a budget-conscious "
            "traveler. Use the tools to pick a suitable area and estimate the "
            "budget. Return only the structured result."
        ),
        response_format=TripDecision,
    )

    print("=== Raw Content ===")
    print(response.msgs[0].content)

    print("\n=== Parsed Object ===")
    print(response.msgs[0].parsed)

    print("\n=== Parsed JSON ===")
    print(
        json.dumps(
            response.msgs[0].parsed.model_dump(),
            ensure_ascii=False,
            indent=2,
        )
    )

    print("\n=== Tool Calls ===")
    for tool_call in response.info.get("tool_calls", []):
        print(
            f"- {tool_call.tool_name} args={tool_call.args} "
            f"result={tool_call.result}"
        )


if __name__ == "__main__":
    main()

"""
===============================================================================
=== Raw Content ===
{"recommended_area":"Higashiyama","estimated_total_budget_rmb":1100,
"must_visit_spot":"Kiyomizu-dera","transport_tip":"Take a bus or taxi early in
the morning to avoid crowds and save time-consider a Kyoto Bus One-Day Pass
for unlimited rides."}

=== Parsed Object ===
recommended_area='Higashiyama' estimated_total_budget_rmb=1100
must_visit_spot='Kiyomizu-dera' transport_tip='Take a bus or taxi early in
the morning to avoid crowds and save time-consider a Kyoto Bus One-Day Pass
for unlimited rides.'

=== Parsed JSON ===
{
  "recommended_area": "Higashiyama",
  "estimated_total_budget_rmb": 1100,
  "must_visit_spot": "Kiyomizu-dera",
  "transport_tip": "Take a bus or taxi early in the morning to avoid crowds and
  save time-consider a Kyoto Bus One-Day Pass for unlimited rides."
}

=== Tool Calls ===
- lookup_kyoto_area args={'area': 'Higashiyama'} result={'must_visit_spot':
'Kiyomizu-dera', 'transport_tip': 'Take a bus or taxi early in the morning.'}
- estimate_kyoto_budget args={'days': 2, 'hotel_tier': 'budget'}
result={'total_budget_rmb': 1100}
===============================================================================
"""
