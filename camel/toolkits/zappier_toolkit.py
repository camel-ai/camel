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

import os
from typing import Dict, List, Optional, Any

import requests

from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.utils import api_keys_required, dependencies_required


class ZapierToolkit(BaseToolkit):
    r"""A class representing a toolkit for interacting with Zapier's NLA API.

    This class provides methods for executing Zapier actions through natural
    language commands, allowing integration with various web services and
    automation of workflows through the Zapier platform.
    """

    @dependencies_required("requests")
    @api_keys_required([
        (None, "ZAPIER_NLA_API_KEY"),
    ])
    def __init__(self) -> None:
        r"""Initialize the ZapierToolkit with API client. The API key is
        retrieved from environment variables.
        """
        self.api_key = os.environ.get("ZAPIER_NLA_API_KEY")
        self.base_url = "https://actions.zapier.com/api/v1/"

    def list_actions(self) -> Dict[str, Any]:
        r"""List all available Zapier actions.

        This function retrieves all exposed actions from your Zapier account
        that can be controlled through the Natural Language Actions API.

        Returns:
            Dict[str, Any]: A dictionary containing the list of available
                actions.
        """
        headers = {
            'accept': 'application/json',
            'x-api-key': self.api_key,
        }
        response = requests.get(
            f"{self.base_url}exposed/",
            params={'api_key': self.api_key},
            headers=headers,
        )
        response.raise_for_status()
        return response.json()

    def execute_action(
        self,
        action_id: str,
        instructions: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        r"""Execute a specific Zapier action using natural language instructions.

        This function allows you to execute any exposed Zapier action using
        natural language instructions. The API will interpret the instructions
        and map them to the appropriate action parameters.

        Args:
            action_id (str): The ID of the Zapier action to execute.
            instructions (str): Natural language instructions for executing
                the action. For example: "Send an email to john@example.com
                with subject 'Hello' and body 'How are you?'"
            params (Optional[Dict[str, Any]], optional): Optional explicit
                parameters for the action. If provided, these will override
                any parameters inferred from the instructions.
                (default: :obj:`None`)

        Returns:
            Dict[str, Any]: The result of the action execution, including
                status and any output data.

        Note:
            The action must be previously exposed in your Zapier NLA
            dashboard for it to be executable.
        """
        try:
            headers = {
                'accept': 'application/json',
                'x-api-key': self.api_key,
                'Content-Type': 'application/json',
            }
            data = {
                "instructions": instructions,
                "preview_only": False,
                **(params or {})
            }
            response = requests.post(
                f"{self.base_url}exposed/{action_id}/execute/",
                params={'api_key': self.api_key},
                headers=headers,
                json=data
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"Request failed: {str(e)}"}
        except ValueError:
            return {"error": "Response is not valid JSON"}

    def preview_action(
        self,
        action_id: str,
        instructions: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        r"""Preview a specific Zapier action using natural language instructions.

        This function allows you to preview any exposed Zapier action using
        natural language instructions. Instead of actually executing the action,
        will instead return a preview of params that have been guessed by the AI
        in case you need to explicitly review before executing.

        Args:
            action_id (str): The ID of the Zapier action to preview.
            instructions (str): Natural language instructions for previewing
                the action. For example: "Send an email to john@example.com
                with subject 'Hello' and body 'How are you?'"
            params (Optional[Dict[str, Any]], optional): Optional explicit
                parameters for the action. If provided, these will override
                any parameters inferred from the instructions.
                (default: :obj:`None`)

        Returns:
            Dict[str, Any]: The preview result showing what parameters would
                be used if the action were executed.

        Note:
            The action must be previously exposed in your Zapier NLA
            dashboard for it to be previewable.
        """
        try:
            headers = {
                'accept': 'application/json',
                'x-api-key': self.api_key,
                'Content-Type': 'application/json',
            }
            data = {
                "instructions": instructions,
                "preview_only": True,
                **(params or {})
            }
            response = requests.post(
                f"{self.base_url}exposed/{action_id}/execute/",
                params={'api_key': self.api_key},
                headers=headers,
                json=data
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"Request failed: {str(e)}"}
        except ValueError:
            return {"error": "Response is not valid JSON"}

    def get_execution_result(self, execution_id: str) -> Dict[str, Any]:
        r"""Get the execution result of a Zapier action.

        This function retrieves the execution log and status of a previously
        executed Zapier action using its execution ID.

        Args:
            execution_id (str): The execution ID returned from execute_action.

        Returns:
            Dict[str, Any]: The execution result containing status, logs,
                and any output data from the action execution.
        """
        try:
            headers = {
                'accept': 'application/json',
                'x-api-key': self.api_key,
            }
            response = requests.get(
                f"{self.base_url}execution-log/{execution_id}/",  
                params={'api_key': self.api_key},
                headers=headers,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"Request failed: {str(e)}"}
        except ValueError:
            return {"error": "Response is not valid JSON"}

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the functions
        in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects representing
                the functions in the toolkit.
        """
        return [
            FunctionTool(self.list_actions),
            FunctionTool(self.execute_action),
            FunctionTool(self.preview_action),
            FunctionTool(self.get_execution_result),
        ]