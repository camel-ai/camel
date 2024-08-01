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
from pathlib import PurePath, PurePosixPath, PureWindowsPath
from unittest.mock import MagicMock, patch

import pytest

from camel.loaders.base_io import TxtFile
from camel.storages.object_storages import S3Storage


@pytest.fixture
def mock_instance():
    with patch(
        "camel.storages.object_storages.amazon_s3.boto3.client"
    ) as mock_create_client:
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_client.head_bucket.return_value = None

        response_body = MagicMock()
        response_body.read.return_value = b"file content"
        mock_client.get_object.return_value = {"Body": response_body}

        yield S3Storage(bucket_name='mock-bucket')


def test_canonicalize_path():
    windows_path = PureWindowsPath('relative\\path\\to\\file.pdf')
    posix_path = PurePosixPath('relative/path/to/file.pdf')

    windows_key = S3Storage.canonicalize_path(windows_path)
    posix_key = S3Storage.canonicalize_path(posix_path)

    assert windows_key == 'relative/path/to/file.pdf'
    assert posix_key == 'relative/path/to/file.pdf'


def test_get_file(mock_instance: S3Storage):
    file = mock_instance.get_file(PurePath('file.txt'))
    assert file.name == 'file.txt'
    assert isinstance(file, TxtFile)
    assert file.raw_bytes == b'file content'


def test_not_accessible_bucket():
    with pytest.raises(PermissionError):
        S3Storage(bucket_name='amazon')
