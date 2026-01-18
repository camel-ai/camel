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
# ruff: noqa: E501
"""Common utility functions for subtask toolkit."""

import datetime
import json
from typing import Any, Dict, List, Optional

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType


# === Model & Agent Creation ===
def create_gpt4_model(temperature: float = 0.0):
    """
    Create standard GPT-4 model.

    Args:
        temperature: Model temperature (default: 0.0)

    Returns:
        Configured GPT-4 model
    """
    return ModelFactory.create(
        model_platform=ModelPlatformType.AZURE,
        model_type=ModelType.GPT_4_1,
        model_config_dict={"temperature": temperature},
    )


def create_chat_agent(
    role_name: str,
    system_content: str,
    model=None,
    tools: Optional[List] = None,
) -> ChatAgent:
    """
    Create standard ChatAgent with system message.

    Args:
        role_name: Role name for the agent
        system_content: System message content
        model: Model instance (default: creates GPT-4 with temp=0.0)
        tools: List of tools for the agent

    Returns:
        Configured ChatAgent
    """
    if model is None:
        model = create_gpt4_model()

    system_message = BaseMessage.make_assistant_message(
        role_name=role_name, content=system_content
    )

    return ChatAgent(
        system_message=system_message, model=model, tools=tools or []
    )


# === Token Usage ===
def extract_token_usage(usage) -> Dict[str, int]:
    """
    Extract token usage from response usage object.

    Args:
        usage: Usage object or dict from model response

    Returns:
        Dict with 'prompt', 'completion', and 'total' token counts
    """
    if hasattr(usage, 'prompt_tokens') and hasattr(usage, 'completion_tokens'):
        prompt_tokens = usage.prompt_tokens
        completion_tokens = usage.completion_tokens
    elif isinstance(usage, dict):
        prompt_tokens = usage.get('prompt_tokens', 0)
        completion_tokens = usage.get('completion_tokens', 0)
    else:
        prompt_tokens = 0
        completion_tokens = 0

    return {
        'prompt': prompt_tokens,
        'completion': completion_tokens,
        'total': prompt_tokens + completion_tokens,
    }


# === File I/O ===
def load_json(file_path: str) -> Dict[str, Any]:
    """
    Load JSON file with standard encoding.

    Args:
        file_path: Path to JSON file

    Returns:
        Parsed JSON data
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(file_path: str, data: Any, indent: int = 2):
    """
    Save JSON file with standard encoding.

    Args:
        file_path: Path to save JSON file
        data: Data to serialize
        indent: Indentation level (default: 2)
    """
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)


# === Formatting ===
def print_section(
    title: str,
    char: str = "=",
    width: int = 80,
    newline_before: bool = True,
):
    """
    Print section title with separator lines.

    Args:
        title: Section title
        char: Character for separator line
        width: Width of separator line
        newline_before: Add newline before section
    """
    if newline_before:
        print()
    print(char * width)
    print(title)
    print(char * width)


def print_separator(char: str = "=", width: int = 80):
    """
    Print separator line.

    Args:
        char: Character for separator line
        width: Width of separator line
    """
    print(char * width)


# === Timestamps ===
def get_timestamp_iso() -> str:
    """
    Get ISO format timestamp.

    Returns:
        Current timestamp in ISO format
    """
    return datetime.datetime.now().isoformat()


def get_timestamp_filename() -> str:
    """
    Get filename-safe timestamp.

    Returns:
        Current timestamp in YYYYMMDD_HHMMSS format
    """
    return datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
