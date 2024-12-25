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
from typing import Any, Literal, Type, Union
from pydantic import BaseModel
from camel.configs.base_config import BaseConfig

class LinkupConfig(BaseConfig):
    r"""Defines the parameters for generating chat completions using the
        Linkup API.
    Reference: https://docs.linkup.so/pages/get-started/introduction

    Args:
        depth: The depth of the search. Can be either "standard", for a 
            straighforward and fast search, or "deep" for a more powerful 
            agentic workflow.
        output_type: The type of output which is expected:  "sourcedAnswer" 
            will output the answer to the query and sources supporting it, and 
            "structured" will base the output on the format provided in
            structured_output_schema.
        structured_output_schema: If output_type is "structured", specify the 
            schema of the output. Supported formats are a pydantic.BaseModel 
            or a string representing a valid object JSON schema.
        include_images: If output_type is "searchResults", specifies if the 
            response can include images. Default to False.
    """

    depth: Literal["standard", "deep"] = "deep"
    output_type: Literal["sourcedAnswer", "structured"] = "sourcedAnswer"
    structured_output_schema: Union[Type[BaseModel], str, None] = None
    include_images: bool = False,

    def as_dict(self) -> dict[str, Any]:
        config_dict = super().as_dict()
        if "tools" in config_dict:
            del config_dict["tools"]  # Linkup does not support tool calling
        return config_dict

LINKUP_API_PARAMS = {param for param in LinkupConfig.model_fields.keys()}
