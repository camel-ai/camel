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

from camel.runtimes import DockerRuntime
from camel.toolkits import CodeExecutionToolkit, MathToolkit


@pytest.mark.skip(reason="Need Docker environment to run this test.")
def test_docker_runtime():
    runtime = (
        DockerRuntime("xukunliu/camel")  # change to your own docker image
        .add(MathToolkit().get_tools(), "camel.toolkits.MathToolkit")
        .add(
            CodeExecutionToolkit().get_tools(),
            "camel.toolkits.CodeExecutionToolkit",
            dict(verbose=True),
        )
    )

    with (
        runtime as r
    ):  # using with statement to automatically close the runtime
        print("Waiting for runtime to be ready...")
        r.wait()
        print("Runtime is ready.")

        tools = r.get_tools()

        assert len(tools) == 4

        add, sub, mul = tools[:3]

        assert add.func(1, 2) == 3
        assert sub.func(5, 3) == 2
        assert mul.func(2, 3) == 6

        assert add.func(a=1, b=2) == 3
        assert sub.func(a=5, b=3) == 2
        assert mul.func(a=2, b=3) == 6

        assert r.docs == "http://localhost:8000/docs"
