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

import e2b

from ..exceptions import DeployError


class E2BDeployer:
    """E2B deployment implementation"""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize E2B deployer

        Args:
            config: Configuration dictionary containing:
                - api_key: E2B API key
                - project_name: Name of the project
                - runtime: Python runtime version
        """
        self.config = config
        self.api_key = config.get('api_key')
        if not self.api_key:
            raise DeployError("E2B API key is required")

        # Initialize E2B client
        e2b.init(api_key=self.api_key)

    async def deploy(self) -> Dict[str, Any]:
        """
        Deploy the application to E2B

        Returns:
            Dict containing deployment information
        """
        try:
            # Create new deployment
            session = await e2b.Session.create(
                id="camel-deployment",
                runtime=self.config.get('runtime', 'python3.9'),
            )

            # Install dependencies
            await session.run("pip install -r requirements.txt")

            # Start the application
            await session.daemon("python app.py")

            return {
                "status": "success",
                "url": session.url,
                "session_id": session.id,
            }

        except Exception as e:
            raise DeployError(f"E2B deployment failed: {e!s}")

    async def destroy(self, session_id: str):
        """
        Destroy a deployment

        Args:
            session_id: ID of the session to destroy
        """
        try:
            session = await e2b.Session.get(session_id)
            await session.close()
        except Exception as e:
            raise DeployError(f"Failed to destroy deployment: {e!s}")
