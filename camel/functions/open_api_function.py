import prance
from typing import Dict, Any, List
import json

from camel.functions import OpenAIFunction


def openapi_parse(openapi_spec):
    # Load the OpenAPI spec
    parser = prance.ResolvingParser(openapi_spec)
    openapi = parser.specification
    return (openapi)


def convert_openapi_to_json(api_name: str, openapi: Dict[str, Any]) -> List[Dict[str, Any]]:
    result = []  # Initialize the result list

    # Iterate over each path and operation in the OpenAPI spec
    for path, path_item in openapi.get('paths', {}).items():
        for method, operation in path_item.items():

            # Get the parameters for the operation, if any
            parameters = operation.get('parameters', [])

            properties = {}  # Initialize the properties dictionary
            required = []  # Initialize the required list

            # Iterate over each parameter
            for parameter in parameters:
                # Only parameters in path or query need to be inputed by agent
                if parameter['in'] in ['path', 'query'] and not parameter.get('deprecated', False):
                    param_name = parameter['name']
                    properties[param_name] = {}  # Initialize the property dictionary for this parameter

                    # If the parameter has a description, add it to the property dictionary
                    if 'description' in parameter:
                        properties[param_name]['description'] = parameter['description']

                    # If the parameter has a schema, add it to the property dictionary
                    if 'schema' in parameter:
                        # If 'description' exists in the properties dictionary and is not empty, remove 'description' from the schema dictionary
                        if properties[param_name].get('description') and 'description' in parameter['schema']:
                            parameter['schema'].pop('description')

                        if 'type' not in parameter['schema']:
                            parameter['schema']['type'] = 'Any'

                        properties[param_name].update(parameter['schema'])

                    # If the parameter is required, add it to the required list
                    if parameter.get('required'):
                        required.append(param_name)

                    # If the property dictionary does not have a description, use the parameter name as the description
                    if 'description' not in properties[param_name]:
                        properties[param_name]['description'] = param_name

            # Process requestBody if present
            if 'requestBody' in operation:
                properties['requestBody'] = {}
                requestBody = operation['requestBody']
                if requestBody.get('required') is True:
                    required.append('requestBody')

                content = requestBody.get('content', {})
                json_schema = content.get('application/json', {}).get('schema', {})
                if json_schema:
                    properties['requestBody'] = json_schema
                if 'description' not in properties['requestBody']:
                    properties['requestBody']['description'] = "The request body, with parameters specifically described under the `properties` key"

            # Get the function name from the operationId, or construct it from the API method, and path
            function_name = f"{api_name}"
            operation_id = operation.get('operationId')
            function_name += f"_{operation_id}" if operation_id else f"{method}{path.replace('/', '_')}"


            # Get the description from the operation, or raise an error if it does not exist
            description = operation.get('description') or operation.get('summary')
            if not description:
                raise ValueError("Operation does not have a description or summary.")
            description = f"{description} This function is from {api_name} API."

            # If the OpenAPI spec has a description, add it to the function description
            if 'description' in openapi.get('info', {}):
                description += f" {openapi['info']['description']}"

            # Construct the function dictionary and add it to the result list
            function = {
                "type": "function",
                "function": {
                    "name": function_name,
                    "description": description,
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required,
                    },
                }
            }
            result.append(function)

    return result  # Return the result list

openai_schemas = convert_openapi_to_json('zapier', openapi_parse('open_api_try/zapier/openapi.yaml'))


def fake_fun():
    return True


OPENAPI_FUNCS: List[OpenAIFunction] = [
    OpenAIFunction(fake_fun, a_schema)
    for a_schema in openai_schemas
]
