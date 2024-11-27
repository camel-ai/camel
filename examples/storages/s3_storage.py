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

from pathlib import Path

from camel.storages.object_storages import AmazonS3Storage


def get_file():
    s3_storage = AmazonS3Storage(bucket_name="camel-ai-bucket")
    print(s3_storage._get_file(Path("folder1/example.txt")))


def upload_file():
    s3_storage = AmazonS3Storage(bucket_name="camel-ai-bucket")
    s3_storage.upload_file(
        local_file_path=Path("./redis_storage.py"),
        s3_file_path=Path("folder1/redis_storage.py"),
    )


if __name__ == "__main__":
    upload_file()
