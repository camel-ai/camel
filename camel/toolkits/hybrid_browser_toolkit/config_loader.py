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
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class BrowserConfig:
    """Browser configuration settings."""

    # Browser configuration
    headless: bool = True
    user_data_dir: Optional[str] = None
    stealth: bool = False
    console_log_limit: int = 1000

    # Default settings
    default_start_url: str = "https://google.com/"

    # Timeout configurations (in milliseconds)
    default_timeout: Optional[int] = None
    short_timeout: Optional[int] = None
    navigation_timeout: int = 30000
    network_idle_timeout: int = 5000
    screenshot_timeout: int = 15000
    page_stability_timeout: int = 1500
    dom_content_loaded_timeout: int = 5000

    # Viewport configuration
    viewport_limit: bool = False

    # CDP connection configuration
    connect_over_cdp: bool = False
    cdp_url: Optional[str] = None
    cdp_keep_current_page: bool = False

    # Full visual mode configuration
    full_visual_mode: bool = False


@dataclass
class ToolkitConfig:
    """Toolkit-specific configuration."""

    cache_dir: str = "tmp/"
    browser_log_to_file: bool = False
    log_dir: Optional[str] = None
    session_id: Optional[str] = None
    enabled_tools: Optional[list] = None


class ConfigLoader:
    """Configuration loader for HybridBrowserToolkit."""

    def __init__(
        self,
        browser_config: Optional[BrowserConfig] = None,
        toolkit_config: Optional[ToolkitConfig] = None,
    ) -> None:
        self.browser_config = browser_config or BrowserConfig()
        self.toolkit_config = toolkit_config or ToolkitConfig()

    @classmethod
    def from_kwargs(cls, **kwargs) -> 'ConfigLoader':
        """Create ConfigLoader from keyword arguments."""
        browser_kwargs = {}
        toolkit_kwargs = {}

        # Map arguments to appropriate config classes
        browser_fields = set(BrowserConfig.__dataclass_fields__.keys())
        toolkit_fields = set(ToolkitConfig.__dataclass_fields__.keys())

        for key, value in kwargs.items():
            # Skip None values to preserve dataclass defaults
            if value is None:
                continue

            if key in browser_fields:
                browser_kwargs[key] = value
            elif key in toolkit_fields:
                toolkit_kwargs[key] = value
            # Handle some common aliases
            elif key == "userDataDir":
                browser_kwargs["user_data_dir"] = value
            elif key == "defaultStartUrl":
                browser_kwargs["default_start_url"] = value
            elif key == "navigationTimeout":
                browser_kwargs["navigation_timeout"] = value
            elif key == "networkIdleTimeout":
                browser_kwargs["network_idle_timeout"] = value
            elif key == "screenshotTimeout":
                browser_kwargs["screenshot_timeout"] = value
            elif key == "pageStabilityTimeout":
                browser_kwargs["page_stability_timeout"] = value
            elif key == "domContentLoadedTimeout":
                browser_kwargs["dom_content_loaded_timeout"] = value
            elif key == "viewportLimit":
                browser_kwargs["viewport_limit"] = value
            elif key == "connectOverCdp":
                browser_kwargs["connect_over_cdp"] = value
            elif key == "cdpUrl":
                browser_kwargs["cdp_url"] = value
            elif key == "cdpKeepCurrentPage":
                browser_kwargs["cdp_keep_current_page"] = value
            elif key == "consoleLogLimit":
                browser_kwargs["console_log_limit"] = value
            elif key == "cacheDir":
                toolkit_kwargs["cache_dir"] = value
            elif key == "browserLogToFile":
                toolkit_kwargs["browser_log_to_file"] = value
            elif key == "sessionId":
                toolkit_kwargs["session_id"] = value
            elif key == "enabledTools":
                toolkit_kwargs["enabled_tools"] = value
            elif key == "fullVisualMode":
                browser_kwargs["full_visual_mode"] = value

        browser_config = BrowserConfig(**browser_kwargs)
        toolkit_config = ToolkitConfig(**toolkit_kwargs)

        return cls(browser_config, toolkit_config)

    def get_browser_config(self) -> BrowserConfig:
        """Get browser configuration."""
        return self.browser_config

    def get_toolkit_config(self) -> ToolkitConfig:
        """Get toolkit configuration."""
        return self.toolkit_config

    def to_ws_config(self) -> Dict[str, Any]:
        """Convert to WebSocket wrapper configuration format."""
        return {
            "headless": self.browser_config.headless,
            "userDataDir": self.browser_config.user_data_dir,
            "stealth": self.browser_config.stealth,
            "defaultStartUrl": self.browser_config.default_start_url,
            "navigationTimeout": self.browser_config.navigation_timeout,
            "networkIdleTimeout": self.browser_config.network_idle_timeout,
            "screenshotTimeout": self.browser_config.screenshot_timeout,
            "pageStabilityTimeout": self.browser_config.page_stability_timeout,
            "browser_log_to_file": self.toolkit_config.browser_log_to_file,
            "log_dir": self.toolkit_config.log_dir,
            "session_id": self.toolkit_config.session_id,
            "viewport_limit": self.browser_config.viewport_limit,
            "connectOverCdp": self.browser_config.connect_over_cdp,
            "cdpUrl": self.browser_config.cdp_url,
            "cdpKeepCurrentPage": self.browser_config.cdp_keep_current_page,
            "fullVisualMode": self.browser_config.full_visual_mode,
        }

    def get_timeout_config(self) -> Dict[str, Optional[int]]:
        """Get all timeout configurations."""
        return {
            "default_timeout": self.browser_config.default_timeout,
            "short_timeout": self.browser_config.short_timeout,
            "navigation_timeout": self.browser_config.navigation_timeout,
            "network_idle_timeout": self.browser_config.network_idle_timeout,
            "screenshot_timeout": self.browser_config.screenshot_timeout,
            "page_stability_timeout": self.browser_config.page_stability_timeout,  # noqa:E501
            "dom_content_loaded_timeout": self.browser_config.dom_content_loaded_timeout,  # noqa:E501
        }

    def update_browser_config(self, **kwargs) -> None:
        """Update browser configuration."""
        for key, value in kwargs.items():
            if hasattr(self.browser_config, key):
                setattr(self.browser_config, key, value)

    def update_toolkit_config(self, **kwargs) -> None:
        """Update toolkit configuration."""
        for key, value in kwargs.items():
            if hasattr(self.toolkit_config, key):
                setattr(self.toolkit_config, key, value)
