# Output Format

## 1. Concepts

The CAMEL Output Format module is an enhancement tool based on the Prompt module, designed to control and process the output format of Large Language Models (LLMs). This module implements control over LLM outputs through three core concepts:

- **Prompt Control**: Using classes like `OutputFormatPrompt` to guide LLMs to generate output in specific formats.
- **Model Response Unified Processing**: Using `OutputFormatHandler` and other tools to extract formatted data from model responses (addressing the instability of large model outputs) and validate the extracted data to meet business requirements.
- **Data Extraction**: Using `Extractor` to extract structured data from LLM responses.
- **Data Validation**: Using `Validator` to verify whether the extracted data meets expected requirements.

This module addresses the challenge of converting unstructured text to structured data, enabling developers to more reliably generate and process data using LLMs.

## 2. Getting Started

### 2.1 Using OutputFormatPrompt

`OutputFormatPrompt` is the base class for controlling LLM output formats. It extends standard prompts by adding format control functionality.

```python
from camel.prompts.output_format import OutputFormatPrompt, OutputFormat
from camel.types.enums import OutputFormatType

# Create a JSON format prompt
json_prompt = OutputFormatPrompt(
    "Please provide basic information about a character.",
    output_format=OutputFormat(
        output_format_type=OutputFormatType.JSON,
        output_format_spec="""
        {
            "name": "The character's name",
            "age": "The character's age, numeric type",
            "occupation": "The character's occupation"
        }
        """
    )
)

# Send to LLM and get response
response = ...

# Process response
result = json_prompt.handle_output_format(response)
print(f"Name: {result['name']}, Age: {result['age']}, Occupation: {result['occupation']}")
```

### 2.2 Custom Inheritance from OutputFormatPrompt

You can create your own data format prompt classes by inheriting from `OutputFormatPrompt`, implementing more specialized functionality:

```python
from camel.prompts.output_format import OutputFormatPrompt, OutputFormat
from camel.types.enums import OutputFormatType

class XMLOutputFormatPrompt(OutputFormatPrompt):
    """XML format prompt class"""
    
    def __new__(cls, *args, **kwargs):
        # Extract possible format specifications
        output_format_spec = kwargs.pop('output_format_spec', None)
        
        # Create output format with fixed XML type
        output_format = OutputFormat(
            output_format_type=OutputFormatType.XML,
            output_format_spec=output_format_spec
        )
        
        # Set output format
        kwargs['output_format'] = output_format
        
        return super().__new__(cls, *args, **kwargs)
```

### 2.3 Example of Using JsonOutputFormatPrompt

`JsonOutputFormatPrompt` is a predefined JSON format prompt class that can be used directly:

```python
from camel.prompts.output_format import JsonOutputFormatPrompt

# Create JSON prompt
user_info_prompt = JsonOutputFormatPrompt(
    "Please provide detailed user information.",
    output_format_spec="""
    {
        "user_id": "Unique user identifier",
        "name": "User's full name",
        "email": "User's email address",
        "age": "User's age, numeric type",
        "interests": ["List of user interests"]
    }
    """
)

# Get LLM response
response = ...

# Parse response as JSON data
try:
    user_data = user_info_prompt.handle_output_format(response)
    print(f"User ID: {user_data['user_id']}")
    print(f"Interests: {', '.join(user_data['interests'])}")
except ValueError as e:
    print(f"Parsing failed: {e}")
```

## 3. Using OutputFormatHandler

The `OutputFormatHandler` class is responsible for actually processing LLM output, converting text into structured data. It manages a series of extractors and validators, attempting to extract data in sequence and then validate it.

### 3.1 Custom OutputFormatHandler

Now let's demonstrate how to customize a formatted output prompt and its corresponding format handler, and how to use them. We hope this example will help you achieve your specific formatting requirements.

#### 3.1.1 Defining Data Extractor

Extractors are responsible for extracting structured data from text:

```python
from camel.prompts.output_format.base import Extractor, ExtractionResult, OutputFormat
from camel.types.enums import OutputExtractionErrorType
import xml.etree.ElementTree as ET
from typing import Dict

class XMLExtractor(Extractor[Dict]):
    """XML data extractor"""
    
    def extract(self, text: str, output_format: OutputFormat) -> ExtractionResult[Dict]:
        try:
            # Find XML content
            if "```xml" in text:
                start = text.find("```xml") + 7
                end = text.find("```", start)
                if end == -1:
                    return ExtractionResult(
                        is_success=False,
                        error_message="XML code block not properly closed",
                        error_type=OutputExtractionErrorType.EXTRACTION
                    )
                text = text[start:end].strip()
            
            # Parse XML
            root = ET.fromstring(text)
            data = self._xml_to_dict(root)
            return ExtractionResult(data=data, is_success=True)
        except Exception as e:
            return ExtractionResult(
                is_success=False,
                error_message=f"XML parsing error: {str(e)}",
                error_type=OutputExtractionErrorType.EXTRACTION
            )
    
    def _xml_to_dict(self, element) -> Dict:
        # XML to dictionary implementation (simplified)
        result = {}
        for child in element:
            if len(child) == 0:
                result[child.tag] = child.text
            else:
                result[child.tag] = self._xml_to_dict(child)
        return result
```

#### 3.1.2 Defining Data Validator

Validators ensure that extracted data meets requirements:

```python
from camel.prompts.output_format.base import Validator, ExtractionResult
from camel.types.enums import OutputExtractionErrorType
from typing import Dict, Set, Optional

class XMLRequiredElementsValidator(Validator):
    """XML required elements validator"""
    
    def __init__(self, required_elements: Optional[Set[str]] = None) -> None:
        self.required_elements = required_elements or set()
    
    def validate(self, data: Dict) -> ExtractionResult:
        if not self.required_elements:
            return ExtractionResult(data=data, is_success=True)
        
        if not isinstance(data, dict):
            return ExtractionResult(
                is_success=False,
                error_message="Data is not a dictionary type",
                error_type=OutputExtractionErrorType.VALIDATION
            )
        
        missing_elements = self.required_elements - set(data.keys())
        if missing_elements:
            return ExtractionResult(
                is_success=False,
                error_message=f"Missing required elements: {', '.join(missing_elements)}",
                error_type=OutputExtractionErrorType.VALIDATION
            )
        
        return ExtractionResult(data=data, is_success=True)
```

#### 3.1.3 Custom OutputFormatHandler and Registering to Factory

Create a custom handler and register it to the factory:

```python
from camel.prompts.output_format.base import OutputFormatHandler, OutputFormat
from camel.prompts.output_format.handler_factory import OutputFormatHandlerFactory
from camel.types.enums import OutputFormatType
from typing import Optional, Set

# Add new type to OutputFormatType enum
class XMLOutputFormatHandler(OutputFormatHandler):
    """XML output format handler"""
    
    def __init__(
        self,
        required_elements: Optional[Set[str]] = None,
        output_format: Optional[OutputFormat] = None,
        **kwargs
    ) -> None:
        self.required_elements = required_elements
        
        if output_format is None:
            output_format = OutputFormat(OutputFormatType.XML)
            
        super().__init__(
            output_format=output_format,
            extractors=[XMLExtractor()],
            validators=[XMLRequiredElementsValidator(required_elements)]
        )

# Register handler to factory
OutputFormatHandlerFactory.register_handler("XML", XMLOutputFormatHandler)
```

#### 3.1.4 Example of Using Custom Handler for Data Extraction and Validation

```python
from camel.prompts.output_format import OutputFormatPrompt, OutputFormat

# Create XML format prompt
xml_prompt = OutputFormatPrompt(
    "Please provide contact information for a person.",
    output_format=OutputFormat(
        output_format_type="XML",
        output_format_spec="""
        <person>
          <name>Person's name</name>
          <email>Email address</email>
          <phone>Phone number</phone>
        </person>
        """
    )
)

# Get LLM response
response = ...

# Use handler to extract and validate data - get extraction result (with error info if extraction fails)
handler = xml_prompt.get_output_format_handler(required_elements={"name", "email"})
result = handler.extract_data(response)

if result.is_success:
    print(f"Name: {result.data['name']}")
    print(f"Email: {result.data['email']}")
else:
    print(f"Processing failed: {result.error_messages}")
# Or directly get the final data (get the corresponding data type handler from the factory, then extract, validate, and return data)
data = xml_prompt.handle_output_format()
print(data)
```

## 4. Simple Summary

The CAMEL Output Format module provides a set of tools for controlling LLM output formats and converting outputs to structured data. It solves the following key problems:

1. **Output Format Control**: Guides LLMs to generate output in specific formats through formatted prompts, reducing the possibility of non-standard outputs.

2. **Data Extraction**: Provides flexible extractor mechanisms to extract structured data from various formats (such as JSON, code blocks, etc.).

3. **Data Validation**: Validates whether extracted data meets expected requirements, improving data quality and reliability.

4. **Extensibility**: Supports custom format types, extractors, and validators to meet various specific needs.

5. **Error Handling**: Provides detailed error information and types to help debug and improve prompts.

This module is particularly suitable for application scenarios requiring structured data from LLMs, such as information extraction, data analysis, automated report generation, business code invocation, and API request data assembly. Through a unified interface and flexible extension mechanism, it simplifies the process of obtaining and processing structured data from LLMs, improving development efficiency and data quality.
