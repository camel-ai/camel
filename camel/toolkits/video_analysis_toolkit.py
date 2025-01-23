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

import logging
import tempfile
from pathlib import Path
from typing import List, Optional

import ffmpeg

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory, OpenAIAudioModels
from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.types import ModelPlatformType, ModelType
from camel.utils import dependencies_required

from .video_downloader_toolkit import VideoDownloaderToolkit

logger = logging.getLogger(__name__)

VIDEO_QA_PROMPT = """
Using the provided frames from a video and audio transcription from the same \
video, answer the following question(s) concisely. 

**Audio Transcription**: {audio_transcription}  

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


class VideoAnalysisToolkit(BaseToolkit):
    r"""A class for downloading videos and optionally splitting them into
    chunks.

    Args:
        download_directory (Optional[str], optional): The directory where the
            video will be downloaded to. If not provided, video will be stored
            in a temporary directory and will be cleaned up after use.
            (default: :obj:`None`)
    """

    @dependencies_required("ffmpeg")
    def __init__(
        self,
        download_directory: Optional[str] = None,
    ) -> None:
        self._cleanup = download_directory is None

        self._download_directory = Path(
            download_directory or tempfile.mkdtemp()
        ).resolve()

        self.video_downloader_toolkit = VideoDownloaderToolkit(
            download_directory=str(self._download_directory)
        )

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
        self.audio_models = OpenAIAudioModels()

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

    def _transcribe_audio(self, audio_path: str) -> str:
        r"""Transcribe the audio of the video."""
        audio_transcript = self.audio_models.speech_to_text(audio_path)
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

        from urllib.parse import urlparse

        parsed_url = urlparse(video_path)
        is_url = all([parsed_url.scheme, parsed_url.netloc])

        if is_url:
            video_path = self.video_downloader_toolkit.download_video(
                video_path
            )
        audio_path = self._extract_audio_from_video(video_path)

        total_frames = 100
        video_frames = self.video_downloader_toolkit.get_video_screenshots(
            video_path, total_frames
        )

        audio_transcript = self._transcribe_audio(audio_path)

        prompt = VIDEO_QA_PROMPT.format(
            audio_transcription=audio_transcript,
            question=question,
        )

        msg = BaseMessage.make_user_message(
            role_name="User",
            content=prompt,
            image_list=video_frames,
        )

        response = self.vl_agent.step(msg)
        answer = response.msgs[0].content

        return answer

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the
        functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects representing
                the functions in the toolkit.
        """
        return [FunctionTool(self.ask_question_about_video)]
