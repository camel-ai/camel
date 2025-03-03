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

from copy import deepcopy
from typing import Any, Dict, List, Optional

from camel.storages.key_value_storages import BaseKeyValueStorage


class InMemoryKeyValueStorage(BaseKeyValueStorage):
    r"""A concrete implementation of the :obj:`BaseKeyValueStorage` using
    in-memory list. Ideal for temporary storage purposes, as data will be lost
    when the program ends.
    """

    def __init__(self) -> None:
        self.memory_list: List[Dict] = []

    def save(self, records: List[Dict[str, Any]]) -> None:
        r"""Saves a batch of records to the key-value storage system.

        Args:
            records (List[Dict[str, Any]]): A list of dictionaries, where each
                dictionary represents a unique record to be stored.
        """
        self.memory_list.extend(deepcopy(records))

    def load(self, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        r"""Loads all stored records from the key-value storage system.
        If agent_id is provided, only records associated with the specified
        agent will be returned.

        Args:
            agent_id (str, optional): The ID of the agent associated with the
                records. If not provided, all records will be loaded.
                (default: :obj:`None`)

        Returns:
            List[Dict[str, Any]]: A list of dictionaries, where each dictionary
                represents a stored record.
        """
        all_records = deepcopy(self.memory_list)

        if agent_id is not None:
            all_records = [
                r for r in all_records if r.get("agent_id") == agent_id
            ]
        return all_records

    def clear(self) -> None:
        r"""Removes all records from the key-value storage system."""
        self.memory_list.clear()
