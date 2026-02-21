# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
# Mock the dotenv functionality to prevent the TypeError
import sys
from unittest.mock import MagicMock, mock_open, patch

import pytest

from camel.toolkits.video_download_toolkit import (
    VideoDownloaderToolkit,
    _check_ffmpeg_installed,
)

sys.modules['dotenv'] = MagicMock()
sys.modules['dotenv.main'] = MagicMock()
sys.modules['dotenv.parser'] = MagicMock()


@pytest.fixture
def mock_downloader():
    # Mock the FastMCP class to avoid dotenv loading issues
    with (
        patch("builtins.open", mock_open(read_data=b"test")),
        patch("yt_dlp.YoutubeDL") as mock_youtube_dl,
        patch("shutil.which", return_value="/usr/bin/ffmpeg"),
        patch('tempfile.mkdtemp') as mock_mkdtemp,
        patch('pathlib.Path.mkdir'),
        patch('ffmpeg.input') as mock_ffmpeg_input,
        patch('ffmpeg.probe') as mock_ffmpeg_probe,
        patch('PIL.Image.open'),
        patch('mcp.server.fastmcp.server.FastMCP') as mock_fastmcp,
        patch(
            'pydantic_settings.sources.DotEnvSettingsSource._read_env_files',
            return_value={},
        ),
    ):
        mock_ydl_instance = MagicMock()
        mock_ydl_instance.prepare_filename.return_value = "test.mp4"
        mock_youtube_dl.return_value.__enter__.return_value = mock_ydl_instance

        mock_mkdtemp.return_value = "C:\\temp\\abcdefg"

        mock_ffmpeg = MagicMock()
        mock_ffmpeg_input.return_value = mock_ffmpeg
        mock_ffmpeg.filter.return_value = mock_ffmpeg
        mock_ffmpeg.output.return_value = mock_ffmpeg
        mock_ffmpeg.run.return_value = (b"test", b"test")

        mock_ffmpeg_probe.return_value = {'format': {'duration': 10}}

        # Configure the FastMCP mock
        mock_fastmcp_instance = MagicMock()
        mock_fastmcp.return_value = mock_fastmcp_instance
        mock_fastmcp_instance.tool.return_value = lambda x: x

        yield VideoDownloaderToolkit()


def test_video_bytes_download(mock_downloader):
    video_bytes = mock_downloader.get_video_bytes(
        video_path="https://test_video.mp4",
    )
    assert len(video_bytes) > 0
    assert video_bytes == b"test"


def test_video_screenshots_download(mock_downloader):
    screenshots = mock_downloader.get_video_screenshots(
        "https://test_video.mp4",
        2,
    )
    assert len(screenshots) == 2


def test_check_ffmpeg_installed_when_present():
    r"""Test that _check_ffmpeg_installed passes when FFmpeg is installed."""
    # Mock shutil.which to return a path (FFmpeg installed)
    with patch('shutil.which', return_value='/usr/bin/ffmpeg'):
        # Should not raise any exception
        _check_ffmpeg_installed()


def test_check_ffmpeg_installed_when_missing():
    r"""Test that _check_ffmpeg_installed raises RuntimeError when FFmpeg is
    missing.
    """
    # Mock shutil.which to return None (FFmpeg not installed)
    with patch('shutil.which', return_value=None):
        with pytest.raises(RuntimeError) as exc_info:
            _check_ffmpeg_installed()

        error_msg = str(exc_info.value)
        # Verify the error message contains key information
        assert "FFmpeg is not installed" in error_msg
        assert "Windows" in error_msg
        assert "winget install ffmpeg" in error_msg
        assert "macOS" in error_msg
        assert "brew install ffmpeg" in error_msg
        assert "Linux" in error_msg
        assert (
            "apt install ffmpeg" in error_msg
            or "yum install ffmpeg" in error_msg
        )
        assert "https://ffmpeg.org/download.html" in error_msg


def test_video_screenshots_raises_error_when_ffmpeg_missing():
    r"""Test that get_video_screenshots raises error when FFmpeg is missing."""
    # Mock shutil.which to return None (FFmpeg not installed)
    # Mock ffmpeg module to avoid import errors
    with (
        patch('shutil.which', return_value=None),
        patch.dict('sys.modules', {'ffmpeg': MagicMock()}),
    ):
        toolkit = VideoDownloaderToolkit()
        with pytest.raises(RuntimeError) as exc_info:
            toolkit.get_video_screenshots("test.mp4", 2)

        error_msg = str(exc_info.value)
        assert "FFmpeg is not installed" in error_msg


def test_capture_screenshot_raises_error_when_ffmpeg_missing():
    r"""Test that _capture_screenshot raises error when FFmpeg is missing."""
    from camel.toolkits.video_download_toolkit import _capture_screenshot

    # Mock shutil.which to return None (FFmpeg not installed)
    # Mock ffmpeg module to avoid import errors
    with (
        patch('shutil.which', return_value=None),
        patch.dict('sys.modules', {'ffmpeg': MagicMock()}),
    ):
        with pytest.raises(RuntimeError) as exc_info:
            _capture_screenshot("test.mp4", 1.0)

        error_msg = str(exc_info.value)
        assert "FFmpeg is not installed" in error_msg
