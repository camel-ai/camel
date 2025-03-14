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

"""Output format module for handling different data formats.

This module provides classes and utilities for working with structured output
formats, including extraction, validation, and formatting of data in various
formats like JSON.
"""

# Base classes and interfaces
from camel.prompts.output_format.base import (
    OutputFormat,
    ValidationResult,
    ExtractionResult,
    Extractor,
    Validator,
    OutputFormatHandler,
)

# Factory for creating output format handlers
from camel.prompts.output_format.output_format_factory import (
    OutputFormatHandlerFactory,
)

# Concrete handler implementations
from camel.prompts.output_format.output_format_handlers import (
    DefaultOutputFormatHandler,
    JsonOutputFormatHandler,
    JsonDirectExtractor,
    JsonCodeBlockExtractor,
    JsonRequiredKeysValidator,
)

# Prompt templates for output formats
from camel.prompts.output_format.enhance_output_prompt_templates import (
    OUTPUT_FORMAT_INSTRUCTION_TEMPLATE,
    OUTPUT_FORMAT_SPEC_INSTRUCTION_TEMPLATE,
)

# Output format prompts
from camel.prompts.output_format.prompts import OutputFormatPrompt, JsonOutputFormatPrompt

__all__ = [
    # Base classes
    'OutputFormat',
    'ValidationResult',
    'ExtractionResult',
    'Extractor',
    'Validator',
    'OutputFormatHandler',
    
    # Factory
    'OutputFormatHandlerFactory',
    
    # Handlers
    'DefaultOutputFormatHandler',
    'JsonOutputFormatHandler',
    
    # Extractors
    'JsonDirectExtractor',
    'JsonCodeBlockExtractor',
    
    # Validators
    'JsonRequiredKeysValidator',
    
    # Prompt templates
    'OUTPUT_FORMAT_INSTRUCTION_TEMPLATE',
    'OUTPUT_FORMAT_SPEC_INSTRUCTION_TEMPLATE',
    
    # Output format prompts
    'OutputFormatPrompt',
    'JsonOutputFormatPrompt',
] 