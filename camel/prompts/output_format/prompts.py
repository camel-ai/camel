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

from typing import Any, Dict

from camel.prompts.base import TextPrompt
from camel.prompts.output_format.base import OutputFormat, OutputFormatHandler
from camel.prompts.output_format.output_format_factory import OutputFormatHandlerFactory
from camel.prompts.output_format.enhance_output_prompt_templates import (
    OUTPUT_FORMAT_INSTRUCTION_TEMPLATE,
    OUTPUT_FORMAT_SPEC_INSTRUCTION_TEMPLATE,
)
from camel.types.enums import OutputFormatType


class OutputFormatPrompt(TextPrompt):
    r"""A prompt class representing specific data formats. It extends the :obj:`TextPrompt` class
    by adding functionality for output format data.

    Attributes:
        output_format: An instance of :obj:`OutputFormat` containing the output format type and specifications.
    """

    def __new__(cls, *args: Any, **kwargs: Any) -> 'OutputFormatPrompt':
        r"""Creates a new instance of the :obj:`OutputFormatPrompt` class.

        Args:
            *args (Any): Positional arguments.
            **kwargs (Any): Keyword arguments.
            output_format (OutputFormat, optional): Instance containing output format information.

        Returns:
            OutputFormatPrompt: The created :obj:`OutputFormatPrompt` instance.
        """
        # Get output_format parameter or create a new one
        output_format = kwargs.pop('output_format', None)
        
        if output_format is None:
            output_format = OutputFormat()
        
        instance = super().__new__(cls, *args, **kwargs)
        instance._output_format = output_format
        return instance

    @property
    def output_format(self) -> OutputFormat:
        r"""Returns the output format object.

        Returns:
            OutputFormat: The output format object.
        """
        return self._output_format

    def format(self, *args: Any, **kwargs: Any) -> 'OutputFormatPrompt':
        r"""Formats the prompt text and optionally adds format requirements.
        
        Extends the TextPrompt's format method while allowing specification or 
        updating of return data format.

        Args:
            *args (Any): Positional arguments for formatting.
            **kwargs (Any): Keyword arguments for formatting.
            output_format (OutputFormat, optional): Set or override the output format.

        Returns:
            OutputFormatPrompt: The formatted prompt, potentially including format requirements.
        """
        # Extract output_format from kwargs
        output_format = kwargs.pop('output_format', None)
        
        if output_format is None:
            # Clone the current output format
            output_format = OutputFormat(
                output_format_type=self._output_format.output_format_type, 
                output_format_spec=self._output_format.output_format_spec
            )
        
        # First use parent class's format method to format text
        default_kwargs = {key: '{' + f'{key}' + '}' for key in self.key_words}
        default_kwargs.update(kwargs)
        formatted_text = super().format(*args, **default_kwargs)
        
        # Create new OutputFormatPrompt instance
        result = OutputFormatPrompt(formatted_text, output_format=output_format)
        
        # If output_format_type is specified, enhance the prompt
        if output_format.output_format_type:
            base_text = formatted_text
            output_format_instruction = OUTPUT_FORMAT_INSTRUCTION_TEMPLATE.format(
                output_format_type=output_format.output_format_type
            )
            
            if output_format.output_format_spec:
                output_format_instruction += OUTPUT_FORMAT_SPEC_INSTRUCTION_TEMPLATE.format(
                    output_format_spec=output_format.output_format_spec
                )
            
            enhanced_text = f"{base_text}{output_format_instruction}"
            result = OutputFormatPrompt(enhanced_text, output_format=output_format)
        
        return result
        
    def get_output_format_handler(self, **kwargs: Any) -> 'OutputFormatHandler':
        """Creates and returns an appropriate OutputFormatHandler based on this prompt's format type.
        
        This method provides a convenient way to obtain a handler that's specialized for processing
        the response data according to the prompt's output format type. The handler can then be used
        to extract structured data from LLM responses.
        
        The primary benefits of using this method include:
        1. Automatic handler selection based on the prompt's format type
        2. Direct connection between prompt configuration and response processing
        3. Simplified workflow for extracting structured data from responses
        
        Args:
            **kwargs: Additional parameters to pass to the handler constructor.
                These can include specific requirements for the handler, such as:
                - required_keys: For JSON handlers, a set of keys that must be present
                - validation_schema: For handlers that support validation
                - custom parsing options specific to the handler type
                
        Returns:
            OutputFormatHandler: An appropriate handler instance for this prompt's format type.
            
        Examples:
            Simple usage with a JSON output format prompt:
            
            ```python
            # Create a JSON format prompt
            user_info_prompt = JsonOutputFormatPrompt(
                "Please provide user information."
            )
            
            # Get response from LLM
            response = ...
            
            # Get handler and parse the response
            handler = user_info_prompt.get_output_format_handler(required_keys={"user_id", "name"})
            parsed_data = handler.extract_data(response)
            
            # Access structured data
            user_id = parsed_data["user_id"]
            ```
            
        Extension:
            To support custom format types and handlers:
            
            1. Create a custom OutputFormatHandler subclass:
            ```python
            class XMLOutputFormatHandler(OutputFormatHandler):
                def parse(self, text: str) -> Dict[str, Any]:
                    # XML parsing logic here
                    import xml.etree.ElementTree as ET
                    root = ET.fromstring(text)
                    # Convert XML to dictionary
                    result = self._xml_to_dict(root)
                    return result
                
                def _xml_to_dict(self, element):
                    # Implementation details...
                    pass
            ```
            
            2. Register your custom handler with the factory:
            ```python
            from camel.prompts.output_format.output_format_factory import OutputFormatHandlerFactory
            from camel.types.enums import OutputFormatType
            
            # Register new format type and handler
            OutputFormatType.XML = "XML"  # Add to enum if not already there
            OutputFormatHandlerFactory.register_handler("XML", XMLOutputFormatHandler)
            
            # Now you can use it with appropriate prompts
            xml_prompt = OutputFormatPrompt(
                "Generate an XML contact card.",
                output_format=OutputFormat(output_format_type="XML")
            )
            # Or you already have a prompt class for the output format which is derived from OutputFormatPrompt and which presets the output format type.
            xml_prompt = XmlOutputFormatPrompt(
                "Generate an XML contact card."
            )
            
            handler = xml_prompt.get_output_format_handler()

            # Get response from LLM
            response = ...

            # Get handler and parse the response
            parsed_data = handler.extract_data(response)
            ```
        """
        
        # Use the factory to create a handler based on this prompt's output format
        return OutputFormatHandlerFactory.create(
            output_format=self.output_format,
            **kwargs
        )
    
    def handle_output_format(self, text: str, **kwargs: Any) -> Dict[str, Any]:
        r"""Loads the text into a dictionary according to the output format.
        
        Args:
            text (str): The text to load.
            
        """
        handler = self.get_output_format_handler(**kwargs)
        extracted_result = handler.extract_data(text)
        if not extracted_result.is_success:
            raise ValueError(f"Failed to extract data from the response. Error: {extracted_result.error_messages}")
        return extracted_result.data


# JsonOutputFormatPrompt Usage Guide
"""
The JsonOutputFormatPrompt class helps enforce structured JSON output from LLMs by providing:

1. Output Format Control:
   - Forces LLM to return only raw JSON data
   - Prevents unstructured text or explanations in responses
   - Ensures consistent data structure across multiple calls

2. Schema Specification Priority:
   a) Format-time schema (highest priority):
      - Specified via format(output_format_spec=...) 
      - Allows dynamic schema changes for different use cases
   b) Construction-time schema (medium priority):
      - Specified when creating the prompt
      - Sets default schema for the prompt instance
   c) No schema (base case):
      - LLM determines appropriate JSON structure
      - Less controlled but more flexible output

Example 1 - With Default Schema:
base_user_info_prompt = JsonOutputFormatPrompt(
    '''Please provide information about the user.''',
    output_format_spec='''
    {
        "user_id": "unique identifier for the user, e.g. 'u123'",
        "name": "full name of the user, e.g. 'John Smith'"
    }
    '''
)

Example 2 - Without Schema:
base_user_info_prompt = JsonOutputFormatPrompt(
    '''Please provide information about the user.'''
)

Example 3 - Dynamic Schema Override:
# For detailed user profile:
detailed_info = base_user_info_prompt.format(
    output_format_spec='''
    {
        "user_id": "unique identifier for the user, e.g. 'u123'",
        "name": "full name of the user, e.g. 'John Smith'", 
        "email": "email address of the user, e.g. 'john@example.com'",
        "age": "age of the user as a number, e.g. 25",
        "preferences": ["list of user preferences, e.g. ['reading', 'music']"]
    }
    '''
)

# For minimal identification:
minimal_info = base_user_info_prompt.format(
    output_format_spec='''
    {
        "user_id": "unique identifier for the user, e.g. 'u123'"
    }
    '''
)

This approach enables:
- Consistent base prompts with flexible schema adaptation
- Runtime schema modifications without prompt recreation
- Clear schema hierarchy for predictable behavior
- Strong output format enforcement for reliable parsing
"""
class JsonOutputFormatPrompt(OutputFormatPrompt):
    r"""A prompt class for JSON output format. It extends the :obj:`OutputFormatPrompt` class
    by pre-setting the output format type to JSON.

    Attributes:
        output_format: An instance of :obj:`OutputFormat` with output format type fixed to "JSON".
    """

    def __new__(cls, *args: Any, **kwargs: Any) -> 'JsonOutputFormatPrompt':
        r"""Creates a new instance of the :obj:`JsonOutputFormatPrompt` class.

        Args:
            *args (Any): Positional arguments.
            **kwargs (Any): Keyword arguments.
            output_format_spec (str, optional): Optional JSON schema or format specification.

        Returns:
            JsonOutputFormatPrompt: The created :obj:`JsonOutputFormatPrompt` instance.
        """
        # Extract output_format_spec if provided directly
        output_format_spec = kwargs.pop('output_format_spec', None)
        
        # Check if output_format was provided and extract spec if available
        if 'output_format' in kwargs:
            output_format = kwargs.pop('output_format')
            # If output_format_spec wasn't provided directly but is in output_format, use that
            if output_format_spec is None and hasattr(output_format, 'output_format_spec'):
                output_format_spec = output_format.output_format_spec
        
        # Create a new OutputFormat with fixed JSON type and provided spec
        output_format = OutputFormat(
            output_format_type=OutputFormatType.JSON,
            output_format_spec=output_format_spec
        )
        
        # Set the output_format in kwargs
        kwargs['output_format'] = output_format
        
        return super().__new__(cls, *args, **kwargs)
        
    def format(self, *args: Any, **kwargs: Any) -> 'JsonOutputFormatPrompt':
        """Formats the prompt text and allows overriding the JSON schema specification.
        
        This method extends the parent's format method by adding the ability to temporarily
        override the output_format_spec while maintaining the JSON output type. This is 
        particularly useful in scenarios where:
        
        1. You've created a general JSON prompt template but need different JSON structures
           for different business use cases without creating multiple prompt templates.
        2. You need to dynamically generate JSON schemas based on runtime conditions.
        3. You want to reuse the same prompt but with varying degrees of specificity in the
           output structure requirements.
        
        The priority order for output_format_spec is:
        1. The value passed directly to this format method (highest priority)
        2. The value stored in the current prompt instance (lower priority)
        
        Args:
            *args (Any): Positional arguments for formatting.
            **kwargs (Any): Keyword arguments for formatting.
            output_format_spec (str, optional): A temporary JSON schema specification that
                overrides the current instance's specification for this format operation only.
                
        Returns:
            JsonOutputFormatPrompt: A new formatted prompt instance with the appropriate
                JSON schema specification applied.
        """
        # Extract temporary output_format_spec if provided
        temp_output_format_spec = kwargs.pop('output_format_spec', None)
        
        # Determine which output_format_spec to use (temporary one has priority)
        final_output_format_spec = temp_output_format_spec if temp_output_format_spec is not None else self.output_format.output_format_spec
        
        # Create a new OutputFormat with the determined spec but keep JSON type
        output_format = OutputFormat(
            output_format_type=OutputFormatType.JSON,
            output_format_spec=final_output_format_spec
        )
        
        # Add the output_format to kwargs for the parent's format method
        kwargs['output_format'] = output_format
        
        # Call parent's format method
        return super().format(*args, **kwargs) 