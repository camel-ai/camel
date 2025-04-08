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

from .config import validate_e2b_config
from .platforms.e2b import E2BDeployer


class DeployToolkit:
    """Main deployment toolkit interface"""

    def __init__(self, platform: str, config: Dict[str, Any]):
        self.platform = platform
        self.config = config

        if platform == "e2b":
            self.config = validate_e2b_config(config)
            self.deployer = E2BDeployer(self.config)
        else:
            raise ValueError(f"Unsupported platform: {platform}")

    async def deploy(self) -> Dict[str, Any]:
        """Deploy the application"""
        return await self.deployer.deploy()

    async def destroy(self, session_id: str):
        """Destroy a deployment"""
        await self.deployer.destroy(session_id)
