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

import json
from typing import Dict, Optional, Set

from camel.prompts.output_format.base import (
    Extractor,
    ExtractionResult,
    OutputFormat,
    OutputFormatHandler,
    ValidationResult,
    Validator
)
from camel.types.enums import OutputFormatType


class DefaultOutputFormatHandler(OutputFormatHandler):
    """Default output format handler that directly returns the input text."""
    
    def __init__(
        self, 
        output_format: Optional[OutputFormat] = None,
        **kwargs
    ) -> None:
        """Initialize the default output format handler.
        
        Args:
            output_format (Optional[OutputFormat]): Output format. If None, TEXT type is used.
            **kwargs: Additional parameters, ignored
        """
        # If OutputFormat is not provided, create a default TEXT type
        if output_format is None:
            output_format = OutputFormat(OutputFormatType.TEXT)
        super().__init__(output_format)
    
    def _setup_extractors(self) -> None:
        """Set up extractors (none)."""
        pass
    
    def _setup_validators(self) -> None:
        """Set up validators (none)."""
        pass
    
    def extract_data(self, text: str, validate: bool = True) -> ExtractionResult[str]:
        """Directly return the input text.
        
        Args:
            text (str): Input text
            validate (bool): Whether to validate (ignored here)
            
        Returns:
            ExtractionResult[str]: Successful result containing the input text
        """
        return ExtractionResult(data=text, is_success=True)
    

class JsonDirectExtractor(Extractor[Dict]):
    """Extractor that directly parses JSON."""
    
    def extract(self, text: str) -> ExtractionResult[Dict]:
        try:
            data = json.loads(text)
            if not isinstance(data, dict):
                return ExtractionResult(
                    is_success=False,
                    error_message="Extracted data is not a JSON object",
                    error_type="extraction"
                )
            return ExtractionResult(data=data, is_success=True)
        except json.JSONDecodeError as e:
            return ExtractionResult(
                is_success=False,
                error_message=f"JSON parsing error: {str(e)}",
                error_type="extraction"
            )


class JsonCodeBlockExtractor(Extractor[Dict]):
    """Extractor that extracts JSON from code blocks."""
    
    def extract(self, text: str) -> ExtractionResult[Dict]:
        try:
            # Find content between ```json and ```
            start = text.find("```json")
            if start == -1:
                start = text.find("```")  # Try to find regular code block
            
            if start == -1:
                return ExtractionResult(
                    is_success=False,
                    error_message="JSON code block not found",
                    error_type="extraction"
                )
                
            # Skip ```json or ```
            start = text.find("\n", start) + 1
            end = text.find("```", start)
            
            if end == -1:
                return ExtractionResult(
                    is_success=False,
                    error_message="JSON code block not properly closed",
                    error_type="extraction"
                )
                
            json_text = text[start:end].strip()
            data = json.loads(json_text)
            
            if not isinstance(data, dict):
                return ExtractionResult(
                    is_success=False,
                    error_message="Extracted data is not a JSON object",
                    error_type="extraction"
                )
                
            return ExtractionResult(data=data, is_success=True)
            
        except json.JSONDecodeError as e:
            return ExtractionResult(
                is_success=False,
                error_message=f"JSON parsing error: {str(e)}",
                error_type="extraction"
            )


class JsonRequiredKeysValidator(Validator):
    """JSON required keys validator."""
    
    def __init__(self, required_keys: Optional[Set[str]] = None) -> None:
        """Initialize the validator.
        
        Args:
            required_keys (Optional[Set[str]]): Set of required keys
        """
        self.required_keys = required_keys or set()
        
    def validate(self, data: Dict) -> ValidationResult:
        if not self.required_keys:
            return ValidationResult(True)
            
        if not isinstance(data, dict):
            return ValidationResult(
                False,
                "Data is not a dictionary type"
            )
            
        missing_keys = self.required_keys - set(data.keys())
        if missing_keys:
            return ValidationResult(
                False,
                f"Missing required keys: {', '.join(missing_keys)}"
            )
            
        return ValidationResult(True)


class JsonOutputFormatHandler(OutputFormatHandler):
    """JSON output format handler."""
    
    def __init__(
        self,
        output_format: Optional[OutputFormat] = None,
        required_keys: Optional[Set[str]] = None,
        **kwargs
    ) -> None:
        """Initialize the JSON output format handler.
        
        Args:
            output_format (Optional[OutputFormat]): Output format. If None, JSON type is used.
            required_keys (Optional[Set[str]]): Set of required keys
            **kwargs: Additional parameters, ignored
        """
        self.required_keys = required_keys
        # If OutputFormat is not provided, create a default JSON type
        if output_format is None:
            output_format = OutputFormat(OutputFormatType.JSON)
        # Ensure format_type is JSON
        elif output_format.output_format_type != str(OutputFormatType.JSON):
            output_format = OutputFormat(
                OutputFormatType.JSON,
                output_format.output_format_spec
            )
        super().__init__(output_format)
        
    def _setup_extractors(self) -> None:
        """Set up JSON extractors."""
        self.extractors = [
            JsonDirectExtractor(),
            JsonCodeBlockExtractor()
        ]
        
    def _setup_validators(self) -> None:
        """Set up JSON validators."""
        if self.required_keys:
            self.validators = [JsonRequiredKeysValidator(self.required_keys)]
