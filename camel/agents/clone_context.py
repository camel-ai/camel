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
from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, ConfigDict


class CloneContext(BaseModel):
    r"""Context object for cloning agents and stateful toolkits."""

    model_config = ConfigDict(extra='forbid')

    session_id: Optional[str] = None
    execution_id: Optional[str] = None
    mode: Literal["fresh", "shared_session", "external_session"] = "fresh"
    resource_hints: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    execution_context: Optional[Dict[str, Any]] = None
