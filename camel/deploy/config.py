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
from typing import Any, Dict

from pydantic import BaseModel


class E2BConfig(BaseModel):
    """E2B configuration model"""

    api_key: str
    project_name: str
    runtime: str = "python3.9"
    requirements_path: str = "requirements.txt"
    app_path: str = "app.py"


def validate_e2b_config(config: Dict[str, Any]) -> E2BConfig:
    """Validate E2B configuration"""
    return E2BConfig(**config)
