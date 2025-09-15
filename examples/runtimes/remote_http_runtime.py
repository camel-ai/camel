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
from camel.runtimes import RemoteHttpRuntime
from camel.toolkits import MathToolkit

if __name__ == "__main__":
    runtime = (
        RemoteHttpRuntime("localhost")
        .add(MathToolkit().get_tools(), "camel.toolkits.MathToolkit")
        .build()
    )
    print("Waiting for runtime to be ready...")
    runtime.wait()
    print("Runtime is ready.")
    add, sub, mul = runtime.get_tools()[:3]
    print(f"Add 1 + 2: {add.func(1, 2)}")
    print(f"Subtract 5 - 3: {sub.func(5, 3)}")
    print(f"Multiply 2 * 3: {mul.func(2, 3)}")

    print("Documents: ", runtime.docs)
    # you can open this url in browser to see the API Endpoints
    # before the runtime is stopped.
    # time.sleep(60)

    # call runtime.stop() if you want to stop the runtime manually
    # otherwise it will be stopped automatically when the program ends


"""
Waiting for runtime to be ready...
Runtime is ready.
Add 1 + 2: 3
Subtract 5 - 3: 2
Multiply 2 * 3: 6
Documents:  http://localhost:8000/docs
"""
