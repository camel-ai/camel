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

import logging
import sys

from colorama import init

from camel.runtime import UbuntuDockerRuntime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize colorama for cross-platform colored output
init()


def main():
    """Main function to test the Ubuntu Docker runtime."""
    try:
        # Initialize runtime
        runtime = UbuntuDockerRuntime(
            image="my-camel:latest",
            python_path="/usr/bin/python3",
            ports=0,
            environment={
                "HOST": "0.0.0.0",
            },
        )

        # Build and verify container
        logger.info("Building Docker container...")
        runtime.build()
        logger.info("Container built successfully")

        # Test basic functionality
        logger.info("Testing basic functionality...")
        result = runtime.exec_python_file(
            local_file_path="./test_docker_roleplaying.py"
        )
        logger.info("Test completed successfully")

        return result

    except Exception as e:
        logger.error("Test failed: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
