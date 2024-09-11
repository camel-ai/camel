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

import pytest

from camel.toolkits import VideoDownloaderToolkit


@pytest.fixture
def video_url():
    return 'https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4'


@pytest.fixture
def downloader(video_url):
    return VideoDownloaderToolkit(video_url=video_url)


def test_download_video(downloader):
    """Test the video download functionality."""
    downloader.download_video(split_into_chunks=False)
    video_files = os.listdir(downloader.current_directory)
    assert (
        len(video_files) > 0
    ), "At least one video file should be downloaded."


def test_download_video_in_chunks(downloader):
    """Test the video download functionality with chunks."""
    downloader.download_video(split_into_chunks=True)
    video_files = os.listdir(downloader.current_directory)
    assert len(video_files) > 1, "Multiple chunks should be downloaded."


def test_cookies_path(downloader):
    """Test the retrieval of cookies path."""
    downloader.cookies_path = downloader.get_cookies_path()
    assert os.path.exists(
        downloader.cookies_path
    ), "Cookies file should exist at the specified path."


def test_get_video_directory(downloader):
    """Test if the video directory is created correctly."""
    video_directory = downloader.get_video_directory()
    assert os.path.exists(
        video_directory
    ), "Video directory should be created."
    assert os.path.isdir(
        video_directory
    ), "Video directory should be a valid directory."


@pytest.fixture(scope="function", autouse=True)
def cleanup(downloader):
    """Cleanup any created directories or files after each test."""
    yield
    if os.path.exists(downloader.current_directory):
        for file in os.listdir(downloader.current_directory):
            file_path = os.path.join(downloader.current_directory, file)
            os.remove(file_path)
        os.rmdir(downloader.current_directory)
