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

import os
import tempfile
from pathlib import Path
from typing import List, Optional

from PIL import Image

from camel.logger import get_logger
from camel.messages import BaseMessage
from camel.models import BaseModelBackend, OpenAIAudioModels
from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.utils import dependencies_required

from .video_download_toolkit import (
    VideoDownloaderToolkit,
    _capture_screenshot,
)

logger = get_logger(__name__)

VIDEO_QA_PROMPT = """
Analyze the provided video frames and corresponding audio transcription to \
answer the given question(s) thoroughly and accurately.

Instructions:
    1. Visual Analysis:
        - Examine the video frames to identify visible entities.
        - Differentiate objects, species, or features based on key attributes \
such as size, color, shape, texture, or behavior.
        - Note significant groupings, interactions, or contextual patterns \
relevant to the analysis.

    2. Audio Integration:
        - Use the audio transcription to complement or clarify your visual \
observations.
        - Identify names, descriptions, or contextual hints in the \
transcription that help confirm or refine your visual analysis.

    3. Detailed Reasoning and Justification:
        - Provide a brief explanation of how you identified and distinguished \
each species or object.
        - Highlight specific features or contextual clues that informed \
your reasoning.

    4. Comprehensive Answer:
        - Specify the total number of distinct species or object types \
identified in the video.
        - Describe the defining characteristics and any supporting evidence \
from the video and transcription.

    5. Important Considerations:
        - Pay close attention to subtle differences that could distinguish \
similar-looking species or objects 
          (e.g., juveniles vs. adults, closely related species).
        - Provide concise yet complete explanations to ensure clarity.

**Audio Transcription:**
{audio_transcription}

**Question:**
{question}
"""


class VideoAnalysisToolkit(BaseToolkit):
    r"""A class for analysing videos with vision-language model.

    Args:
        download_directory (Optional[str], optional): The directory where the
            video will be downloaded to. If not provided, video will be stored
            in a temporary directory and will be cleaned up after use.
            (default: :obj:`None`)
        model (Optional[BaseModelBackend], optional): The model to use for
            visual analysis. (default: :obj:`None`)
        use_audio_transcription (bool, optional): Whether to enable audio
            transcription using OpenAI's audio models. Requires a valid OpenAI
            API key. When disabled, video analysis will be based solely on
            visual content. (default: :obj:`False`)
    """

    @dependencies_required("ffmpeg", "scenedetect")
    def __init__(
        self,
        download_directory: Optional[str] = None,
        model: Optional[BaseModelBackend] = None,
        use_audio_transcription: bool = False,
    ) -> None:
        self._cleanup = download_directory is None
        self._temp_files: list[str] = []  # Track temporary files for cleanup
        self._use_audio_transcription = use_audio_transcription

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

        self.vl_model = model
        # Ensure ChatAgent is initialized with a model if provided
        if self.vl_model:
            # Import ChatAgent at runtime to avoid circular imports
            from camel.agents import ChatAgent

            self.vl_agent = ChatAgent(model=self.vl_model)
        else:
            # If no model is provided, use default model in ChatAgent
            # Import ChatAgent at runtime to avoid circular imports
            from camel.agents import ChatAgent

            self.vl_agent = ChatAgent()
            logger.warning(
                "No vision-language model provided. Using default model in"
                " ChatAgent."
            )

        # Initialize audio models only if audio transcription is enabled
        self.audio_models = None
        if self._use_audio_transcription:
            try:
                self.audio_models = OpenAIAudioModels()
            except Exception as e:
                logger.warning(
                    f"Failed to initialize OpenAIAudioModels: {e}. "
                    "Audio transcription will be disabled."
                )
                self._use_audio_transcription = False

    def __del__(self):
        r"""Clean up temporary directories and files when the object is
        destroyed.
        """
        # Clean up temporary files
        for temp_file in self._temp_files:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                    logger.debug(f"Removed temporary file: {temp_file}")
                except OSError as e:
                    logger.warning(
                        f"Failed to remove temporary file {temp_file}: {e}"
                    )

        # Clean up temporary directory if needed
        if self._cleanup and os.path.exists(self._download_directory):
            try:
                import shutil

                shutil.rmtree(self._download_directory)
                logger.debug(
                    f"Removed temporary directory: {self._download_directory}"
                )
            except OSError as e:
                logger.warning(
                    f"Failed to remove temporary directory"
                    f" {self._download_directory}: {e}"
                )

    def _extract_audio_from_video(
        self, video_path: str, output_format: str = "mp3"
    ) -> str:
        r"""Extract audio from the video.

        Args:
            video_path (str): The path to the video file.
            output_format (str): The format of the audio file to be saved.
                (default: :obj:`"mp3"`)

        Returns:
            str: The path to the audio file.
        """
        import ffmpeg

        # Handle case where video file doesn't have an extension
        base_path = os.path.splitext(video_path)[0]
        output_path = f"{base_path}.{output_format}"

        if os.path.exists(output_path):
            return output_path
        try:
            (
                ffmpeg.input(video_path)
                .output(output_path, vn=None, acodec="libmp3lame")
                .run(quiet=True)
            )
            # Track the audio file for cleanup
            self._temp_files.append(output_path)
            return output_path
        except ffmpeg.Error as e:
            error_message = f"FFmpeg-Python failed: {e}"
            logger.error(error_message)
            raise RuntimeError(error_message)
        

    def convert_webm_to_mp4(self, video_path: str) -> str:
        r"""Convert a .webm video file to .mp4 format.

        Args:
            video_path (str): The path to the .webm video file.

        Returns:
            str: The path to the converted .mp4 file.

        Raises:
            RuntimeError: If the conversion fails.
        """
        import ffmpeg
        # 检查文件是否存在
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        # 检查文件是否为 .webm 格式
        if not video_path.lower().endswith(".webm"):
            raise ValueError(f"File is not a .webm video: {video_path}")

        # 生成输出文件路径
        output_path = video_path.rsplit('.', 1)[0]  ".mp4"

        # 如果输出文件已存在，直接返回
        if os.path.exists(output_path):
            return output_path

        try:
            # 使用 FFmpeg 转换格式
            (
                ffmpeg.input(video_path)
                .output(output_path, vcodec="libx264", acodec="aac")
                .run()
            )
            return output_path
        except ffmpeg.Error as e:
            raise RuntimeError(f"FFmpeg-Python failed: {e}")

    def split_audio_segments(self, video_path, segment_duration=60 * 2, sample_rate=16000):
        """
        将视频中的音频拆分为多个大小相同的片段，并保存为 WAV 格式。

        Args:
            video_path (str): 视频文件路径。
            output_dir (str): 输出目录路径。
            segment_duration (int): 每个音频片段的时长（秒）。
            sample_rate (int): 音频采样率（Hz）。

        Returns:
            List[str]: 生成的音频片段文件路径列表。
        """
        import os
        # 确保输出目录存在
        output_dir = os.path.dirname(video_path)

        # 生成输出文件模板
        output_template = os.path.join(output_dir, "segment_%03d.wav")

        # 使用 FFmpeg 拆分音频
        import ffmpeg
        try:
            (
                ffmpeg.input(video_path)
                .output(
                    output_template,
                    f="segment",  # 使用 segment 过滤器
                    segment_time=segment_duration,  # 每个片段的时长
                    acodec="pcm_s16le",  # 使用 WAV 格式的编码器
                    ar=sample_rate,  # 设置采样率
                    ac=1,  # 单声道（可选）
                )
                .run()
            )
        except ffmpeg.Error as e:
            raise RuntimeError(f"FFmpeg failed: {e}")
 
        # 返回生成的音频片段文件列表
        return sorted([os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.startswith("segment_")])
 

    def _transcribe_audio(self, segments: list[str]) -> str:
        r"""Transcribe the audio of the video."""
        # Check if audio transcription is enabled and audio models are
        # available
        if not self._use_audio_transcription or self.audio_models is None:
            logger.warning("Audio transcription is disabled or not available")
            return "No audio transcription available."

        try:
            result = ''
            for segment in segments:
                audio_transcript = self.audio_models.speech_to_text(segment)
                result += audio_transcript
            if not audio_transcript:
                logger.warning("Audio transcription returned empty result")
                return "No audio transcription available."
            return audio_transcript
        except Exception as e:
            logger.error(f"Audio transcription failed: {e}")
            try:
                audio_transcript = self.transcribe_audio_whisper(segments=segments)
                return audio_transcript
            except Exception as e:
                logger.warning("Audio transcription failed.")
                return None

    def transcribe_audio_whisper(self, segments, type='tiny'):
        import whisper
        from concurrent.futures import ProcessPoolExecutor
        import os
        import time

        # 设置 OpenMP 为单线程模式
        os.environ["OMP_NUM_THREADS"] = "1"

        # 加载 Whisper 模型
        start = time.time()
          # 显式使用 FP32

        def transcribe_segment(segment_path):
            # 禁用 FFmpeg 日志输出
            import whisper
            # whisper.transcribe = whisper.transcribe.DisableFFmpegLogging()
            model = whisper.load_model(type, device="cpu")
            # 转录音频片段
            result = model.transcribe(segment_path)
            return result['text']

        # 使用线程池并行转录
        results = []
        for segment_path in segments:
            result = transcribe_segment(segment_path)
            results.append(result)

        print(f'audio to txt cost {time.time() - start}')
        return results

    def _extract_keyframes(
        self, video_path: str, num_frames: int, threshold: float = 25.0
    ) -> List[Image.Image]:
        r"""Extract keyframes from a video based on scene changes
        and return them as PIL.Image.Image objects.

        Args:
            video_path (str): Path to the video file.
            num_frames (int): Number of keyframes to extract.
            threshold (float): The threshold value for scene change detection.

        Returns:
            list: A list of PIL.Image.Image objects representing
                the extracted keyframes.
        """
        from scenedetect import (  # type: ignore[import-untyped]
            SceneManager,
            VideoManager,
        )
        from scenedetect.detectors import (  # type: ignore[import-untyped]
            ContentDetector,
        )

        if num_frames <= 0:
            logger.warning(
                f"Invalid num_frames: {num_frames}, using default of 1"
            )
            num_frames = 1

        video_manager = VideoManager([video_path])
        scene_manager = SceneManager()
        scene_manager.add_detector(ContentDetector(threshold=threshold))

        video_manager.set_duration()
        video_manager.start()
        scene_manager.detect_scenes(video_manager)

        scenes = scene_manager.get_scene_list()
        keyframes: List[Image.Image] = []

        # Handle case where no scenes are detected
        if not scenes:
            logger.warning(
                "No scenes detected in video, capturing frames at "
                "regular intervals"
            )
            import cv2

            cap = cv2.VideoCapture(video_path)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            duration = total_frames / fps if fps > 0 else 0

            if duration > 0 and total_frames > 0:
                # Extract frames at regular intervals
                interval = duration / min(num_frames, total_frames)
                for i in range(min(num_frames, total_frames)):
                    time_sec = i * interval
                    frame = _capture_screenshot(video_path, time_sec)
                    keyframes.append(frame)

            cap.release()
        else:
            # Extract frames from detected scenes
            for start_time, _ in scenes:
                if len(keyframes) >= num_frames:
                    break
                frame = _capture_screenshot(video_path, start_time)
                keyframes.append(frame)

        if not keyframes:
            logger.error("Failed to extract any keyframes from video")
            raise ValueError("Failed to extract keyframes from video")

        logger.info(f"Extracted {len(keyframes)} keyframes")
        return keyframes

    def ask_question_about_video(
        self,
        video_path: str,
        question: str,
        num_frames: int = 28,
    ) -> str:
        r"""Ask a question about the video.

        Args:
            video_path (str): The path to the video file.
                It can be a local file or a URL (such as Youtube website).
            question (str): The question to ask about the video.
            num_frames (int): The number of frames to extract from the video.
                To be adjusted based on the length of the video.
                (default: :obj:`28`)

        Returns:
            str: The answer to the question.
        """
        from urllib.parse import urlparse

        if not question:
            raise ValueError("Question cannot be empty")

        if num_frames <= 0:
            logger.warning(
                f"Invalid num_frames: {num_frames}, using default of 28"
            )
            num_frames = 28

        parsed_url = urlparse(video_path)
        is_url = all([parsed_url.scheme, parsed_url.netloc])

        downloaded_video_path = None
        try:
            if is_url:
                downloaded_video_path = (
                    self.video_downloader_toolkit.download_video(video_path)
                )
                if not downloaded_video_path or not os.path.exists(
                    downloaded_video_path
                ):
                    raise ValueError(
                        f"Failed to download video from {video_path}"
                    )
                video_path = downloaded_video_path

            if not os.path.exists(video_path):
                raise FileNotFoundError(f"Video file not found: {video_path}")

            audio_transcript = "No audio transcription available."
            if self._use_audio_transcription:
                
                if video_path.lower().endswith(".webm"):
                    video_path = self.convert_webm_to_mp4(video_path=video_path)

                segments = self.split_audio_segments(video_path)
                audio_transcript = self._transcribe_audio(segments)

            video_frames = self._extract_keyframes(video_path, num_frames)
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
            if not response or not response.msgs:
                logger.error("Model returned empty response")
                return (
                    "Failed to generate an answer. "
                    "The model returned an empty response."
                )

            answer = response.msgs[0].content
            return answer

        except Exception as e:
            error_message = f"Error processing video: {e!s}"
            logger.error(error_message)
            return f"Error: {error_message}"

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the
        functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects representing
                the functions in the toolkit.
        """
        return [FunctionTool(self.ask_question_about_video)]
