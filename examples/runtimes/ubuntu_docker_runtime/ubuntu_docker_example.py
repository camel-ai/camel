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
import sys

from camel.runtimes import UbuntuDockerRuntime


def main():
    r"""Main function to demonstrate Ubuntu Docker Runtime."""
    try:
        # Get OpenAI API key from environment
        openai_api_key = os.environ.get("OPENAI_API_KEY")

        # Initialize the runtime
        runtime = UbuntuDockerRuntime(
            image="my-camel:latest",
            python_path="/usr/bin/python3",
            ports=0,
            environment={
                "HOST": "0.0.0.0",
                "OPENAI_API_KEY": openai_api_key,  # Pass API key to container
            },
        )

        runtime.build()
        script_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        script_path = script_dir + "/ai_society/role_playing.py"
        runtime.exec_python_file(local_file_path=script_path)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
