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

import gradio as gr
import pytest

from apps.data_explorer.data_explorer import construct_blocks, parse_arguments
from apps.data_explorer.loader import REPO_ROOT


@pytest.mark.skip(reason="Skipping this test temporarily")
def test_app():
    test_data_url = (
        "https://storage.googleapis.com/camel-bucket/datasets/test/DATA.zip"
    )
    data_dir = os.path.join(REPO_ROOT, "datasets_test")
    test_file_path = os.path.join(data_dir, os.path.split(test_data_url)[1])
    os.makedirs(data_dir, exist_ok=True)
    urllib.request.urlretrieve(test_data_url, test_file_path)

    blocks = construct_blocks(data_dir, None)

    assert isinstance(blocks, gr.Blocks)


def test_utils():
    args = parse_arguments()
    assert args is not None
