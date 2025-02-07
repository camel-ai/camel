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
import random

from pytube import Search
from youtube_transcript_api import YouTubeTranscriptApi

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType


def get_youtube_transcript(query: str) -> str:
    """
    Use the query to search for a YouTube video and get the transcript.

    Args:
        query: The query to search for a YouTube video.

    Returns:
        The title and transcript of the YouTube video.
    """
    search = Search(query)
    random.shuffle(search.results)
    for video in search.results:
        try:
            srt = YouTubeTranscriptApi.get_transcript(video.video_id)
            title = video.title
            transcript = " ".join([f"{item['text']}" for item in srt])
            return f"Title: {title}\n\nTranscript: {transcript}"
        except Exception:
            continue


model = ModelFactory.create(
    model_platform=ModelPlatformType.DEEPSEEK,
    model_type=ModelType.DEEPSEEK_CHAT,
)

agent = ChatAgent(
    (
        "You are a helpful assistant that can summarize the transcript of a"
        " YouTube video."
    ),
    model=model,
    tools=[get_youtube_transcript],
)

resp = agent.step(
    "Hi! Can you find a youtube video about Hollow Knight and summarize it?"
)

print(resp.msg.content)
print("-" * 100)

history, _ = agent.memory.get_context()
print("\n".join([f"{item['role']}: {item['content']}" for item in history]))
