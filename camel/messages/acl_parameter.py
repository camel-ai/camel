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
from pydantic import UUID4, BaseModel, Field, ConfigDict
from typing import Any, Dict, List, Optional, Tuple, Type, Union
import uuid
from camel.types import (
    RoleType,
    MessageType,
)
from camel.utils import get_local_time
from PIL import Image

class Sender(BaseModel):
    r"""Represents the sender of a message in the system.
    
    Attributes:
        id (UUID4): Unique identifier for the sender, automatically generated.
        name (str): Name of the sender.
        role_type (RoleType): Role type of the sender.
    """
    id: UUID4 = Field(
        default_factory=uuid.uuid4,
        description="Unique identifier for the sender, not set by user.",
    )
    """Name of the sender."""
    name: str
    """Role type of the sender."""
    role_type: RoleType
    
class Receiver(BaseModel):
    r"""Represents the receiver of a message in the system.
    
    Attributes:
        id (UUID4): Unique identifier for the receiver, automatically generated.
        name (str): Name of the receiver.
        role_type (RoleType): Role type of the receiver.
    """
    id: UUID4 = Field(
        default_factory=uuid.uuid4,
        description="Unique identifier for the receiver, not set by user.",
    )
    """Name of the receiver."""
    name: str
    """Role type of the receiver."""
    role_type: RoleType
    

class Envelope(BaseModel):
    r"""Represents the envelope containing metadata about a message.
    
    Attributes:
        time_sent (str): Timestamp indicating when the message was sent.
    """
    time_sent: str = Field(
        default_factory=get_local_time,
        description="Timestamp when the message was sented.",
    )

class Content(BaseModel):
    r"""Represents the content of a message, including text, images, videos, 
        and audio.
    
    Attributes:
        text (Optional[str]): Text content of the message.
        image_list (Optional[List[Image.Image]]): List of images included in 
            the message.
        image_detail (str): Level of detail for the images (e.g., "auto").
        video_bytes (Optional[bytes]): Binary data for video content.
        video_detail (str): Level of detail for the video (e.g., "low").
        audio_url (Optional[List[str]]): List of URLs pointing to audio 
            content.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    """Text content of the message."""
    text: Optional[str] = Field(default="")
    """List of images included in the message."""
    image_list: Optional[List[Image.Image]] = None
    """Level of detail for the images."""
    image_detail: str = Field(default="auto")
    """Binary data for video content."""
    video_bytes: Optional[bytes] = None
    """Level of detail for the video."""
    video_detail: str = Field(default="low")
    """List of URLs pointing to audio content."""
    audio_url: Optional[List[str]] = Field(default_factory=list)

class ACLParameter(BaseModel):
    r"""Represents the parameters for an ACL (Agent Communication Language) message.
    
    Attributes:
        sender (Optional[Sender]): Sender of the message.
        receiver (Optional[Union[Receiver, Tuple[Receiver, ...]]]): Receiver
            (s) of the message.
        subject (Optional[str]): Subject of the message.
        reply_with (Optional[Content]): Content of the reply message.
        in_reply_to (Optional[UUID4]): Identifier for the message being 
            replied to.
        envelope (Optional[Envelope]): Metadata about the message.
        language (str): Language used in the message.
        ontology (Optional[str]): Ontology used in the message.
        protocol (Optional[Dict[str, str]]): Protocol information for the 
            message.
        message_type (MessageType): Type of the message.
        conversation_id (Optional[UUID4]): Unique identifier for the 
            conversation.
    """
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
    conversation_id: Optional[UUID4] = Field(
        default=None,
        description="Unique identifier for the conversation, \
        need set by user.",
    )