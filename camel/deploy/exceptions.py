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
class DeployError(Exception):
    """Base exception for deployment errors"""

    pass


class ConfigurationError(DeployError):
    """Raised when there is a configuration error"""

    pass


class PlatformError(DeployError):
    """Raised when there is a platform-specific error"""

    pass


class E2BError(PlatformError):
    """Base exception for E2B-specific errors"""

    pass


class E2BConnectionError(E2BError):
    """Raised when there is a connection error with E2B"""

    pass


class E2BAuthenticationError(E2BError):
    """Raised when there is an authentication error with E2B"""

    pass


class E2BDeploymentError(E2BError):
    """Raised when deployment to E2B fails"""

    pass


class E2BRuntimeError(E2BError):
    """Raised when there is a runtime error in E2B environment"""

    pass


class ResourceNotFoundError(DeployError):
    """Raised when a required resource is not found"""

    pass


class ValidationError(DeployError):
    """Raised when validation fails"""

    pass


class TimeoutError(DeployError):
    """Raised when an operation times out"""

    pass


# usage example:
"""
try:
    if not api_key:
        raise E2BAuthenticationError("API key is required")
    if not os.path.exists(requirements_path):
        # 将长行拆分成多行
        error_msg = f"Requirements file not found: {requirements_path}"
        raise ResourceNotFoundError(error_msg)
except E2BAuthenticationError as e:
    logger.error(f"Authentication failed: {str(e)}")
    raise
except ResourceNotFoundError as e:
    logger.error(f"Resource error: {str(e)}")
    raise
except E2BError as e:
    logger.error(f"E2B error: {str(e)}")
    raise
except DeployError as e:
    logger.error(f"Deployment error: {str(e)}")
    raise
"""
