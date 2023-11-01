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

from copy import deepcopy
from typing import Any, Dict, List

from camel.storages.key_value_storages.base import BaseKeyValueStorage


class InMemoryKeyValueStorage(BaseKeyValueStorage):
    r"""A concrete implementation of the :obj:`BaseKeyValueStorage` using in-memory
    list. Ideal for temporary storage purposes, as data will be lost when the
    program ends.
    """

    def __init__(self) -> None:
        self.memory_list: List[Dict] = []

    def save(self, records: List[Dict[str, Any]]) -> None:
        self.memory_list.extend(deepcopy(records))

    def load(self) -> List[Dict[str, Any]]:
        return deepcopy(self.memory_list)

    def clear(self) -> None:
        self.memory_list.clear()
