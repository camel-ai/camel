#!/usr/bin/env python3
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

"""
Configuration for browser automation including stealth mode and timeouts.

This module contains all the configuration needed to make the browser
appear as a regular user browser and configure action timeouts.
"""

import os
from typing import Any, Dict, List, Optional


class BrowserConfig:
    r"""Configuration class for browser settings including stealth mode and
    timeouts."""

    # Default timeout values (in milliseconds)
    DEFAULT_ACTION_TIMEOUT = 3000
    DEFAULT_SHORT_TIMEOUT = 1000
    DEFAULT_NAVIGATION_TIMEOUT = 10000
    DEFAULT_NETWORK_IDLE_TIMEOUT = 5000
    DEFAULT_SCREENSHOT_TIMEOUT = 15000
    DEFAULT_PAGE_STABILITY_TIMEOUT = 1500
    DEFAULT_DOM_CONTENT_LOADED_TIMEOUT = 5000

    # Default action limits
    DEFAULT_MAX_SCROLL_AMOUNT = 5000  # Maximum scroll distance in pixels

    @staticmethod
    def get_timeout_config() -> Dict[str, int]:
        r"""Get timeout configuration with environment variable support.

        Returns:
            Dict[str, int]: Timeout configuration in milliseconds.
        """
        return {
            'default_timeout': int(
                os.getenv(
                    'HYBRID_BROWSER_DEFAULT_TIMEOUT',
                    BrowserConfig.DEFAULT_ACTION_TIMEOUT,
                )
            ),
            'short_timeout': int(
                os.getenv(
                    'HYBRID_BROWSER_SHORT_TIMEOUT',
                    BrowserConfig.DEFAULT_SHORT_TIMEOUT,
                )
            ),
            'navigation_timeout': int(
                os.getenv(
                    'HYBRID_BROWSER_NAVIGATION_TIMEOUT',
                    BrowserConfig.DEFAULT_NAVIGATION_TIMEOUT,
                )
            ),
            'network_idle_timeout': int(
                os.getenv(
                    'HYBRID_BROWSER_NETWORK_IDLE_TIMEOUT',
                    BrowserConfig.DEFAULT_NETWORK_IDLE_TIMEOUT,
                )
            ),
            'screenshot_timeout': int(
                os.getenv(
                    'HYBRID_BROWSER_SCREENSHOT_TIMEOUT',
                    BrowserConfig.DEFAULT_SCREENSHOT_TIMEOUT,
                )
            ),
            'page_stability_timeout': int(
                os.getenv(
                    'HYBRID_BROWSER_PAGE_STABILITY_TIMEOUT',
                    BrowserConfig.DEFAULT_PAGE_STABILITY_TIMEOUT,
                )
            ),
            'dom_content_loaded_timeout': int(
                os.getenv(
                    'HYBRID_BROWSER_DOM_CONTENT_LOADED_TIMEOUT',
                    BrowserConfig.DEFAULT_DOM_CONTENT_LOADED_TIMEOUT,
                )
            ),
        }

    @staticmethod
    def get_action_limits() -> Dict[str, int]:
        r"""Get action limits configuration with environment variable support.

        Returns:
            Dict[str, int]: Action limits configuration.
        """
        return {
            'max_scroll_amount': int(
                os.getenv(
                    'HYBRID_BROWSER_MAX_SCROLL_AMOUNT',
                    BrowserConfig.DEFAULT_MAX_SCROLL_AMOUNT,
                )
            ),
        }

    @staticmethod
    def get_action_timeout(override: Optional[int] = None) -> int:
        r"""Get action timeout with optional override.

        Args:
            override: Optional timeout override value in milliseconds.

        Returns:
            int: Timeout value in milliseconds.
        """
        if override is not None:
            return override
        return BrowserConfig.get_timeout_config()['default_timeout']

    @staticmethod
    def get_short_timeout(override: Optional[int] = None) -> int:
        r"""Get short timeout with optional override.

        Args:
            override: Optional timeout override value in milliseconds.

        Returns:
            int: Timeout value in milliseconds.
        """
        if override is not None:
            return override
        return BrowserConfig.get_timeout_config()['short_timeout']

    @staticmethod
    def get_navigation_timeout(override: Optional[int] = None) -> int:
        r"""Get navigation timeout with optional override.

        Args:
            override: Optional timeout override value in milliseconds.

        Returns:
            int: Timeout value in milliseconds.
        """
        if override is not None:
            return override
        return BrowserConfig.get_timeout_config()['navigation_timeout']

    @staticmethod
    def get_network_idle_timeout(override: Optional[int] = None) -> int:
        r"""Get network idle timeout with optional override.

        Args:
            override: Optional timeout override value in milliseconds.

        Returns:
            int: Timeout value in milliseconds.
        """
        if override is not None:
            return override
        return BrowserConfig.get_timeout_config()['network_idle_timeout']

    @staticmethod
    def get_max_scroll_amount(override: Optional[int] = None) -> int:
        r"""Get maximum scroll amount with optional override.

        Args:
            override: Optional scroll amount override value in pixels.

        Returns:
            int: Maximum scroll amount in pixels.
        """
        if override is not None:
            return override
        return BrowserConfig.get_action_limits()['max_scroll_amount']

    @staticmethod
    def get_screenshot_timeout(override: Optional[int] = None) -> int:
        r"""Get screenshot timeout with optional override.

        Args:
            override: Optional timeout override value in milliseconds.

        Returns:
            int: Timeout value in milliseconds.
        """
        if override is not None:
            return override
        return BrowserConfig.get_timeout_config()['screenshot_timeout']

    @staticmethod
    def get_page_stability_timeout(override: Optional[int] = None) -> int:
        r"""Get page stability timeout with optional override.

        Args:
            override: Optional timeout override value in milliseconds.

        Returns:
            int: Timeout value in milliseconds.
        """
        if override is not None:
            return override
        return BrowserConfig.get_timeout_config()['page_stability_timeout']

    @staticmethod
    def get_dom_content_loaded_timeout(override: Optional[int] = None) -> int:
        r"""Get DOM content loaded timeout with optional override.

        Args:
            override: Optional timeout override value in milliseconds.

        Returns:
            int: Timeout value in milliseconds.
        """
        if override is not None:
            return override
        return BrowserConfig.get_timeout_config()['dom_content_loaded_timeout']

    @staticmethod
    def get_launch_args() -> List[str]:
        r"""Get Chrome launch arguments for stealth mode.

        Returns:
            List[str]: Chrome command line arguments to avoid detection.
        """
        return [
            '--disable-blink-features=AutomationControlled',
            '--disable-features=VizDisplayCompositor',
            '--disable-ipc-flooding-protection',
            '--disable-renderer-backgrounding',
            '--disable-backgrounding-occluded-windows',
            '--disable-dev-shm-usage',
            '--disable-extensions',
            '--disable-plugins',
            '--disable-default-apps',
            '--disable-sync',
            '--no-default-browser-check',
            '--no-first-run',
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-web-security',
            '--disable-features=TranslateUI',
            '--disable-features=BlinkGenPropertyTrees',
            '--disable-component-extensions-with-background-pages',
        ]

    @staticmethod
    def get_context_options() -> Dict[str, Any]:
        r"""Get browser context options for stealth mode.

        Returns:
            Dict[str, Any]: Browser context configuration options.
        """
        return {
            'user_agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/131.0.0.0 Safari/537.36'
            ),
            'viewport': {'width': 1920, 'height': 1080},
            'locale': 'en-US',
            'timezone_id': 'America/New_York',
            'geolocation': {'latitude': 40.7128, 'longitude': -74.0060},
            'permissions': ['geolocation'],
        }

    @staticmethod
    def get_http_headers() -> Dict[str, str]:
        r"""Get HTTP headers for stealth mode.

        Returns:
            Dict[str, str]: HTTP headers to appear more like a real browser.
        """
        return {
            'Accept': (
                'text/html,application/xhtml+xml,application/xml;q=0.9,'
                'image/avif,image/webp,image/apng,*/*;q=0.8,'
                'application/signed-exchange;v=b3;q=0.7'
            ),
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Cache-Control': 'max-age=0',
            'Sec-Ch-Ua': (
                '"Google Chrome";v="131", "Chromium";v="131", '
                '"Not=A?Brand";v="24"'
            ),
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
        }

    @staticmethod
    def get_stealth_config() -> Dict[str, Any]:
        r"""Get stealth configuration.

        Returns:
            Dict[str, Any]: Complete stealth configuration.
        """
        return {
            'launch_args': BrowserConfig.get_launch_args(),
            'context_options': BrowserConfig.get_context_options(),
            'http_headers': BrowserConfig.get_http_headers(),
        }

    @staticmethod
    def get_all_config() -> Dict[str, Any]:
        r"""Get all browser configuration including stealth, timeouts,
        and action limits.

        Returns:
            Dict[str, Any]: Complete browser configuration.
        """
        return {
            'timeouts': BrowserConfig.get_timeout_config(),
            'action_limits': BrowserConfig.get_action_limits(),
            'stealth': BrowserConfig.get_stealth_config(),
        }


# Legacy ConfigLoader class for compatibility (now just wraps BrowserConfig)
class ConfigLoader:
    r"""Legacy wrapper for BrowserConfig - maintained for backward
    compatibility."""

    @classmethod
    def get_browser_config(cls):
        r"""Get the BrowserConfig class."""
        return BrowserConfig

    @classmethod
    def get_stealth_config(cls):
        r"""Get the StealthConfig class (alias)."""
        return BrowserConfig  # StealthConfig is an alias for BrowserConfig

    @classmethod
    def get_timeout_config(cls) -> Dict[str, int]:
        r"""Get timeout configuration."""
        return BrowserConfig.get_timeout_config()

    @classmethod
    def get_action_timeout(cls, override: Optional[int] = None) -> int:
        r"""Get action timeout with optional override."""
        return BrowserConfig.get_action_timeout(override)

    @classmethod
    def get_short_timeout(cls, override: Optional[int] = None) -> int:
        r"""Get short timeout with optional override."""
        return BrowserConfig.get_short_timeout(override)

    @classmethod
    def get_navigation_timeout(cls, override: Optional[int] = None) -> int:
        r"""Get navigation timeout with optional override."""
        return BrowserConfig.get_navigation_timeout(override)

    @classmethod
    def get_network_idle_timeout(cls, override: Optional[int] = None) -> int:
        r"""Get network idle timeout with optional override."""
        return BrowserConfig.get_network_idle_timeout(override)

    @classmethod
    def get_max_scroll_amount(cls, override: Optional[int] = None) -> int:
        r"""Get maximum scroll amount with optional override."""
        return BrowserConfig.get_max_scroll_amount(override)

    @classmethod
    def get_screenshot_timeout(cls, override: Optional[int] = None) -> int:
        r"""Get screenshot timeout with optional override."""
        return BrowserConfig.get_screenshot_timeout(override)

    @classmethod
    def get_page_stability_timeout(cls, override: Optional[int] = None) -> int:
        r"""Get page stability timeout with optional override."""
        return BrowserConfig.get_page_stability_timeout(override)

    @classmethod
    def get_dom_content_loaded_timeout(
        cls, override: Optional[int] = None
    ) -> int:
        r"""Get DOM content loaded timeout with optional override."""
        return BrowserConfig.get_dom_content_loaded_timeout(override)


# Backward compatibility aliases and convenience functions
StealthConfig = BrowserConfig


def get_browser_config():
    r"""Get BrowserConfig class."""
    return BrowserConfig


def get_stealth_config():
    r"""Get StealthConfig class."""
    return BrowserConfig


def get_timeout_config() -> Dict[str, int]:
    r"""Get timeout configuration."""
    return BrowserConfig.get_timeout_config()


def get_action_timeout(override: Optional[int] = None) -> int:
    r"""Get action timeout with optional override."""
    return BrowserConfig.get_action_timeout(override)


def get_short_timeout(override: Optional[int] = None) -> int:
    r"""Get short timeout with optional override."""
    return BrowserConfig.get_short_timeout(override)


def get_navigation_timeout(override: Optional[int] = None) -> int:
    r"""Get navigation timeout with optional override."""
    return BrowserConfig.get_navigation_timeout(override)


def get_network_idle_timeout(override: Optional[int] = None) -> int:
    r"""Get network idle timeout with optional override."""
    return BrowserConfig.get_network_idle_timeout(override)


def get_max_scroll_amount(override: Optional[int] = None) -> int:
    r"""Get maximum scroll amount with optional override."""
    return BrowserConfig.get_max_scroll_amount(override)


def get_screenshot_timeout(override: Optional[int] = None) -> int:
    r"""Get screenshot timeout with optional override."""
    return BrowserConfig.get_screenshot_timeout(override)


def get_page_stability_timeout(override: Optional[int] = None) -> int:
    r"""Get page stability timeout with optional override."""
    return BrowserConfig.get_page_stability_timeout(override)


def get_dom_content_loaded_timeout(override: Optional[int] = None) -> int:
    r"""Get DOM content loaded timeout with optional override."""
    return BrowserConfig.get_dom_content_loaded_timeout(override)
