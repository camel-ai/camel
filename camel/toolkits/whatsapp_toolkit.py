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

import os
import time
from typing import Any, Dict, List, Union

from requests.exceptions import RequestException
import requests

from camel.toolkits import OpenAIFunction
from camel.toolkits.base import BaseToolkit


class WhatsAppToolkit(BaseToolkit):
    """A class representing a toolkit for WhatsApp operations.

    This toolkit provides methods to interact with the WhatsApp Business API,
    allowing users to send messages, retrieve message templates, and get
    business profile information.

    Attributes:
        retries (int): Number of retries for API requests in case of failure.
        delay (int): Delay between retries in seconds.
        base_url (str): Base URL for the WhatsApp Business API.
        version (str): API version.
    """

    def __init__(self, retries: int = 3, delay: int = 1):
        """Initializes the WhatsAppToolkit with the specified number of retries
        and delay.

        Args:
            retries (int): Number of times to retry the request in case of
                failure. Defaults to 3.
            delay (int): Time in seconds to wait between retries. Defaults to 1.
        """
        self.retries = retries
        self.delay = delay
        self.base_url = "https://graph.facebook.com"
        self.version = "v17.0"

        self.access_token = os.environ.get("WHATSAPP_ACCESS_TOKEN", "")
        self.phone_number_id = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")

        if not all([self.access_token, self.phone_number_id]):
            raise ValueError(
                "WhatsApp API credentials are not set. "
                "Please set the WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID environment variables."
            )

    def _retry_request(self, func, *args, **kwargs):
        """Retries a function in case of any errors.

        Args:
            func (callable): The function to be retried.
            *args: Arguments to pass to the function.
            **kwargs: Keyword arguments to pass to the function.

        Returns:
            Any: The result of the function call if successful.

        Raises:
            Exception: If all retry attempts fail.
        """
        for attempt in range(self.retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                print(f"Attempt {attempt + 1}/{self.retries} failed: {e}")
                if attempt < self.retries - 1:
                    time.sleep(self.delay)
                else:
                    raise

    def send_message(
        self, to: str, message: str
    ) -> Union[Dict[str, Any], str]:
        """Sends a text message to a specified WhatsApp number.

        Args:
            to (str): The recipient's WhatsApp number in international format.
            message (str): The text message to send.

        Returns:
            Union[Dict[str, Any], str]: A dictionary containing the API response
                if successful, or an error message string if failed.
        """
        url = f"{self.base_url}/{self.version}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        data = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": message},
        }

        try:
            response = self._retry_request(
                requests.post, url, headers=headers, json=data
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return f"Failed to send message: {str(e)}"

    def get_message_templates(self) -> Union[List[Dict[str, Any]], str]:
        """Retrieves all message templates for the WhatsApp Business account.

        Returns:
            Union[List[Dict[str, Any]], str]: A list of dictionaries containing
                template information if successful, or an error message string if failed.
        """
        url = f"{self.base_url}/{self.version}/{self.phone_number_id}/message_templates"
        headers = {"Authorization": f"Bearer {self.access_token}"}

        try:
            response = self._retry_request(requests.get, url, headers=headers)
            response.raise_for_status()
            return response.json().get("data", [])
        except Exception as e:
            return f"Failed to retrieve message templates: {str(e)}"

    def get_business_profile(self) -> Union[Dict[str, Any], str]:
        """Retrieves the WhatsApp Business profile information.

        Returns:
            Union[Dict[str, Any], str]: A dictionary containing the business profile
                information if successful, or an error message string if failed.
        """
        url = f"{self.base_url}/{self.version}/{self.phone_number_id}/whatsapp_business_profile"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        params = {"fields": "about,address,description,email,profile_picture_url,websites,vertical"}

        try:
            response = self._retry_request(
                requests.get, url, headers=headers, params=params
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return f"Failed to retrieve business profile: {str(e)}"

    def get_tools(self) -> List[OpenAIFunction]:
        """Returns a list of OpenAIFunction objects representing the
        functions in the toolkit.

        Returns:
            List[OpenAIFunction]: A list of OpenAIFunction objects for the
                toolkit methods.
        """
        return [
            OpenAIFunction(self.send_message),
            OpenAIFunction(self.get_message_templates),
            OpenAIFunction(self.get_business_profile),
        ]