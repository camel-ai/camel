import prance
import requests
import json
import os
from typing import Dict, Any, List, Callable, Tuple

from camel.functions import OpenAIFunction
from camel.types import OpenApiName


def parse_openapi_file(openapi_spec: str) -> Dict[str, Any]:
    # Load the OpenAPI spec
    parser = prance.ResolvingParser(openapi_spec)
    openapi = parser.specification
    return (openapi)


def openapi_spec2openai_schemas(
    api_name: str, openapi: Dict[str, Any]
) -> List[Dict[str, Any]]:

    result = []

    for path, path_item in openapi.get('paths', {}).items():
        for method, op in path_item.items():
            if op.get('deprecated') is True:
                continue

            # Get the function name from the operationId
            # or construct it from the API method, and path
            function_name = f"{api_name}"
            operation_id = op.get('operationId')
            if operation_id:
                function_name += f"_{operation_id}"
            else:
                function_name += f"{method}{path.replace('/', '_')}"

            description = op.get('description') or op.get('summary')
            if not description:
                error_message = (
                    f"{method} {path} Operation from {api_name} "
                    "does not have a description or summary."
                )
                raise ValueError(error_message)

            description += f" This function is from {api_name} API."

            # If the OpenAPI spec has a description,
            # add it to the operation description
            if 'description' in openapi.get('info', {}):
                description += f" {openapi['info']['description']}"

            # Get the parameters for the operation, if any
            params = op.get('parameters', [])
            properties = {}
            required = []

            for param in params:
                if not param.get('deprecated', False):
                    param_name = param['name'] + '_in_' + param['in']
                    properties[param_name] = {}

                    if 'description' in param:
                        properties[param_name]['description'] = (
                            param['description']
                        )

                    if 'schema' in param:
                        if (properties[param_name].get('description') is not
                           None and 'description' in param['schema']):
                            param['schema'].pop('description')
                        properties[param_name].update(param['schema'])

                    if param.get('required'):
                        required.append(param_name)

                    # If the property dictionary does not have a description,
                    # use the parameter name as the description
                    if 'description' not in properties[param_name]:
                        properties[param_name]['description'] = param['name']

                    if 'type' not in properties[param_name]:
                        properties[param_name]['type'] = 'Any'

            # Process requestBody if present
            if 'requestBody' in op:
                properties['requestBody'] = {}
                requestBody = op['requestBody']
                if requestBody.get('required') is True:
                    required.append('requestBody')

                content = requestBody.get('content', {})
                json_content = content.get('application/json', {})
                json_schema = json_content.get('schema', {})
                if json_schema:
                    properties['requestBody'] = json_schema
                if 'description' not in properties['requestBody']:
                    properties['requestBody']['description'] = (
                        "The request body, with parameters specifically "
                        "described under the `properties` key"
                    )

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


def openapi_function_decorator(
    base_url: str,
    path: str,
    method: str,
    operation: Dict[str, Any]
) -> Callable:
    def inner_decorator(openapi_function: Callable) -> Callable:
        def wrapper(**kwargs):
            request_url = base_url + path
            headers = {}
            params = {}
            cookies = {}

            # Assign parameters to the correct position
            for param in operation.get('parameters', []):
                input_param_name = param['name'] + '_in_' + param['in']
                param_in = param['in']
                # Irrelevant arguments does not affect function operation
                if input_param_name in kwargs:
                    if param_in == 'path':
                        request_url = request_url.replace(
                            f"{{{param['name']}}}",
                            str(kwargs[input_param_name]))
                    elif param_in == 'query':
                        params[param['name']] = kwargs[input_param_name]
                    elif param_in == 'header':
                        headers[param['name']] = kwargs[input_param_name]
                    elif param_in == 'cookie':
                        cookies[param['name']] = kwargs[input_param_name]

            if 'requestBody' in operation:
                request_body = kwargs.get('requestBody', {})
                content_type_list = list(operation.get(
                    'requestBody', {}).get('content', {}).keys())
                if content_type_list != []:
                    content_type = content_type_list[0]
                    headers.update({"Content-Type": content_type})

                # send the request body based on the Content-Type
                if content_type == "application/json":
                    response = requests.request(
                        method.upper(),
                        request_url,
                        params=params,
                        headers=headers,
                        cookies=cookies,
                        json=request_body
                    )
                else:
                    raise ValueError(
                        f"Unsupported content type: {content_type}")
            else:
                # If there is no requestBody, no request body is sent
                response = requests.request(
                    method.upper(),
                    request_url,
                    params=params,
                    headers=headers,
                    cookies=cookies
                )

            try:
                return response.json()
            except json.JSONDecodeError:
                raise ValueError(
                    "Response could not be decoded as JSON. "
                    "Please check the input parameters."
                )
        return wrapper
    return inner_decorator


def generate_openapi_funcs(
        openapi_spec: Dict[str, Any], api_name: str
) -> List[Callable]:
    # Check server information
    servers = openapi_spec.get('servers', [])
    if not servers:
        raise ValueError("No server information found in OpenAPI spec.")
    base_url = servers[0].get('url')  # Use the first server URL

    functions = []

    # Traverse paths and methods
    for path, methods in openapi_spec.get('paths', {}).items():

        for method, operation in methods.items():
            # Get the function name from the operationId
            # or construct it from the API method, and path
            function_name = f"{api_name}"
            operation_id = operation.get('operationId')
            if operation_id:
                function_name += f"_{operation_id}"
            else:
                function_name += f"{method}{path.replace('/', '_')}"

            @openapi_function_decorator(base_url, path, method, operation)
            def openapi_function(**kwargs):
                pass

            openapi_function.__name__ = function_name

            functions.append(openapi_function)

    return functions


def combine_all_funcs_schemas(
) -> Tuple[List[Callable], List[Dict[str, Any]]]:
    combined_func_lst = []
    combined_schemas_list = []

    for api_name in OpenApiName:
        # Parse the OpenAPI specification for each API
        current_dir = os.path.dirname(__file__)
        spec_file_path = os.path.join(current_dir, 'open_api_specs',
                                      f'{api_name.value}', 'openapi.yaml')

        openapi = parse_openapi_file(spec_file_path)

        # Generate and merge function lists
        openapi_functions_list = generate_openapi_funcs(
            openapi, api_name.value)
        combined_func_lst.extend(openapi_functions_list)

        # Generate and merge function schemas
        openapi_functions_schemas = openapi_spec2openai_schemas(
            api_name.value, openapi)
        combined_schemas_list.extend(openapi_functions_schemas)

    return combined_func_lst, combined_schemas_list


combined_funcs_lst, combined_schemas_list = combine_all_funcs_schemas()

OPENAPI_FUNCS: List[OpenAIFunction] = [
    OpenAIFunction(a_func, a_schema)
    for a_func, a_schema in zip(combined_funcs_lst, combined_schemas_list)
]
