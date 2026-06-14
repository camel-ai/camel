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
"""
Test that the following decorators are correctly applied to camel.storages:
@api_keys_required - should raise ValueError if value is missing
@dependencies_required - should raise ImportError if package/module is missing
"""

from unittest.mock import patch

import pytest

fake_api_key = "fake_api_key"


def _mock_missing(module_name: str):
    """Patch is_module_available to return False for a specific module."""
    original = __import__(
        'camel.utils.commons', fromlist=['is_module_available']
    ).is_module_available

    def fake(m):
        if m == module_name:
            return False
        return original(m)

    return patch('camel.utils.commons.is_module_available', side_effect=fake)


def test_redis_storage_missing_dependency():
    from camel.storages import RedisStorage

    with _mock_missing('redis'):
        with pytest.raises(ImportError, match="redis"):
            RedisStorage(sid="test")


def test_mem0_storage_missing_dependency():
    from camel.storages.key_value_storages import Mem0Storage

    with _mock_missing('mem0'):
        with pytest.raises(ImportError, match="mem0"):
            Mem0Storage(agent_id="test_agent", api_key=fake_api_key)


def test_amazon_s3_storage_missing_dependency():
    from camel.storages.object_storages import AmazonS3Storage

    with _mock_missing('botocore'):
        with pytest.raises(ImportError, match="botocore"):
            AmazonS3Storage(bucket_name="test-bucket")


def test_azure_blob_storage_missing_dependency():
    from camel.storages.object_storages import AzureBlobStorage

    with _mock_missing('azure.storage.blob'):
        with pytest.raises(ImportError, match=r"azure\.storage\.blob"):
            AzureBlobStorage(
                storage_account_name="test-account",
                container_name="test-container",
            )


def test_google_cloud_storage_missing_dependency():
    from camel.storages.object_storages import GoogleCloudStorage

    with _mock_missing('google.cloud.storage'):
        with pytest.raises(ImportError, match=r"google\.cloud\.storage"):
            GoogleCloudStorage(bucket_name="test-bucket")
