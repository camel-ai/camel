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
from pathlib import PurePosixPath, PureWindowsPath

import pytest

from camel.storages.object_storages import AzureBlobStorage


def test_canonicalize_path():
    windows_path = PureWindowsPath('relative\\path\\to\\file.pdf')
    posix_path = PurePosixPath('relative/path/to/file.pdf')

    windows_key, win_filename = AzureBlobStorage.canonicalize_path(
        windows_path
    )
    posix_key, posix_filename = AzureBlobStorage.canonicalize_path(posix_path)

    assert windows_key == 'relative/path/to/file.pdf'
    assert win_filename == 'file.pdf'

    assert posix_key == 'relative/path/to/file.pdf'
    assert posix_filename == 'file.pdf'


def test_canonicalize_tricky_path():
    tricky_posix_path = PurePosixPath('relative/path/to\\file.pdf')
    tricky_win_path = PureWindowsPath('relative/path/to\\file.pdf')

    with pytest.raises(ValueError):
        AzureBlobStorage.canonicalize_path(tricky_posix_path)

    win_key, win_filename = AzureBlobStorage.canonicalize_path(tricky_win_path)

    assert win_key == 'relative/path/to/file.pdf'
    assert win_filename == 'file.pdf'
