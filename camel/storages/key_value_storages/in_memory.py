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
from typing import Any, Dict, List, Set

from camel.storages.key_value_storages import BaseKeyValueStorage


class InMemoryKeyValueStorage(BaseKeyValueStorage):
    r"""A concrete implementation of the :obj:`BaseKeyValueStorage` using
    in-memory list. Ideal for temporary storage purposes, as data will be lost
    when the program ends.
    """

    def __init__(self) -> None:
        self.memory_list: List[Dict] = []
        self._record_uuids: Set[str] = set()

    def save(self, records: List[Dict[str, Any]]) -> None:
        r"""Saves a batch of records to the key-value storage system.

        This method prevents duplicate records by checking the 'uuid' field.
        If a record with the same UUID already exists, it will be skipped.

        Args:
            records (List[Dict[str, Any]]): A list of dictionaries, where each
                dictionary represents a unique record to be stored.
        """
        new_records = []
        for record in records:
            # Check for duplicate by uuid if available
            record_uuid = record.get('uuid')
            if record_uuid and record_uuid in self._record_uuids:
                continue

            # Deep copy the record to prevent external mutations
            new_record = deepcopy(record)
            new_records.append(new_record)

            # Track the uuid for deduplication
            if record_uuid:
                self._record_uuids.add(record_uuid)

        self.memory_list.extend(new_records)

    def load(self) -> List[Dict[str, Any]]:
        r"""Loads all stored records from the key-value storage system.

        Returns a shallow copy of the list with references to the original
        record dictionaries. Since records are already deep copied during
        save(), this avoids the expensive deep copy operation on load().

        Returns:
            List[Dict[str, Any]]: A list of dictionaries, where each dictionary
                represents a stored record.
        """
        return list(self.memory_list)

    def clear(self) -> None:
        r"""Removes all records from the key-value storage system."""
        self.memory_list.clear()
        self._record_uuids.clear()
