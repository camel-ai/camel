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
import os
from pathlib import PurePath
from typing import Optional

from azure.core.exceptions import ClientAuthenticationError
from azure.storage.blob import ContainerClient
from colorama import Fore

from camel.loaders import File
from camel.storages.object_storages.base import BaseObjectStorage


class AzureBlobStorage(BaseObjectStorage):
    """A class to connect to Azure Blob Storage. It will connect to one
    container in the storage account.

    Args:
        storage_account_name (str): The name of the storage account.
        container_name (str): The name of the container.
        access_key (Optional[str], optional): The access key of the storage
            account. Defaults to None.
    """

    def __init__(
        self,
        storage_account_name: str,
        container_name: str,
        create_if_not_exists: bool = True,
        access_key: Optional[str] = None,
    ) -> None:
        access_key = access_key or os.getenv("AZURE_ACCESS_KEY")
        self._create_if_not_exists = create_if_not_exists

        if not access_key:
            print(
                f"{Fore.YELLOW}Warning: AZURE_ACCESS_KEY not provided."
                f"{Fore.RESET}"
            )
            # make all the empty values None
            access_key = None

        self._client = ContainerClient(
            account_url="https://"
            f"{storage_account_name}.blob.core.windows.net",
            credential=access_key,
            container_name=container_name,
        )

        self._prepare_and_check()

    def _prepare_and_check(self) -> None:
        try:
            exists = self._client.exists()
            if not exists and self._create_if_not_exists:
                self._client.create_container()
                print(
                    f"{Fore.GREEN}Container {self._client.container_name} "
                    f"not found. Automatically created.{Fore.RESET}"
                )
            elif not exists:
                raise FileNotFoundError(
                    f"Failed to access container {self._client.container_name}"
                    f": Not found."
                )
        except ClientAuthenticationError:
            raise PermissionError(
                f"Failed to access container {self._client.container_name}: "
                f"No permission."
            )

    def _put_file(self, file_key: str, file: File) -> None:
        self._client.upload_blob(
            name=file_key, data=file.raw_bytes, overwrite=True
        )

    def _get_file(self, file_key: str, filename: str) -> File:
        raw_bytes = self._client.download_blob(file_key).readall()
        file = File.create_file_from_raw_bytes(raw_bytes, filename)
        return file

    @staticmethod
    def canonicalize_path(file_path: PurePath) -> str:
        # for Azure, both slash and backslash will be treated as separator
        return str(file_path)
