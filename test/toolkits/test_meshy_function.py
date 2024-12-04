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
import time

import pytest

from camel.toolkits import MeshyToolkit


@pytest.fixture
def meshy_toolkit():
    api_key = os.getenv('MESHY_API_KEY')
    if not api_key:
        pytest.skip("MESHY_API_KEY not found in environment variables")
    return MeshyToolkit()


def test_generate_3d_preview_live(meshy_toolkit):
    response = meshy_toolkit.generate_3d_preview(
        prompt="A simple cube",
        art_style="realistic",
        negative_prompt="low quality",
    )
    assert 'result' in response
    assert isinstance(response['result'], str)
    return response['result']


def test_get_task_status_live(meshy_toolkit):
    preview_id = test_generate_3d_preview_live(meshy_toolkit)
    max_attempts = 10
    attempts = 0

    while attempts < max_attempts:
        status_response = meshy_toolkit.get_task_status(preview_id)
        assert 'status' in status_response

        if status_response['status'] == 'SUCCEEDED':
            break

        time.sleep(10)  # Wait 10 seconds between checks
        attempts += 1

    assert attempts < max_attempts, "Preview generation timed out"
    assert status_response['status'] == 'SUCCEEDED'


def test_refine_3d_model_live(meshy_toolkit):
    preview_id = test_generate_3d_preview_live(meshy_toolkit)

    # Wait for preview to complete
    max_attempts = 10
    attempts = 0
    while attempts < max_attempts:
        status = meshy_toolkit.get_task_status(preview_id)
        if status['status'] == 'SUCCEEDED':
            break
        time.sleep(10)
        attempts += 1

    assert attempts < max_attempts, "Preview generation timed out"

    # Test refine
    refine_response = meshy_toolkit.refine_3d_model(preview_id)
    assert 'result' in refine_response
    assert isinstance(refine_response['result'], str)
