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
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

import numpy as np
from pydantic import BaseModel

from camel.messages import (
    OpenAIAssistantMessage,
    OpenAIMessage,
    OpenAISystemMessage,
    OpenAIUserMessage,
)
from camel.prompts import CodePrompt, TextPrompt
from camel.types import (
    OpenAIBackendRole,
    RoleType,
)
from camel.utils import Constants


class BaseMessage(BaseModel):
    r"""Base class for message objects used in CAMEL chat system.

    Args:
        role_name (str): The name of the user or assistant role.
        role_type (RoleType): The type of role, either :obj:`RoleType.
            ASSISTANT` or :obj:`RoleType.USER`.
        meta_dict (Optional[Dict[str, str]]): Additional metadata dictionary
            for the message.
        content (str): The content of the message.
        video_bytes (Optional[str]): Optional bytes of a video associated
            with the message. Default is None.
        image_bytes_list (Optional[List[str]]): Optional list of image base64
            bytes associated with the message. Default is None.
        image_detail (Literal["auto", "low", "high"]): Detail level of the
            images associated with the message. Default is "auto".
        video_detail (Literal["auto", "low", "high"]): Detail level of the
            videos associated with the message. Default is "low".
    """

    role_name: str
    role_type: RoleType
    meta_dict: Optional[Dict[str, str]]
    content: str
    video_bytes: Optional[str] = None
    image_bytes_list: Optional[List[str]] = None
    image_detail: Literal["auto", "low", "high"] = "auto"
    video_detail: Literal["auto", "low", "high"] = "low"

    @classmethod
    def make_user_message(
        cls,
        role_name: str,
        content: str,
        meta_dict: Optional[Dict[str, str]] = None,
        video_bytes: Optional[str] = None,
        image_bytes_list: Optional[List[str]] = None,
        image_detail: Literal["auto", "low", "high"] = "auto",
        video_detail: Literal["auto", "low", "high"] = "low",
    ) -> "BaseMessage":
        return cls(
            role_name=role_name,
            role_type=RoleType.USER,
            meta_dict=meta_dict,
            content=content,
            video_bytes=video_bytes,
            image_bytes_list=image_bytes_list,
            image_detail=image_detail,
            video_detail=video_detail,
        )

    @classmethod
    def make_assistant_message(
        cls,
        role_name: str,
        content: str,
        meta_dict: Optional[Dict[str, str]] = None,
        video_bytes: Optional[str] = None,
        image_bytes_list: Optional[List[str]] = None,
        image_detail: Literal["auto", "low", "high"] = "auto",
        video_detail: Literal["auto", "low", "high"] = "low",
    ) -> "BaseMessage":
        return cls(
            role_name=role_name,
            role_type=RoleType.USER,
            meta_dict=meta_dict,
            content=content,
            video_bytes=video_bytes,
            image_bytes_list=image_bytes_list,
            image_detail=image_detail,
            video_detail=video_detail,
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
        hybird_content: List[Any] = []
        hybird_content.append(
            {
                "type": "text",
                "text": self.content,
            }
        )

        if self.image_bytes_list and len(self.image_bytes_list) > 0:
            for encoded_image in self.image_bytes_list:
                hybird_content.append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{encoded_image}",
                            "detail": self.image_detail,
                        },
                    }
                )

        if self.video_bytes:
            import imageio.v3 as iio
            from PIL import Image

            base64Frames: List[str] = []
            frame_count = 0
            # read video bytes
            video = iio.imiter(
                self.video_bytes, plugin=Constants.VIDEO_DEFAULT_PLUG_PYAV
            )

            for frame in video:
                frame_count += 1
                if (
                    frame_count % Constants.VIDEO_IMAGE_EXTRACTION_INTERVAL
                    == 0
                ):
                    # convert frame to numpy array
                    frame_array = np.asarray(frame)
                    frame_image = Image.fromarray(frame_array)

                    # Get the dimensions of the frame
                    width, height = frame_image.size

                    # resize the frame to the default image size
                    new_width = Constants.VIDEO_DEFAULT_IMAGE_SIZE
                    aspect_ratio = width / height
                    new_height = int(new_width / aspect_ratio)
                    resized_img = frame_image.resize((new_width, new_height))

                    # encode the image to base64
                    with io.BytesIO() as buffer:
                        resized_img.save(fp=buffer, format="JPEG")
                        encoded_image = base64.b64encode(
                            buffer.getvalue()
                        ).decode("utf-8")

                    base64Frames.append(encoded_image)

            for encoded_image in base64Frames:
                item = {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{encoded_image}",
                        "detail": self.video_detail,
                    },
                }

                hybird_content.append(item)

        if len(hybird_content) > 1:
            return {
                "role": "user",
                "content": hybird_content,
            }
        # This return just for str message
        else:
            return {
                "role": "user",
                "content": self.content,
            }

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
