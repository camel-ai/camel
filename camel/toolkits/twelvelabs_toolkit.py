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

import os
from typing import Any, Dict, List, Optional

from camel.logger import get_logger
from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.utils import MCPServer, api_keys_required, dependencies_required

logger = get_logger(__name__)


@MCPServer()
class TwelveLabsToolkit(BaseToolkit):
    r"""A toolkit for video understanding powered by TwelveLabs' Pegasus
    video-language model.

    Unlike frame-sampling approaches, Pegasus reasons natively over the video
    (visuals, motion, and audio), which lets an agent answer questions about,
    summarize, or extract information from a video given only its URL. This is
    useful in multi-agent tasks where one agent needs to ground its reasoning
    in video content.

    Get a free API key at https://twelvelabs.io (generous free tier).

    Args:
        api_key (Optional[str], optional): The TwelveLabs API key. If not
            provided, it is read from the :obj:`TWELVELABS_API_KEY`
            environment variable. (default: :obj:`None`)
        model_name (str, optional): The Pegasus model to use for analysis.
            (default: :obj:`"pegasus1.5"`)
        max_tokens (int, optional): The maximum number of tokens to generate
            in a response. (default: :obj:`2048`)
        timeout (Optional[float], optional): The timeout value for API
            requests in seconds. If :obj:`None`, no timeout is applied.
            (default: :obj:`None`)
    """

    @api_keys_required([("api_key", "TWELVELABS_API_KEY")])
    @dependencies_required("twelvelabs")
    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "pegasus1.5",
        max_tokens: int = 2048,
        timeout: Optional[float] = None,
    ) -> None:
        super().__init__(timeout=timeout)
        self.api_key = api_key or os.environ.get("TWELVELABS_API_KEY")
        self.model_name = model_name
        self.max_tokens = max_tokens
        self._client = None

    @property
    def client(self):
        r"""Lazily initialise and cache the TwelveLabs client."""
        if self._client is None:
            from twelvelabs import TwelveLabs

            self._client = TwelveLabs(api_key=self.api_key)
        return self._client

    def _analyze(
        self,
        prompt: str,
        video_url: Optional[str] = None,
        video_id: Optional[str] = None,
    ) -> str:
        r"""Run a Pegasus analysis on a video given either a public URL or an
        indexed video id, and return the generated text.
        """
        if not video_url and not video_id:
            return "Error: provide either video_url or video_id."

        try:
            kwargs: Dict[str, Any] = {
                "model_name": self.model_name,
                "prompt": prompt,
                "max_tokens": self.max_tokens,
            }
            if video_id:
                kwargs["video_id"] = video_id
            else:
                from twelvelabs.types import VideoContext_Url

                kwargs["video"] = VideoContext_Url(url=video_url)  # type: ignore[arg-type]

            response = self.client.analyze(**kwargs)
            text = response.data
            if not text:
                logger.warning("Pegasus returned an empty response.")
                return "No analysis was generated for the video."
            return text
        except Exception as e:
            error_message = f"Error analyzing video with TwelveLabs: {e}"
            logger.error(error_message)
            return f"Error: {error_message}"

    def ask_question_about_video(
        self,
        question: str,
        video_url: Optional[str] = None,
        video_id: Optional[str] = None,
    ) -> str:
        r"""Ask a free-form question about a video using Pegasus.

        Provide exactly one of :obj:`video_url` (a publicly accessible video
        URL, analysed server-side without downloading) or :obj:`video_id` (a
        video already indexed in your TwelveLabs account).

        Args:
            question (str): The question to ask about the video.
            video_url (Optional[str]): A public URL of the video to analyse.
                (default: :obj:`None`)
            video_id (Optional[str]): The id of a video already indexed in
                TwelveLabs. (default: :obj:`None`)

        Returns:
            str: Pegasus' answer to the question, or an error message.
        """
        return self._analyze(
            prompt=question, video_url=video_url, video_id=video_id
        )

    def summarize_video(
        self,
        video_url: Optional[str] = None,
        video_id: Optional[str] = None,
        prompt: str = "Summarize this video in a few concise paragraphs.",
    ) -> str:
        r"""Generate a summary of a video using Pegasus.

        Provide exactly one of :obj:`video_url` (a publicly accessible video
        URL, analysed server-side without downloading) or :obj:`video_id` (a
        video already indexed in your TwelveLabs account).

        Args:
            video_url (Optional[str]): A public URL of the video to summarize.
                (default: :obj:`None`)
            video_id (Optional[str]): The id of a video already indexed in
                TwelveLabs. (default: :obj:`None`)
            prompt (str): The instruction used to guide the summary.
                (default: :obj:`"Summarize this video in a few concise
                paragraphs."`)

        Returns:
            str: The generated summary, or an error message.
        """
        return self._analyze(
            prompt=prompt, video_url=video_url, video_id=video_id
        )

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the
        functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects representing
                the functions in the toolkit.
        """
        return [
            FunctionTool(self.ask_question_about_video),
            FunctionTool(self.summarize_video),
        ]
