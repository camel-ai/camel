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
import argparse
import sys

from camel.toolkits import AudioAnalysisToolkit
from camel.configs import ChatGPTConfig
from camel.models import OpenAIAudioModels, ModelFactory
from camel.types import ModelPlatformType, ModelType


def generate_example_audio(storage_path: str = "example_audio.mp3"):
    """
    Generate an example audio file using OpenAIAudioModels.
    """
    audio_models = OpenAIAudioModels()

    # Set example input
    input = """CAMEL-AI.org is an open-source community dedicated to the study of 
    autonomous and communicative agents. We believe that studying these agents on 
    a large scale offers valuable insights into their behaviors, capabilities, and 
    potential risks. To facilitate research in this field, we provide, implement, 
    and support various types of agents, tasks, prompts, models, datasets, and 
    simulated environments.

    Join us via Slack, Discord, or WeChat in pushing the boundaries of building AI 
    Society."""

    # Convert the example input into audio and store it locally
    audio_models.text_to_speech(input=input, storage_path=storage_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run Audio Analysis Toolkit with MCP server mode.",
        usage=f"python {sys.argv[0]} [--mode MODE]",
    )
    parser.add_argument(
        "--mode",
        choices=["stdio", "sse"],
        default="stdio",
        help="MCP server mode (default: 'stdio')",
    )

    args = parser.parse_args()

    # Set example local path to store the file
    storage_path = "example_audio.mp3"

    # Convert the example input into audio and store it locally
    generate_example_audio(storage_path=storage_path)

    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O_MINI,
        model_config_dict=ChatGPTConfig(
            temperature=0.0,
        ).as_dict(),
    )

    audio_reason_model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O_MINI,
        model_config_dict=ChatGPTConfig(
            temperature=0.0,
        ).as_dict(),
    )

    toolkit = AudioAnalysisToolkit(
        audio_reasoning_model=audio_reason_model
    )

    toolkit.mcp.run(args.mode)
