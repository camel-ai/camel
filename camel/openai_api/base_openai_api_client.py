# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========

from openai import OpenAI
import logging

class BaseOpenAIAPIClient:
    #A wrapper class for the OpenAI API client.

    def __init__(self) -> None:
        self.client = OpenAI()
        self.logger = logging.getLogger(__name__)

    def _get_api_key(self) -> str:
        """
        Get the API key.

        Returns:
            The API key.

        Example:
            api_key = client.get_api_key()
        """
        return self.client.api_key
    
    def _set_api_key(self, api_key: str) -> None:
        """
        Set the API key.

        Args:
            api_key: The API key.

        Example:
            client.set_api_key('my-api-key')
        """
        self.client.api_key = api_key

    def get_api_base(self) -> str:
        """
        Get the API base URL.

        Returns:
            The API base URL.

        Example:
            api_base = client.get_api_base()
        """
        return self.client.api_base

    def set_api_base(self, api_base: str) -> None:
        """
        Set the API base URL.

        Args:
            api_base: The API base URL.

        Example:
            client.set_api_base('my-api-base')
        """
        self.client.api_base = api_base

    def get_organization(self) -> str:
        """
        Get the organization.

        Returns:
            The organization.

        Example:
            organization = client.get_organization()
        """
        return self.client.organization