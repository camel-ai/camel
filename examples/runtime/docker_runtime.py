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
from camel.runtimes import DockerRuntime
from camel.toolkits import CodeExecutionToolkit, MathToolkit

if __name__ == "__main__":
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

        add, sub, mul = tools[:3]
        code_exec = tools[3]

        # without kwargs
        print(f"Add 1 + 2: {add.func(1, 2)}")
        print(f"Subtract 5 - 3: {sub.func(5, 3)}")
        print(f"Multiply 2 * 3: {mul.func(2, 3)}")
        print(f"Execute code: {code_exec.func('1 + 2')}")

        # with kwargs
        print(f"Add 1 + 2: {add.func(a=1, b=2)}")
        print(f"Subtract 5 - 3: {sub.func(a=5, b=3)}")
        print(f"Multiply 2 * 3: {mul.func(a=2, b=3)}")
        print(f"Execute code: {code_exec.func(code='1 + 2')}")

        print("Documents: ", r.docs)
        # you can open this url in browser to see the API Endpoints
        # before the runtime is stopped.

    # you can also use the runtime without the with statement
    # runtime.build()
    # runtime.stop()

"""
Add 1 + 2: 3
Subtract 5 - 3: 2
Multiply 2 * 3: 6
Execute code: Executed the code below:
```py
1 + 2
```
> Executed Results:
3
Documents:  http://localhost:8000/docs
"""
