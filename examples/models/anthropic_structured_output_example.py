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
End-to-end structured output check for AnthropicModel.

Required environment variable:
    export ANTHROPIC_API_KEY="<your-anthropic-api-key>"

Optional environment variables:
    export ANTHROPIC_API_BASE_URL="<your-anthropic-compatible-base-url>"
    export ANTHROPIC_USE_BETA_STRUCTURED_OUTPUTS="true"

Run:
    python3 examples/models/anthropic_structured_output_example.py

Notes:
    CAMEL forwards ``response_format`` to Anthropic via
    ``output_config.format`` so the model returns schema-constrained JSON.
    For older Anthropic-compatible gateways that still require the transition
    beta header, set ``ANTHROPIC_USE_BETA_STRUCTURED_OUTPUTS=true``.
"""

import json
import os
import warnings

from pydantic import BaseModel, Field

from camel.agents import ChatAgent
from camel.configs import AnthropicConfig
from camel.models import AnthropicModel


class Attraction(BaseModel):
    name: str = Field(description="Name of the attraction")
    visit_duration_hours: float = Field(
        description="Approximate visit duration in hours"
    )


class DayPlan(BaseModel):
    day: int = Field(description="Day number starting from 1")
    city: str = Field(description="City for this day")
    attractions: list[Attraction] = Field(
        description="Main attractions planned for the day"
    )
    food_recommendation: str = Field(
        description="One representative local food recommendation"
    )


class WeekendTripPlan(BaseModel):
    title: str = Field(description="A short title for the trip")
    total_budget_rmb: int = Field(description="Estimated total budget in RMB")
    packing_list: list[str] = Field(
        description="A compact packing checklist"
    )
    itinerary: list[DayPlan] = Field(
        description="Detailed plan for each day of the trip"
    )


def main() -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Missing ANTHROPIC_API_KEY. "
            "Please export it before running this example."
        )

    base_url = os.environ.get("ANTHROPIC_API_BASE_URL")
    use_beta_for_structured_outputs = (
        os.environ.get("ANTHROPIC_USE_BETA_STRUCTURED_OUTPUTS", "")
        .strip()
        .lower()
        == "true"
    )

    anthropic_model = AnthropicModel(
        model_type="anthropic/claude-sonnet-4.5",
        url=base_url,
        api_key=api_key,
        use_beta_for_structured_outputs=use_beta_for_structured_outputs,
        model_config_dict=AnthropicConfig(
            temperature=0.0,
            max_tokens=800,
        ).as_dict(),
    )

    agent = ChatAgent(
        system_message=(
            "You are a helpful assistant. "
            "When the user asks for structured data, keep the content concise "
            "and return data that matches the requested schema."
        ),
        model=anthropic_model,
    )

    user_msg = (
        "Create a 2-day travel plan for a first-time visitor going to Kyoto. "
        "Keep it practical and budget-conscious. "
        "Return only the structured result."
    )

    with warnings.catch_warnings(record=True) as caught_warnings:
        warnings.simplefilter("always")
        response = agent.step(user_msg, response_format=WeekendTripPlan)

    message = response.msgs[0]

    print("=== Warnings ===")
    if caught_warnings:
        for item in caught_warnings:
            print(f"- {item.message}")
    else:
        print("- None")

    print("\n=== Raw Content ===")
    print(message.content)

    print("\n=== Parsed Object ===")
    print(message.parsed)

    if message.parsed is None:
        raise RuntimeError(
            "Structured output parsing failed. "
            "Check the raw content printed above."
        )

    print("\n=== Parsed JSON ===")
    print(
        json.dumps(
            message.parsed.model_dump(),
            ensure_ascii=False,
            indent=2,
        )
    )

    print("\n=== Parsed Type ===")
    print(type(message.parsed))


if __name__ == "__main__":
    main()
