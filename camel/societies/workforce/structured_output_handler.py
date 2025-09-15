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
import re
from typing import Any, ClassVar, Dict, List, Optional, Type, Union

from pydantic import BaseModel, ValidationError

from camel.logger import get_logger
from camel.societies.workforce.utils import (
    RecoveryDecision,
    RecoveryStrategy,
    TaskAssignResult,
    WorkerConf,
)

logger = get_logger(__name__)


class StructuredOutputHandler:
    r"""Handler for generating prompts and extracting structured output from
    agent responses.

    This handler provides functionality to:
    - Generate prompts that guide agents to produce structured output
    - Extract structured data from agent responses using regex patterns
    - Provide fallback mechanisms when extraction fails
    - Support the existing structured output schemas used in workforce.py
    """

    # Common JSON extraction patterns
    JSON_PATTERNS: ClassVar[List[str]] = [
        # Pattern 1: Standard JSON block
        r'```json\s*\n(.*?)\n```',
        # Pattern 2: JSON without code block
        r'(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})',
        # Pattern 3: JSON with potential nested objects
        r'(\{(?:[^{}]|(?:\{[^{}]*\}))*\})',
    ]

    # Schema-specific patterns for more targeted extraction
    SCHEMA_PATTERNS: ClassVar[Dict[str, List[str]]] = {
        'TaskAssignResult': [
            r'"assignments"\s*:\s*\[(.*?)\]',
            r'assignments.*?:\s*\[(.*?)\]',
        ],
        'WorkerConf': [
            (
                r'"role"\s*:\s*"([^"]+)".*?"sys_msg"\s*:\s*"([^"]+)".*?'
                r'"description"\s*:\s*"([^"]+)"'
            ),
            (
                r'role.*?:\s*"([^"]+)".*?sys_msg.*?:\s*"([^"]+)".*?'
                r'description.*?:\s*"([^"]+)"'
            ),
        ],
        'RecoveryDecision': [
            r'"strategy"\s*:\s*"([^"]+)".*?"reasoning"\s*:\s*"([^"]+)"',
            r'strategy.*?:\s*"([^"]+)".*?reasoning.*?:\s*"([^"]+)"',
        ],
    }

    @staticmethod
    def generate_structured_prompt(
        base_prompt: str,
        schema: Type[BaseModel],
        examples: Optional[List[Dict[str, Any]]] = None,
        additional_instructions: Optional[str] = None,
    ) -> str:
        r"""Generate a prompt that guides agents to produce structured output.

        Args:
            base_prompt (str): The base prompt content.
            schema (Type[BaseModel]): The Pydantic model schema for the
                expected output.
            examples (Optional[List[Dict[str, Any]]]): Optional examples of
                valid output.
            additional_instructions (Optional[str]): Additional instructions
                for output formatting.

        Returns:
            str: The enhanced prompt with structured output instructions.
        """
        # Get schema information
        schema_name = schema.__name__
        schema_json = schema.model_json_schema()
        required_fields = schema_json.get('required', [])
        properties = schema_json.get('properties', {})

        # Build field descriptions
        field_descriptions = []
        for field_name, field_info in properties.items():
            description = field_info.get('description', 'No description')
            field_type = field_info.get('type', 'unknown')
            required = field_name in required_fields
            field_descriptions.append(
                f"- {field_name} ({field_type}{'*' if required else ''}): "
                f"{description}"
            )

        # Build structured output section
        structured_section = f"""
**STRUCTURED OUTPUT REQUIREMENTS:**

You must return a valid JSON object that conforms to the {schema_name} schema.

Required fields:
{chr(10).join(field_descriptions)}

Fields marked with * are required and must be present in your response.

**FORMAT YOUR RESPONSE AS:**
```json
{{
    // Your JSON response here following the schema
}}
```
"""

        # Add examples if provided
        if examples:
            examples_section = "\n**VALID EXAMPLES:**\n"
            for i, example in enumerate(examples, 1):
                examples_section += f"\nExample {i}:\n```json\n"
                examples_section += json.dumps(example, indent=2)
                examples_section += "\n```\n"
            structured_section += examples_section

        # Add additional instructions if provided
        if additional_instructions:
            structured_section += "\n**ADDITIONAL INSTRUCTIONS:**\n"
            structured_section += additional_instructions + "\n"

        # Add critical reminder
        structured_section += """
**CRITICAL**: Your response must contain ONLY the JSON object within the code 
block.
Do not include any explanatory text, comments, or content outside the JSON 
structure.
Ensure the JSON is valid and properly formatted.
"""

        # Combine with base prompt
        return base_prompt + "\n\n" + structured_section

    @staticmethod
    def extract_json(
        text: str,
        schema: Optional[Type[BaseModel]] = None,
    ) -> Optional[Dict[str, Any]]:
        r"""Extract JSON data from text using multiple patterns.

        Args:
            text (str): The text containing JSON data.
            schema (Optional[Type[BaseModel]]): Optional schema for targeted
                extraction.

        Returns:
            Optional[Dict[str, Any]]: Extracted JSON data or None if extraction
                fails.
        """
        if not text:
            return None

        # Try standard JSON patterns first
        for pattern in StructuredOutputHandler.JSON_PATTERNS:
            matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
            for match in matches:
                try:
                    # Clean up the match
                    json_str = match.strip()
                    # Remove any trailing commas
                    json_str = re.sub(r',\s*}', '}', json_str)
                    json_str = re.sub(r',\s*]', ']', json_str)

                    data = json.loads(json_str)
                    if isinstance(data, dict):
                        return data
                except json.JSONDecodeError:
                    continue

        # Try direct JSON parsing of the entire text
        try:
            data = json.loads(text.strip())
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

        # Try schema-specific patterns if schema is provided
        if (
            schema
            and schema.__name__ in StructuredOutputHandler.SCHEMA_PATTERNS
        ):
            return StructuredOutputHandler._extract_with_schema_patterns(
                text, schema
            )

        return None

    @staticmethod
    def _extract_with_schema_patterns(
        text: str,
        schema: Type[BaseModel],
    ) -> Optional[Dict[str, Any]]:
        r"""Extract data using schema-specific patterns.

        Args:
            text (str): The text to extract from.
            schema (Type[BaseModel]): The schema to use for extraction.

        Returns:
            Optional[Dict[str, Any]]: Extracted data or None.
        """
        schema_name = schema.__name__
        patterns = StructuredOutputHandler.SCHEMA_PATTERNS.get(schema_name, [])

        if schema_name == 'WorkerConf':
            for pattern in patterns:
                match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
                if match:
                    try:
                        return {
                            'role': match.group(1),
                            'sys_msg': match.group(2),
                            'description': match.group(3),
                        }
                    except (IndexError, AttributeError):
                        continue

        elif schema_name == 'RecoveryDecision':
            for pattern in patterns:
                match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
                if match:
                    try:
                        strategy = match.group(1)
                        reasoning = match.group(2)
                        # Look for modified_task_content
                        content_match = re.search(
                            r'"modified_task_content"\s*:\s*"([^"]*)"',
                            text,
                            re.IGNORECASE,
                        )
                        return {
                            'strategy': strategy,
                            'reasoning': reasoning,
                            'modified_task_content': (
                                content_match.group(1)
                                if content_match
                                else None
                            ),
                        }
                    except (IndexError, AttributeError):
                        continue

        return None

    @staticmethod
    def parse_structured_response(
        response_text: str,
        schema: Type[BaseModel],
        fallback_values: Optional[Dict[str, Any]] = None,
    ) -> Union[BaseModel, Dict[str, Any]]:
        r"""Parse agent response into structured data with fallback support.

        Args:
            response_text (str): The agent's response text.
            schema (Type[BaseModel]): The expected schema.
            fallback_values (Optional[Dict[str, Any]]): Fallback values to use
                if parsing fails.

        Returns:
            Union[BaseModel, Dict[str, Any]]: Parsed data as schema instance
                or fallback dictionary.
        """
        # Try to extract JSON
        extracted_data = StructuredOutputHandler.extract_json(
            response_text, schema
        )

        if extracted_data:
            try:
                # Validate against schema
                return schema(**extracted_data)
            except ValidationError as e:
                logger.warning(
                    f"Validation error for {schema.__name__}: {e}. "
                    f"Attempting to fix common issues."
                )

                # Try to fix common validation issues
                fixed_data = StructuredOutputHandler._fix_common_issues(
                    extracted_data, schema
                )
                if fixed_data:
                    try:
                        return schema(**fixed_data)
                    except ValidationError:
                        pass

        # Use fallback values if provided
        if fallback_values:
            logger.warning(
                f"Failed to parse {schema.__name__} from response. "
                f"Using fallback values."
            )
            try:
                return schema(**fallback_values)
            except ValidationError:
                return fallback_values

        # Return default instance if possible
        try:
            logger.warning(f"Creating default {schema.__name__} instance.")
            return StructuredOutputHandler._create_default_instance(schema)
        except Exception:
            logger.error(
                f"Failed to create default instance for {schema.__name__}"
            )
            return {}

    @staticmethod
    def _fix_common_issues(
        data: Dict[str, Any],
        schema: Type[BaseModel],
    ) -> Optional[Dict[str, Any]]:
        r"""Attempt to fix common validation issues in extracted data.

        Args:
            data (Dict[str, Any]): The extracted data.
            schema (Type[BaseModel]): The target schema.

        Returns:
            Optional[Dict[str, Any]]: Fixed data or None if unfixable.
        """
        fixed_data = data.copy()
        schema_name = schema.__name__

        if schema_name == 'TaskAssignResult':
            # Ensure assignments is a list
            if 'assignments' not in fixed_data:
                fixed_data['assignments'] = []
            elif not isinstance(fixed_data['assignments'], list):
                fixed_data['assignments'] = [fixed_data['assignments']]

            # Fix each assignment
            for _i, assignment in enumerate(fixed_data['assignments']):
                if isinstance(assignment, dict):
                    # Ensure dependencies is a list
                    if 'dependencies' not in assignment:
                        assignment['dependencies'] = []
                    elif isinstance(assignment['dependencies'], str):
                        # Handle comma-separated string
                        deps = assignment['dependencies'].strip()
                        if deps:
                            assignment['dependencies'] = [
                                d.strip() for d in deps.split(',')
                            ]
                        else:
                            assignment['dependencies'] = []

        elif schema_name == 'RecoveryDecision':
            # Ensure strategy is valid
            if 'strategy' in fixed_data:
                strategy = fixed_data['strategy'].lower()
                valid_strategies = [
                    'retry',
                    'replan',
                    'decompose',
                    'create_worker',
                ]
                if strategy not in valid_strategies:
                    # Try to match partial
                    for valid in valid_strategies:
                        if valid.startswith(strategy) or strategy in valid:
                            fixed_data['strategy'] = valid
                            break

        return fixed_data

    @staticmethod
    def _create_default_instance(schema: Type[BaseModel]) -> BaseModel:
        r"""Create a default instance of the schema with minimal required
        fields.

        Args:
            schema (Type[BaseModel]): The schema to instantiate.

        Returns:
            BaseModel: Default instance of the schema.
        """
        schema_name = schema.__name__

        if schema_name == 'TaskAssignResult':
            return TaskAssignResult(assignments=[])
        elif schema_name == 'WorkerConf':
            return WorkerConf(
                role="General Assistant",
                sys_msg="You are a helpful assistant.",
                description="A general-purpose worker",
            )
        elif schema_name == 'RecoveryDecision':
            return RecoveryDecision(
                strategy=RecoveryStrategy.RETRY,
                reasoning="Unable to parse response, defaulting to retry",
                modified_task_content=None,
            )
        else:
            # Try to create with empty dict and let defaults handle it
            return schema()

    @staticmethod
    def validate_response(
        response: Union[BaseModel, Dict[str, Any]],
        schema: Type[BaseModel],
    ) -> bool:
        r"""Validate that a response conforms to the expected schema.

        Args:
            response: The response to validate.
            schema (Type[BaseModel]): The expected schema.

        Returns:
            bool: True if valid, False otherwise.
        """
        if isinstance(response, schema):
            return True

        if isinstance(response, dict):
            try:
                schema(**response)
                return True
            except ValidationError:
                return False

        return False

    @staticmethod
    def create_fallback_response(
        schema: Type[BaseModel],
        error_message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> BaseModel:
        r"""Create a fallback response for a given schema with error context.

        Args:
            schema (Type[BaseModel]): The schema to create a response for.
            error_message (str): The error message to include.
            context (Optional[Dict[str, Any]]): Additional context for the
                fallback.

        Returns:
            BaseModel: A valid instance of the schema with fallback values.
        """
        schema_name = schema.__name__

        if schema_name == 'TaskAssignResult':
            # Return empty assignments
            return TaskAssignResult(assignments=[])

        elif schema_name == 'WorkerConf':
            # Create a generic worker config
            task_content = ""
            if context and 'task_content' in context:
                task_content = context['task_content'][:50]

            return WorkerConf(
                role="General Assistant",
                sys_msg=f"You are a general assistant. Error during "
                f"configuration: {error_message}",
                description=f"Fallback worker for task: {task_content}...",
            )

        elif schema_name == 'RecoveryDecision':
            # Default to retry strategy
            return RecoveryDecision(
                strategy=RecoveryStrategy.RETRY,
                reasoning=f"Fallback decision due to: {error_message}",
                modified_task_content=None,
            )

        else:
            # Generic fallback
            try:
                return schema()
            except Exception as e:
                raise ValueError(
                    f"Cannot create fallback for unknown schema: {schema_name}"
                ) from e
