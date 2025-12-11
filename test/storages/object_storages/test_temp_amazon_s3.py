# tests/storages/test_amazon_s3_storage_integration.py
from __future__ import annotations

r"""Integration-style tests for AmazonS3Storage with a mocked S3 backend.

These tests use moto to mock AWS S3 in memory, allowing validation of the
AmazonS3Storage implementation without requiring real AWS credentials or
network access. The goal is to ensure that core S3 operations (put, get,
upload, download, and existence checks) behave as expected.
"""

from pathlib import Path

import pytest
from moto import mock_aws
import boto3

from camel.storages.object_storages import AmazonS3Storage
from camel.loaders import create_file_from_raw_bytes


@mock_aws
def test_put_get_file_roundtrip() -> None:
    r"""Write a file to S3 and read it back using the storage wrapper.

    This test uploads a file object to a mocked S3 bucket using
    :meth:`AmazonS3Storage._put_file` and then retrieves it using
    :meth:`AmazonS3Storage._get_file`, asserting that the raw bytes are
    preserved across the round trip.
    """
    # Create a mocked S3 bucket
    s3 = boto3.client("s3", region_name="us-east-1")
    bucket_name = "camel-test-bucket"
    s3.create_bucket(Bucket=bucket_name)

    storage = AmazonS3Storage(
        bucket_name=bucket_name,
        create_if_not_exists=False,
    )

    key = "foo/bar.txt"
    content = b"hello s3"
    file = create_file_from_raw_bytes(content, "bar.txt")

    # Upload and retrieve the file
    storage._put_file(key, file)
    out_file = storage._get_file(key, "bar.txt")

    assert out_file.raw_bytes == content


@mock_aws
def test_upload_and_download_file(tmp_path: Path) -> None:
    r"""Upload a local file to S3 and download it back to disk.

    This test writes a temporary local file, uploads it to the mocked S3
    bucket using :meth:`AmazonS3Storage._upload_file`, then downloads it
    to a new local path using :meth:`AmazonS3Storage._download_file`. The
    downloaded file contents should match the original bytes.
    """
    # Create a mocked S3 bucket
    s3 = boto3.client("s3", region_name="us-east-1")
    bucket_name = "camel-test-bucket"
    s3.create_bucket(Bucket=bucket_name)

    storage = AmazonS3Storage(
        bucket_name=bucket_name,
        create_if_not_exists=False,
    )

    # Create a local source file
    src = tmp_path / "source.txt"
    src.write_bytes(b"local-data")

    key = "dir/source.txt"
    storage._upload_file(src, key)

    # Download to a new local file
    dest = tmp_path / "dest.txt"
    storage._download_file(dest, key)

    assert dest.read_bytes() == b"local-data"


@mock_aws
def test_object_exists_true_and_false() -> None:
    r"""Verify that `_object_exists` reports S3 object presence correctly.

    This test seeds one object directly into the mocked S3 bucket and
    asserts that :meth:`AmazonS3Storage._object_exists` returns
    :obj:`True` for an existing key and :obj:`False` for a missing key.
    """
    # Create a mocked S3 bucket
    s3 = boto3.client("s3", region_name="us-east-1")
    bucket_name = "camel-test-bucket"
    s3.create_bucket(Bucket=bucket_name)

    storage = AmazonS3Storage(
        bucket_name=bucket_name,
        create_if_not_exists=False,
    )

    # Seed an object directly via boto3
    key = "exists.txt"
    s3.put_object(Bucket=bucket_name, Key=key, Body=b"data")

    assert storage._object_exists(key) is True
    assert storage._object_exists("missing.txt") is False
