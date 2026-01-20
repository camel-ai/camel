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

from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

# === Single source of truth for the example scripts ===
DEFAULT_MODEL_PLATFORM: ModelPlatformType = ModelPlatformType.AZURE
DEFAULT_MODEL_TYPE: ModelType = ModelType.GPT_4_1


def create_default_model():
    """Create the default model used by the example scripts."""
    return ModelFactory.create(
        model_platform=DEFAULT_MODEL_PLATFORM,
        model_type=DEFAULT_MODEL_TYPE,
        model_config_dict={
            "temperature": 0.0,
            "parallel_tool_calls": False,
        },
    )
