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

from camel.models import ModelFactory
from camel.toolkits import VideoAnalysisToolkit
from camel.types import ModelPlatformType, ModelType
from camel.configs import ChatGPTConfig

if __name__ == "__main__":
    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O_MINI,
        model_config_dict=ChatGPTConfig(
            temperature=0.0,
        ).as_dict(),
    )

    parser = argparse.ArgumentParser(
        description="Run Video Analysis Toolkit with MCP server mode.",
        usage=f"python {sys.argv[0]} [--mode MODE]",
    )
    parser.add_argument(
        "--mode",
        choices=["stdio", "sse"],
        default="stdio",
        help="MCP server mode (default: 'stdio')",
    )

    args = parser.parse_args()

    toolkit = VideoAnalysisToolkit(
        model=model, use_audio_transcription=False,
    )

    toolkit.mcp.run(args.mode)
