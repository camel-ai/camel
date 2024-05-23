# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
import json
import os
from typing import Any, Callable, Dict, List, Tuple

import prance
import requests

from camel.functions import OpenAIFunction
from camel.types import OpenAPIName


def parse_openapi_file(openapi_spec_path: str) -> Dict[str, Any]:
    r"""Load and parse an OpenAPI specification file.

    This function utilizes the `prance.ResolvingParser` to parse and resolve
    the given OpenAPI specification file, returning the parsed OpenAPI
    specification as a dictionary.

    Args:
        openapi_spec_path (str): The file path or URL to the OpenAPI
            specification.

    Returns:
        Dict[str, Any]: The parsed OpenAPI specification as a dictionary.
    """
    # Load the OpenAPI spec
    parser = prance.ResolvingParser(openapi_spec_path)
    openapi_spec = parser.specification
    return openapi_spec


def openapi_spec_to_openai_schemas(
    api_name: str, openapi_spec: Dict[str, Any]
) -> List[Dict[str, Any]]:
    r"""Convert OpenAPI specification to OpenAI schema format.

    This function iterates over the paths and operations defined in an
    OpenAPI specification, filtering out deprecated operations. For each
    operation, it constructs a schema in a format suitable for OpenAI,
    including operation metadata such as function name, description,
    parameters, and request bodies. It raises a ValueError if an operation
    lacks a description or summary.

    Args:
        api_name (str): The name of the API, used to prefix generated function
            names.
        openapi_spec (Dict[str, Any]): The OpenAPI specification as a
            dictionary.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, each representing a
            function in the OpenAI schema format, including details about the
            function's name, description, and parameters.

    Raises:
        ValueError: If an operation in the OpenAPI specification does not have
            a description or summary.

    Note:
        This function assumes that the OpenAPI specification follows the 3.0+
            format.

    Reference:
        https://swagger.io/specification/
    """
    result = []

    for path, path_item in openapi_spec.get('paths', {}).items():
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
                raise ValueError(
                    f"{method} {path} Operation from {api_name} "
                    f"does not have a description or summary."
                )
            description += " " if description[-1] != " " else ""
            description += f"This function is from {api_name} API. "

            # If the OpenAPI spec has a description,
            # add it to the operation description
            if 'description' in openapi_spec.get('info', {}):
                description += f"{openapi_spec['info']['description']}"

            # Get the parameters for the operation, if any
            params = op.get('parameters', [])
            properties: Dict[str, Any] = {}
            required = []

            for param in params:
                if not param.get('deprecated', False):
                    param_name = param['name'] + '_in_' + param['in']
                    properties[param_name] = {}

                    if 'description' in param:
                        properties[param_name]['description'] = param[
                            'description'
                        ]

                    if 'schema' in param:
                        if (
                            properties[param_name].get('description')
                            and 'description' in param['schema']
                        ):
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
                },
            }
            result.append(function)

    return result  # Return the result list


def openapi_function_decorator(
    base_url: str, path: str, method: str, operation: Dict[str, Any]
) -> Callable:
    r"""Decorate a function to make HTTP requests based on OpenAPI operation
    details.

    This decorator takes the base URL, path, HTTP method, and operation details
    from an OpenAPI specification, and returns a decorator. The decorated
    function can then be called with keyword arguments corresponding to the
    operation's parameters. The decorator handles constructing the request URL,
    setting headers, query parameters, and the request body as specified by the
    operation details.

    Args:
        base_url (str): The base URL for the API.
        path (str): The path for the API endpoint, relative to the base URL.
        method (str): The HTTP method (e.g., 'get', 'post') for the request.
        operation (Dict[str, Any]): A dictionary containing the OpenAPI
            operation details, including parameters and request body
            definitions.

    Returns:
        Callable: A decorator that, when applied to a function, enables the
            function to make HTTP requests based on the provided OpenAPI
            operation details.
    """

    def inner_decorator(openapi_function: Callable) -> Callable:
        def wrapper(**kwargs):
            request_url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
            headers = {}
            params = {}
            cookies = {}

            # Assign parameters to the correct position
            for param in operation.get('parameters', []):
                input_param_name = param['name'] + '_in_' + param['in']
                # Irrelevant arguments does not affect function operation
                if input_param_name in kwargs:
                    if param['in'] == 'path':
                        request_url = request_url.replace(
                            f"{{{param['name']}}}",
                            str(kwargs[input_param_name]),
                        )
                    elif param['in'] == 'query':
                        params[param['name']] = kwargs[input_param_name]
                    elif param['in'] == 'header':
                        headers[param['name']] = kwargs[input_param_name]
                    elif param['in'] == 'cookie':
                        cookies[param['name']] = kwargs[input_param_name]

            if 'requestBody' in operation:
                request_body = kwargs.get('requestBody', {})
                content_type_list = list(
                    operation.get('requestBody', {}).get('content', {}).keys()
                )
                if content_type_list:
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
                        json=request_body,
                    )
                else:
                    raise ValueError(
                        f"Unsupported content type: {content_type}"
                    )
            else:
                # print(params)
                # If there is no requestBody, no request body is sent
                response = requests.request(
                    method.upper(),
                    request_url,
                    params=params,
                    headers=headers,
                    cookies=cookies,
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
    api_name: str, openapi_spec: Dict[str, Any]
) -> List[Callable]:
    r"""Generates a list of Python functions based on an OpenAPI specification.

    This function dynamically creates a list of callable functions that
    represent the API operations defined in an OpenAPI specification document.
    Each function is designed to perform an HTTP request corresponding to an
    API operation (e.g., GET, POST) as defined in the specification. The
    functions are decorated with `openapi_function_decorator`, which
    configures them to construct and send the HTTP requests with appropriate
    parameters, headers, and body content.

    Args:
        api_name (str): The name of the API, used to prefix generated function
            names.
        openapi_spec (Dict[str, Any]): The OpenAPI specification as a
            dictionary.

    Returns:
        List[Callable]: A list containing the generated functions. Each
            function, when called, will make an HTTP request according to its
            corresponding API operation defined in the OpenAPI specification.

    Raises:
        ValueError: If the OpenAPI specification does not contain server
            information, which is necessary for determining the base URL for
            the API requests.
    """
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
            operation_id = operation.get('operationId')
            if operation_id:
                function_name = f"{api_name}_{operation_id}"
            else:
                sanitized_path = path.replace('/', '_').strip('_')
                function_name = f"{api_name}_{method}_{sanitized_path}"

            @openapi_function_decorator(base_url, path, method, operation)
            def openapi_function(**kwargs):
                pass

            openapi_function.__name__ = function_name

            functions.append(openapi_function)

    return functions


def combine_all_funcs_schemas() -> Tuple[List[Callable], List[Dict[str, Any]]]:
    r"""Combines functions and schemas from multiple OpenAPI specifications.

    Iterates over a list of OpenAPI specs, parses each, and generates functions
    and schemas based on the defined operations and schemas respectively.
    Assumes specification files are named 'openapi.yaml' located in
    `open_api_specs/<api_name>/`.

    Returns:
        Tuple[List[Callable], List[Dict[str, Any]]]:: one of callable
            functions for API operations, and another of dictionaries
            representing the schemas from the specifications.
    """
    combined_func_lst = []
    combined_schemas_list = []

    for api_name in OpenAPIName:
        # Parse the OpenAPI specification for each API
        current_dir = os.path.dirname(__file__)
        spec_file_path = os.path.join(
            current_dir, 'open_api_specs', f'{api_name.value}', 'openapi.yaml'
        )

        openapi_spec = parse_openapi_file(spec_file_path)

        # Generate and merge function schemas
        openapi_functions_schemas = openapi_spec_to_openai_schemas(
            api_name.value, openapi_spec
        )
        combined_schemas_list.extend(openapi_functions_schemas)

        # Generate and merge function lists
        openapi_functions_list = generate_openapi_funcs(
            api_name.value, openapi_spec
        )
        combined_func_lst.extend(openapi_functions_list)

    return combined_func_lst, combined_schemas_list


combined_funcs_lst, combined_schemas_list = combine_all_funcs_schemas()

OPENAPI_FUNCS: List[OpenAIFunction] = [
    OpenAIFunction(a_func, a_schema)
    for a_func, a_schema in zip(combined_funcs_lst, combined_schemas_list)
]
