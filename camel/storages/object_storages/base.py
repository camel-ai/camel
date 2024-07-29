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

from abc import ABC, abstractmethod
from pathlib import Path

from camel.loaders import File


class BaseObjectStorage(ABC):
    @abstractmethod
    def put_file(self, file_path: Path, file: File) -> None:
        r"""Put a file to the object storage.

        Args:
            file_path (Path): The path to the object in the storage.
            file: The file to be put.
        """

    @abstractmethod
    def get_file(self, file_path: Path) -> File:
        r"""Get a file from the object storage.

        Args:
            file_path (Path): The path to the object in the storage.

        Returns:
            File: The file object get from the storage.
        """

    @staticmethod
    @abstractmethod
    def canonicalize_path(file_path: Path) -> str:
        r"""Canonicalize the file path into the file key in the storage.

        Args:
            file_path (Path): The path to the object in the storage.

        Returns:
            str: The canonicalized file key.
        """
