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

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict


class CloneContext(BaseModel):
    r"""Context object for cloning agents and stateful toolkits.

    Only fields consumed by the current ChatAgent clone path live here.
    Additional resource-selection hints should be introduced together with the
    toolkit/runtime code that reads them.
    """

    model_config = ConfigDict(extra='forbid')

    session_id: Optional[str] = None
    execution_context: Optional[Dict[str, Any]] = None
