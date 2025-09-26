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
Utility functions for streaming token counting support.

This module provides helper functions to enable accurate token counting
in streaming mode by leveraging provider-specific features like OpenAI's
stream_options: {"include_usage": true}.
"""

from typing import Dict, Any
from camel.logger import get_logger

logger = get_logger(__name__)


def enable_streaming_usage_for_openai(model_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enable usage tracking for OpenAI streaming requests.
    
    This function modifies the model configuration to include stream_options
    that enable usage data in the final chunk of streaming responses.
    
    Args:
        model_config: The model configuration dictionary
        
    Returns:
        Modified model configuration with streaming usage enabled
        
    Example:
        >>> config = {"stream": True, "temperature": 0.7}
        >>> updated_config = enable_streaming_usage_for_openai(config)
        >>> print(updated_config)
        {
            "stream": True, 
            "temperature": 0.7,
            "stream_options": {"include_usage": True}
        }
    """
    config = model_config.copy()
    
    if config.get("stream", False):
        if "stream_options" not in config:
            config["stream_options"] = {}
        
        config["stream_options"]["include_usage"] = True
        logger.debug("Enabled streaming usage tracking for OpenAI model")
    
    return config


def get_streaming_usage_config_for_provider(
    provider: str, 
    model_config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Get provider-specific streaming configuration for usage tracking.
    
    Args:
        provider: The model provider name (e.g., "openai", "anthropic", "mistral")
        model_config: The base model configuration
        
    Returns:
        Updated configuration with provider-specific streaming usage settings
    """
    config = model_config.copy()
    if provider.lower() == "openai":
        return enable_streaming_usage_for_openai(config)
    elif provider.lower() == "anthropic":
        logger.debug("Anthropic streaming includes usage by default")
        return config
    elif provider.lower() == "mistral":
        logger.debug("Mistral streaming includes usage by default")
        return config
    elif provider.lower() == "litellm":
        return enable_streaming_usage_for_openai(config)
    else:
        logger.warning(f"Unknown provider '{provider}' for streaming usage configuration")
        return config


def validate_streaming_usage_support(provider: str, model_config: Dict[str, Any]) -> bool:
    """
    Validate if streaming usage tracking is properly configured for a provider.
    
    Args:
        provider: The model provider name
        model_config: The model configuration
        
    Returns:
        True if streaming usage is properly configured, False otherwise
    """
    if not model_config.get("stream", False):
        return True
    
    if provider.lower() == "openai":
        stream_options = model_config.get("stream_options", {})
        return stream_options.get("include_usage", False)
    elif provider.lower() in ["anthropic", "mistral"]:
        return True
    elif provider.lower() == "litellm":
        stream_options = model_config.get("stream_options", {})
        return stream_options.get("include_usage", False)
    else:
        logger.warning(f"Cannot validate streaming usage support for provider '{provider}'")
        return False

"""
STREAMING_USAGE_EXAMPLES = {
    "openai": {
        "description": "OpenAI requires stream_options.include_usage = true",
        "config": {
            "stream": True,
            "stream_options": {"include_usage": True},
            "temperature": 0.7
        },
        "usage_location": "Final chunk of stream"
    },
    "anthropic": {
        "description": "Anthropic includes usage in streaming responses by default",
        "config": {
            "stream": True,
            "temperature": 0.7
        },
        "usage_location": "Each message event in stream"
    },
    "mistral": {
        "description": "Mistral includes usage in streaming responses by default", 
        "config": {
            "stream": True,
            "temperature": 0.7
        },
        "usage_location": "Final chunk of stream"
    }
}
"""
