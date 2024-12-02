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
import os
import sys

# Create a private logger
_logger = logging.getLogger('camel')
_logging_disabled = False


class PrintLogger(logging.Logger):
    def _log(self, level, msg, args, **kwargs):
        if args:
            msg = msg + ' ' + ' '.join(str(arg) for arg in args)
        super()._log(level, msg, (), **kwargs)


def _configure_library_logging():
    global _logging_disabled
    if _logging_disabled:
        return

    if not logging.root.handlers and not _logger.handlers:
        logging.basicConfig(
            level=os.environ.get('LOGLEVEL', 'INFO').upper(),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            stream=sys.stdout,
        )

        logging.setLoggerClass(PrintLogger)

        _logger.info("Camel library logging has been configured.")
    else:
        _logger.debug("Existing logger configuration found, using that.")


def disable_logging():
    """
    Disable all logging for the Camel library.

    This function sets the log level to a value higher than CRITICAL,
    effectively disabling all log messages, and adds a NullHandler to
    suppress any potential warnings about no handlers being found.
    """
    global _logging_disabled
    _logging_disabled = True
    _logger.setLevel(logging.CRITICAL + 1)
    _logger.addHandler(logging.NullHandler())


def enable_logging():
    """
    Enable logging for the Camel library.

    This function re-enables logging if it was previously disabled,
    and configures the library logging using the default settings.
    If the logging is already configured,
        this function does not change its configuration.
    """
    global _logging_disabled
    _logging_disabled = False
    _configure_library_logging()


def set_log_level(level):
    """
    Set the logging level for the Camel library.

    Args:
        level: The logging level to set. This can be a string (e.g., 'INFO')
               or a logging level constant (e.g., logging.INFO, logging.DEBUG).
               See https://docs.python.org/3/library/logging.html#levels

    Raises:
        ValueError: If the provided level is not a valid logging level.
    """
    valid_levels = ['NOTSET', 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    if isinstance(level, str):
        if level.upper() not in valid_levels:
            raise ValueError(
                f"Invalid logging level."
                f" Choose from: {', '.join(valid_levels)}"
            )
        level = level.upper()
    elif not isinstance(level, int):
        raise ValueError(
            "Logging level must be an option from the logging module."
        )

    _logger.setLevel(level)


def get_logger(name):
    """
    Get a logger with the specified name, prefixed with 'camel.'.

    Args:
        name (str): The name to be appended to 'camel.' to create the logger.

    Returns:
        logging.Logger: A logger instance with the name 'camel.{name}'.
    """
    return logging.getLogger(f'camel.{name}')


_configure_library_logging()
