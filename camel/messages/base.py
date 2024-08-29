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
import base64
import io
import uuid
import requests
import logging
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from pydantic import UUID4, BaseModel, Field

from camel.messages import (
    OpenAIAssistantMessage,
    OpenAIMessage,
    OpenAISystemMessage,
    OpenAIUserMessage,
)
from camel.prompts import CodePrompt, TextPrompt
from camel.types import MessageType, OpenAIBackendRole, RoleType
from camel.utils import Constants

logger = logging.getLogger(__name__)


class Sender(BaseModel):
    id: str


class Receiver(BaseModel):
    id: str


class Content(BaseModel):
    text: Optional[str] = Field(default="")
    image_url: Optional[List[str]] = Field(default_factory=list)
    image_detail: str = Field(default="auto")
    video_url: Optional[List[str]] = Field(default_factory=list)
    video_detail: str = Field(default="low")
    audio_url: Optional[List[str]] = Field(default_factory=list)


class Envelope(BaseModel):
    time_sent: str


class ACLParameter(BaseModel):
    sender: Optional[Sender] = None
    receiver: Optional[Union[Receiver, Tuple[Receiver, ...]]] = None
    subject: Optional[str] = None
    reply_with: Optional[Content] = None
    in_reply_to: Optional[UUID4] = None
    envelope: Optional[Envelope] = None
    language: str = Field(default="en")
    ontology: Optional[str] = None
    protocol: Optional[Dict[str, str]] = None
    message_type: MessageType = MessageType.DEFAULT


class BaseMessage(BaseModel):
    role_name: str
    role_type: RoleType
    content: Content
    meta_dict: Optional[Dict[str, str]] = None
    acl_params: Optional[ACLParameter] = None
    message_id: UUID4 = Field(
        default_factory=uuid.uuid4,
        description="Unique identifier for the message, not set by user.",
    )
    conversation_id: Optional[UUID4] = Field(
        default=None,
        description="Unique identifier for the conversation, \
        need set by user.",
    )

    @classmethod
    def make_user_message(
        cls,
        role_name: str,
        content: Content,
        conversation_id: Optional[UUID4] = None,
        meta_dict: Optional[Dict[str, str]] = None,
        acl_params: Optional[ACLParameter] = None,
    ) -> "BaseMessage":
        return cls(
            role_name=role_name,
            role_type=RoleType.USER,
            conversation_id=conversation_id,
            content=content,
            meta_dict=meta_dict,
            acl_params=acl_params,
        )

    @classmethod
    def make_assistant_message(
        cls,
        role_name: str,
        content: Content,
        conversation_id: Optional[UUID4] = None,
        meta_dict: Optional[Dict[str, str]] = None,
        acl_params: Optional[ACLParameter] = None,
    ) -> "BaseMessage":
        return cls(
            role_name=role_name,
            role_type=RoleType.USER,
            conversation_id=conversation_id,
            content=content,
            meta_dict=meta_dict,
            acl_params=acl_params,
        )

    def create_new_instance(self, content: Content) -> "BaseMessage":
        return self.model_copy(update={"content": content})

    def __add__(self, other: Any) -> Union["BaseMessage", Any]:
        if isinstance(other, BaseMessage):
            new_content = Content(
                text=(self.content.text or "") + (other.content.text or ""),
                image_url=(self.content.image_url or [])
                + (other.content.image_url or []),
                video_url=(self.content.video_url or [])
                + (other.content.video_url or []),
                audio_url=(self.content.audio_url or [])
                + (other.content.audio_url or []),
            )
            return self.create_new_instance(new_content)
        raise TypeError(
            f"Unsupported operand type(s) for"
            f" +: '{type(self)}' and '{type(other)}'"
        )

    def __mul__(self, other: Any) -> Union["BaseMessage", Any]:
        if isinstance(other, int):
            new_content = Content(
                text=(self.content.text or "") * other,
                image_url=(self.content.image_url or []) * other,
                video_url=(self.content.video_url or []) * other,
                audio_url=(self.content.audio_url or []) * other,
            )
            return self.create_new_instance(new_content)
        raise TypeError(
            f"Unsupported operand type(s) for *:"
            f" '{type(self)}' and '{type(other)}'"
        )

    def __len__(self) -> int:
        return sum(
            len(getattr(self.content, attr) or [])
            for attr in ["text", "image_url", "video_url", "audio_url"]
        )

    def __contains__(self, item: str) -> bool:
        return any(
            item in getattr(self.content, attr) or []
            for attr in ["text", "image_url", "video_url", "audio_url"]
        )

    def extract_text_and_code_prompts(
        self,
    ) -> Tuple[List[TextPrompt], List[CodePrompt]]:
        text_prompts: List[TextPrompt] = []
        code_prompts: List[CodePrompt] = []
        text = self.content.text or ""
        lines = text.split("\n")
        idx = 0
        start_idx = 0
        while idx < len(lines):
            while idx < len(lines) and not lines[idx].lstrip().startswith(
                "```"
            ):
                idx += 1
            txt = "\n".join(lines[start_idx:idx]).strip()
            if txt:
                text_prompts.append(TextPrompt(txt))
            if idx >= len(lines):
                break
            code_type = lines[idx].strip()[3:].strip()
            idx += 1
            start_idx = idx
            while idx < len(lines) and not lines[idx].lstrip().startswith(
                "```"
            ):
                idx += 1
            code = "\n".join(lines[start_idx:idx]).strip()
            if code:
                code_prompts.append(CodePrompt(code, code_type=code_type))
            idx += 1
            start_idx = idx
        return text_prompts, code_prompts

    def to_openai_message(
        self, role_at_backend: OpenAIBackendRole
    ) -> OpenAIMessage:
        if role_at_backend == OpenAIBackendRole.SYSTEM:
            return self.to_openai_system_message()
        if role_at_backend == OpenAIBackendRole.USER:
            return self.to_openai_user_message()
        if role_at_backend == OpenAIBackendRole.ASSISTANT:
            return self.to_openai_assistant_message()
        raise ValueError(f"Unsupported role: {role_at_backend}.")

    def to_openai_system_message(self) -> OpenAISystemMessage:
        return OpenAISystemMessage(
            role="system",
            content=self.content.text or "",
        )

    def to_openai_user_message(self) -> OpenAIUserMessage:
        hybrid_content: List[Any] = []
        if self.content.audio_url:
            from camel.models.openai_audio_models import OpenAIAudioModels

            audio_models = OpenAIAudioModels()
            # step 1 download audio file to local path
            audio_file_path = self._download_file_to_local(
                url=self.content.audio_url)
            
            self.content.text = audio_models.speech_to_text(
                audio_file_path)
            
        if self.content.text:
            hybrid_content.append(
                {
                    "type": "text",
                    "text": self.content.text,
                }
            )

        if self.content.image_url:
            for url in self.content.image_url:
                hybrid_content.append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": url,
                            "detail": self.content.image_detail,
                        },
                    }
                )

        if self.content.video_url:
            for video_url in self.content.video_url:
                base64_frames = self._extract_frames_from_video(video_url)
                for encoded_img in base64_frames:
                    hybrid_content.append(
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{encoded_img}",
                                "detail": self.content.video_detail,
                            },
                        }
                    )
        if self.content.audio_url:
            hybrid_content.append(
                [
                    {"type": "audio_url", "audio_url": {"url": url}}
                    for url in self.content.audio_url
                ]
            )
        return OpenAIUserMessage(role="user", content=hybrid_content)

    def to_openai_assistant_message(self) -> OpenAIAssistantMessage:
        return OpenAIAssistantMessage(
            role="assistant",
            content=self.content.text or "",
        )
    
    def _download_file_to_local(self, url, save_path="./"):
        try:
            from urllib.parse import urlparse
            # Parse the URL to get the file name
            parsed_url = urlparse(url)
            file_name = parsed_url.path.split('/')[-1]  # Extract the file name from the URL
            
            # Construct the complete save path
            full_save_path = f"{save_path.rstrip('/')}/{file_name}"
            
            # Send a GET request to the URL
            response = requests.get(url, stream=True)
            
            # Check if the request was successful
            if response.status_code == 200:
                # Open a file to write the data
                with open(full_save_path, 'wb') as f:
                    # Write the file in chunks to avoid high memory usage
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:
                            f.write(chunk)
                logger.info(f"File successfully downloaded to {full_save_path}")
                return full_save_path  
            else:
                logger.warning("Failed to download, status code: "
                            f"{response.status_code}")
        except Exception as e:
            logger.error(f"An error occurred: {e}")
        
        return None 

    def _extract_frames_from_video(self, video_url: str) -> List[str]:
        import imageio.v3 as iio
        from PIL import Image

        response = requests.get(video_url, stream=True)
        if response.status_code == 200:
            video_bytes = response.content
            base64_frames: List[str] = []
            frame_count = 0
            video = iio.imiter(
                video_bytes, plugin=Constants.VIDEO_DEFAULT_PLUG_PYAV
            )
            for frame in video:
                frame_count += 1
                if (
                    frame_count % Constants.VIDEO_IMAGE_EXTRACTION_INTERVAL
                    == 0
                ):
                    frame_array = np.asarray(frame)
                    frame_image = Image.fromarray(frame_array)
                    width, height = frame_image.size
                    new_width = Constants.VIDEO_DEFAULT_IMAGE_SIZE
                    aspect_ratio = width / height
                    new_height = int(new_width / aspect_ratio)
                    resized_img = frame_image.resize((new_width, new_height))
                    with io.BytesIO() as buffer:
                        resized_img.save(fp=buffer, format="JPEG")
                        encoded_image = base64.b64encode(
                            buffer.getvalue()
                        ).decode("utf-8")
                    base64_frames.append(encoded_image)
            return base64_frames
        return []

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()
