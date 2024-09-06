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
import hashlib
import io
import os
import re
import subprocess
from typing import List, Optional, Tuple, Union

import ffmpeg  # type: ignore
import yt_dlp  # type: ignore
from PIL import Image

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
        self._cookies_path: Optional[str] = None
        self._current_directory: Optional[str] = None
        self._video_extension: Optional[str] = None

    @property
    def cookies_path(self) -> Optional[str]:
        """
        Get the path to the cookies.txt file. Cached after first access.

        Returns:
            Optional[str]: The path to the cookies file if it exists, otherwise None.
        """
        if self._cookies_path is None:
            project_root = os.getcwd()
            cookies_path = os.path.join(project_root, "cookies.txt")
            if not os.path.exists(cookies_path):
                print(
                    f"Warning: cookies.txt file not found at path {cookies_path}."
                )
                self._cookies_path = None
            else:
                self._cookies_path = cookies_path
        return self._cookies_path

    @property
    def current_directory(self) -> str:
        """
        Create or retrieve the directory for storing the downloaded video.
        Cached after first access.

        Returns:
            str: The path to the directory where the video will be stored.
        """
        if self._current_directory is None:
            if not self.video_url:
                raise ValueError("video_url is not set.")

            video_hash = hashlib.md5(
                self.video_url.encode('utf-8')
            ).hexdigest()
            project_root = os.getcwd()
            video_directory = os.path.join(
                project_root, "temp_video", video_hash
            )

            if not os.path.exists(video_directory):
                os.makedirs(video_directory)

            self._current_directory = video_directory

        return self._current_directory

    @property
    def video_extension(self) -> str:
        """
        Retrieve the video file extension. If the extension does not exist,
        the video download method will be called to fetch the full video.

        Returns:
            str: The video file extension (e.g., '.mp4', '.webm').
        """
        if self._video_extension is None:
            video_files = [
                f
                for f in os.listdir(self.current_directory)
                if re.match(r'full_video\..+', f)
            ]

            if video_files:
                self._video_extension = os.path.splitext(video_files[0])[1]
            else:
                # If no video file is found, proceed to download the video
                self.download_video()
                video_files = [
                    f
                    for f in os.listdir(self.current_directory)
                    if re.match(r'full_video\..+', f)
                ]
                if video_files:
                    self._video_extension = os.path.splitext(video_files[0])[1]
                else:
                    raise FileNotFoundError(
                        "Video download failed, and no video file was found."
                    )

        return self._video_extension

    def extract_youtube_video_url(self, url: str) -> Optional[str]:
        """
        Convert an embedded YouTube URL to a standard YouTube video URL.
        Only applies to YouTube links, otherwise returns None.

        Args:
            url (str): The input URL, which could be an embedded YouTube URL.

        Returns:
            Optional[str]: The standard YouTube URL, or None if it's not a YouTube link.
        """
        if "youtube.com/embed/" in url:
            match = re.search(r"embed/([a-zA-Z0-9_-]+)", url)
            if match:
                video_id = match.group(1)
                return f"https://www.youtube.com/watch?v={video_id}"
        elif "youtube.com/watch" in url or "youtu.be" in url:
            return url
        return None

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

        converted_url = self.extract_youtube_video_url(self.video_url)
        if converted_url:
            self.video_url = converted_url

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

    def is_video_downloaded(self) -> bool:
        """
        Check if the video has already been downloaded.

        Returns:
            bool: True if the video file(s) exist(s), False otherwise.
        """
        if self.split_into_chunks:
            first_chunk_path = os.path.join(
                self.current_directory, f'video_chunk_0{self.video_extension}'
            )
            return os.path.exists(first_chunk_path)
        else:
            video_path = os.path.join(
                self.current_directory, f'full_video{self.video_extension}'
            )
            return os.path.exists(video_path)

    def get_video_length(self) -> int:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'cookiefile': self.cookies_path,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(self.video_url, download=False)
                video_length = info_dict.get('duration', 0)
        except Exception as e:
            print(f"Error retrieving video length from network: {e}")
            video_length = 0

        if video_length == 0:
            if self.is_video_downloaded():
                if self.split_into_chunks:
                    video_length = 0
                    chunk_index = 0
                    while True:
                        chunk_filename = os.path.join(
                            self.current_directory,
                            f'video_chunk_{chunk_index}{self.video_extension}',
                        )
                        if not os.path.exists(chunk_filename):
                            break

                        video_length += self._get_video_length_from_file(
                            chunk_filename
                        )
                        chunk_index += 1
                else:
                    video_path = os.path.join(
                        self.current_directory,
                        f'full_video{self.video_extension}',
                    )
                    if os.path.exists(video_path):
                        video_length = self._get_video_length_from_file(
                            video_path
                        )

        return video_length

    def _get_video_length_from_file(self, file_path: str) -> int:
        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    file_path,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            duration = float(result.stdout)
            return int(duration)
        except Exception as e:
            print(f"Error calculating video length from file: {e}")
            return 0

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
                    self.current_directory,
                    f'video_chunk_{chunk_index}{self.video_extension}',
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

        video_path = os.path.join(
            self.current_directory, f'full_video{self.video_extension}'
        )

        if not os.path.exists(video_path):
            self.download_video()
            return self.get_video_bytes()

        with open(video_path, "rb") as video_file:
            video_bytes = video_file.read()

        return video_bytes

    def get_video_screenshots(
        self, timestamps: Union[List[int], int]
    ) -> List[Image.Image]:
        """
        Capture screenshots from the video at specified timestamps or by
        dividing the video into equal parts if an integer is provided.

        Args:
            timestamps (Union[List[int], int]): A list of timestamps (in seconds)
              from which to capture the screenshots, or an integer specifying
              the number of evenly spaced screenshots to capture.

        Returns:
            List[Image.Image]: A list of screenshots as PIL Image objects.
        """
        if not self.is_video_downloaded():
            self.download_video()

        if isinstance(timestamps, int):
            video_length = self.get_video_length()
            intervals = video_length // (timestamps + 1)
            timestamps = [(i + 1) * intervals for i in range(timestamps)]

        images = []
        if self.split_into_chunks:
            for timestamp in timestamps:
                chunk_index, local_timestamp = (
                    self._get_chunk_index_and_local_timestamp(timestamp)
                )
                chunk_filename = os.path.join(
                    self.current_directory,
                    f'video_chunk_{chunk_index}{self.video_extension}',
                )
                images.append(
                    self._capture_screenshot(chunk_filename, local_timestamp)
                )
        else:
            video_path = os.path.join(
                self.current_directory, f'full_video{self.video_extension}'
            )
            images = [
                self._capture_screenshot(video_path, ts) for ts in timestamps
            ]

        return images

    def _get_chunk_index_and_local_timestamp(
        self, timestamp: int
    ) -> Tuple[int, int]:
        """
        Determine the chunk index and the local timestamp within that chunk for
          a global timestamp.

        Args:
            timestamp (int): The global timestamp in the video.

        Returns:
            (int, int): The chunk index and the local timestamp within that
              chunk.
        """
        chunk_index = timestamp // self.chunk_duration
        local_timestamp = timestamp % self.chunk_duration
        return chunk_index, local_timestamp

    def _capture_screenshot(
        self, video_path: str, timestamp: int
    ) -> Image.Image:
        """
        Capture a screenshot from a video file at a specific timestamp.

        Args:
            video_path (str): The path to the video file.
            timestamp (int): The time in seconds from which to capture the
              screenshot.

        Returns:
            Image.Image: The captured screenshot as a PIL Image object.
        """
        out, _ = (
            ffmpeg.input(video_path, ss=timestamp)
            .filter('scale', 320, -1)
            .output('pipe:', vframes=1, format='image2', vcodec='png')
            .run(capture_stdout=True, capture_stderr=True)
        )
        return Image.open(io.BytesIO(out))

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

    if downloader.is_video_downloaded():
        print("Video has already been downloaded.")

    print(downloader.get_video_length())

    timestamps = 3
    image_list = downloader.get_video_screenshots(timestamps)

    for _, img in enumerate(image_list):
        img.show()
