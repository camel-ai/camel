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

# Enables postponed evaluation of annotations (for string-based type hints)
from __future__ import annotations

import logging
import time
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from typing import Any, ClassVar, Dict, Optional, Set
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from camel.messages import BaseMessage, FunctionCallingMessage, OpenAIMessage
from camel.types import OpenAIBackendRole, RoleType


class MemoryRecord(BaseModel):
    r"""The basic message storing unit in the CAMEL memory system.

    Attributes:
        message (BaseMessage): The main content of the record.
        role_at_backend (OpenAIBackendRole): An enumeration value representing
            the role this message played at the OpenAI backend. Note that this
            value is different from the :obj:`RoleType` used in the CAMEL role
            playing system.
        uuid (UUID, optional): A universally unique identifier for this record.
            This is used to uniquely identify this record in the memory system.
            If not given, it will be assigned with a random UUID.
        extra_info (Dict[str, str], optional): A dictionary of additional
            key-value pairs that provide more information. If not given, it
            will be an empty `Dict`.
        timestamp (float, optional): The timestamp when the record was created.
        agent_id (str): The identifier of the agent associated with this
            memory.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    message: BaseMessage
    role_at_backend: OpenAIBackendRole
    uuid: UUID = Field(default_factory=uuid4)
    extra_info: Dict[str, str] = Field(default_factory=dict)
    timestamp: float = Field(
        default_factory=lambda: time.time_ns()
        / 1_000_000_000  # Nanosecond precision
    )
    agent_id: str = Field(default="")

    _MESSAGE_TYPES: ClassVar[dict] = {
        "BaseMessage": BaseMessage,
        "FunctionCallingMessage": FunctionCallingMessage,
    }

    @staticmethod
    def _safe_enum_conversion(obj: Any, _seen: Optional[Set[int]] = None) -> Any:
        r"""Convert Enum values safely for JSON serialization with path-based cycle protection.
        
        - Converts Enums to their .value for JSON compatibility
        - Detects circular references along traversal paths and raises ValueError
        - Allows the same object to appear in different branches (not a cycle)
        - Supports dict, list, tuple, and other Mapping/Sequence containers
        - Excludes string/bytes which are Sequences but shouldn't be traversed
        
        Note: This performs path-based cycle detection, not full graph-level detection.
        The same object can safely appear in multiple branches of the data structure.
        """
        if isinstance(obj, Enum):
            return obj.value
        
        # Check for containers that could create cycles, excluding strings/bytes
        if isinstance(obj, (Mapping, Sequence)) and not isinstance(obj, (str, bytes)):
            if _seen is None:
                _seen = set()
            
            obj_id = id(obj)
            if obj_id in _seen:
                raise ValueError(
                    f"Circular reference detected in data structure. "
                    f"MemoryRecord cannot serialize self-referencing objects."
                )
            
            _seen.add(obj_id)
            try:
                if isinstance(obj, Mapping):
                    return {k: MemoryRecord._safe_enum_conversion(v, _seen) for k, v in obj.items()}
                else:  # Sequence (list, tuple, etc.)
                    converted = [MemoryRecord._safe_enum_conversion(v, _seen) for v in obj]
                    # JSON doesn't support tuples, convert to list for consistency
                    return converted
            finally:
                # Remove from seen set to allow same object in different branches
                _seen.discard(obj_id)
        
        return obj

    @classmethod
    def from_dict(cls, record_dict: Dict[str, Any]) -> "MemoryRecord":
        r"""Reconstruct a :obj:`MemoryRecord` from the input dict.

        Args:
            record_dict(Dict[str, Any]): A dict generated by :meth:`to_dict`.
        """
        message_cls = cls._MESSAGE_TYPES[record_dict["message"]["__class__"]]
        kwargs: Dict = record_dict["message"].copy()
        kwargs.pop("__class__")
        # Restore enums expected by BaseMessage
        if "role_type" in kwargs and isinstance(kwargs["role_type"], str):
            try:
                kwargs["role_type"] = RoleType(kwargs["role_type"]) 
            except ValueError as e:
                logging.warning(
                    f"Failed to restore RoleType from '{kwargs['role_type']}' for {message_cls.__name__}: {e}. "
                    "Falling back to RoleType.DEFAULT."
                )
                kwargs["role_type"] = RoleType.DEFAULT
        reconstructed_message = message_cls(**kwargs)

        # Restore OpenAIBackendRole with error handling and sensible fallback
        raw_backend_role = record_dict.get("role_at_backend")
        role_at_backend: OpenAIBackendRole
        if isinstance(raw_backend_role, str):
            try:
                role_at_backend = OpenAIBackendRole(raw_backend_role)
            except ValueError as e:
                logging.warning(
                    f"Failed to restore OpenAIBackendRole from '{raw_backend_role}': {e}. "
                    "Falling back based on message.role_type."
                )
                role_at_backend = (
                    OpenAIBackendRole.USER
                    if getattr(reconstructed_message, "role_type", RoleType.ASSISTANT) == RoleType.USER
                    else OpenAIBackendRole.ASSISTANT
                )
        elif isinstance(raw_backend_role, OpenAIBackendRole):
            role_at_backend = raw_backend_role
        else:
            logging.warning(
                f"Unexpected type for role_at_backend: {type(raw_backend_role)}. "
                "Falling back based on message.role_type."
            )
            role_at_backend = (
                OpenAIBackendRole.USER
                if getattr(reconstructed_message, "role_type", RoleType.ASSISTANT) == RoleType.USER
                else OpenAIBackendRole.ASSISTANT
            )

        return cls(
            uuid=UUID(record_dict["uuid"]),
            message=reconstructed_message,
            role_at_backend=role_at_backend,
            extra_info=record_dict["extra_info"],
            timestamp=record_dict["timestamp"],
            agent_id=record_dict["agent_id"],
        )

    def to_dict(self) -> Dict[str, Any]:
        r"""Convert the :obj:`MemoryRecord` to a JSON-serializable dict."""
        message_dict: Dict[str, Any] = {
            "__class__": self.message.__class__.__name__,
            **asdict(self.message),
        }

        # Normalize enums inside message payload (e.g., role_type)
        message_dict = MemoryRecord._safe_enum_conversion(message_dict)

        out: Dict[str, Any] = {
            "uuid": str(self.uuid),
            "message": message_dict,
            "role_at_backend": self.role_at_backend.value
            if isinstance(self.role_at_backend, Enum)
            else self.role_at_backend,
            "extra_info": MemoryRecord._safe_enum_conversion(self.extra_info),
            "timestamp": self.timestamp,
            "agent_id": self.agent_id,
        }
        return out

    def to_openai_message(self) -> OpenAIMessage:
        r"""Converts the record to an :obj:`OpenAIMessage` object."""
        return self.message.to_openai_message(self.role_at_backend)


class ContextRecord(BaseModel):
    r"""The result of memory retrieving."""

    memory_record: MemoryRecord
    score: float
    timestamp: float = Field(
        default_factory=lambda: time.time_ns()
        / 1_000_000_000  # Nanosecond precision
    )
