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
import time
from typing import List, Optional

import yt_dlp  # type: ignore

from camel.toolkits.openai_function import OpenAIFunction


class VideoDownloaderToolkit:
    """A class for downloading videos and optionally splitting them into
    chunks."""

    def __init__(
        self,
        video_url: Optional[str] = None,
        chunk_duration: int = 30,
        split_into_chunks: bool = False,
    ):
        """
        Initialize the VideoDownloaderToolkit.

        Args:
            video_url (str, optional): The URL of the video to download.
            chunk_duration (int, optional): The duration of each chunk in
                seconds. Defaults to 30.
            split_into_chunks (bool, optional): If True, split the video into
                chunks. Defaults to False.
        """
        self.video_url = video_url
        self.chunk_duration = chunk_duration
        self.split_into_chunks = split_into_chunks
        self.cookies_path: Optional[str] = None
        self.current_directory = ""

    def get_video_directory(self) -> str:
        """
        Create a directory for storing the downloaded video.

        Returns:
            str: The path to the directory where the video will be stored.
        """
        if not self.video_url:
            raise ValueError("video_url is not set.")

        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'cookiefile': self.cookies_path,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(self.video_url, download=False)
            video_title = info_dict.get('title', 'unknown_video').replace(
                ' ', '_'
            )

        timestamp = time.strftime("%Y%m%d-%H%M%S")

        project_root = os.getcwd()
        video_directory = os.path.join(
            project_root, "temp_video", f"{video_title}_{timestamp}"
        )

        if not os.path.exists(video_directory):
            os.makedirs(video_directory)

        return video_directory

    def get_cookies_path(self) -> Optional[str]:
        """
        Get the path to the cookies.txt file.

        Returns:
            str: The path to the cookies file if it exists, otherwise None.
        """
        project_root = os.getcwd()
        cookies_path = os.path.join(project_root, "cookies.txt")
        if not os.path.exists(cookies_path):
            print(
                f"Warning: cookies.txt file not found at path {cookies_path}."
            )
            return None
        return cookies_path

    def download_video(self, video_url: Optional[str] = None) -> None:
        """
        Download the video and optionally split it into chunks.

        Args:
            video_url (str, optional): The URL of the video to download.
        """
        if video_url:
            self.video_url = video_url

        if not self.video_url:
            raise ValueError(
                "No video URL provided. Please provide a valid video URL."
            )

        self.cookies_path = self.get_cookies_path()
        self.current_directory = self.get_video_directory()

        try:
            if self.split_into_chunks and self.chunk_duration is not None:
                video_length = self.get_video_length()
                if video_length == 0:
                    raise ValueError(
                        """Unable to determine video duration. Please download 
                            the full video."""
                    )

                for chunk_index, start_time in enumerate(
                    range(0, video_length, self.chunk_duration)
                ):
                    end_time = min(
                        start_time + self.chunk_duration, video_length
                    )
                    self._download_chunk(start_time, end_time, chunk_index)

            else:
                video_template = os.path.join(
                    self.current_directory, 'full_video.%(ext)s'
                )
                ydl_opts = {
                    'format': 'bestvideo+bestaudio/best',
                    'outtmpl': video_template,
                    'force_generic_extractor': True,
                }

                if self.cookies_path:
                    ydl_opts['cookiefile'] = self.cookies_path

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([self.video_url])

        except yt_dlp.utils.DownloadError as e:
            print(f"Error downloading video: {e}")

    def _download_chunk(
        self, start_time: int, end_time: int, chunk_index: int
    ) -> None:
        """
        Download a specific chunk of the video.

        Args:
            start_time (int): The start time of the chunk in seconds.
            end_time (int): The end time of the chunk in seconds.
            chunk_index (int): The index of the chunk.
        """
        video_template = os.path.join(
            self.current_directory, f'video_chunk_{chunk_index}.%(ext)s'
        )
        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',
            'outtmpl': video_template,
            'postprocessor_args': [
                '-ss',
                str(start_time),
                '-to',
                str(end_time),
            ],
            'force_generic_extractor': True,
        }

        if self.cookies_path:
            ydl_opts['cookiefile'] = self.cookies_path

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(self.video_url, download=False)
                ydl.download([self.video_url])
                video_filename = ydl.prepare_filename(info_dict)

            if not os.path.exists(video_filename):
                raise FileNotFoundError(
                    f"""Downloaded video file {video_filename} does not exist
                    or is empty."""
                )

        except yt_dlp.utils.DownloadError as e:
            print(f"Error downloading chunk: {e}")

    def get_video_length(self) -> int:
        """
        Get the length of the video in seconds.

        Returns:
            int: The duration of the video in seconds.
        """
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'cookiefile': self.cookies_path,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(self.video_url, download=False)
            video_length = info_dict.get('duration', 0)
        return video_length

    def get_video_bytes(self) -> bytes:
        """
        Returns the video bytes for the downloaded video. If the video was
        downloaded in chunks, the chunks will be read and concatenated.

        Returns:
            bytes: The video file content in bytes.
        """
        if self.split_into_chunks:
            video_bytes = b""
            chunk_index = 0

            while True:
                chunk_filename = os.path.join(
                    self.current_directory, f'video_chunk_{chunk_index}.mp4'
                )
                if not os.path.exists(chunk_filename):
                    break

                with open(chunk_filename, "rb") as chunk_file:
                    video_bytes += chunk_file.read()

                chunk_index += 1

            if chunk_index == 0:
                self.download_video()
                return self.get_video_bytes()

            return video_bytes

        video_path = os.path.join(self.current_directory, 'full_video.mp4')

        if not os.path.exists(video_path):
            self.download_video()
            return self.get_video_bytes()

        with open(video_path, "rb") as video_file:
            video_bytes = video_file.read()

        return video_bytes

    def get_tools(self) -> List[OpenAIFunction]:
        """
        Returns a list of OpenAIFunction objects representing the functions in
            the toolkit.

        Returns:
            List[OpenAIFunction]: A list of OpenAIFunction objects representing
                the functions in the toolkit.
        """
        return [
            OpenAIFunction(self.download_video),
            OpenAIFunction(self.get_video_bytes),
        ]


VIDEO_DOWNLOAD_FUNCS: List[OpenAIFunction] = (
    VideoDownloaderToolkit().get_tools()
)

if __name__ == "__main__":
    video_url = 'https://sample-videos.com/video321/mp4/720/big_buck_bunny_720p_1mb.mp4'
    downloader = VideoDownloaderToolkit(
        video_url=video_url, split_into_chunks=False
    )

    # Get the video bytes
    video_bytes = downloader.get_video_bytes()
    print(f"Video bytes length: {len(video_bytes)}")

    # or
    # downloader = VideoDownloaderToolkit(video_url=video_url)
    # downloader.download_video()
