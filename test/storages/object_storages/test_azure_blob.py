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
from pathlib import Path, PurePosixPath, PureWindowsPath
from unittest.mock import MagicMock, patch

import pytest

from camel.loaders.base_io import TxtFile
from camel.storages.object_storages import AzureBlobStorage


@pytest.fixture
def mock_instance():
    with patch(
        "camel.storages.object_storages.azure_blob.ContainerClient"
    ) as mock_container_client:
        mock_client = MagicMock()
        mock_container_client.return_value = mock_client
        mock_client.exists.return_value = True

        mock_blob = MagicMock()
        mock_client.download_blob.return_value = mock_blob
        mock_blob.readall.return_value = b"file content"

        yield AzureBlobStorage(
            storage_account_name="mock-account",
            container_name="mock-container",
        )


def test_canonicalize_path():
    windows_path = PureWindowsPath('relative\\path\\to\\file.pdf')
    posix_path = PurePosixPath('relative/path/to/file.pdf')

    windows_key = AzureBlobStorage.canonicalize_path(windows_path)
    posix_key = AzureBlobStorage.canonicalize_path(posix_path)

    assert windows_key == 'relative\\path\\to\\file.pdf'
    assert posix_key == 'relative/path/to/file.pdf'


def test_get_file(mock_instance: AzureBlobStorage):
    file = mock_instance.get_file(Path("file.txt"))
    assert file.name == "file.txt"
    assert isinstance(file, TxtFile)
    assert file.raw_bytes == b"file content"
