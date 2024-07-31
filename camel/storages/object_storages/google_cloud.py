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
from pathlib import PurePath

from google.auth.exceptions import InvalidOperation
from google.cloud import storage

from camel.loaders import File
from camel.storages.object_storages.base import BaseObjectStorage


class GoogleCloudStorage(BaseObjectStorage):
    r"""A class to connect to Google Cloud Storage. It will connect to one
    bucket in the storage account.

    Note that Google Cloud Storage does not support api key authentication.
    Therefore, before using this class, you need to log in with gcloud command
    line tool and save the credentials first.

    Args:
        bucket_name (str): The name of the bucket.
        create_if_not_exists (bool, optional): Whether to create the bucket if
            it does not exist. Defaults to True.
        anonymous (bool, optional): Whether to use anonymous access. Defaults
            to False.

    References:
        https://cloud.google.com/storage

        https://cloud.google.com/docs/authentication/api-keys
    """

    def __init__(
        self,
        bucket_name: str,
        create_if_not_exists: bool = True,
        anonymous: bool = False,
    ) -> None:
        self.create_if_not_exists = create_if_not_exists

        if anonymous:
            client = storage.Client.create_anonymous_client()
        else:
            client = storage.Client()
        self._client = client.bucket(bucket_name)

        self._prepare_and_check()

    def _prepare_and_check(self) -> None:
        try:
            exists = self._client.exists()
            if not exists and self.create_if_not_exists:
                self._client.create()
            elif not exists:
                raise FileNotFoundError(
                    f"Failed to access bucket {self._client.name}: Not found."
                )
        except InvalidOperation:
            raise PermissionError(
                f"Failed to access bucket {self._client.name}: No permission."
            )

    def _put_file(self, file_key: str, file: File) -> None:
        self._client.blob(file_key).upload_from_bytes(file.raw_bytes)

    def _get_file(self, file_key: str, filename: str) -> File:
        raw_bytes = self._client.get_blob(file_key).download_as_bytes()
        return File.create_file_from_raw_bytes(raw_bytes, filename)

    def upload_file(
        self, local_file_path: PurePath, gcloud_file_path: PurePath
    ) -> None:
        r"""Upload a local file to the Google Cloud Storage bucket.

        Args:
            local_file_path (PurePath): The path to the local file to be
                uploaded.
            gcloud_file_path (PurePath): The path to the object in the Google
                Cloud Storage bucket.
        """
        file_key = self.canonicalize_path(gcloud_file_path)
        self._client.blob(file_key).upload_from_filename(local_file_path)

    def download_file(
        self, local_file_path: PurePath, gcloud_file_path: PurePath
    ) -> None:
        r"""Download a file from the Google Cloud Storage bucket to the local
        system.

        Args:
            local_file_path (PurePath): The path to the local file to be saved.
            gcloud_file_path (PurePath): The path to the object in the S3
            bucket.
        """
        file_key = self.canonicalize_path(gcloud_file_path)
        self._client.get_blob(file_key).download_to_filename(local_file_path)

    @staticmethod
    def canonicalize_path(file_path: PurePath) -> str:
        return file_path.as_posix()
