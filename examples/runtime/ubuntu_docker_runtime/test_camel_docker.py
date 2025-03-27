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
import time

from colorama import Fore

from camel.runtime.ubuntu_docker_runtime import UbuntuDockerRuntime
from camel.toolkits import MathToolkit
from camel.utils import print_text_animated

# Set logging level to debug for more detailed information
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


def check_api_server(container):
    """Check API server status and configuration."""
    logger.info("Checking API server status...")

    # Check if API process is running
    _, ps_result = container.exec_run("ps aux | grep api.py")
    logger.info("Running processes:\n%s", ps_result.decode())

    # Check API endpoints
    _, curl_result = container.exec_run("curl -v http://localhost:8000/docs")
    logger.info("API documentation:\n%s", curl_result.decode())


def main():
    # Initialize runtime environment
    logger.info("Setting up Docker runtime...")
    runtime = UbuntuDockerRuntime(
        "my-camel:latest",
        ports={'8000/tcp': 8000},
        environment={"HOST": "0.0.0.0", "PORT": "8000"},
    )

    # Add math tools
    logger.info("Adding math tools...")
    runtime.add(MathToolkit().get_tools(), "camel.toolkits.MathToolkit")

    # Run test with context manager
    logger.info("Starting runtime context...")
    with runtime as r:
        print(Fore.YELLOW + "Waiting for runtime to start...\n")

        # Wait with progress indication
        for i in range(30):
            if r.ok:
                logger.info("Runtime is ready!")
                break
            logger.debug(f"Waiting... {i+1}/30 seconds")
            time.sleep(1)
        else:
            logger.error("Runtime failed to start")
            if hasattr(r, 'container') and r.container:
                check_api_server(r.container)
            return

        # Get and verify tools
        logger.info("Getting tools...")
        tools = r.get_tools()
        add, sub, mul = tools[:3]

        try:
            # Test math operations
            print(Fore.YELLOW + "Testing math operations...\n")

            # Test addition
            result = add.func(1, 2)
            print_text_animated(Fore.GREEN + f"Add 1 + 2: {result}\n")

            # Test subtraction
            result = sub.func(5, 3)
            print_text_animated(Fore.GREEN + f"Subtract 5 - 3: {result}\n")

            # Test multiplication
            result = mul.func(2, 3)
            print_text_animated(Fore.GREEN + f"Multiply 2 * 3: {result}\n")

        except Exception as e:
            print(Fore.RED + f"Error during execution: {e}")
            if hasattr(r, 'container') and r.container:
                check_api_server(r.container)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger.exception("Unexpected error occurred")
