import prance
import requests
import importlib
import os
from typing import Dict, Any, List, Callable

from camel.functions import OpenAIFunction
from camel.types import OpenApiName


def parse_openapi_file(openapi_spec):
    # Load the OpenAPI spec
    parser = prance.ResolvingParser(openapi_spec)
    openapi = parser.specification
    return (openapi)


def openapi_spec2openai_schemas(api_name: str, openapi: Dict[str, Any]) -> List[Dict[str, Any]]:
    result = []

    # Iterate over each path and operation in the OpenAPI spec
    for path, path_item in openapi.get('paths', {}).items():
        for method, operation in path_item.items():
            if operation.get('deprecated') is True:
                continue

            # Get the function name from the operationId, or construct it from the API method, and path
            function_name = f"{api_name}"
            operation_id = operation.get('operationId')
            function_name += f"_{operation_id}" if operation_id else f"{method}{path.replace('/', '_')}"

            # Get the description from the operation, or raise an error if it does not exist
            description = operation.get('description') or operation.get('summary')
            if not description:
                raise ValueError("{method} {path} Operation from {api_name} does not have a description or summary.")
            description = f"{description} This function is from {api_name} API."

            # If the OpenAPI spec has a description, add it to the function description
            if 'description' in openapi.get('info', {}):
                description += f" {openapi['info']['description']}"

            # Get the parameters for the operation, if any
            params = operation.get('parameters', [])
            properties = {}
            required = []

            # Iterate over each parameter
            for param in params:
                if not param.get('deprecated', False):
                    param_name = param['name'] + '_in_' + param['in']
                    properties[param_name] = {}

                    # If the parameter has a description, add it to the property dictionary
                    if 'description' in param:
                        properties[param_name]['description'] = param['description']

                    # If the parameter has a schema, add it to the property dictionary
                    if 'schema' in param:
                        # If 'description' exists in the properties dictionary and is not empty, remove 'description' from the schema dictionary
                        if properties[param_name].get('description') and 'description' in param['schema']:
                            param['schema'].pop('description')
                        properties[param_name].update(param['schema'])

                    # If the parameter is required, add it to the required list
                    if param.get('required'):
                        required.append(param_name)

                    # If the property dictionary does not have a description, use the parameter name as the description
                    if 'description' not in properties[param_name]:
                        properties[param_name]['description'] = param['name']

                    if 'type' not in properties[param_name]:
                        properties[param_name]['type'] = 'Any'

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


def openapi_function_decorator(base_url, path, method, operation):
    def inner_decorator(openapi_function):
        def wrapper(**kwargs):
            request_url = base_url + path
            headers = {}
            params = {}
            cookies = {}

            # 分配参数到正确位置
            for param in operation.get('parameters', []):
                input_param_name = param['name'] + '_in_' + param['in']
                param_in = param['in']
                # 传入无关参数不影响函数运行
                if input_param_name in kwargs:
                    if param_in == 'path':
                        request_url = request_url.replace(f"{{{param['name']}}}", str(kwargs[input_param_name]))
                    elif param_in == 'query':
                        params[param['name']] = kwargs[input_param_name]
                    elif param_in == 'header':
                        headers[param['name']] = kwargs[input_param_name]
                    elif param_in == 'cookie':
                        cookies[param['name']] = kwargs[input_param_name]

            if 'requestBody' in operation:
                request_body = kwargs.get('requestBody', {})
                content_type_list = list(operation.get('requestBody', {}).get('content', {}).keys())
                if content_type_list != []:
                    content_type = content_type_list[0]
                    headers.update({"Content-Type": content_type})

                # 根据Content-Type来决定如何发送请求体
                if content_type == "application/json":
                    response = requests.request(method.upper(), request_url, params=params, headers=headers, cookies=cookies, json=request_body)
                else:
                    raise ValueError(f"Unsupported content type: {content_type}")
            else:
                # 如果没有requestBody，那么不发送请求体
                response = requests.request(method.upper(), request_url, params=params, headers=headers, cookies=cookies)

            return response.json()
        return wrapper
    return inner_decorator


def generate_openapi_functions(openapi_spec: Dict[str, Any], api_name: str) -> List[Callable]:
    # 检查服务器信息
    servers = openapi_spec.get('servers', [])
    if not servers:
        raise ValueError("No server information found in OpenAPI spec.")
    base_url = servers[0].get('url')  # 使用第一个服务器URL

    # 函数列表
    functions = []

    # 遍历路径和方法
    for path, methods in openapi_spec.get('paths', {}).items():

        for method, operation in methods.items():
            # print(method, operation)
            operation_id = operation.get('operationId')
            function_name = f"{api_name}"
            function_name += f"_{operation_id}" if operation_id else f"{method}{path.replace('/', '_')}"

            @openapi_function_decorator(base_url, path, method, operation)
            def openapi_function(**kwargs):
                pass

            # 动态设置函数名称
            openapi_function.__name__ = function_name

            # 添加到列表
            functions.append(openapi_function)

    return functions


def combine_all_functions_schemas():
    combined_openapi_functions_list = []
    combined_openapi_functions_schemas = []

    for api_name in OpenApiName:
        # 解析每个API的OpenAPI规范
        current_dir = os.path.dirname(__file__)
        spec_file_path = os.path.join(current_dir, 'open_api_specs',
                                      f'{api_name.value}', 'openapi.yaml')

        openapi = parse_openapi_file(spec_file_path)

        # 生成并合并函数列表
        openapi_functions_list = generate_openapi_functions(openapi, api_name)
        combined_openapi_functions_list.extend(openapi_functions_list)

        # 生成并合并函数schemas
        openapi_functions_schemas = openapi_spec2openai_schemas(api_name.value, openapi)
        combined_openapi_functions_schemas.extend(openapi_functions_schemas)

    return combined_openapi_functions_list, combined_openapi_functions_schemas


combined_openapi_functions_list, combined_openapi_functions_schemas = combine_all_functions_schemas()


OPENAPI_FUNCS: List[OpenAIFunction] = [
    OpenAIFunction(a_func, a_schema)
    for a_func, a_schema in zip(combined_openapi_functions_list, combined_openapi_functions_schemas)
]
