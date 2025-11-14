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

from .api_key_provider import ApiKeyProvider
from .auth_manager import (
    AuthenticationManager,
    get_auth_manager,
    register_auth_provider,
)
from .base import (
    AuthenticationError,
    AuthenticationProvider,
    AuthenticationType,
)
from .oauth2_provider import OAuth2Provider
from .service_account_provider import ServiceAccountProvider
from .token_provider import TokenProvider

__all__ = [
    'AuthenticationProvider',
    'AuthenticationType',
    'AuthenticationError',
    'OAuth2Provider',
    'TokenProvider',
    'ApiKeyProvider',
    'ServiceAccountProvider',
    'AuthenticationManager',
    'get_auth_manager',
    'register_auth_provider',
]
