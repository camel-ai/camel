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

from camel.memory.base import MemoryRecord
from camel.memory.vectordb_memory import VectorDBMemory
from camel.messages import BaseMessage
from camel.typing import OpenAIBackendRole, RoleType


# flake8: noqa :E501
def testVectorDBMemeory():
    texts = [
        "Every once in a long while, a game comes along that is so memorable, exciting, fresh, and well-written that it sets a new high-water mark for an entire genre.",
        "Baldur's Gate 3 is such an achievement for the tabletop roleplaying-inspired, swords and sorcery adventuring that its BioWare-made CRPG predecessors helped popularize decades ago.",
        "Larian Studios has turned this corner of Dungeons & Dragons' Forgotten Realms into a beautiful, detailed world stocked with too many fully-realized, powerfully written, and skillfully voiced characters to count.",
        "There are heart-wrenching choices to be made, alliances to be forged, bears to be romanced, and a vast diversity of interesting, challenging turn-based combat encounters.",
        "I didn't merely enjoy my 130-plus hours on this journey.",
        "I fell in love.",
    ]
    memory = VectorDBMemory()

    records = [
        MemoryRecord(
            message=BaseMessage(
                "AI user",
                role_type=RoleType.USER,
                meta_dict={"idx": idx},
                content=sentence,
            ), role_at_backend=OpenAIBackendRole.USER)
        for idx, sentence in enumerate(texts)
    ]

    memory.write_records(records)
    search_results = memory.retrieve("How long have I been playing this game?")
    assert search_results[0].to_dict() == records[4].to_dict()
