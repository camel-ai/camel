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
from typing import TYPE_CHECKING, Dict, List, Optional, Union

if TYPE_CHECKING:
    from aci.types.app_configurations import AppConfiguration
    from aci.types.apps import AppBasic, AppDetails
    from aci.types.linked_accounts import LinkedAccount

from camel.logger import get_logger
from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit
from camel.utils import api_keys_required, dependencies_required

logger = get_logger(__name__)


@api_keys_required(
    [
        (None, 'ACI_API_KEY'),
    ]
)
class ACIToolkit(BaseToolkit):
    r"""A toolkit for interacting with the ACI API."""

    @dependencies_required('aci')
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        linked_account_owner_id: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> None:
        r"""Initialize the ACI toolkit.

        Args:
            api_key (Optional[str]): The API key for authentication.
                (default: :obj: `None`)
            base_url (Optional[str]): The base URL for the ACI API.
                (default: :obj: `None`)
            linked_account_owner_id (Optional[str]): ID of the owner of the
                linked account, e.g., "johndoe"
                (default: :obj: `None`)
            timeout (Optional[float]): Request timeout.
                (default: :obj: `None`)
        """
        from aci import ACI

        super().__init__(timeout)

        self._api_key = api_key or os.getenv("ACI_API_KEY")
        self._base_url = base_url or os.getenv("ACI_BASE_URL")
        self.client = ACI(api_key=self._api_key, base_url=self._base_url)
        self.linked_account_owner_id = linked_account_owner_id

    def search_tool(
        self,
        intent: Optional[str] = None,
        allowed_app_only: bool = True,
        include_functions: bool = False,
        categories: Optional[List[str]] = None,
        limit: Optional[int] = 10,
        offset: Optional[int] = 0,
    ) -> Union[List["AppBasic"], str]:
        r"""Search for apps based on intent.

        Args:
            intent (Optional[str]): Search results will be sorted by relevance
                to this intent.
                (default: :obj: `None`)
            allowed_app_only (bool): If true, only return apps that
                are allowed by the agent/accessor, identified by the api key.
                (default: :obj: `True`)
            include_functions (bool): If true, include functions
                (name and description) in the search results.
                (default: :obj: `False`)
            categories (Optional[List[str]]): List of categories to filter the
                search results. Defaults to an empty list.
                (default: :obj: `None`)
            limit (Optional[int]): Maximum number of results to return.
                (default: :obj: `10`)
            offset (Optional[int]): Offset for pagination.
                (default: :obj: `0`)

        Returns:
            Optional[List[AppBasic]]: List of matching apps if successful,
                error message otherwise.
        """
        try:
            apps = self.client.apps.search(
                intent=intent,
                allowed_apps_only=allowed_app_only,
                include_functions=include_functions,
                categories=categories,
                limit=limit,
                offset=offset,
            )
            return apps
        except Exception as e:
            logger.error(f"Error: {e}")
            return str(e)

    def list_configured_apps(
        self,
        app_names: Optional[List[str]] = None,
        limit: Optional[int] = 10,
        offset: Optional[int] = 0,
    ) -> Union[List["AppConfiguration"], str]:
        r"""List all configured apps.

        Args:
            app_names (Optional[List[str]]): List of app names to filter the
                results. (default: :obj: `None`)
            limit (Optional[int]): Maximum number of results to return.
                (default: :obj: `10`)
            offset (Optional[int]): Offset for pagination. (default: :obj: `0`)

        Returns:
            Union[List[AppConfiguration], str]: List of configured apps if
                successful, error message otherwise.
        """
        try:
            apps = self.client.app_configurations.list(
                app_names=app_names, limit=limit, offset=offset
            )
            return apps
        except Exception as e:
            logger.error(f"Error: {e}")
            return str(e)

    def configure_app(self, app_name: str) -> Union[Dict, str]:
        r"""Configure an app with specified authentication type.

        Args:
            app_name (str): Name of the app to configure.

        Returns:
            Union[Dict, str]: Configuration result or error message.
        """
        from aci.types.enums import SecurityScheme

        try:
            app_details = self.get_app_details(app_name)
            if app_details and app_details.security_schemes[0] == "api_key":
                security_scheme = SecurityScheme.API_KEY
            elif app_details and app_details.security_schemes[0] == "oauth2":
                security_scheme = SecurityScheme.OAUTH2
            else:
                security_scheme = SecurityScheme.NO_AUTH
            configuration = self.client.app_configurations.create(
                app_name=app_name, security_scheme=security_scheme
            )
            return configuration
        except Exception as e:
            logger.error(f"Error: {e}")
            return str(e)

    def get_app_configuration(
        self, app_name: str
    ) -> Union["AppConfiguration", str]:
        r"""Get app configuration by app name.

        Args:
            app_name (str): Name of the app to get configuration for.

        Returns:
            Union[AppConfiguration, str]: App configuration if successful,
                error message otherwise.
        """
        try:
            app = self.client.app_configurations.get(app_name=app_name)
            return app
        except Exception as e:
            logger.error(f"Error: {e}")
            return str(e)

    def delete_app(self, app_name: str) -> Optional[str]:
        r"""Delete an app configuration.

        Args:
            app_name (str): Name of the app to delete.

        Returns:
            Optional[str]: None if successful, error message otherwise.
        """
        try:
            self.client.app_configurations.delete(app_name=app_name)
            return None
        except Exception as e:
            logger.error(f"Error: {e}")
            return str(e)

    def link_account(
        self,
        app_name: str,
    ) -> Union["LinkedAccount", str]:
        r"""Link an account to a configured app.

        Args:
            app_name (str): Name of the app to link the account to.

        Returns:
            Union[LinkedAccount, str]: LinkedAccount object if successful,
                error message otherwise.
        """
        from aci.types.enums import SecurityScheme

        try:
            security_scheme = self.client.app_configurations.get(
                app_name=app_name
            ).security_scheme

            if security_scheme == SecurityScheme.API_KEY:
                return self.client.linked_accounts.link(
                    app_name=app_name,
                    linked_account_owner_id=self.linked_account_owner_id,
                    security_scheme=security_scheme,
                    api_key=self._api_key,
                )
            else:
                return self.client.linked_accounts.link(
                    app_name=app_name,
                    linked_account_owner_id=self.linked_account_owner_id,
                    security_scheme=security_scheme,
                )
        except Exception as e:
            logger.error(f"Error linking account: {e!s}")
            return str(e)

    def get_app_details(self, app_name: str) -> "AppDetails":
        r"""Get details of an app.

        Args:
            app_name (str): Name of the app to get details for.

        Returns:
            AppDetails: App details.
        """
        app = self.client.apps.get(app_name=app_name)
        return app

    def get_linked_accounts(
        self, app_name: str
    ) -> Union[List["LinkedAccount"], str]:
        r"""List all linked accounts for a specific app.

        Args:
            app_name (str): Name of the app to get linked accounts for.

        Returns:
            Union[List[LinkedAccount], str]: List of linked accounts if
                successful, error message otherwise.
        """
        try:
            accounts = self.client.linked_accounts.list(app_name=app_name)
            return accounts
        except Exception as e:
            logger.error(f"Error: {e}")
            return str(e)

    def enable_linked_account(
        self, linked_account_id: str
    ) -> Union["LinkedAccount", str]:
        r"""Enable a linked account.

        Args:
            linked_account_id (str): ID of the linked account to enable.

        Returns:
            Union[LinkedAccount, str]: Linked account if successful, error
                message otherwise.
        """
        try:
            linked_account = self.client.linked_accounts.enable(
                linked_account_id=linked_account_id
            )
            return linked_account
        except Exception as e:
            logger.error(f"Error: {e}")
            return str(e)

    def disable_linked_account(
        self, linked_account_id: str
    ) -> Union["LinkedAccount", str]:
        r"""Disable a linked account.

        Args:
            linked_account_id (str): ID of the linked account to disable.

        Returns:
            Union[LinkedAccount, str]: The updated linked account if
                successful, error message otherwise.
        """
        try:
            linked_account = self.client.linked_accounts.disable(
                linked_account_id=linked_account_id
            )
            return linked_account
        except Exception as e:
            logger.error(f"Error: {e}")
            return str(e)

    def delete_linked_account(self, linked_account_id: str) -> str:
        r"""Delete a linked account.

        Args:
            linked_account_id (str): ID of the linked account to delete.

        Returns:
            str: Success message if successful, error message otherwise.
        """
        try:
            self.client.linked_accounts.delete(
                linked_account_id=linked_account_id
            )
            return (
                f"linked_account_id: {linked_account_id} deleted successfully"
            )
        except Exception as e:
            logger.error(f"Error: {e}")
            return str(e)

    def function_definition(self, func_name: str) -> Dict:
        r"""Get the function definition for an app.

        Args:
            app_name (str): Name of the app to get function definition for

        Returns:
            Dict: Function definition dictionary.
        """
        return self.client.functions.get_definition(func_name)

    def search_function(
        self,
        app_names: Optional[List[str]] = None,
        intent: Optional[str] = None,
        allowed_apps_only: bool = True,
        limit: Optional[int] = 10,
        offset: Optional[int] = 0,
    ) -> List[Dict]:
        r"""Search for functions based on intent.

        Args:
            app_names (Optional[List[str]]): List of app names to filter the
                search results. (default: :obj: `None`)
            intent (Optional[str]): The search query/intent.
                (default: :obj: `None`)
            allowed_apps_only (bool): If true, only return
                functions from allowed apps. (default: :obj: `True`)
            limit (Optional[int]): Maximum number of results to return.
                (default: :obj: `10`)
            offset (Optional[int]): Offset for pagination.
                (default: :obj: `0`)

        Returns:
            List[Dict]: List of matching functions
        """
        return self.client.functions.search(
            app_names=app_names,
            intent=intent,
            allowed_apps_only=allowed_apps_only,
            limit=limit,
            offset=offset,
        )

    def execute_function(
        self,
        function_name: str,
        function_arguments: Dict,
        linked_account_owner_id: str,
        allowed_apps_only: bool = False,
    ) -> Dict:
        r"""Execute a function call.

        Args:
            function_name (str): Name of the function to execute.
            function_arguments (Dict): Arguments to pass to the function.
            linked_account_owner_id (str): To specify the end-user (account
                owner) on behalf of whom you want to execute functions
                You need to first link corresponding account with the same
                owner id in the ACI dashboard (https://platform.aci.dev).
            allowed_apps_only (bool): If true, only returns functions/apps
                that are allowed to be used by the agent/accessor, identified
                by the api key. (default: :obj: `False`)

        Returns:
            Dict: Result of the function execution
        """
        result = self.client.handle_function_call(
            function_name,
            function_arguments,
            linked_account_owner_id,
            allowed_apps_only,
        )
        return result

    def get_tools(self) -> List[FunctionTool]:
        r"""Get a list of tools (functions) available in the configured apps.

        Returns:
            List[FunctionTool]: List of FunctionTool objects representing
                available functions
        """
        _configure_app = [
            app.app_name  # type: ignore[union-attr]
            for app in self.list_configured_apps() or []
        ]
        _all_function = self.search_function(app_names=_configure_app)
        tools = [
            FunctionTool(self.search_tool),
            FunctionTool(self.list_configured_apps),
            FunctionTool(self.configure_app),
            FunctionTool(self.get_app_configuration),
            FunctionTool(self.delete_app),
            FunctionTool(self.link_account),
            FunctionTool(self.get_app_details),
            FunctionTool(self.get_linked_accounts),
            FunctionTool(self.enable_linked_account),
            FunctionTool(self.disable_linked_account),
            FunctionTool(self.delete_linked_account),
            FunctionTool(self.function_definition),
            FunctionTool(self.search_function),
        ]

        for function in _all_function:
            schema = self.client.functions.get_definition(
                function['function']['name']
            )

            def dummy_func(*, schema=schema, **kwargs):
                return self.execute_function(
                    function_name=schema['function']['name'],
                    function_arguments=kwargs,
                    linked_account_owner_id=self.linked_account_owner_id,
                )

            tool = FunctionTool(
                func=dummy_func,
                openai_tool_schema=schema,
            )
            tools.append(tool)
        return tools
