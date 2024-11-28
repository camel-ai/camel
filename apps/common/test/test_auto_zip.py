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

from apps.common.auto_zip import AutoZip

REPO_ROOT = os.path.realpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../..")
)


def test_dict():
    path = os.path.join(REPO_ROOT, "apps/common/test/test_archive_1.zip")
    zp = AutoZip(path, ".txt")

    d = zp.as_dict()
    assert isinstance(d, dict)
    assert len(d) == 3

    d = zp.as_dict(include_zip_name=True)
    assert isinstance(d, dict)
    assert len(d) == 3
