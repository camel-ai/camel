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
import urllib.request

from huggingface_hub import hf_hub_download
from huggingface_hub.utils._errors import RepositoryNotFoundError

from camel.logger import get_logger

REPO_ROOT = os.path.realpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "../..")
)

logger = get_logger(__name__)


def download_data():
    logger.info("Downloading...")

    data_dir = os.path.join(REPO_ROOT, "datasets/")

    os.makedirs(data_dir, exist_ok=True)

    try:
        hf_hub_download(
            repo_id="camel-ai/ai_society",
            repo_type="dataset",
            filename="ai_society_chat.zip",
            local_dir=data_dir,
            local_dir_use_symlinks=False,
        )

        hf_hub_download(
            repo_id="camel-ai/code",
            repo_type="dataset",
            filename="code_chat.zip",
            local_dir=data_dir,
            local_dir_use_symlinks=False,
        )
    except RepositoryNotFoundError:
        for name in ("ai_society_chat.zip", "code_chat.zip"):
            data_url = (
                "https://storage.googleapis.com/"
                f"camel-bucket/datasets/private/{name}"
            )
            file_path = os.path.join(data_dir, os.path.split(data_url)[1])
            urllib.request.urlretrieve(data_url, file_path)

    data_url = (
        "https://storage.googleapis.com/"
        "camel-bucket/datasets/private/misalignment.zip"
    )
    file_path = os.path.join(data_dir, os.path.split(data_url)[1])
    urllib.request.urlretrieve(data_url, file_path)

    logger.info("Download done")


if __name__ == "__main__":
    download_data()
