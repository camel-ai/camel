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
from camel.toolkits.video_toolkit import VideoDownloaderToolkit


def test_video_download_initialization():
    downloader = VideoDownloaderToolkit(
        video_url='https://sample-videos.com/video321/mp4/720/big_buck_bunny_720p_1mb.mp4',
        split_into_chunks=False,
    )
    assert downloader.video_url is not None
    assert downloader.split_into_chunks is False


def test_video_bytes_download():
    downloader = VideoDownloaderToolkit(
        video_url='https://sample-videos.com/video321/mp4/720/big_buck_bunny_720p_1mb.mp4',
        split_into_chunks=False,
    )
    video_bytes = downloader.get_video_bytes()
    assert len(video_bytes) > 0


def test_video_length():
    downloader = VideoDownloaderToolkit(
        video_url='https://sample-videos.com/video321/mp4/720/big_buck_bunny_720p_1mb.mp4',
        split_into_chunks=False,
    )
    video_length = downloader.get_video_length()
    assert video_length > 0


def test_video_is_downloaded():
    downloader = VideoDownloaderToolkit(
        video_url='https://sample-videos.com/video321/mp4/720/big_buck_bunny_720p_1mb.mp4',
        split_into_chunks=False,
    )
    is_downloaded = downloader.is_video_downloaded()
    assert isinstance(is_downloaded, bool)
