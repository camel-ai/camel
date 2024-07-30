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
from pathlib import PurePath

from camel.loaders import File


class BaseObjectStorage(ABC):
    @abstractmethod
    def _put_file(self, file_key: str, file: File) -> None:
        r"""Put a file to the object storage.

        Args:
            file_key (str): The path to the object in the storage.
            file (File): The file to be put.
        """

    @abstractmethod
    def _get_file(self, file_key: str, filename: str) -> File:
        r"""Get a file from the object storage.

        Args:
            file_key (str): The path to the object in the storage.
            filename (str): The name of the file.

        Returns:
            File: The file object get from the storage.
        """

    def put_file(self, file_path: PurePath, file: File) -> None:
        r"""Put a file to the object storage.

        Args:
            file_path (PurePath): The path to the object in the storage.
            file (File): The file to be put.
        """
        file_key = self.canonicalize_path(file_path)
        self._put_file(file_key, file)

    def get_file(self, file_path: PurePath) -> File:
        r"""Get a file from the object storage.

        Args:
            file_path (PurePath): The path to the object in the storage.

        Returns:
            File: The file object get from the storage.
        """
        file_key = self.canonicalize_path(file_path)
        filename = file_path.name
        return self._get_file(file_key, filename)

    @staticmethod
    @abstractmethod
    def canonicalize_path(file_path: PurePath) -> str:
        r"""Canonicalize the file path into the file key in the storage.

        Args:
            file_path (PurePath): The path to the object in the storage.

        Returns:
            str: The canonicalized file key.
        """
