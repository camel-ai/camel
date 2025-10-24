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
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional, TypedDict

from camel.logger import get_logger
from camel.utils.token_counting import BaseTokenCounter

logger = get_logger(__name__)


class ToolCategory(Enum):
    """Categories of tools based on their typical token consumption."""

    # Low-cost tools (typically < 100 tokens)
    SEARCH_API = "search_api"  # Google Search, Bing Search, etc.
    SIMPLE_UTILITY = (
        "simple_utility"  # Basic file operations, simple calculations
    )

    # Medium-cost tools (100-1000 tokens)
    CODE_EXECUTION = "code_execution"  # Python execution, shell commands
    DOCUMENT_PROCESSING = "document_processing"  # PDF parsing, text analysis
    API_CALLS = "api_calls"  # REST API calls, webhooks

    # High-cost tools (1000+ tokens)
    BROWSER_AUTOMATION = (
        "browser_automation"  # Browser interactions, screenshots
    )
    MULTIMODAL_PROCESSING = (
        "multimodal_processing"  # Image analysis, audio processing
    )
    LLM_CALLS = "llm_calls"  # Sub-agent calls, complex reasoning


@dataclass
class ToolCostProfile:
    """Cost profile for a specific tool type."""

    category: ToolCategory
    base_tokens: int  # Base token consumption
    input_token_multiplier: float = 1.0  # Multiplier based on input size
    output_token_multiplier: float = 1.0  # Multiplier based on output size
    cost_per_token_usd: float = (
        0.00001  # Cost per token in USD (default: $0.00001)
    )
    execution_overhead_ms: int = 0  # Additional execution time overhead


class ToolCostInfo(TypedDict):
    """Typed return structure for tool cost estimation."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    tool_category: str


class ToolCostCalculator:
    """Calculator for estimating token usage and costs of tool calls."""

    def __init__(self, token_counter: Optional[BaseTokenCounter] = None):
        """Initialize the tool cost calculator.

        Args:
            token_counter: Token counter for accurate token estimation.
                          If None, uses simple word-based estimation.
        """
        self.token_counter = token_counter
        self._tool_profiles: Dict[str, ToolCostProfile] = (
            self._initialize_default_profiles()
        )

    def _initialize_default_profiles(self) -> Dict[str, ToolCostProfile]:
        """Initialize default cost profiles for common tool types."""
        return {
            # Search tools - low cost
            "search_google": ToolCostProfile(
                category=ToolCategory.SEARCH_API,
                base_tokens=50,
                # input_token_multiplier=0.1,
                # output_token_multiplier=0.2,
                # cost_per_token_usd=0.000005,
                # execution_overhead_ms=500,
            ),
            "search_bing": ToolCostProfile(
                category=ToolCategory.SEARCH_API,
                base_tokens=50,
                # input_token_multiplier=0.1,
                # output_token_multiplier=0.2,
                # cost_per_token_usd=0.000005,
                # execution_overhead_ms=500,
            ),
            "search_exa": ToolCostProfile(
                category=ToolCategory.SEARCH_API,
                base_tokens=50,
                # input_token_multiplier=0.1,
                # output_token_multiplier=0.2,
                # cost_per_token_usd=0.000005,
                # execution_overhead_ms=500,
            ),
            # Browser tools - high cost
            "browser_visit_page": ToolCostProfile(
                category=ToolCategory.BROWSER_AUTOMATION,
                base_tokens=200,
                # input_token_multiplier=0.05,
                # output_token_multiplier=0.1,
                # cost_per_token_usd=0.00002,
                # execution_overhead_ms=2000,
            ),
            "browser_get_som_screenshot": ToolCostProfile(
                category=ToolCategory.BROWSER_AUTOMATION,
                base_tokens=500,
                # input_token_multiplier=0.0,
                # output_token_multiplier=0.0,
                # cost_per_token_usd=0.00005,
                # execution_overhead_ms=3000,
            ),
            "browser_click": ToolCostProfile(
                category=ToolCategory.BROWSER_AUTOMATION,
                base_tokens=100,
                # input_token_multiplier=0.05,
                # output_token_multiplier=0.05,
                # cost_per_token_usd=0.00002,
                # execution_overhead_ms=1000,
            ),
            "browser_type": ToolCostProfile(
                category=ToolCategory.BROWSER_AUTOMATION,
                base_tokens=100,
                # input_token_multiplier=0.1,
                # output_token_multiplier=0.05,
                # cost_per_token_usd=0.00002,
                # execution_overhead_ms=1000,
            ),
            # Terminal tools - medium cost
            "shell_exec": ToolCostProfile(
                category=ToolCategory.CODE_EXECUTION,
                base_tokens=100,
                # input_token_multiplier=0.2,
                # output_token_multiplier=0.3,
                # cost_per_token_usd=0.00001,
                # execution_overhead_ms=1000,
            ),
            # Note-taking tools - low cost
            "create_note": ToolCostProfile(
                category=ToolCategory.SIMPLE_UTILITY,
                base_tokens=50,
                # input_token_multiplier=0.1,
                # output_token_multiplier=0.0,
                # cost_per_token_usd=0.000005,
                # execution_overhead_ms=100,
            ),
        }

    def estimate_tool_cost(
        self,
        tool_name: str,
        args: Dict[str, Any],
        result: Any,
        execution_time_ms: Optional[int] = None,
    ) -> ToolCostInfo:
        """Estimate the token usage and cost for a tool call.

        Args:
            tool_name: Name of the tool being called.
            args: Arguments passed to the tool.
            result: Result returned by the tool.
            execution_time_ms: Actual execution time in milliseconds.

        Returns:
            Dictionary containing token usage and cost estimates.
        """
        profile = self._tool_profiles.get(tool_name)
        if not profile:
            # Default profile for unknown tools
            profile = ToolCostProfile(
                category=ToolCategory.SIMPLE_UTILITY,
                base_tokens=100,
                # input_token_multiplier=0.1,
                # output_token_multiplier=0.1,
                # cost_per_token_usd=0.00001,
                # execution_overhead_ms=500,
            )

        # Calculate input tokens
        input_text = self._extract_text_from_args(args)
        input_tokens = self._count_tokens(input_text)

        # Calculate output tokens
        output_text = self._extract_text_from_result(result)
        output_tokens = self._count_tokens(output_text)

        # Calculate total tokens
        total_tokens = profile.base_tokens + input_tokens + output_tokens

        return {
            "prompt_tokens": input_tokens,
            "completion_tokens": output_tokens,
            "total_tokens": total_tokens,
            "tool_category": profile.category.value,
        }

    def _extract_text_from_args(self, args: Dict[str, Any]) -> str:
        """Extract text content from tool arguments."""
        text_parts = []
        for _key, value in args.items():
            if isinstance(value, str):
                text_parts.append(value)
            elif isinstance(value, (list, dict)):
                text_parts.append(str(value))
        return " ".join(text_parts)

    def _extract_text_from_result(self, result: Any) -> str:
        """Extract text content from tool result."""
        if isinstance(result, str):
            return result
        elif isinstance(result, dict):
            # Extract text from common result fields
            text_fields = ["content", "text", "message", "result", "output"]
            for field in text_fields:
                if field in result and isinstance(result[field], str):
                    return result[field]
            return str(result)
        else:
            return str(result)

    def _count_tokens(self, text: str) -> int:
        """Count tokens using tokenizer encode when available;
        otherwise, estimate.
        """
        if self.token_counter:
            try:
                return len(self.token_counter.encode(text))
            except Exception as e:
                logger.error(f"Error counting tokens: {e}")
                pass

        return len(text.split())

    def register_tool_profile(
        self, tool_name: str, profile: ToolCostProfile
    ) -> None:
        """Register a custom cost profile for a tool.

        Args:
            tool_name: Name of the tool.
            profile: Cost profile for the tool.
        """
        self._tool_profiles[tool_name] = profile

    def get_tool_profile(self, tool_name: str) -> Optional[ToolCostProfile]:
        """Get the cost profile for a tool.

        Args:
            tool_name: Name of the tool.

        Returns:
            Cost profile for the tool, or None if not found.
        """
        return self._tool_profiles.get(tool_name)
