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
import pytest

from camel.runtimes import DockerRuntime
from camel.toolkits import CodeExecutionToolkit, TerminalToolkit


@pytest.mark.skip(reason="Need Docker environment to run this test.")
def test_shared_runtime_filesystem():
    """Test that multiple toolkits share the same filesystem in a runtime."""
    runtime = (
        DockerRuntime("camel-multi-toolkit:latest", port=8000)
        .add(TerminalToolkit().get_tools(), "camel.toolkits.TerminalToolkit")
        .add(
            CodeExecutionToolkit().get_tools(),
            "camel.toolkits.CodeExecutionToolkit",
            arguments={"verbose": True},
        )
        .build()
    )

    with runtime as r:
        r.wait(timeout=30)
        tools = r.get_tools()

        # find tools by name
        shell_exec = next(
            t for t in tools if t.get_function_name() == "shell_exec"
        )
        execute_code = next(
            t for t in tools if t.get_function_name() == "execute_code"
        )

        # terminal creates a file
        shell_exec.func(
            id="test1",
            command="echo 'shared content' > /workspace/shared.txt",
            block=True,
        )

        # code execution reads the same file
        result = execute_code.func(
            code="print(open('/workspace/shared.txt').read().strip())"
        )
        assert "shared content" in result
