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
from typing import Any, Dict, List, Optional

from camel.memories.base import MemoryBlock
from camel.memories.records import ContextRecord, MemoryRecord
from camel.storages.graph_storages import BaseGraphStorage


class GraphDBBlock(MemoryBlock):
    r"""An implementation of the MemoryBlock abstract base class for
    maintaining and retrieving information using a graph database.

    Args:
        storage (Optional[BaseGraphStorage], optional): The storage mechanism
            for the graph database. Defaults to a specific implementation
            if not provided. (default: None)
    """

    def __init__(self, storage: Optional[BaseGraphStorage] = None) -> None:
        self.storage = storage or self.default_graph_storage()

    def default_graph_storage(self) -> BaseGraphStorage:
        raise NotImplementedError("Default graph storage is not implemented.")

    def retrieve(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> List[ContextRecord]:
        r"""Retrieves records from the graph database based on a query.

        Args:
            query (str): The query string to execute.
            params (Optional[Dict[str, Any]]): Parameters for the query.

        Returns:
            List[ContextRecord]: A list of context records retrieved from the
                graph database.
        """
        results = self.storage.query(query, params)
        score = 1.0
        return [
            ContextRecord(
                memory_record=MemoryRecord.from_dict(result), score=score
            )
            for result in results
        ]

    def write_records(self, records: List[MemoryRecord]) -> None:
        """Writes records to the graph database."""
        for record in records:
            content = record.message.content

            if isinstance(content, str):
                try:
                    data = json.loads(content)
                    subj = data.get('subject')
                    obj = data.get('object')
                    rel = data.get('relation')
                except json.JSONDecodeError:
                    print("Error parsing content as JSON:", content)
                    continue
            else:
                subj = content.get('subject')
                obj = content.get('object')
                rel = content.get('relation')

            if subj and obj and rel:
                self.write_triplet(subj, obj, rel)

    def write_triplet(self, subj: str, obj: str, rel: str) -> None:
        r"""Writes a triplet to the graph database.

        Args:
            subj (str): The subject of the triplet.
            obj (str): The object of the triplet.
            rel (str): The relationship between subject and object.
        """
        self.storage.add_triplet(subj, obj, rel)

    def delete_triplet(self, subj: str, obj: str, rel: str) -> None:
        r"""Deletes a triplet from the graph database.

        Args:
            subj (str): The subject of the triplet.
            obj (str): The object of the triplet.
            rel (str): The relationship between subject and object.
        """
        self.storage.delete_triplet(subj, obj, rel)

    def clear(self) -> None:
        """Clears all data from the graph database."""
        pass
