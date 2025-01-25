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

import signal
from functools import wraps
from typing import List, Optional, Union

from camel.logger import get_logger
from camel.toolkits import FunctionTool
from camel.utils import AgentOpsMeta

# Get logger for toolkits
logger = get_logger("toolkits")


def timeout_handler(signum, frame):
    raise TimeoutError("Operation timed out")


def with_timeout(seconds: Optional[int] = None):
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Get timeout from instance or default
            timeout = self.timeout if hasattr(self, 'timeout') else seconds

            # If timeout is 0 or None, run without timeout
            if timeout is None or timeout <= 0:
                return func(self, *args, **kwargs)

            # Set the signal handler and a timeout
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(timeout)
            try:
                result = func(self, *args, **kwargs)
            finally:
                # Disable the alarm
                signal.alarm(0)
            return result

        return wrapper

    return decorator


class BaseToolkit(metaclass=AgentOpsMeta):
    r"""Base class for toolkits.

    Args:
        timeout (Optional[int]): Default timeout in seconds for toolkit
            operations. If `None`, uses `DEFAULT_TIMEOUT`. Set to `0` to
            disable timeout.
    """

    # Default timeout in seconds for toolkit operations
    DEFAULT_TIMEOUT = 180

    def __init__(self, timeout: Optional[int] = None):
        r"""Initialize the toolkit with optional timeout setting."""
        self.timeout = timeout if timeout is not None else self.DEFAULT_TIMEOUT

    @with_timeout()
    def get_tools(self) -> Union[List[FunctionTool], str]:
        r"""Returns a list of FunctionTool objects representing the
        functions in the toolkit. Will timeout based on the instance timeout
        setting.

        This method can be overridden by subclasses, but it's recommended to
        implement _get_tools_impl() instead to get timeout and error handling.

        Returns:
            Union[List[FunctionTool], str]: Either a list of FunctionTool
                objects representing the functions in the toolkit, or an error
                message string if an error occurred.
        """
        try:
            # First try to call _get_tools_impl if it's implemented
            if hasattr(self, '_get_tools_impl'):
                return self._get_tools_impl()
            # Otherwise, this must be overridden by the subclass
            raise NotImplementedError(
                "Subclasses must either implement _get_tools_impl() or"
                " override get_tools()"
            )
        except TimeoutError:
            timeout_msg = (
                f"Toolkit operation timed out after {self.timeout} seconds"
            )
            logger.error(timeout_msg)
            return f"Error: {timeout_msg}"
        except Exception as e:
            error_msg = f"Error retrieving tools: {e!s}"
            logger.error(error_msg, exc_info=True)
            return f"Error: {error_msg}"

    def _get_tools_impl(self) -> List[FunctionTool]:
        r"""Internal method to implement tool retrieval.

        This method can be implemented by subclasses as an alternative to
        overriding get_tools(). If implemented, this method will be called
        by get_tools() with timeout and error handling.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects
                representing the functions in the toolkit.

        Raises:
            NotImplementedError: If neither this method nor get_tools()
                is implemented by the subclass.
        """
        raise NotImplementedError(
            "Subclasses must either implement _get_tools_impl() or override"
            " get_tools()"
        )
