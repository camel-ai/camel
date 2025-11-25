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

from typing import Any, List, Literal, Optional

from camel.toolkits.base import BaseToolkit


class HybridBrowserToolkit(BaseToolkit):
    r"""A hybrid browser toolkit that can switch between TypeScript and Python
    implementations.

    This wrapper allows users to choose between:
    - 'typescript': WebSocket-based implementation using TypeScript/Node.js
    - 'python': Pure Python implementation using Playwright directly

    Args:
        mode (Literal["typescript", "python"]): Implementation mode. -
            'typescript': Uses WebSocket-based TypeScript implementation -
            'python': Uses pure Python Playwright implementation. Defaults to
            "typescript".
        headless (bool): Whether to run browser in headless mode.
            Defaults to True.
        user_data_dir (Optional[str]): Directory for user data
            persistence. Defaults to None.
        stealth (bool): Whether to enable stealth mode. Defaults to
            False.
        cache_dir (str): Directory for caching. Defaults to "tmp/".
        enabled_tools (Optional[List[str]]): List of enabled tools.
            Defaults to None.
        browser_log_to_file (bool): Whether to log browser actions to
            file. Defaults to False.
        log_dir (Optional[str]): Custom directory path for log files.
            If None, defaults to "browser_log". Defaults to None.
        session_id (Optional[str]): Session identifier. Defaults to None.
        default_start_url (str): Default URL to start with. Defaults
            to "https://google.com/".
        default_timeout (Optional[int]): Default timeout in
            milliseconds. Defaults to None.
        short_timeout (Optional[int]): Short timeout in milliseconds.
            Defaults to None.
        navigation_timeout (Optional[int]): Navigation timeout in
            milliseconds. Defaults to None.
        network_idle_timeout (Optional[int]): Network idle timeout in
            milliseconds. Defaults to None.
        screenshot_timeout (Optional[int]): Screenshot timeout in
            milliseconds. Defaults to None.
        page_stability_timeout (Optional[int]): Page stability timeout
            in milliseconds. Defaults to None.
        dom_content_loaded_timeout (Optional[int]): DOM content loaded
            timeout in milliseconds. Defaults to None.
        viewport_limit (bool): Whether to filter page snapshot
            elements to only those visible in the current viewport.
            Defaults to False.
        connect_over_cdp (bool): Whether to connect to an existing
            browser via Chrome DevTools Protocol. Defaults to False.
            (Only supported in TypeScript mode)
        cdp_url (Optional[str]): WebSocket endpoint URL for CDP
            connection. Required when connect_over_cdp is True.
            Defaults to None. (Only supported in TypeScript mode)
        cdp_keep_current_page (bool): When True and using CDP mode,
        won't create new pages but use the existing one. Defaults to False.
            (Only supported in TypeScript mode)
        full_visual_mode (bool): When True, browser actions like click,
            browser_open, visit_page, etc. will return 'full visual mode'
            as snapshot instead of actual page content. The
            browser_get_page_snapshot method will still return the actual
            snapshot. Defaults to False.
        **kwargs: Additional keyword arguments passed to the
            implementation.

    Returns:
        HybridBrowserToolkit instance of the specified implementation.
    """

    def __new__(
        cls,
        *,
        mode: Literal["typescript", "python"] = "typescript",
        headless: bool = True,
        user_data_dir: Optional[str] = None,
        stealth: bool = False,
        cache_dir: Optional[str] = None,
        enabled_tools: Optional[List[str]] = None,
        browser_log_to_file: bool = False,
        log_dir: Optional[str] = None,
        session_id: Optional[str] = None,
        default_start_url: Optional[str] = None,
        default_timeout: Optional[int] = None,
        short_timeout: Optional[int] = None,
        navigation_timeout: Optional[int] = None,
        network_idle_timeout: Optional[int] = None,
        screenshot_timeout: Optional[int] = None,
        page_stability_timeout: Optional[int] = None,
        dom_content_loaded_timeout: Optional[int] = None,
        viewport_limit: bool = False,
        connect_over_cdp: bool = False,
        cdp_url: Optional[str] = None,
        cdp_keep_current_page: bool = False,
        full_visual_mode: bool = False,
        **kwargs: Any,
    ) -> Any:
        r"""Create a HybridBrowserToolkit instance with the specified mode.

        Args:
            mode (Literal["typescript", "python"]): Implementation mode.
                - 'typescript': Uses WebSocket-based TypeScript implementation
                - 'python': Uses pure Python Playwright implementation
                Defaults to "typescript".
            headless (bool): Whether to run browser in headless mode.
                Defaults to True.
            user_data_dir (Optional[str]): Directory for user data
                persistence. Defaults to None.
            stealth (bool): Whether to enable stealth mode. Defaults to
                False.
            cache_dir (str): Directory for caching. Defaults to "tmp/".
            enabled_tools (Optional[List[str]]): List of enabled tools.
                Defaults to None.
            browser_log_to_file (bool): Whether to log browser actions to
                file. Defaults to False.
            log_dir (Optional[str]): Custom directory path for log files.
                If None, defaults to "browser_log". Defaults to None.
            session_id (Optional[str]): Session identifier. Defaults to None.
            default_start_url (str): Default URL to start with. Defaults
                to "https://google.com/".
            default_timeout (Optional[int]): Default timeout in
                milliseconds. Defaults to None.
            short_timeout (Optional[int]): Short timeout in milliseconds.
                Defaults to None.
            navigation_timeout (Optional[int]): Navigation timeout in
                milliseconds. Defaults to None.
            network_idle_timeout (Optional[int]): Network idle timeout in
                milliseconds. Defaults to None.
            screenshot_timeout (Optional[int]): Screenshot timeout in
                milliseconds. Defaults to None.
            page_stability_timeout (Optional[int]): Page stability timeout
                in milliseconds. Defaults to None.
            dom_content_loaded_timeout (Optional[int]): DOM content loaded
                timeout in milliseconds. Defaults to None.
            viewport_limit (bool): Whether to filter page snapshot
                elements to only those visible in the current viewport.
                Defaults to False.
            connect_over_cdp (bool): Whether to connect to an existing
                browser via Chrome DevTools Protocol. Defaults to False.
                (Only supported in TypeScript mode)
            cdp_url (Optional[str]): WebSocket endpoint URL for CDP
                connection. Required when connect_over_cdp is True.
                Defaults to None. (Only supported in TypeScript mode)
            cdp_keep_current_page (bool): When True and using CDP mode,
            won't create new pages but use the existing one. Defaults to False.
                (Only supported in TypeScript mode)
            full_visual_mode (bool): When True, browser actions like click,
                browser_open, visit_page, etc. will return 'full visual mode'
                as snapshot instead of actual page content. The
                browser_get_page_snapshot method will still return the actual
                snapshot. Defaults to False.
            **kwargs: Additional keyword arguments passed to the
                implementation.

        Returns:
            HybridBrowserToolkit instance of the specified implementation.
        """
        if mode == "typescript":
            from .hybrid_browser_toolkit_ts import (
                HybridBrowserToolkit as TSToolkit,
            )

            return TSToolkit(
                headless=headless,
                user_data_dir=user_data_dir,
                stealth=stealth,
                cache_dir=cache_dir,
                enabled_tools=enabled_tools,
                browser_log_to_file=browser_log_to_file,
                log_dir=log_dir,
                session_id=session_id,
                default_start_url=default_start_url,
                default_timeout=default_timeout,
                short_timeout=short_timeout,
                navigation_timeout=navigation_timeout,
                network_idle_timeout=network_idle_timeout,
                screenshot_timeout=screenshot_timeout,
                page_stability_timeout=page_stability_timeout,
                dom_content_loaded_timeout=dom_content_loaded_timeout,
                viewport_limit=viewport_limit,
                connect_over_cdp=connect_over_cdp,
                cdp_url=cdp_url,
                cdp_keep_current_page=cdp_keep_current_page,
                full_visual_mode=full_visual_mode,
                **kwargs,
            )
        elif mode == "python":
            from ..hybrid_browser_toolkit_py import (
                HybridBrowserToolkit as PyToolkit,
            )

            # Note: Python implementation doesn't support CDP connection
            if connect_over_cdp:
                raise ValueError(
                    "CDP connection is only supported in TypeScript mode"
                )

            # Note: Python implementation doesn't support viewport_limit
            if viewport_limit:
                import warnings

                warnings.warn(
                    "viewport_limit is not supported "
                    "in Python mode and will be ignored",
                    UserWarning,
                )

            return PyToolkit(
                headless=headless,
                user_data_dir=user_data_dir,
                stealth=stealth,
                cache_dir=cache_dir,
                enabled_tools=enabled_tools,
                browser_log_to_file=browser_log_to_file,
                log_dir=log_dir,
                session_id=session_id,
                default_start_url=default_start_url,
                default_timeout=default_timeout,
                short_timeout=short_timeout,
                navigation_timeout=navigation_timeout,
                network_idle_timeout=network_idle_timeout,
                screenshot_timeout=screenshot_timeout,
                page_stability_timeout=page_stability_timeout,
                dom_content_loaded_timeout=dom_content_loaded_timeout,
                **kwargs,
            )
        else:
            raise ValueError(
                f"Invalid mode: {mode}. Must be 'typescript' or 'python'."
            )
