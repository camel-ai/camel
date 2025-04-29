from typing import Dict, Optional, Set

from camel.types.enums import OutputExtractionErrorType
from camel.prompts.output_format.base import (
    Validator, ExtractionResult
)


class JsonRequiredKeysValidator(Validator):
    """JSON required keys validator."""
    
    def __init__(self, required_keys: Optional[Set[str]] = None) -> None:
        """Initialize the validator.
        
        Args:
            required_keys (Optional[Set[str]]): Set of required keys
        """
        self.required_keys = required_keys or set()
        
    def validate(self, data: Dict) -> ExtractionResult:
        if not self.required_keys:
            return ExtractionResult(data = data, is_success=True)
            
        if not isinstance(data, dict):
            return ExtractionResult(
                is_success=False,
                error_message="Data is not a dictionary type",
                error_type=OutputExtractionErrorType.VALIDATION
            )
            
        missing_keys = self.required_keys - set(data.keys())
        if missing_keys:
            return ExtractionResult(
                is_success=False,
                error_message=f"Missing required keys: {', '.join(missing_keys)}",
                error_type=OutputExtractionErrorType.VALIDATION
            )
            
        return ExtractionResult(data=data, is_success=True)
