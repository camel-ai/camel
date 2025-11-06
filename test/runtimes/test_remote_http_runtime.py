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
import pytest

from camel.runtimes import RemoteHttpRuntime
from camel.toolkits import MathToolkit


@pytest.mark.skip(reason="Cannot run this test without a running server.")
def test_remote_http_runtime():
    runtime = (
        RemoteHttpRuntime("localhost")
        .add(MathToolkit().get_tools(), "camel.toolkits.MathToolkit")
        .build()
    )
    print("Waiting for runtime to be ready...")
    runtime.wait()
    print("Runtime is ready.")
    add, sub, mul = runtime.get_tools()

    assert add.func(1, 2) == 3
    assert sub.func(5, 3) == 2
    assert mul.func(2, 3) == 6

    assert runtime.docs == "http://localhost:8000/docs"
