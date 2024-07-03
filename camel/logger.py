# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========


import logging
import os
import sys

# Create a private logger
_logger = logging.getLogger('camel')
_logging_disabled = False


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
        _logger.info("Camel library logging has been configured.")
    else:
        _logger.debug("Existing logger configuration found, using that.")


def disable_logging():
    global _logging_disabled
    _logging_disabled = True
    _logger.setLevel(logging.CRITICAL + 1)
    _logger.addHandler(logging.NullHandler())


def enable_logging():
    global _logging_disabled
    _logging_disabled = False
    _configure_library_logging()


def set_log_level(level):
    _logger.setLevel(level)


# Function to get a logger for a specific module
def get_logger(name):
    return logging.getLogger(f'camel.{name}')
