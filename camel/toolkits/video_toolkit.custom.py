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
import os
import subprocess
from pathlib import Path
from typing import List, Optional
from .audio_toolkit import AudioToolkit

from PIL import Image

from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.utils import dependencies_required

# logger = logging.getLogger(__name__)
from loguru import logger
from transformers import Qwen2VLForConditionalGeneration, AutoTokenizer, AutoProcessor
from qwen_vl_utils import process_vision_info
import cv2
from loguru import logger
from datetime import datetime
from retry import retry


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
        cache_dir (Optional[str], optional): The directory to cache the model.
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
        self._audio_toolkit = AudioToolkit(cache_dir=cache_dir)

        download_directory = "tmp/"

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

        logger.info(f"Video will be downloaded into {self._download_directory}")

        # initialize model for video understanding
        self.model = Qwen2VLForConditionalGeneration.from_pretrained(
            "Qwen/Qwen2-VL-7B-Instruct", 
            attn_implementation="flash_attention_2",
            torch_dtype="auto", 
            device_map="auto",
            cache_dir=cache_dir
        )
        self.processor = AutoProcessor.from_pretrained("Qwen/Qwen2-VL-7B-Instruct", cache_dir=cache_dir)

    
    def _ask_vllm(self, video_path: str, question: str) -> str:
        r"""Ask a question about the video using VLLM.

        Args:
            video_path (str): The path to the video file.
            question (str): The question to ask about the video.
        
        Returns:
            str: The answer to the question.
        """
        prompt = f"{question} Please answer the question based on the video content and give your reason. If you think you cannot answer the question based on the vision information, please give your reason (e.g. audio is required)."
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "video",
                        "video": video_path,
                        "max_pixels": 512*28*28,
                        "fps": 2,
                    },
                    {
                        "type": "text", 
                        "text": prompt
                    },
                ],
            }
        ]

        text = self.processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        image_inputs, video_inputs = process_vision_info(messages)

        inputs = self.processor(
            text=[text],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt",
        )
        inputs = inputs.to("cuda")

        generated_ids = self.model.generate(**inputs, max_new_tokens=512)
        generated_ids_trimmed = [
            out_ids[len(in_ids) :] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]
        output_text = self.processor.batch_decode(
            generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
        )
        return output_text[0]


    def _get_formatted_time(self) -> str:
        import time
        return time.strftime("%m%d-%H%M")

    @retry()
    def _download_video(self, url: str) -> str:
        r"""Download the video and optionally split it into chunks.

        yt-dlp will detect if the video is downloaded automatically so there
        is no need to check if the video exists.

        Returns:
            str: The path to the downloaded video file.
        """
        import yt_dlp

        # Get the current time and format it as 'YYYYMMDDHHMM'
        current_time = datetime.now().strftime("%Y%m%d%H%M")
        # get title of the video


        # Define the custom file name using the current time
        video_template = self._download_directory / f"{current_time}.%(ext)s"

        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',
            'outtmpl': str(video_template),  # Use the formatted current time as file name
            'force_generic_extractor': True,
            'cookiefile': self._cookies_path,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Download the video and get the filename
                logger.info(f"Downloading video from {url}...")
                info = ydl.extract_info(url, download=True)
                # Prepare the filename after download
                filename = ydl.prepare_filename(info)
                return filename  # Return the custom file path
        except yt_dlp.utils.DownloadError as e:
            raise RuntimeError(f"Failed to download video from {url}: {e}")


    def _extract_audio_from_video(self, video_file_path: str) -> str:
        r"""Extract audio from video and convert it to text.

        Args:
            video_file_path (str): The path to the video file.

        Returns:
            str: The extracted text from the audio of the video.
        """

        file_name = os.path.basename(video_file_path).split(".")[0]
        output_file_path = f"tmp/{file_name}.mp3"

        if os.path.exists(output_file_path):
            os.remove(output_file_path)
        
        # cmd = f'ffmpeg -i "{video_file_path}" -vn -acodec pcm_s16le -ar 44100 -ab 160k -ac 2 "{output_file_path}"'
        cmd = f'ffmpeg -i "{video_file_path}" -vn -acodec libmp3lame -ar 44100 -ab 160k -ac 2 "{output_file_path}"'

        subprocess.call(cmd, shell=True)

        return output_file_path
    

    def ask_question_about_video(self, video_path: str, question: str) -> str:
        r"""Ask a question about the video.

        Args:
            video_path (str): The path to the video file. It can be a local file or a URL.
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
        
        audio_file_path = self._extract_audio_from_video(video_path)
        
        vision_answer = self._ask_vllm(video_path, question)
        audio_answer = self._audio_toolkit.ask_question_about_audio(audio_file_path, question)

        return_text = f"""
            Here is the answer from the vision model:
            ```
            {vision_answer}
            ```
            Here is the answer from the audio model:
            ```
            {audio_answer}
            ```
            Please note that the vision model can only process visual information, and the audio model can only process audio information.
            Thus, You need to decide whether the questions you ask should focus on the visual model or the extracted audio text information, and make final answer by yourself.
        """
        logger.debug(f"Answer to the question: {return_text}")
        return return_text


    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the
        functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects representing
                the functions in the toolkit.
        """
        return [
            FunctionTool(self.ask_question_about_video),
            # FunctionTool(self._ask_vllm),
        ]
