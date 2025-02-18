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

import time
from typing import Optional

from camel.toolkits.base import BaseToolkit
from camel.utils import with_timeout


# Example 1: Basic function with timeout
@with_timeout(1.0)
def basic_function() -> str:
    r"""A basic function with a 1-second timeout."""
    time.sleep(0.5)  # Simulating some work
    return "Basic function completed successfully!"


# Example 2: Function that exceeds timeout
@with_timeout(1.0)
def slow_function() -> str:
    r"""A slow function that will exceed the timeout."""
    time.sleep(2.0)  # This will exceed the timeout
    return "This message will never be returned"


# Example 3: Class with configurable timeout
class TimeoutExample:
    def __init__(self, timeout: Optional[float] = None):
        self.timeout = timeout

    @with_timeout()  # Uses instance timeout
    def instance_timeout_method(self) -> str:
        r"""Method using the instance's timeout value."""
        time.sleep(0.5)
        return "Instance timeout method completed!"

    @with_timeout(0.1)  # Uses decorator-specific timeout
    def decorator_timeout_method(self) -> str:
        r"""Method using the decorator's timeout value."""
        time.sleep(0.5)
        return "This will timeout"


# Example 4: Toolkit with timeout
class TimeoutToolkit(BaseToolkit):
    def __init__(self, timeout: Optional[float] = None):
        super().__init__(timeout=timeout)

    @with_timeout()
    def fast_operation(self) -> str:
        r"""A fast operation that completes within timeout."""
        time.sleep(0.1)
        return "Fast operation completed!"

    @with_timeout()
    def slow_operation(self) -> str:
        r"""A slow operation that exceeds timeout."""
        time.sleep(1.0)
        return "Slow operation completed!"


def main():
    # Example 1: Basic function
    print("\nExample 1: Basic function")
    print(basic_function())

    # Example 2: Slow function
    print("\nExample 2: Slow function")
    print(slow_function())

    # Example 3: Class with timeout
    print("\nExample 3: Class with timeout")
    example = TimeoutExample(timeout=0.2)
    print(example.instance_timeout_method())
    print(example.decorator_timeout_method())

    # Example 4: Toolkit
    print("\nExample 4: Toolkit with timeout")
    toolkit = TimeoutToolkit(timeout=0.5)
    print(toolkit.fast_operation())
    print(toolkit.slow_operation())


if __name__ == "__main__":
    main()

"""
===============================================================================
Example 1: Basic function
Basic function completed successfully!

Example 2: Slow function
Function `slow_function` execution timed out, exceeded 1.0 seconds.

Example 3: Class with timeout
Function `instance_timeout_method` execution timed out, exceeded 0.2 seconds.
Function `decorator_timeout_method` execution timed out, exceeded 0.1 seconds.

Example 4: Toolkit with timeout
Fast operation completed!
Function `slow_operation` execution timed out, exceeded 0.5 seconds.
===============================================================================
"""
