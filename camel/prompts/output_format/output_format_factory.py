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

from typing import Dict, Optional, Type, Union

from camel.prompts.output_format.base import OutputFormat, OutputFormatHandler
from camel.types.enums import OutputFormatType
from camel.prompts.output_format.output_format_handlers import (
    JsonOutputFormatHandler, DefaultOutputFormatHandler
)


class OutputFormatHandlerFactory:
    """Output format handler factory.
    
    Used for creating different types of output format handler instances.
    
    Attributes:
        _format_handlers (Dict[str, Type[OutputFormatHandler]]): Mapping from format types to handler classes.
            The format type strings are case-insensitive and will be converted to uppercase.
    
    Raises:
        ValueError: When provided format type is unknown.
    """
    
    # Initialize with default handlers (case-insensitive)
    _format_handlers: Dict[str, Type[OutputFormatHandler]] = {
        str(OutputFormatType.JSON).upper(): JsonOutputFormatHandler,
        str(OutputFormatType.TEXT).upper(): DefaultOutputFormatHandler
    }
    
    @classmethod
    def register_handler(
        cls,
        format_type: Union[str, OutputFormatType],
        handler_class: Type[OutputFormatHandler]
    ) -> None:
        """Register a new format handler.

        Args:
            format_type (Union[str, OutputFormatType]): Format type to register.
                Case-insensitive, will be converted to uppercase.
            handler_class (Type[OutputFormatHandler]): Corresponding handler class.

        Example:
            >>> class XMLOutputFormatHandler(OutputFormatHandler):
            ...     pass
            >>> OutputFormatHandlerFactory.register_handler(
            ...     OutputFormatType.XML,
            ...     XMLOutputFormatHandler
            ... )
        """
        # Convert format type string to uppercase for case-insensitive lookup
        format_type_str = (
            str(format_type) if isinstance(format_type, OutputFormatType)
            else format_type
        ).upper()

        cls._format_handlers[format_type_str] = handler_class
  
    @staticmethod
    def create(
        output_format: Optional[OutputFormat] = None,
        **kwargs
    ) -> OutputFormatHandler:
        """Create an OutputFormatHandler instance of the specified type.
        
        Args:
            output_format (Optional[OutputFormat]): Output format.
                If None, returns the default handler.
                The format type is case-insensitive and will be converted to uppercase.
            **kwargs: Additional parameters passed to the handler constructor.
            
        Returns:
            OutputFormatHandler: Initialized handler instance.
            
        Raises:
            ValueError: If format_type is neither None nor a supported format type.
            
        Example:
            >>> from camel.prompts.output_format.base import OutputFormat
            >>> from camel.types.enums import OutputFormatType
            >>> # Create a JSON handler with required keys
            >>> handler = OutputFormatHandlerFactory.create(
            ...     OutputFormat(OutputFormatType.JSON),
            ...     required_keys={"name", "age"}
            ... )
        """
        # If no output format specified, use default handler
        if output_format is None:
            return DefaultOutputFormatHandler(**kwargs)

        # Get format type string and convert to uppercase
        format_type_str = output_format.output_format_type.upper()

        # Get corresponding handler class, or use default if not found
        handler_class = OutputFormatHandlerFactory._format_handlers.get(
            format_type_str,
            DefaultOutputFormatHandler
        )
        
        return handler_class(
            output_format=output_format,
            **kwargs
        )
