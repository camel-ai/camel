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
"""Model configuration for browser_skills_example."""
import os

from dotenv import load_dotenv

from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

load_dotenv()

# === Single source of truth for the example scripts ===
DEFAULT_MODEL_PLATFORM: ModelPlatformType = ModelPlatformType.OPENAI
# DEFAULT_MODEL_TYPE = ModelType.GPT_4_1  # Direct OpenAI
DEFAULT_MODEL_TYPE = "qwen/qwen3-vl-235b-a22b-instruct"



def create_default_model():
    """Create the default model used by the example scripts."""
    if DEFAULT_MODEL_PLATFORM == ModelPlatformType.AZURE:
        return ModelFactory.create(
            model_platform=DEFAULT_MODEL_PLATFORM,
            model_type=DEFAULT_MODEL_TYPE,
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            url=os.getenv("AZURE_OPENAI_BASE_URL"),
            api_version=os.getenv("AZURE_API_VERSION"),
            model_config_dict={
                "temperature": 0.0,
                "parallel_tool_calls": False,
            },
        )
    else:
        return ModelFactory.create(
            model_platform=DEFAULT_MODEL_PLATFORM,
            model_type=DEFAULT_MODEL_TYPE,
            api_key=os.getenv("OPENAI_API_KEY"),
            url=os.getenv("OPENAI_BASE_URL"),
            model_config_dict={
                "temperature": 0.0,
                "parallel_tool_calls": False,
            },
        )
