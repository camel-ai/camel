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
    """A toolkit for interacting with the ACI API."""

    @dependencies_required('aci')
    def __init__(
        self,
        api_key: Union[str, None] = None,
        linked_account: Union[str, None] = None,
        timeout: Optional[float] = None,
    ) -> None:
        r"""Initialize the ACI toolkit.

        Args:
            api_key (str): The API key for authentication
            timeout (Optional[float], optional): Request timeout.
                Defaults to None.
        """
        from aci import ACI

        super().__init__(timeout)
        self.client = ACI(api_key=os.getenv("ACI_API_KEY"))
        self.linked_account = linked_account

    def search_tool(
        self,
        query: str = "",
        allowed_app_only: bool = True,
        include_functions: bool = False,
        categories=None,
        limit: int = 10,
        offset: int = 0,
    ) -> Optional[List["AppBasic"]]:
        r"""Search for apps based on intent.

        Args:
            query (str,optional): The search query/intent
            allowed_app_only(bool,optional): If true, only return apps that
                are allowed by the agent/accessor, identified by the api key.
            include_functions (bool,optional): If true, include functions
                (name and description) in the search results.
            categories (list,optional): List of categories to filter the
                search results. Defaults to an empty list.
            limit (int, optional): Maximum number of results to return.
                Defaults to 10.
            offset (int, optional): Offset for pagination. Defaults to 0.

        Returns:
            List[AppBasic]: List of matching apps
        """
        if categories is None:
            categories = []
        try:
            apps = self.client.apps.search(
                intent=query,
                allowed_apps_only=allowed_app_only,
                include_functions=include_functions,
                categories=categories,
                limit=limit,
                offset=offset,
            )
            return apps
        except Exception as e:
            logger.error(f"Error: {e}")
            return None

    def list_configured_apps(
        self, app_names=None, limit: int = 10, offset: int = 0
    ) -> Optional[List["AppConfiguration"]]:
        r"""List all configured apps

        Args:
            app_names (list, optional): List of app names to filter the
                results. Defaults to an empty list.
            limit (int, optional): Maximum number of results to return.
                Defaults to 10.
            offset (int, optional): Offset for pagination. Defaults to 0.

        Returns:
            Optional[List[AppBasic]]: List of configured apps if successful,
                None otherwise
        """
        if app_names is None:
            app_names = []
        try:
            apps = self.client.app_configurations.list(
                app_names=app_names, limit=limit, offset=offset
            )
            return apps
        except Exception as e:
            logger.error(f"Error: {e}")
            return None

    def configure_app(self, app_name: str) -> Optional[Dict]:
        r"""Configure an app with specified authentication type.

        Args:
            app_name (str): Name of the app to configure

        Returns:
            Optional[Dict]: Configuration result or None on error
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
            return None

    def get_app_configuration(
        self, app_name: str
    ) -> Optional["AppConfiguration"]:
        r"""Get app configuration by app name

        Args:
            app_name (str): Name of the app to get configuration for

        Returns:
            Optional[AppDetails]: App configuration if successful,
                None otherwise
        """
        try:
            app = self.client.app_configurations.get(app_name=app_name)
            return app
        except Exception as e:
            logger.error(f"Error: {e}")
            return None

    def delete_app(self, app_name: str) -> None:
        r"""Delete an app configuration.
        Args:
            app_name (str): Name of the app to delete
        Returns:
            None
        """
        try:
            self.client.app_configurations.delete(app_name=app_name)
        except Exception as e:
            logger.error(f"Error: {e}")

    def link_account(
        self,
        app_name: str,
        api_key: Optional[str] = None,  # <-- FIXED
    ) -> Optional["LinkedAccount"]:
        r"""Link an account to a configured app.

        Args:
            app_name (str): Name of the app to link the account to
            api_key (str, optional): API key for API_KEY authentication.
                Required for API_KEY auth type. Defaults to None

        Returns:
            LinkedAccount: LinkedAccount object if successful,
                None if error occurs
        """
        from aci.types.enums import SecurityScheme

        try:
            security_scheme = self.client.app_configurations.get(
                app_name=app_name
            ).security_scheme

            if security_scheme == SecurityScheme.API_KEY:
                if not api_key:
                    raise ValueError(
                        "API key is required for API_KEY authentication type"
                    )

                return self.client.linked_accounts.link(
                    app_name=app_name,
                    linked_account_owner_id=self.linked_account,
                    security_scheme=security_scheme,
                    api_key=api_key,
                )
            else:
                return self.client.linked_accounts.link(
                    app_name=app_name,
                    linked_account_owner_id=self.linked_account,
                    security_scheme=security_scheme,
                )
        except Exception as e:
            logger.error(f"Error linking account: {e!s}")
            return None

    def get_app_details(self, app_name: str) -> Optional["AppDetails"]:
        r"""Get details of an app.

        Args:
            app_name (str): Name of the app to get details for

        Returns:
            Optional[AppDetails]: App details if successful, None otherwise
        """
        try:
            app = self.client.apps.get(app_name=app_name)
            return app
        except Exception as e:
            logger.error(f"Error: {e}")
            return None

    def get_linked_accounts(
        self, app_name: str
    ) -> Optional[List["LinkedAccount"]]:
        r"""List all linked accounts for a specific app.

        Args:
            app_name (str): Name of the app to get linked accounts for

        Returns:
            Optional[List[LinkedAccount]]: List of linked accounts if
                successful, None otherwise
        """
        try:
            accounts = self.client.linked_accounts.list(app_name=app_name)
            return accounts
        except Exception as e:
            logger.error(f"Error: {e}")
            return None

    def enable_linked_account(self, linked_account_id: str) -> None:
        r"""Enable a linked account.

        Args:
            linked_account_id (str): ID of the linked account to enable

        Returns:
            None
        """
        try:
            self.client.linked_accounts.enable(
                linked_account_id=linked_account_id
            )
        except Exception as e:
            logger.error(f"Error: {e}")

    def disable_linked_account(self, linked_account_id: str) -> None:
        r"""Disable a linked account.

        Args:
            linked_account_id (str): ID of the linked account to disable

        Returns:
            None
        """
        try:
            self.client.linked_accounts.disable(
                linked_account_id=linked_account_id
            )
        except Exception as e:
            logger.error(f"Error: {e}")

    def delete_linked_account(self, linked_account_id: str) -> None:
        r"""Delete a linked account.

        Args:
            linked_account_id (str): ID of the linked account to delete

        Returns:
            None
        """
        try:
            self.client.linked_accounts.delete(
                linked_account_id=linked_account_id
            )
        except Exception as e:
            logger.error(f"Error: {e}")

    def function_definition(self, func_name: str) -> Dict:
        r"""Get the function definition for an app.

        Args:
            app_name (str): Name of the app to get function definition for

        Returns:
            Dict: Function definition dictionary
        """
        return self.client.functions.get_definition(func_name)

    def search_function(
        self,
        app_names=None,
        intent: str = "",
        allowed_apps_only: bool = True,
        limit: int = 10,
        offset: int = 0,
    ) -> List[Dict]:
        r"""Search for functions based on intent.

        Args:
            app_names (list, optional): List of app names to filter the
                search results. Defaults to an empty list.
            intent (str, optional): The search query/intent.
                Defaults to an empty string.
            allowed_apps_only (bool, optional): If true, only return
                functions from allowed apps. Defaults to True.
            limit (int, optional): Maximum number of results to return.
                Defaults to 10.
            offset (int, optional): Offset for pagination. Defaults to 0.

        Returns:
            List[Dict]: List of matching functions
        """
        if app_names is None:
            app_names = []
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
        arguments: Dict,
        linked_account: str,
        allowed_apps_only: bool = False,
    ) -> Dict:
        r"""Execute a function call.

        Args:
            function_name (str): Name of the function to execute
            arguments (Dict): Arguments to pass to the function
            linked_account (LinkedAccount): Linked account to execute
                function with
            allowed_apps_only (bool, optional): Whether to restrict to
                allowed apps. Defaults to False

        Returns:
            Dict: Result of the function execution
        """
        result = self.client.handle_function_call(
            function_name, arguments, str(linked_account), allowed_apps_only
        )
        return result

    def get_tools(self) -> List[FunctionTool]:
        r"""Get a list of tools (functions) available in the configured apps.

        Returns:
            List[FunctionTool]: List of FunctionTool objects representing
                available functions
        """
        _configure_app = [
            app.app_name for app in self.list_configured_apps() or []
        ]
        _all_function = self.client.functions.search(app_names=_configure_app)
        tools = []

        for function in _all_function:
            schema = self.client.functions.get_definition(
                function['function']['name']
            )

            def dummy_func(*, schema=schema, **kwargs):
                return self.execute_function(
                    function_name=schema['function']['name'],
                    arguments=kwargs,
                    linked_account=self.linked_account,
                )

            tool = FunctionTool(
                func=dummy_func,
                openai_tool_schema=schema,
            )
            tools.append(tool)
        return tools
