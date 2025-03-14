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


from typing import Optional, Union, List, Any, TypeVar, Generic
from abc import ABC, abstractmethod

from camel.types.enums import OutputFormatType


class OutputFormat:
    """Output format data structure for storing format type and specifications.

    Attributes:
        output_format_type (Union[str, OutputFormatType], optional): 
            Data format type (e.g., json, xml, etc.) or OutputFormatType enum value. Defaults to None.
        output_format_spec (str, optional): Format specification or description of key-value pairs/tags. Defaults to None.
    """

    def __init__(
        self,
        output_format_type: Optional[Union[str, OutputFormatType]] = None,
        output_format_spec: Optional[str] = None,
    ) -> None:
        """Initialize an OutputFormat instance.

        Args:
            output_format_type (Union[str, OutputFormatType], optional): 
                Data format type (e.g., json, xml, etc.) or OutputFormatType enum value. Defaults to None.
            output_format_spec (str, optional): Format specification or description of key-value pairs/tags. Defaults to None.
        """
        if isinstance(output_format_type, OutputFormatType):
            self._output_format_type = str(output_format_type)
        else:
            self._output_format_type = output_format_type
        self._output_format_spec = output_format_spec

    @property
    def output_format_type(self) -> Optional[str]:
        """Get the data format type.

        Returns:
            Optional[str]: The data format type.
        """
        return self._output_format_type

    @output_format_type.setter
    def output_format_type(self, output_format_type: Union[str, OutputFormatType]) -> None:
        """Set the data format type.

        Args:
            output_format_type (Union[str, OutputFormatType]): The data format type or OutputFormatType enum value.
        """
        if isinstance(output_format_type, OutputFormatType):
            self._output_format_type = str(output_format_type)
        else:
            self._output_format_type = output_format_type

    @property
    def output_format_spec(self) -> Optional[str]:
        """Get the format specification.

        Returns:
            Optional[str]: The format specification.
        """
        return self._output_format_spec

    @output_format_spec.setter
    def output_format_spec(self, output_format_spec: str) -> None:
        """Set the format specification.

        Args:
            output_format_spec (str): The format specification.
        """
        self._output_format_spec = output_format_spec


# Validation result class
class ValidationResult:
    """Validation result class representing the result of data validation.

    Attributes:
        is_valid (bool): Whether the data is valid
        error_message (Optional[str]): Error message if the data is invalid
    """

    def __init__(self, is_valid: bool, error_message: Optional[str] = None) -> None:
        """Initialize a ValidationResult instance.

        Args:
            is_valid (bool): Whether the data is valid
            error_message (Optional[str], optional): Error message if the data is invalid. Defaults to None.
        """
        self.is_valid = is_valid
        self.error_message = error_message

    def __bool__(self) -> bool:
        """Return boolean representation for conditional evaluation.

        Returns:
            bool: Whether the data is valid
        """
        return self.is_valid


# Data type
T = TypeVar('T')


# Extraction result class
class ExtractionResult(Generic[T]):
    """Extraction result class representing the result of data extraction and validation.
    
    Attributes:
        data (Optional[T]): The extracted data, or None if extraction or validation failed
        is_success (bool): Whether extraction and validation succeeded
        error_messages (List[str]): List of error messages containing extraction and validation errors
        error_type (Optional[str]): Error type, can be 'extraction' or 'validation'
    """
    
    def __init__(
        self, 
        data: Optional[T] = None, 
        is_success: bool = False, 
        error_message: Optional[str] = None,
        error_type: Optional[str] = None
    ) -> None:
        """Initialize an ExtractionResult instance.
        
        Args:
            data (Optional[T], optional): The extracted data. Defaults to None.
            is_success (bool, optional): Whether extraction and validation succeeded. Defaults to False.
            error_message (Optional[str], optional): Error message. Defaults to None.
            error_type (Optional[str], optional): Error type. Defaults to None.
        """
        self.data = data
        self.is_success = is_success
        self.error_messages: List[str] = [error_message] if error_message else []
        self.error_type = error_type
    
    def add_error(self, message: str, error_type: str) -> None:
        """Add an error message.
        
        Args:
            message (str): Error message
            error_type (str): Error type
        """
        self.is_success = False
        self.error_messages.append(message)
        self.error_type = error_type
    
    def __bool__(self) -> bool:
        """Return boolean representation for conditional evaluation.
        
        Returns:
            bool: Whether extraction and validation succeeded
        """
        return self.is_success


# Extractor base class
class Extractor(Generic[T], ABC):
    """Abstract base class for data extractors that extract specific types of data from text."""

    @abstractmethod
    def extract(self, text: str) -> ExtractionResult[T]:
        """Extract data from text.

        Args:
            text (str): The text to extract data from

        Returns:
            ExtractionResult[T]: Extraction result containing the extracted data or error information
        """
        pass


# Validator base class
class Validator(ABC):
    """Abstract base class for data validators that validate whether data conforms to specific rules."""

    @abstractmethod
    def validate(self, data: Any) -> ValidationResult:
        """Validate data.

        Args:
            data (Any): The data to validate

        Returns:
            ValidationResult: Validation result containing whether the data is valid and error information
        """
        pass


class OutputFormatHandler(ABC):
    """Abstract base class for output format handlers that handle extraction, validation, and formatting for different format types.

    Attributes:
        output_format (OutputFormat): The output format object
        extractors (List[Extractor]): List of data extractors
        validators (List[Validator]): Optional list of data validators
    """

    def __init__(
        self,
        output_format: OutputFormat
    ) -> None:
        """Initialize an OutputFormatHandler instance.

        Args:
            output_format (OutputFormat): The output format object
        """
        self.output_format = output_format
        self.extractors: List[Extractor] = []
        self.validators: List[Validator] = []
        self._setup_extractors()
        self._setup_validators()
        
    @property
    def format_type(self) -> OutputFormatType:
        """Get the format type.

        Returns:
            OutputFormatType: The format type
        """
        return OutputFormatType(self.output_format.output_format_type)
    
    @property
    def format_spec(self) -> Optional[str]:
        """Get the format specification.

        Returns:
            Optional[str]: The format specification
        """
        return self.output_format.output_format_spec

    @abstractmethod
    def _setup_extractors(self) -> None:
        """Set up the list of extractors, implemented by subclasses."""
        pass

    @abstractmethod
    def _setup_validators(self) -> None:
        """Set up the list of validators, implemented by subclasses."""
        pass

    def _try_vadiate_result_data(
        self, 
        validate: bool,
        result: ExtractionResult
    ) -> ValidationResult:
        """Try to validate the extracted data.
        
        Args:
            validate (bool): Whether to validate the data
            result (ExtractionResult): The extraction result containing the data to validate
            
        Returns:
            ValidationResult: The validation result
        """
        # If extraction failed or validation is not needed, return directly
        if not validate or not self.validators:
            return result
            
        # Validate the extracted data
        for validator in self.validators:
            validation_result = validator.validate(result.data)
            if not validation_result:
                result.add_error(
                    f"Validation failed: {validation_result.error_message}. The extracted data that failed validation was: {result.data}. This may be due to invalid LLM output or improper extractor handling.",
                    "validation"
                )
                return result
        return result
    
    def extract_data(
        self, 
        text: str,
        validate: bool = True
    ) -> ExtractionResult:
        """Extract and validate data from text.
        
        Args:
            text (str): The text to extract data from
            validate (bool, optional): Whether to validate the extracted data. Defaults to True.
            
        Returns:
            ExtractionResult: The extraction result containing the extracted and validated data or error information
        """
        if not self.extractors:
            return ExtractionResult(
                is_success=False,
                error_message="No extractors configured. Please configure extractors by overriding _setup_extractors() method.",
                error_type="extraction"
            )
            
        extraction_errors = []
        
        # Try each extractor
        for i, extractor in enumerate(self.extractors):
            result = extractor.extract(text)
            if result.is_success:
                # Validate data
                return self._try_vadiate_result_data(validate, result)
            
            # Record extraction errors
            extractor_name = extractor.__class__.__name__
            extraction_errors.append(f"Extractor {i+1} ({extractor_name}) failed: {result.error_messages[0] if result.error_messages else 'Unknown error'}")
        
        # All extractors failed
        return ExtractionResult(
            is_success=False,
            error_message=f"All extractors failed. This may be because the LLM output does not follow the specified format. Original text:\n{text}\n\nError information:\n" + "\n".join(extraction_errors),
            error_type="extraction"
        )

