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
from enum import Enum
from typing import Any, Type, Union

from synthetic_datagen.self_instruct.self_instruct_pipeline import (
    SelfInstructPipeline,
)

from camel.synthetic_datagen.base_generator import BaseDataGenerator


class SyntheticDataGeneratorMethodType(Enum):
    SELFINSTRUCT = "selfinstruct"

    @property
    def is_self_instruct(self) -> bool:
        return self is SyntheticDataGeneratorMethodType.SELFINSTRUCT


class SyntheticDataGeneratorFactory:
    @staticmethod
    def create(
        method_type: Union[SyntheticDataGeneratorMethodType, str],
        spec: Any,
        *args,
        **kwargs,
    ) -> BaseDataGenerator:
        method_class: Type[BaseDataGenerator] = (
            SyntheticDataGeneratorFactory._get_method_class(method_type)
        )
        return method_class(spec, *args, **kwargs)

    @staticmethod
    def _get_method_class(
        method_type: Union[SyntheticDataGeneratorMethodType, str],
    ) -> Type[BaseDataGenerator]:
        if isinstance(method_type, str):
            try:
                method_type = SyntheticDataGeneratorMethodType(
                    method_type.lower()
                )
            except ValueError:
                raise ValueError(
                    f"Invalid method type string: '{method_type}'"
                )

        if isinstance(method_type, SyntheticDataGeneratorMethodType):
            if method_type == SyntheticDataGeneratorMethodType.SELFINSTRUCT:
                return SelfInstructPipeline
            else:
                raise ValueError(f"Unknown method type: {method_type}")
        else:
            raise ValueError(f"Invalid method type: {method_type}")
