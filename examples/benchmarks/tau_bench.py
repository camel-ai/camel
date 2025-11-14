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
"""Example script for running Tau-Bench with CAMEL.

This script evaluates GPT-4o-mini as the assistant agent on the airline
domain of Tau-Bench, using GPT-4.1 as the user simulator. It runs the
first five tasks (indices 0-4) and stores both the raw Tau-Bench output
and a short summary JSON next to this file.
"""

from __future__ import annotations

import json
from pathlib import Path

from dotenv import load_dotenv

from camel.agents import ChatAgent
from camel.benchmarks import TauBenchBenchmark
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

RESULTS_DIR = Path(__file__).parent


def main() -> None:
    """Run Tau-Bench airline tasks 0-4 with GPT-4o-mini."""
    load_dotenv()

    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O_MINI,
        model_config_dict={"temperature": 0.0},
    )
    agent = ChatAgent(
        system_message="You are a helpful airline support agent.",
        model=model,
    )

    print("2. Initializing Tau-Bench (airline)...")
    benchmark = TauBenchBenchmark(
        domain="airline",
        user_strategy="llm",
        user_model="gpt-4.1",
        user_provider="openai",
        save_to=str(RESULTS_DIR),
        user_temperature=0.0,
    )
    benchmark.load()
    print("✓ Environment loaded")

    print("\n3. Running tasks 0-4...")
    benchmark.run(
        agent=agent,
        start_index=0,
        end_index=5,  # run first five tasks: indices 0-4
        num_trials=1,
        agent_strategy="tool-calling",
        temperature=0.0,
        max_steps=30,
        max_concurrency=5,
        model_name="gpt-4o-mini",
        model_provider="openai",
    )

    metrics = benchmark.evaluate()
    print("\n4. Evaluation results:")
    print(json.dumps(metrics, indent=2))
    print("\nDone. Results stored under", benchmark.save_to)


if __name__ == "__main__":
    main()
