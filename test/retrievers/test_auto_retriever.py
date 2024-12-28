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
import os
import shutil

import pytest

from camel.loaders import UnstructuredIO
from camel.retrievers import AutoRetriever
from camel.storages import QdrantStorage
from camel.types import StorageType


@pytest.fixture
def temp_storage_path():
    # Define the path to the temporary storage
    path = 'test/functions/tempory_storage'

    yield path

    # Remove the files created in the temporary storage
    if os.path.exists(path):
        shutil.rmtree(path)


@pytest.fixture
def auto_retriever(temp_storage_path):
    return AutoRetriever(
        vector_storage_local_path=temp_storage_path,
        storage_type=StorageType.QDRANT,
    )


def test__initialize_vector_storage(auto_retriever):
    # with tempfile.TemporaryDirectory() as tmpdir:
    storage_custom = auto_retriever._initialize_vector_storage("collection")
    assert isinstance(storage_custom, QdrantStorage)


def test_run_vector_retriever(auto_retriever):
    # Define mock data for testing
    query_unrealted = "unrelated query"
    contents = "https://www.camel-ai.org/"
    top_k = 1
    similarity_threshold = 0.5

    # Test with query unrelated to the content in mock data
    result_unrelated = auto_retriever.run_vector_retriever(
        query_unrealted, contents, top_k, similarity_threshold
    )

    assert "No suitable information retrieved from" in str(result_unrelated)


def test_run_vector_retriever_with_element_input(auto_retriever):
    uio = UnstructuredIO()
    test_element = uio.create_element_from_text(
        text="""Introducing 🦀 CRAB: Cross-environment Agent Benchmark for 
        Multimodal Language Model Agents

    🦀 CRAB provides an end-to-end and easy-to-use framework to build 
    multimodal agents, operate environments, and create benchmarks to evaluate 
    them, featuring three key components:

    - 🔀 Cross-environment support - agents can operate tasks in 📱 Android 
    and 💻 Ubuntu.
    - 🕸️ Graph evaluator - provides a fine-grain evaluation metric for agents.
    - 🤖 Task generation - composes subtasks to automatically generate tasks.

    By connecting all devices to agents, 🦀CRAB unlocks greater capabilities 
    for human-like tasks than ever before.

    Use 🦀 CRAB to benchmark your multimodal agents! """,
        file_directory="https://x.com/CamelAIOrg/status/1821970132606058943",
    )

    output = auto_retriever.run_vector_retriever(
        query="CRAB provides an end-to-end and easy-to-use framework to build"
        " multimodal agents",
        contents=test_element,
        return_detailed_info=True,
    )

    assert (
        output["Retrieved Context"][0]['content path']
        == 'https://x.com/CamelAIOrg/status/1821970132606058943'
    )
