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
"""Example script for running τ²-bench with CAMEL ChatAgents."""

from __future__ import annotations

import json
from pathlib import Path

from dotenv import load_dotenv

from camel.agents import ChatAgent
from camel.benchmarks import Tau2BenchBenchmark
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

RESULTS_DIR = Path(__file__).parent / "tau2_results"


def main() -> None:
    """Evaluate GPT-4o-mini on a handful of τ² airline tasks."""
    load_dotenv()

    assistant_model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O_MINI,
        model_config_dict={"temperature": 0.0},
    )
    assistant_agent = ChatAgent(
        system_message="You are an expert airline support agent.",
        model=assistant_model,
    )

    benchmark = Tau2BenchBenchmark(
        domain="airline",
        save_to=RESULTS_DIR,
        user_model=ModelType.GPT_4_1_MINI,
        user_model_platform=ModelPlatformType.OPENAI,
        user_model_config={"temperature": 0.2},
    )
    benchmark.load()

    benchmark.run(
        agent=assistant_agent,
        task_split_name="base",
        num_trials=1,
        num_tasks=3,
        max_steps=60,
        max_errors=5,
        evaluation_type="all",
    )

    metrics = benchmark.evaluate()
    print(json.dumps(metrics, indent=2))
    print(f"\nResults stored in: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
