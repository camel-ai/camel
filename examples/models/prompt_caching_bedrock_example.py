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

"""AWS Bedrock prompt caching demo (Converse API)."""

from camel.agents import ChatAgent
from camel.configs import BedrockConfig
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from examples.models.prompt_caching_common import (
    ask_with_agent,
    build_long_shared_context,
    get_questions,
    get_system_message,
)


def run_bedrock_demo(shared_context: str, questions: list) -> None:
    print("\n" + "=" * 70)
    print("AWS BEDROCK - Prompt Caching Demo (Converse API)")
    print("=" * 70)
    print("Using cache_control='5m' with cache checkpoints on system + user")
    print()

    system_message = get_system_message()
    model = ModelFactory.create(
        model_platform=ModelPlatformType.AWS_BEDROCK_CONVERSE,
        model_type=ModelType.AWS_CLAUDE_3_5_SONNET,
        model_config_dict=BedrockConfig(
            temperature=0.2,
            max_tokens=256,
            cache_control="5m",
            cache_checkpoint_target="both",
        ).as_dict(),
        api_key="fowhiafhawf1412215wfwifha",
        region_name="us-west-2",
    )

    agent = ChatAgent(system_message=system_message, model=model)
    for i, q in enumerate(questions, 1):
        agent.reset()
        ask_with_agent(agent, shared_context, q, i)


def main() -> None:
    shared_context = build_long_shared_context()
    questions = get_questions()

    print("=" * 70)
    print("PROMPT CACHING DEMO")
    print("=" * 70)
    print(f"Context size: ~{len(shared_context.split())} words")

    run_bedrock_demo(shared_context, questions)


if __name__ == "__main__":
    main()
