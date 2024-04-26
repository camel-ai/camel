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
import os
import shutil
from datetime import datetime
from unittest.mock import patch

import pytest

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
        vector_storage_local_path=temp_storage_path, storage_type=StorageType.QDRANT
    )


def test__initialize_vector_storage(auto_retriever):
    # with tempfile.TemporaryDirectory() as tmpdir:
    storage_custom = auto_retriever._initialize_vector_storage("collection")
    assert isinstance(storage_custom, QdrantStorage)


def test_get_file_modified_date_from_file(auto_retriever):
    with patch('os.path.getmtime') as mocked_getmtime:
        mocked_getmtime.return_value = 1234567890
        mod_date = auto_retriever._get_file_modified_date_from_file("/path/to/file")
        expected_date = datetime.fromtimestamp(1234567890).strftime('%Y-%m-%dT%H:%M:%S')
        assert mod_date == expected_date

    with pytest.raises(FileNotFoundError):
        auto_retriever._get_file_modified_date_from_file("/path/to/nonexistent/file")


def test_run_vector_retriever(auto_retriever):
    # Define mock data for testing
    query_related = "what is camel"
    query_unrealted = "unrelated query"
    content_input_paths = "https://www.camel-ai.org/"
    top_k = 1
    similarity_threshold = 0.75

    # Test with query related to the content in mock data
    result_related = auto_retriever.run_vector_retriever(
        query_related,
        content_input_paths,
        top_k,
        similarity_threshold,
        return_detailed_info=True,
    )

    assert (
        "similarity score" in result_related
    ), "result_related missing 'similarity score'"
    assert "content path" in result_related, "result_related missing 'content path'"
    assert "metadata" in result_related, "result_related missing 'metadata'"
    assert "text" in result_related, "result_related missing 'text'"

    # Test with query unrelated to the content in mock data
    result_unrelated = auto_retriever.run_vector_retriever(
        query_unrealted, content_input_paths, top_k, similarity_threshold
    )

    assert "No suitable information retrieved from" in result_unrelated
