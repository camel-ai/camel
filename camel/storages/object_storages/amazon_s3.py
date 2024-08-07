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
from pathlib import Path, PurePath
from typing import Optional, Tuple

from colorama import Fore

from camel.loaders import File
from camel.storages.object_storages.base import BaseObjectStorage


class AmazonS3Storage(BaseObjectStorage):
    r"""A class to connect with AWS S3 object storage to put and get objects
    from one S3 bucket.

    Args:
        bucket_name (str): The name of the S3 bucket.
        create_if_not_exists (bool, optional): Whether to create the bucket if
            it does not exist. Defaults to True.
        access_key_id (Optional[str], optional): The AWS access key ID,
            can be skipped if logged in with AWS CLI. Defaults to None.
        secret_access_key (Optional[str], optional): The AWS secret access key,
            can be skipped if logged in with AWS CLI. Defaults to None.

    References:
        https://aws.amazon.com/pm/serv-s3
    """

    def __init__(
        self,
        bucket_name: str,
        create_if_not_exists: bool = True,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
    ) -> None:
        self._bucket_name = bucket_name
        self._create_if_not_exists = create_if_not_exists

        aws_key_id = access_key_id or os.getenv("AWS_ACCESS_KEY_ID")
        aws_secret_key = secret_access_key or os.getenv(
            "AWS_SECRET_ACCESS_KEY"
        )
        if not all([aws_key_id, aws_secret_key]):
            print(
                f"{Fore.YELLOW}Warning: AWS access key not configured. "
                f"Local credentials will be used.{Fore.RESET}"
            )
            # make all the empty values None
            aws_key_id = None
            aws_secret_key = None

        import boto3

        self._client = boto3.client(
            "s3",
            aws_access_key_id=aws_key_id,
            aws_secret_access_key=aws_secret_key,
        )

        self._prepare_and_check()

    @staticmethod
    def canonicalize_path(file_path: PurePath) -> Tuple[str, str]:
        r"""Canonicalize the path for the S3 bucket.

        Args:
            file_path (PurePath): The path to be canonicalized.

        Returns:
            Tuple[str, str]: The canonicalized file key and file name.
        """
        return file_path.as_posix(), file_path.name

    def _prepare_and_check(self) -> None:
        r"""Prepare the bucket for future use, and also check if the bucket is
        accessible.
        """
        from botocore.exceptions import ClientError

        try:
            self._client.head_bucket(Bucket=self._bucket_name)
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '403':
                raise PermissionError(
                    f"Failed to access bucket {self._bucket_name}: "
                    f"No permission."
                )
            elif error_code == '404':
                if self._create_if_not_exists:
                    self._client.create_bucket(Bucket=self._bucket_name)
                    print(
                        f"{Fore.GREEN}Bucket {self._bucket_name} not found. "
                        f"Automatically created.{Fore.RESET}"
                    )
                else:
                    raise FileNotFoundError(
                        f"Failed to access bucket {self._bucket_name}: Not "
                        f"found."
                    )
            else:
                raise e

    def _put_file(self, file_key: str, file: File) -> None:
        r"""Upload a file to the S3 bucket.

        Args:
            file_key (str): The path to the object in the S3 bucket.
            file (File): The file to be uploaded.
        """
        self._client.put_object(
            Bucket=self._bucket_name, Key=file_key, Body=file.raw_bytes
        )

    def _get_file(self, file_key: str, filename: str) -> File:
        r"""Download a file from the S3 bucket.

        Args:
            file_key (str): The path to the object in the S3 bucket.
            filename (str): The name of the file.

        Returns:
            File: The object from the S3 bucket.
        """
        response = self._client.get_object(
            Bucket=self._bucket_name, Key=file_key
        )
        raw_bytes = response["Body"].read()
        return File.create_file_from_raw_bytes(raw_bytes, filename)

    def _upload_file(
        self, local_file_path: Path, remote_file_key: str
    ) -> None:
        r"""Upload a local file to the S3 bucket.

        Args:
            local_file_path (Path): The path to the local file to be
                uploaded.
            remote_file_key (str): The path to the object in the S3 bucket.
        """
        self._client.upload_file(
            Bucket=self._bucket_name,
            Key=remote_file_key,
            Filename=local_file_path,
        )

    def _download_file(
        self,
        local_file_path: Path,
        remote_file_key: str,
    ) -> None:
        pass
        r"""Download a file from the S3 bucket to the local system.

        Args:
            local_file_path (Path): The path to the local file to be saved.
            remote_file_key (str): The key of the object in the S3 bucket.
        """
        self._client.download_file(
            Bucket=self._bucket_name,
            Key=remote_file_key,
            Filename=local_file_path,
        )

    def _object_exists(self, file_key: str) -> bool:
        try:
            self._client.head_object(Bucket=self._bucket_name, Key=file_key)
            return True
        except self._client.exceptions.ClientError:
            return False
