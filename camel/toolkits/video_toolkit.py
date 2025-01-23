# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========

import io
import logging
import re
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Optional

import ffmpeg
from PIL import Image

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.types import ModelPlatformType, ModelType
from camel.utils import dependencies_required

from .audio_toolkit import AudioToolkit

logger = logging.getLogger(__name__)

VIDEO_QA_PROMPT = """
Using the provided visual description and audio transcription from the same \
video, answer the following question(s) concisely. 

- **Visual Description**: {visual_description}  
- **Audio Transcription**: {audio_transcription}  

Provide a clear and concise response by combining relevant details from both \
the visual and audio content. If additional context is required, specify what \
is missing.

Question:
{question}
"""

AUDIO_TRANSCRIPTION_PROMPT = """Transcribe the following audio into clear and \
accurate text. \
Ensure proper grammar, punctuation, and formatting to maintain readability. \
Indicate speaker changes if possible and denote inaudible sections with \
'[inaudible]' or '[unintelligible]'. If the audio contains background noises \
or music, include brief notes in brackets only if relevant. Do not summarize \
or omit any spoken content."""

VIDEO_SUMMARISATION_PROMPT = """You are a video analysis assistant. I will 
provide you with frames from a video segment. Your task is to analyze these 
frames and provide a concise, structured description of the video.

Focus on the following points:

1. **Scene/Environment**: Briefly describe the setting (e.g., indoor/outdoor, 
notable background details).
2. **People/Characters**: Note the number of people, their appearance 
(clothing, age, gender, features), and actions.
3. **Objects/Items**: Mention significant objects and their use or position.
4. **Actions/Activities**: Summarize key actions and interactions between 
people or objects.
5. **On-Screen Text/Clues**: Extract visible text (e.g., signs, captions) and 
describe symbols or logos.
6. **Changes Over Time**: Highlight any progression or changes in the scene.
7. **Summary**: Provide a brief synthesis of key observations, focusing on 
notable or unusual elements.

Keep your response concise while covering the key details."""


def _standardize_url(url: str) -> str:
    r"""Standardize the given URL."""
    # Special case for YouTube embed URLs
    if "youtube.com/embed/" in url:
        match = re.search(r"embed/([a-zA-Z0-9_-]+)", url)
        if match:
            return f"https://www.youtube.com/watch?v={match.group(1)}"
        else:
            raise ValueError(f"Invalid YouTube URL: {url}")

    return url


def _capture_screenshot(video_file: str, timestamp: float) -> Image.Image:
    r"""Capture a screenshot from a video file at a specific timestamp.

    Args:
        video_file (str): The path to the video file.
        timestamp (float): The time in seconds from which to capture the
          screenshot.

    Returns:
        Image.Image: The captured screenshot in the form of Image.Image.
    """
    import ffmpeg

    try:
        out, _ = (
            ffmpeg.input(video_file, ss=timestamp)
            .filter('scale', 320, -1)
            .output('pipe:', vframes=1, format='image2', vcodec='png')
            .run(capture_stdout=True, capture_stderr=True)
        )
    except ffmpeg.Error as e:
        raise RuntimeError(f"Failed to capture screenshot: {e.stderr}")

    return Image.open(io.BytesIO(out))


class VideoToolkit(BaseToolkit):
    r"""A class for downloading videos and optionally splitting them into
    chunks.

    Args:
        download_directory (Optional[str], optional): The directory where the
            video will be downloaded to. If not provided, video will be stored
            in a temporary directory and will be cleaned up after use.
            (default: :obj:`None`)
        cookies_path (Optional[str], optional): The path to the cookies file
            for the video service in Netscape format. (default: :obj:`None`)
    """

    @dependencies_required("yt_dlp", "ffmpeg")
    def __init__(
        self,
        download_directory: Optional[str] = None,
        cookies_path: Optional[str] = None,
        cache_dir: Optional[str] = None,
    ) -> None:
        self._cleanup = download_directory is None
        self._cookies_path = cookies_path

        self._download_directory = Path(
            download_directory or tempfile.mkdtemp()
        ).resolve()

        try:
            self._download_directory.mkdir(parents=True, exist_ok=True)
        except FileExistsError:
            raise ValueError(
                f"{self._download_directory} is not a valid directory."
            )
        except OSError as e:
            raise ValueError(
                f"Error creating directory {self._download_directory}: {e}"
            )

        logger.info(f"Video will be downloaded to {self._download_directory}")

        # Set model and ChatAgent for video understanding
        self.vl_model = ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI,
            model_type=ModelType.GPT_4O_MINI,
        )
        self.vl_agent = ChatAgent(
            model=self.vl_model, output_language="English"
        )

        self.qa_agent = ChatAgent()

    def __del__(self) -> None:
        r"""Deconstructor for the VideoDownloaderToolkit class.

        Cleans up the downloaded video if they are stored in a temporary
        directory.
        """
        import shutil

        if self._cleanup:
            shutil.rmtree(self._download_directory, ignore_errors=True)

    def _download_video(self, url: str) -> str:
        r"""Download the video and optionally split it into chunks.

        yt-dlp will detect if the video is downloaded automatically so there
        is no need to check if the video exists.

        Returns:
            str: The path to the downloaded video file.
        """
        import yt_dlp

        video_template = self._download_directory / "%(title)s.%(ext)s"
        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',
            'outtmpl': str(video_template),
            'http_headers': {'User-Agent': 'Mozilla/5.0'},
            'force_generic_extractor': True,
            'cookiefile': self._cookies_path,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Download the video and get the filename
                logger.info(f"Downloading video from {url}...")
                info = ydl.extract_info(url, download=True)
                return ydl.prepare_filename(info)
        except yt_dlp.utils.DownloadError as e:
            raise RuntimeError(f"Failed to download video from {url}: {e}")

    def _extract_audio_from_video(
        self, video_path: str, output_format: str = "mp3"
    ) -> str:
        output_path = video_path.rsplit('.', 1)[0] + f".{output_format}"
        try:
            (
                ffmpeg.input(video_path)
                .output(output_path, vn=None, acodec="libmp3lame")
                .run()
            )
            return output_path
        except ffmpeg.Error as e:
            raise RuntimeError(f"FFmpeg-Python failed: {e}")

    def get_video_bytes(
        self,
        video_path: str,
    ) -> bytes:
        r"""Download video by the URL, and return the content in bytes.

        Args:
            video_url (str): The URL of the video to download.

        Returns:
            bytes: The video file content in bytes.
        """

        with open(video_path, 'rb') as f:
            video_bytes = f.read()

        return video_bytes

    def get_video_screenshots(
        self, video_file: str, amount: int
    ) -> List[Image.Image]:
        r"""Capture screenshots from the video at specified timestamps or by
        dividing the video into equal parts if an integer is provided.

        Args:
            video_url (str): The URL of the video to take screenshots.
            amount (int): the amount of evenly split screenshots to capture.

        Returns:
            List[Image.Image]: A list of screenshots as Image.Image.
        """

        # Get the video length
        try:
            probe = ffmpeg.probe(video_file)
            video_length = float(probe['format']['duration'])
        except ffmpeg.Error as e:
            raise RuntimeError(f"Failed to determine video length: {e.stderr}")

        interval = video_length / (amount + 1)
        timestamps = [i * interval for i in range(1, amount + 1)]

        images = [_capture_screenshot(video_file, ts) for ts in timestamps]

        return images

    def _describe_video_segment(
        self,
        images: List[Image.Image],
    ) -> str:
        r"""Ask a question about the video using VLLM."""

        msg = BaseMessage.make_user_message(
            role_name="User",
            content=VIDEO_SUMMARISATION_PROMPT,
            image_list=images,
        )

        response = self.vl_agent.step(msg)
        segment_description = response.msgs[0].content
        return segment_description

    def _transcribe_video(
        self,
        video_path: str,
        frames_per_second: int = 1,
        segment_size: int = 100,
    ) -> str:
        r"""Transcribe the visual information of the video."""

        probe = ffmpeg.probe(video_path)
        video_length = float(probe['format']['duration'])
        number_of_frames = int(video_length * frames_per_second)

        images = self.get_video_screenshots(video_path, number_of_frames)
        total_frames = len(images)

        def process_segment(start: int):
            r"""Process a single segment."""
            segment_frames = images[start : start + segment_size]
            if not segment_frames:
                return None

            segment_start_time = start / frames_per_second
            segment_end_time = min(
                (start + segment_size) / frames_per_second, video_length
            )
            description = self._describe_video_segment(segment_frames)
            segment_info = f"Segment {start // segment_size + 1} \
                ({segment_start_time:.2f}-{segment_end_time:.2f}s):"
            return f"{segment_info}\n{description}"

        # Use ThreadPoolExecutor to process segments in parallel
        with ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(process_segment, start)
                for start in range(0, total_frames, segment_size)
            ]
            descriptions = [
                future.result() for future in futures if future.result()
            ]

        # Combine all segment descriptions into a full transcription
        full_transcription = "\n\n".join(descriptions)
        print("Visual transcription: " + full_transcription)
        return full_transcription

    def _transcribe_audio(self, audio_path: str) -> str:
        r"""Transcribe the audio of the video."""

        audio_toolkit = AudioToolkit()
        audio_transcript = audio_toolkit.ask_question_about_audio(
            audio_path, AUDIO_TRANSCRIPTION_PROMPT
        )
        print("\nAudio transcription: " + audio_transcript)
        return audio_transcript

    def ask_question_about_video(self, video_path: str, question: str) -> str:
        r"""Ask a question about the video.

        Args:
            video_path (str): The path to the video file.
                It can be a local file or a URL.
            question (str): The question to ask about the video.

        Returns:
            str: The answer to the question.
        """

        # use asr and video understanding model to answer the question
        from urllib.parse import urlparse

        parsed_url = urlparse(video_path)
        is_url = all([parsed_url.scheme, parsed_url.netloc])

        if is_url:
            video_path = self._download_video(video_path)
        audio_path = self._extract_audio_from_video(video_path)

        video_transcript = self._transcribe_video(video_path)
        audio_transcript = self._transcribe_audio(audio_path)

        prompt = VIDEO_QA_PROMPT.format(
            visual_description=video_transcript,
            audio_transcription=audio_transcript,
            question=question,
        )

        response = self.qa_agent.step(prompt)
        answer = response.msgs[0].content

        return answer

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the
        functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects representing
                the functions in the toolkit.
        """
        return [
            FunctionTool(self.ask_question_about_video),
            FunctionTool(self.get_video_bytes),
            FunctionTool(self.get_video_screenshots),
        ]
