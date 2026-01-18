# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========

from typing import Any, Dict

from camel.types.enums import BrowserInteractionMode


class ToolGenerator:
    r"""Generates dynamic tool schemas based on browser interaction mode.

    This class provides methods to generate OpenAI function call compatible
    schemas for browser tools that adapt their parameters based on the
    interaction mode (DEFAULT, FULL_VISION, or PIXEL_INTERACTION).

    In PIXEL_INTERACTION mode:
    - browser_click: Uses (x, y) coordinates instead of ref
    - browser_type: Uses (x, y) coordinates instead of ref
    - Screenshots default to no labels (include_labels=False)

    In DEFAULT/FULL_VISION modes:
    - browser_click: Uses ref parameter
    - browser_type: Uses ref parameter
    - Screenshots default to labels (include_labels=True)
    """

    def generate_click_tool(
        self, mode: BrowserInteractionMode
    ) -> Dict[str, Any]:
        r"""Generate schema for browser_click tool based on mode.

        Args:
            mode: The browser interaction mode.

        Returns:
            Dict[str, Any]: OpenAI function call compatible schema.
        """
        is_pixel_mode = mode == BrowserInteractionMode.PIXEL_INTERACTION

        schema = {
            "type": "function",
            "function": {
                "name": "browser_click",
                "description": (
                    "Performs a click on an element using pixel coordinates. "
                    "Provide the x, y coordinates and a reason for the click."
                    if is_pixel_mode
                    else "Performs a click on an element. The `ref` ID is "
                    "obtained from a page snapshot."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        }

        if is_pixel_mode:
            schema["function"]["parameters"]["properties"] = {
                "x": {
                    "type": "number",
                    "description": "X-coordinate for the click (in pixels).",
                },
                "y": {
                    "type": "number",
                    "description": "Y-coordinate for the click (in pixels).",
                },
                "reason": {
                    "type": "string",
                    "description": "Reason for clicking at this location.",
                },
            }
            schema["function"]["parameters"]["required"] = ["x", "y"]
        else:
            schema["function"]["parameters"]["properties"] = {
                "ref": {
                    "type": "string",
                    "description": "The `ref` ID of the element to click. "
                    "This ID is obtained from a page snapshot "
                    "(get_page_snapshot or get_som_screenshot).",
                }
            }
            schema["function"]["parameters"]["required"] = ["ref"]

        return schema

    def generate_type_tool(
        self, mode: BrowserInteractionMode
    ) -> Dict[str, Any]:
        r"""Generate schema for browser_type tool based on mode.

        Args:
            mode: The browser interaction mode.

        Returns:
            Dict[str, Any]: OpenAI function call compatible schema.
        """
        is_pixel_mode = mode == BrowserInteractionMode.PIXEL_INTERACTION

        schema = {
            "type": "function",
            "function": {
                "name": "browser_type",
                "description": (
                    "Types text into an element using pixel coordinates. "
                    "Provide the x, y coordinates, the text to type, "
                    "and a reason."
                    if is_pixel_mode
                    else "Types text into an input element. The `ref` ID is "
                    "obtained from a page snapshot."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        }

        if is_pixel_mode:
            schema["function"]["parameters"]["properties"] = {
                "x": {
                    "type": "number",
                    "description": "X-coordinate for the element (in pixels).",
                },
                "y": {
                    "type": "number",
                    "description": "Y-coordinate for the element (in pixels).",
                },
                "text": {
                    "type": "string",
                    "description": "The text to type into the element.",
                },
                "reason": {
                    "type": "string",
                    "description": "Reason for typing at this location.",
                },
            }
            schema["function"]["parameters"]["required"] = ["x", "y", "text"]
        else:
            schema["function"]["parameters"]["properties"] = {
                "ref": {
                    "type": "string",
                    "description": "The `ref` ID of the input element, from "
                    "a snapshot.",
                },
                "text": {
                    "type": "string",
                    "description": "The text to type into the element.",
                },
            }
            schema["function"]["parameters"]["required"] = ["ref", "text"]

        return schema

    def generate_screenshot_tool(
        self, mode: BrowserInteractionMode
    ) -> Dict[str, Any]:
        r"""Generate schema for browser_get_som_screenshot tool based on mode.

        Args:
            mode: The browser interaction mode.

        Returns:
            Dict[str, Any]: OpenAI function call compatible schema.
        """
        is_pixel_mode = mode == BrowserInteractionMode.PIXEL_INTERACTION

        schema = {
            "type": "function",
            "function": {
                "name": "browser_get_som_screenshot",
                "description": (
                    "Captures a clean screenshot without element labels. "
                    "Use for visual analysis by vision models."
                    if is_pixel_mode
                    else 'Captures a screenshot with interactive elements '
                    'highlighted and labeled (SoM - "Set of Marks"). '
                    'Use for visual understanding of the page.'
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "include_labels": {
                            "type": "boolean",
                            "description": (
                                "Whether to include element labels in the "
                                "screenshot. False = clean screenshot, "
                                "True = labeled elements."
                            ),
                            "default": False if is_pixel_mode else True,
                        },
                        "read_image": {
                            "type": "boolean",
                            "description": "If True, the screenshot image will "
                            "be included in the agent's context for direct "
                            "visual analysis. If False, only a text message "
                            "(including the saved file path) will be returned.",
                            "default": True,
                        },
                    },
                    "required": [],
                },
            },
        }

        return schema
