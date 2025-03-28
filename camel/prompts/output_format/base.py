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

from camel.types.enums import OutputFormatType, OutputExtractionErrorType


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


# Data type
T = TypeVar('T')


# Extraction result class
class ExtractionResult(Generic[T]):
    """Extraction result class representing the result of data extraction and validation.
    
    Attributes:
        data (Optional[T]): The extracted data, or None if extraction or validation failed
        is_success (bool): Whether extraction and validation succeeded
        error_message (Optional[str]): Error message
        error_messages (List[str]): List of error messages containing extraction and validation errors
        error_type (Optional[OutputExtractionErrorType]): Error type, can be ErrorType.EXTRACTION or ErrorType.VALIDATION
    """
    
    def __init__(
        self, 
        data: Optional[T] = None, 
        is_success: bool = False, 
        error_message: Optional[str] = None,
        error_messages: Optional[List[str]] = None,
        error_type: Optional[OutputExtractionErrorType] = None
    ) -> None:
        """Initialize an ExtractionResult instance.
        
        Args:
            data (Optional[T], optional): The extracted data. Defaults to None.
            is_success (bool, optional): Whether extraction and validation succeeded. Defaults to False.
            error_message (Optional[str], optional): Error message. Defaults to None.
            error_messages (Optional[List[str]], optional): List of error messages. Defaults to None.
            error_type (Optional[ErrorType], optional): Error type. Defaults to None.
        """
        self.data = data
        self.is_success = is_success
        self.error_messages: List[str] = error_messages or []
        if error_message:
            self.error_messages.append(error_message)
        self.error_type = error_type
    
    def add_error(self, message: str, error_type: Union[str, OutputExtractionErrorType]) -> None:
        """Add an error message.
        
        Args:
            message (str): Error message
            error_type (Union[str, OutputExtractionErrorType]): Error type
        """
        self.is_success = False
        self.error_messages.append(message)
        if isinstance(error_type, str):
            self.error_type = OutputExtractionErrorType(error_type)
        else:
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
    def extract(self, text: str, output_format: OutputFormat) -> ExtractionResult[T]:
        """Extract data from text.

        Args:
            text (str): The text to extract data from
            output_format (Optional[OutputFormat], optional): The output format. Defaults to None.

        Returns:
            ExtractionResult[T]: Extraction result containing the extracted data or error information
        """
        pass


# Validator base class
class Validator(ABC):
    """Abstract base class for data validators that validate whether data conforms to specific rules."""

    @abstractmethod
    def validate(self, data: Any) -> ExtractionResult:
        """Validate data.

        Args:
            data (Any): The data to validate

        Returns:
            ExtractionResult: Validation result containing whether the data is valid and error information
        """
        pass


class OutputFormatHandler:
    """base class for output format handlers that handle extraction, validation, and formatting for different format types.

    Attributes:
        output_format (OutputFormat): The output format object
        extractors (List[Extractor]): Optional list of data extractors, which are executed in sequence to attempt extracting data from LLM output. If one extractor succeeds, the remaining extractors will be skipped.
        validators (List[Validator]): Optional list of data validators, which are used to validate the extracted data.
    """

    def __init__(
        self,
        output_format: OutputFormat,
        extractors: Optional[List[Extractor]] = None,
        validators: Optional[List[Validator]] = None,
        at_least_one_extractor: bool = True
    ) -> None:
        """Initialize an OutputFormatHandler instance.

        Args:
            output_format (OutputFormat): The output format object
            extractors (Optional[List[Extractor]], optional): Optional list of data extractors, which are executed in sequence to attempt extracting data from LLM output. If one extractor succeeds, the remaining extractors will be skipped.
            validators (Optional[List[Validator]], optional): Optional list of data validators, which are used to validate the extracted data.
            at_least_one_extractor (bool, optional): Whether at least one extractor is required. If True, the handler will return an error if no extractors are provided.
        """
        self.output_format = output_format
        self.extractors: List[Extractor] = extractors or []
        self.validators: List[Validator] = validators or []
        self.at_least_one_extractor = at_least_one_extractor

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
    
    @property
    def extractors(self) -> List[Extractor]:
        """Get the list of extractors."""
        return self._extractors
    
    @property
    def validators(self) -> List[Validator]:
        """Get the list of validators."""
        return self._validators
    
    @extractors.setter
    def extractors(self, extractors: List[Extractor]) -> None:
        """Set the list of extractors."""
        self._extractors = extractors
    
    @validators.setter
    def validators(self, validators: List[Validator]) -> None:
        """Set the list of validators."""
        self._validators = validators
    
    def add_extractor(self, extractor: Extractor) -> None:
        """Add an extractor to the list of extractors."""
        if not self.extractors:
            self.extractors = []
        self.extractors.append(extractor)


    def add_validator(self, validator: Validator) -> None:
        """Add a validator to the list of validators."""
        if not self.validators:
            self.validators = []
        self.validators.append(validator)

    def _try_validate_result_data(
        self, 
        validate: bool,
        result: ExtractionResult
    ) -> ExtractionResult:
        """Try to validate the extracted data.
        
        Args:
            validate (bool): Whether to validate the data
            result (ExtractionResult): The extraction result containing the data to validate
            
        Returns:
            ExtractionResult: The validated extraction result
        """
        # If extraction failed or validation is not needed, return directly
        if not validate or not self.validators:
            return result
            
        # Validate the extracted data
        for validator in self.validators:
            validation_result = validator.validate(result.data)
            if not validation_result.is_success:
                result.add_error(
                    f"Validation failed: {validation_result.error_messages[0] if validation_result.error_messages else 'Unknown error'}. The extracted data that failed validation was: {result.data}. This may be due to invalid LLM output or improper extractor handling.",
                    OutputExtractionErrorType.VALIDATION
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
            if self.at_least_one_extractor:
                return ExtractionResult(
                    is_success=False,
                    error_message="No extractors configured. Please configure extractors using the constructor or add_extractor() method.",
                    error_type=OutputExtractionErrorType.EXTRACTION
                )
            else:
                return ExtractionResult(
                    is_success=True,
                    data=text
                )

            
        extraction_errors = []
        
        # Try each extractor
        for i, extractor in enumerate(self.extractors):
            result = extractor.extract(text, self.output_format)
            if result.is_success:
                # Validate data
                return self._try_validate_result_data(validate, result)
            
            # Record extraction errors
            extractor_name = extractor.__class__.__name__
            extraction_errors.append(f"Extractor {i+1} ({extractor_name}) failed: {result.error_messages[0] if result.error_messages else 'Unknown error'}")
        
        # All extractors failed
        return ExtractionResult(
            is_success=False,
            error_message=f"All extractors failed. This may be because the LLM output does not follow the specified format. Original text:\n{text}\n\nError information:\n" + "\n".join(extraction_errors),
            error_type=OutputExtractionErrorType.EXTRACTION
        )

