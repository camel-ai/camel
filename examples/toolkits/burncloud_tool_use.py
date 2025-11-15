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
"""BurnCloud + FunctionTool demo showing local tool integration.

Before running:

```bash
export BURNCLOUD_API_KEY="your_burncloud_api_key"
# Optional: export BURNCLOUD_API_BASE_URL="https://ai.burncloud.com/v1"
```
"""

from __future__ import annotations

from camel.agents import ChatAgent
from camel.configs import BurnCloudConfig
from camel.models import ModelFactory
from camel.toolkits import FunctionTool
from camel.types import ModelPlatformType, ModelType


def estimate_solar_payback(
    capacity_kw: float,
    install_cost_per_kw: float,
    feed_in_tariff: float,
    annual_sun_hours: int,
) -> dict[str, float]:
    """Estimate solar ROI metrics with a simple linear payback model."""

    upfront_cost = capacity_kw * install_cost_per_kw
    annual_generation = capacity_kw * annual_sun_hours
    annual_savings = annual_generation * feed_in_tariff
    payback_years = round(upfront_cost / max(annual_savings, 1e-6), 2)

    return {
        "upfront_cost": round(upfront_cost, 2),
        "annual_generation_kwh": round(annual_generation, 2),
        "annual_savings": round(annual_savings, 2),
        "payback_years": payback_years,
    }


def main() -> None:
    tool = FunctionTool(estimate_solar_payback)

    model = ModelFactory.create(
        model_platform=ModelPlatformType.BURNCLOUD,
        model_type=ModelType.GPT_4O,
        model_config_dict=BurnCloudConfig(temperature=0.15).as_dict(),
    )

    agent = ChatAgent(
        system_message=(
            "You are an energy investment advisor. Reference the "
            "`estimate_solar_payback` tool outputs in your reasoning and "
            "summarize recommendations in English."
        ),
        model=model,
        tools=[tool],
    )

    user_msg = (
        "A 12 kW rooftop PV project in Shanghai costs 8,200 CNY per kW, "
        "earns 0.48 CNY per kWh, and gets 1,500 effective sun hours per "
        "year. Present the payback calculation as a table and conclude "
        "whether it is a good investment."
    )

    response = agent.step(user_msg)

    print("User:\n", user_msg)
    print("\nAssistant:\n", response.msgs[0].content)

    tool_calls = response.info.get("tool_calls") if response.info else None
    if tool_calls:
        print("\nTool call details:")
        for call in tool_calls:
            # ChatAgent may return either plain dicts (OpenAI schema) or
            # ToolCallingRecord instances, so normalize both shapes.
            if hasattr(call, "tool_name"):
                print(
                    f"- id={getattr(call, 'tool_call_id', 'N/A')}, "
                    f"name={call.tool_name}"
                )
                print(f"  args={call.args}")
            else:
                call_dict = (
                    call.as_dict() if hasattr(call, "as_dict") else call
                )
                fn_meta = call_dict.get("function", {})
                print(
                    f"- id={call_dict.get('id')}, "
                    f"name={fn_meta.get('name')}"
                )
                print(f"  args={fn_meta.get('arguments')}")


if __name__ == "__main__":
    main()
