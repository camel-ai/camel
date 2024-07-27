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
from io import BytesIO
from pathlib import Path
from typing import Optional

import boto3
from colorama import Fore

from camel.loaders import File, read_file
from camel.storages.object_storages.base import BaseObjectStorage


class S3Storage(BaseObjectStorage):
    """A class to connect with AWS S3 object storage to put and get objects
    from one S3 bucket.

    Args:
        bucket_name (str): The name of the S3 bucket.
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
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
    ) -> None:
        self._bucket_name = bucket_name

        aws_key_id = access_key_id or os.getenv("AWS_ACCESS_KEY_ID")
        aws_secret_key = secret_access_key or os.getenv(
            "AWS_SECRET_ACCESS_KEY"
        )
        if not all([aws_key_id, aws_secret_key]):
            print(
                f"{Fore.YELLOW}Warning: AWS access key not configured. "
                f"Local credentials will be used.{Fore.RESET}"
            )

        self._s3_client = boto3.client(
            "s3",
            aws_access_key_id=aws_key_id,
            aws_secret_access_key=aws_secret_key,
        )

        self._check_bucket_accessibility()

        print(f"Connected to S3 bucket: {bucket_name}")

    def _check_bucket_accessibility(self) -> None:
        r"""Check if the bucket is accessible."""
        try:
            self._s3_client.head_bucket(Bucket=self._bucket_name)
        except Exception as e:
            raise Exception(
                f"Error: Unable to access the S3 bucket: {e}"
            ) from e

    def put_file(self, file_path: Path, file: File) -> None:
        r"""Upload a file to the S3 bucket.

        Args:
            file_path (Path): The path to the object in the S3 bucket.
            file (File): The file to be uploaded.
        """
        file_key = self.canonicalize_path(file_path)
        self._s3_client.put_object(
            Bucket=self._bucket_name, Key=file_key, Body=file.raw_bytes
        )

    def get_file(self, file_path: Path) -> File:
        r"""Download a file from the S3 bucket.

        Args:
            file_path (Path): The path to the object in the S3 bucket.

        Returns:
            File: The object from the S3 bucket.
        """
        file_key = self.canonicalize_path(file_path)
        file_name = file_path.name
        response = self._s3_client.get_object(
            Bucket=self._bucket_name, Key=file_key
        )
        raw_bytes = response["Body"].read()
        file = BytesIO(raw_bytes)
        file.name = file_name
        return read_file(file)

    def canonicalize_path(self, file_path: Path) -> str:
        r"""Canonicalize the path for the S3 bucket.

        Args:
            file_path (Path): The path to be canonicalized.

        Returns:
            str: The canonicalized S3 object path.
        """
        return file_path.as_posix()

    def upload_file(self, local_file_path: Path, s3_file_path: Path) -> None:
        r"""Upload a local file to the S3 bucket.

        Args:
            local_file_path (Path): The path to the local file to be uploaded.
            s3_file_path (Path): The path to the object in the S3 bucket.
        """
        file_key = self.canonicalize_path(s3_file_path)
        self._s3_client.upload_file(
            Filename=local_file_path, Bucket=self._bucket_name, Key=file_key
        )

    def download_file(self, local_file_path: Path, s3_file_path: Path) -> None:
        r"""Download a file from the S3 bucket to the local system.

        Args:
            local_file_path (Path): The path to the local file to be saved.
            s3_file_path (Path): The path to the object in the S3 bucket.
        """
        file_key = self.canonicalize_path(s3_file_path)
        self._s3_client.download_file(
            Bucket=self._bucket_name, Key=file_key, Filename=local_file_path
        )
