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
Stealth configuration for browser automation to avoid bot detection.

This module contains all the configuration needed to make the browser
appear as a regular user browser rather than an automated one.
"""

from typing import Any, Dict, List


class StealthConfig:
    """Configuration class for stealth browser settings."""

    @staticmethod
    def get_launch_args() -> List[str]:
        """Get Chrome launch arguments for stealth mode.

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
        """Get browser context options for stealth mode.

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
        """Get HTTP headers for stealth mode.

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
    def get_all_config() -> Dict[str, Any]:
        """Get all stealth configuration in one dict.

        Returns:
            Dict[str, Any]: Complete stealth configuration.
        """
        return {
            'launch_args': StealthConfig.get_launch_args(),
            'context_options': StealthConfig.get_context_options(),
            'http_headers': StealthConfig.get_http_headers(),
        }
