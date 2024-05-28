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
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

import cv2
from PIL import Image

from camel.common import Constants
from camel.messages import (
    OpenAIAssistantMessage,
    OpenAIMessage,
    OpenAISystemMessage,
    OpenAIUserMessage,
)
from camel.prompts import CodePrompt, TextPrompt
from camel.types import (
    OpenAIBackendRole,
    OpenAIImageDetailType,
    OpenAIImageType,
    OpenAIVideoType,
    RoleType,
)


@dataclass
class BaseMessage:
    r"""Base class for message objects used in CAMEL chat system.

    Args:
        role_name (str): The name of the user or assistant role.
        role_type (RoleType): The type of role, either
            :obj:`RoleType.ASSISTANT` or :obj:`RoleType.USER`.
        meta_dict (Optional[Dict[str, str]]): Additional metadata dictionary
            for the message.
        content (str): The content of the message.
    """

    role_name: str
    role_type: RoleType
    meta_dict: Optional[Dict[str, str]]
    content: str
    video_path: Optional[str] = None
    image: Optional[Image.Image] = None
    image_detail: Literal["auto", "low", "high"] = "auto"

    @classmethod
    def make_user_message(
        cls,
        role_name: str,
        content: str,
        meta_dict: Optional[Dict[str, str]] = None,
        video_path: Optional[str] = None,
        image: Optional[Image.Image] = None,
        image_detail: Union[OpenAIImageDetailType, str] = "auto",
    ) -> "BaseMessage":
        return cls(
            role_name,
            RoleType.USER,
            meta_dict,
            content,
            video_path,
            image,
            OpenAIImageDetailType(image_detail).value,
        )

    @classmethod
    def make_assistant_message(
        cls,
        role_name: str,
        content: str,
        meta_dict: Optional[Dict[str, str]] = None,
        video_path: Optional[str] = None,
        image: Optional[Image.Image] = None,
        image_detail: Union[OpenAIImageDetailType, str] = "auto",
    ) -> "BaseMessage":
        return cls(
            role_name,
            RoleType.ASSISTANT,
            meta_dict,
            content,
            video_path,
            image,
            OpenAIImageDetailType(image_detail).value,
        )

    def create_new_instance(self, content: str) -> "BaseMessage":
        r"""Create a new instance of the :obj:`BaseMessage` with updated
        content.

        Args:
            content (str): The new content value.

        Returns:
            BaseMessage: The new instance of :obj:`BaseMessage`.
        """
        return self.__class__(
            role_name=self.role_name,
            role_type=self.role_type,
            meta_dict=self.meta_dict,
            content=content,
        )

    def __add__(self, other: Any) -> Union["BaseMessage", Any]:
        r"""Addition operator override for :obj:`BaseMessage`.

        Args:
            other (Any): The value to be added with.

        Returns:
            Union[BaseMessage, Any]: The result of the addition.
        """
        if isinstance(other, BaseMessage):
            combined_content = self.content.__add__(other.content)
        elif isinstance(other, str):
            combined_content = self.content.__add__(other)
        else:
            raise TypeError(
                f"Unsupported operand type(s) for +: '{type(self)}' and "
                f"'{type(other)}'"
            )
        return self.create_new_instance(combined_content)

    def __mul__(self, other: Any) -> Union["BaseMessage", Any]:
        r"""Multiplication operator override for :obj:`BaseMessage`.

        Args:
            other (Any): The value to be multiplied with.

        Returns:
            Union[BaseMessage, Any]: The result of the multiplication.
        """
        if isinstance(other, int):
            multiplied_content = self.content.__mul__(other)
            return self.create_new_instance(multiplied_content)
        else:
            raise TypeError(
                f"Unsupported operand type(s) for *: '{type(self)}' and "
                f"'{type(other)}'"
            )

    def __len__(self) -> int:
        r"""Length operator override for :obj:`BaseMessage`.

        Returns:
            int: The length of the content.
        """
        return len(self.content)

    def __contains__(self, item: str) -> bool:
        r"""Contains operator override for :obj:`BaseMessage`.

        Args:
            item (str): The item to check for containment.

        Returns:
            bool: :obj:`True` if the item is contained in the content,
                :obj:`False` otherwise.
        """
        return item in self.content

    def extract_text_and_code_prompts(
        self,
    ) -> Tuple[List[TextPrompt], List[CodePrompt]]:
        r"""Extract text and code prompts from the message content.

        Returns:
            Tuple[List[TextPrompt], List[CodePrompt]]: A tuple containing a
                list of text prompts and a list of code prompts extracted
                from the content.
        """
        text_prompts: List[TextPrompt] = []
        code_prompts: List[CodePrompt] = []

        lines = self.content.split("\n")
        idx = 0
        start_idx = 0
        while idx < len(lines):
            while idx < len(lines) and (
                not lines[idx].lstrip().startswith("```")
            ):
                idx += 1
            text = "\n".join(lines[start_idx:idx]).strip()
            text_prompts.append(TextPrompt(text))

            if idx >= len(lines):
                break

            code_type = lines[idx].strip()[3:].strip()
            idx += 1
            start_idx = idx
            while not lines[idx].lstrip().startswith("```"):
                idx += 1
            code = "\n".join(lines[start_idx:idx]).strip()
            code_prompts.append(CodePrompt(code, code_type=code_type))

            idx += 1
            start_idx = idx

        return text_prompts, code_prompts

    def to_openai_message(
        self,
        role_at_backend: OpenAIBackendRole,
    ) -> OpenAIMessage:
        r"""Converts the message to an :obj:`OpenAIMessage` object.

        Args:
            role_at_backend (OpenAIBackendRole): The role of the message in
                OpenAI chat system.

        Returns:
            OpenAIMessage: The converted :obj:`OpenAIMessage` object.
        """
        if role_at_backend == OpenAIBackendRole.SYSTEM:
            return self.to_openai_system_message()
        elif role_at_backend == OpenAIBackendRole.USER:
            return self.to_openai_user_message()
        elif role_at_backend == OpenAIBackendRole.ASSISTANT:
            return self.to_openai_assistant_message()
        else:
            raise ValueError(f"Unsupported role: {role_at_backend}.")

    def to_openai_system_message(self) -> OpenAISystemMessage:
        r"""Converts the message to an :obj:`OpenAISystemMessage` object.

        Returns:
            OpenAISystemMessage: The converted :obj:`OpenAISystemMessage`
                object.
        """
        return {"role": "system", "content": self.content}

    def to_openai_user_message(self) -> OpenAIUserMessage:
        r"""Converts the message to an :obj:`OpenAIUserMessage` object.

        Returns:
            OpenAIUserMessage: The converted :obj:`OpenAIUserMessage` object.
        """
        if self.image is not None:
            if self.image.format is None:
                raise ValueError(
                    f"Image's `format` is `None`, please "
                    f"transform the `PIL.Image.Image` to  one of "
                    f"following supported formats, such as "
                    f"{list(OpenAIImageType)}"
                )

            image_type: str = self.image.format.lower()
            if image_type not in OpenAIImageType:
                raise ValueError(
                    f"Image type {self.image.format} "
                    f"is not supported by OpenAI vision model"
                )
            with io.BytesIO() as buffer:
                self.image.save(fp=buffer, format=self.image.format)
                encoded_image = base64.b64encode(buffer.getvalue()).decode(
                    "utf-8"
                )
            image_prefix = f"data:image/{image_type};base64,"

            return {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": self.content,
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"{image_prefix}{encoded_image}",
                            "detail": self.image_detail,
                        },
                    },
                ],
            }
        elif self.video_path is not None:
            if not os.path.exists(self.video_path):
                raise FileNotFoundError(
                    f"Video file {self.video_path} does not exist."
                )

            video_format: str = self.video_path.split(".")[-1].lower()
            if video_format not in OpenAIVideoType:
                raise ValueError(
                    f"Video type {video_format} "
                    f"is not supported by OpenAI vision model"
                )

            base64Frames = []
            video = cv2.VideoCapture(self.video_path)
            while video.isOpened():
                success, frame = video.read()
                if not success:
                    break

                # Get the dimensions of the frame
                height, width = frame.shape[:2]

                # Calculate the new dimensions while maintaining the aspect ratio
                new_width = Constants.DEFAULT_IMAGE_SIZE
                aspect_ratio = width / height
                new_height = int(new_width / aspect_ratio)

                # Resize the frame
                resized_frame = cv2.resize(frame, (new_width, new_height))

                # Encode the frame as JPEG
                success, buffer = cv2.imencode(  # type: ignore[assignment]
                    f".{OpenAIImageType.JPEG}", resized_frame
                )

                # Convert the encoded frame to base64
                base64Frame = base64.b64encode(buffer).decode("utf-8")  # type: ignore[arg-type]

                # Append the base64 encoded frame to the list
                base64Frames.append(base64Frame)

            # Release the video capture object
            video.release()

            # Define a list to hold extracted images from base64Frames
            # Extract images at intervals specified by Constants.IMAGE_EXTRACTION_INTERVAL
            # Using list comprehension to select an image at each interval
            image_extraction_list = [
                x
                for x in base64Frames[0 :: Constants.IMAGE_EXTRACTION_INTERVAL]
            ]

            video_content: List[Any] = []
            video_content.append(
                {
                    "type": "text",
                    "text": "These are frames from a video that I want to upload. Generate a compelling description that I can upload along with the video.",
                }
            )
            for image in image_extraction_list:
                item = {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpg;base64,{image}",
                    },
                }
                video_content.append(item)
            return {
                "role": "user",
                "content": video_content,
            }

        else:
            return {"role": "user", "content": self.content}

    def to_openai_assistant_message(self) -> OpenAIAssistantMessage:
        r"""Converts the message to an :obj:`OpenAIAssistantMessage` object.

        Returns:
            OpenAIAssistantMessage: The converted :obj:`OpenAIAssistantMessage`
                object.
        """
        return {"role": "assistant", "content": self.content}

    def to_dict(self) -> Dict:
        r"""Converts the message to a dictionary.

        Returns:
            dict: The converted dictionary.
        """
        return {
            "role_name": self.role_name,
            "role_type": self.role_type.name,
            **(self.meta_dict or {}),
            "content": self.content,
        }
