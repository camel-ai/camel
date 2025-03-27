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
import sys
import time

from colorama import Fore, Style, init

from camel.runtime import UbuntuDockerRuntime

# Initialize colorama for cross-platform colored output
init()


def print_status(
    message: str, status: str = "INFO", color: str = Fore.BLUE
) -> None:
    r"""Print a formatted status message.

    Args:
        message: The message to display
        status: Status type (INFO, SUCCESS, ERROR, etc.)
        color: Color to use for the message
    """
    timestamp = time.strftime("%H:%M:%S")
    print(f"{color}[{timestamp}] {status}: {message}{Style.RESET_ALL}")


def main():
    r"""Main function to run the Ubuntu Docker runtime test."""
    try:
        # Step 1: Initialize runtime
        print_status(
            "Initializing Ubuntu Docker Runtime...", "SETUP", Fore.CYAN
        )
        runtime = UbuntuDockerRuntime(
            image="my-camel:latest",
            python_path="/usr/bin/python3",
            ports=0,
            environment={
                "HOST": "0.0.0.0",
            },
        )
        print_status("Runtime initialized successfully", "SUCCESS", Fore.GREEN)

        # Step 2: Build container
        print_status("Building Docker container...", "SETUP", Fore.CYAN)
        print_status(
            "This may take a few minutes on first run", "INFO", Fore.YELLOW
        )
        runtime.build()
        print_status("Container built successfully", "SUCCESS", Fore.GREEN)

        # Step 3: Execute role-playing test
        print_status("Starting role-playing test...", "TEST", Fore.MAGENTA)
        print_status(
            "Make sure you have set your ModelScope API key in "
            "test_docker_roleplaying.py",
            "IMPORTANT",
            Fore.YELLOW,
        )

        # Add a small delay for readability
        time.sleep(1)

        print_status(
            "Executing test_docker_roleplaying.py...", "RUN", Fore.BLUE
        )
        runtime.exec_python_file(
            local_file_path="./test_docker_roleplaying.py"
        )

    except FileNotFoundError as e:
        print_status(f"File not found: {e}", "ERROR", Fore.RED)
        sys.exit(1)
    except Exception as e:
        print_status(f"An error occurred: {e}", "ERROR", Fore.RED)
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_status("\nTest interrupted by user", "INFO", Fore.YELLOW)
        sys.exit(0)
