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
from camel.memories import GraphDBBlock, MemoryRecord
from camel.messages import BaseMessage
from camel.types import OpenAIBackendRole, RoleType


def main():
    block = None
    try:
        block = GraphDBBlock(
            url="neo4j://localhost:7687",
            username="neo4j",
            password="u4CQDJCKVs@4-LW",
        )
        print("Connected to Neo4j successfully!")

        record = MemoryRecord(
            message=BaseMessage("user", RoleType.USER, None, "Hello world"),
            role_at_backend=OpenAIBackendRole.USER,
        )
        print("Writing record...")
        block.write_records([record])
        print("Record written successfully!")

        print("Retrieving results...")
        results = block.retrieve(query="Hello", numberOfNearestNeighbours=5)
        print(f"Results: {results}")
    except Exception as e:
        print(f"Operation failed: {e}")
    finally:
        if block is not None:  # Check if block was initialized
            print("Clearing the database...")
            block.clear()
            print("Database cleared successfully!")


if __name__ == "__main__":
    main()
