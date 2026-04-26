# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========

from pathlib import PurePosixPath, PureWindowsPath
from unittest.mock import MagicMock

from camel.storages.object_storages import GoogleCloudStorage


def test_canonicalize_path():
    windows_path = PureWindowsPath('relative\\path\\to\\file.pdf')
    posix_path = PurePosixPath('relative/path/to/file.pdf')

    win_key, win_filename = GoogleCloudStorage.canonicalize_path(windows_path)
    posix_key, posix_filename = GoogleCloudStorage.canonicalize_path(
        posix_path
    )

    assert win_key == 'relative/path/to/file.pdf'
    assert win_filename == 'file.pdf'
    assert posix_key == 'relative/path/to/file.pdf'
    assert posix_filename == 'file.pdf'


def test_delete_file_calls_client():
    storage = GoogleCloudStorage.__new__(GoogleCloudStorage)
    blob = MagicMock()
    storage._client = MagicMock()
    storage._client.blob.return_value = blob

    storage.delete_file(PurePosixPath("path/to/file.pdf"))

    storage._client.blob.assert_called_once_with("path/to/file.pdf")
    blob.delete.assert_called_once()


def test_canonicalize_tricky_path():
    tricky_posix_path = PurePosixPath('relative/path/to\\file.pdf')
    tricky_win_path = PureWindowsPath('relative/path/to\\file.pdf')

    posix_key, posix_filename = GoogleCloudStorage.canonicalize_path(
        tricky_posix_path
    )
    win_key, win_filename = GoogleCloudStorage.canonicalize_path(
        tricky_win_path
    )

    assert posix_key == 'relative/path/to\\file.pdf'
    assert posix_filename == 'to\\file.pdf'

    assert win_key == 'relative/path/to/file.pdf'
    assert win_filename == 'file.pdf'
