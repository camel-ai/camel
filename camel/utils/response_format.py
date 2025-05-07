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

from __future__ import annotations

import inspect
import json
from typing import Any, Callable, Dict, List, Optional, Type, Union

from pydantic import BaseModel, Field, create_model


def get_pydantic_model(
    input_data: Union[str, Type[BaseModel], Callable],
) -> Type[BaseModel]:
    r"""A multi-purpose function that can be used as a normal function,
        a class decorator, or a function decorator.

    Args:
    input_data (Union[str, type, Callable]):
        - If a string is provided, it should be a JSON-encoded string
            that will be converted into a BaseModel.
        - If a function is provided, it will be decorated such that
            its arguments are converted into a BaseModel.
        - If a BaseModel class is provided, it will be returned directly.

    Returns:
        Type[BaseModel]: The BaseModel class that will be used to
            structure the input data.
    """
    if isinstance(input_data, str):
        data_dict = json.loads(input_data)
        TemporaryModel = create_model(  # type: ignore[call-overload]
            "TemporaryModel",
            **{key: (type(value), None) for key, value in data_dict.items()},
        )
        return TemporaryModel(**data_dict).__class__

    elif callable(input_data):
        WrapperClass = create_model(  # type: ignore[call-overload]
            f"{input_data.__name__.capitalize()}Model",
            **{
                name: (param.annotation, ...)
                for name, param in inspect.signature(
                    input_data
                ).parameters.items()
            },
        )
        return WrapperClass
    if issubclass(input_data, BaseModel):
        return input_data
    raise ValueError("Invalid input data provided.")


TYPE_MAPPING = {
    "integer": int,
    "number": float,
    "string": str,
    "boolean": bool,
    "array": list,
    "object": dict,
}


def model_from_json_schema(
    name: str,
    schema: Dict[str, Any],
) -> Type[BaseModel]:
    r"""Create a Pydantic model from a JSON schema.

    Args:
        name (str): The name of the model.
        schema (Dict[str, Any]): The JSON schema to create the model from.

    Returns:
        Type[BaseModel]: The Pydantic model.
    """
    properties = schema.get("properties", {})
    required_fields = set(schema.get("required", []))
    fields: Dict[str, Any] = {}

    for field_name, field_schema in properties.items():
        json_type = field_schema.get("type", "string")
        # Handle nested objects recursively.
        if json_type == "object" and "properties" in field_schema:
            py_type = model_from_json_schema(
                f"{name}_{field_name}", field_schema
            )
        elif json_type == "array":
            # Process array items if available.
            items_schema = field_schema.get("items", {"type": "string"})
            items_type: Type[Any] = TYPE_MAPPING.get(
                items_schema.get("type", "string"), str
            )
            if (
                items_schema.get("type") == "object"
                and "properties" in items_schema
            ):
                items_type = model_from_json_schema(
                    f"{name}_{field_name}_item", items_schema
                )
            py_type = List[items_type]  # type: ignore[assignment, valid-type]
        else:
            py_type = TYPE_MAPPING.get(json_type, str)

        # Handle nullable fields.
        if field_schema.get("nullable", False):
            py_type = Optional[py_type]  # type: ignore[assignment]

        # Construct constraints if available.
        constraints = {}
        if "minLength" in field_schema:
            constraints["min_length"] = field_schema["minLength"]
        if "maxLength" in field_schema:
            constraints["max_length"] = field_schema["maxLength"]
        if "minimum" in field_schema:
            constraints["ge"] = field_schema["minimum"]
        if "maximum" in field_schema:
            constraints["le"] = field_schema["maximum"]
        if "enum" in field_schema:
            constraints["enum"] = field_schema["enum"]
        if "description" in field_schema:
            constraints["description"] = field_schema["description"]

        default_value = field_schema.get("default", None)
        if field_name in required_fields:
            fields[field_name] = (py_type, Field(..., **constraints))
        else:
            fields[field_name] = (
                Optional[py_type],
                Field(default_value, **constraints),
            )

    return create_model(name, **fields)  # type: ignore[call-overload]
