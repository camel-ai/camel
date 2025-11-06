<a id="camel.societies.workforce.structured_output_handler"></a>

<a id="camel.societies.workforce.structured_output_handler.StructuredOutputHandler"></a>

## StructuredOutputHandler

```python
class StructuredOutputHandler:
```

Handler for generating prompts and extracting structured output from
agent responses.

This handler provides functionality to:
- Generate prompts that guide agents to produce structured output
- Extract structured data from agent responses using regex patterns
- Provide fallback mechanisms when extraction fails
- Support the existing structured output schemas used in workforce.py

<a id="camel.societies.workforce.structured_output_handler.StructuredOutputHandler.generate_structured_prompt"></a>

### generate_structured_prompt

```python
def generate_structured_prompt(
    base_prompt: str,
    schema: Type[BaseModel],
    examples: Optional[List[Dict[str, Any]]] = None,
    additional_instructions: Optional[str] = None
):
```

Generate a prompt that guides agents to produce structured output.

**Parameters:**

- **base_prompt** (str): The base prompt content.
- **schema** (Type[BaseModel]): The Pydantic model schema for the expected output.
- **examples** (Optional[List[Dict[str, Any]]]): Optional examples of valid output.
- **additional_instructions** (Optional[str]): Additional instructions for output formatting.

**Returns:**

  str: The enhanced prompt with structured output instructions.

<a id="camel.societies.workforce.structured_output_handler.StructuredOutputHandler.extract_json"></a>

### extract_json

```python
def extract_json(text: str, schema: Optional[Type[BaseModel]] = None):
```

Extract JSON data from text using multiple patterns.

**Parameters:**

- **text** (str): The text containing JSON data.
- **schema** (Optional[Type[BaseModel]]): Optional schema for targeted extraction.

**Returns:**

  Optional[Dict[str, Any]]: Extracted JSON data or None if extraction
fails.

<a id="camel.societies.workforce.structured_output_handler.StructuredOutputHandler._extract_with_schema_patterns"></a>

### _extract_with_schema_patterns

```python
def _extract_with_schema_patterns(text: str, schema: Type[BaseModel]):
```

Extract data using schema-specific patterns.

**Parameters:**

- **text** (str): The text to extract from.
- **schema** (Type[BaseModel]): The schema to use for extraction.

**Returns:**

  Optional[Dict[str, Any]]: Extracted data or None.

<a id="camel.societies.workforce.structured_output_handler.StructuredOutputHandler.parse_structured_response"></a>

### parse_structured_response

```python
def parse_structured_response(
    response_text: str,
    schema: Type[BaseModel],
    fallback_values: Optional[Dict[str, Any]] = None
):
```

Parse agent response into structured data with fallback support.

**Parameters:**

- **response_text** (str): The agent's response text.
- **schema** (Type[BaseModel]): The expected schema.
- **fallback_values** (Optional[Dict[str, Any]]): Fallback values to use if parsing fails.

**Returns:**

  Union[BaseModel, Dict[str, Any]]: Parsed data as schema instance
or fallback dictionary.

<a id="camel.societies.workforce.structured_output_handler.StructuredOutputHandler._fix_common_issues"></a>

### _fix_common_issues

```python
def _fix_common_issues(data: Dict[str, Any], schema: Type[BaseModel]):
```

Attempt to fix common validation issues in extracted data.

**Parameters:**

- **data** (Dict[str, Any]): The extracted data.
- **schema** (Type[BaseModel]): The target schema.

**Returns:**

  Optional[Dict[str, Any]]: Fixed data or None if unfixable.

<a id="camel.societies.workforce.structured_output_handler.StructuredOutputHandler._create_default_instance"></a>

### _create_default_instance

```python
def _create_default_instance(schema: Type[BaseModel]):
```

Create a default instance of the schema with minimal required
fields.

**Parameters:**

- **schema** (Type[BaseModel]): The schema to instantiate.

**Returns:**

  BaseModel: Default instance of the schema.

<a id="camel.societies.workforce.structured_output_handler.StructuredOutputHandler.validate_response"></a>

### validate_response

```python
def validate_response(
    response: Union[BaseModel, Dict[str, Any]],
    schema: Type[BaseModel]
):
```

Validate that a response conforms to the expected schema.

**Parameters:**

- **response**: The response to validate.
- **schema** (Type[BaseModel]): The expected schema.

**Returns:**

  bool: True if valid, False otherwise.

<a id="camel.societies.workforce.structured_output_handler.StructuredOutputHandler.create_fallback_response"></a>

### create_fallback_response

```python
def create_fallback_response(
    schema: Type[BaseModel],
    error_message: str,
    context: Optional[Dict[str, Any]] = None
):
```

Create a fallback response for a given schema with error context.

**Parameters:**

- **schema** (Type[BaseModel]): The schema to create a response for.
- **error_message** (str): The error message to include.
- **context** (Optional[Dict[str, Any]]): Additional context for the fallback.

**Returns:**

  BaseModel: A valid instance of the schema with fallback values.
