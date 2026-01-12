from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

from camel.agents import ChatAgent
from camel.benchmarks import Tau2BenchBenchmark
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType


def main() -> None:
    r"""Run τ² airline benchmark with GPT-4.1-mini agent / GPT-4.1 user."""
    load_dotenv(dotenv_path=".env", override=True)

    agent_model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4_1_MINI,
        model_config_dict={"temperature": 0.0},
    )
    agent = ChatAgent(
        system_message="You are a customer service agent.",
        model=agent_model,
    )

    results_dir = Path("results/tau2_airline_gpt41mini")
    benchmark = Tau2BenchBenchmark(
        domain="retail",
        user_model=ModelType.GPT_4_1,
        user_model_platform=ModelPlatformType.OPENAI,
        user_model_config={"temperature": 0.0},
        save_to=results_dir,
    )
    benchmark.load()
    benchmark.run(
        agent=agent,
        num_trials=4,
        max_steps=60,
        max_errors=5,
        max_concurrency=8,
        seed=300,
    )
    metrics = benchmark.evaluate()
    print("Results:", metrics)
    print("Saved under:", benchmark.save_to)


if __name__ == "__main__":
    main()
