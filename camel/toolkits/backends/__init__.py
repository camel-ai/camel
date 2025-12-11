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
r"""Backend abstractions and implementations for CAMEL toolkits.

This package defines the core backend protocol and provides concrete
implementations for interacting with different storage systems. Backends
offer a unified interface for reading, writing, editing, deleting, and
searching content, regardless of the underlying storage mechanism.

The package includes filesystem-backed, in-memory state, composite, and
policy-enforced backends, as well as shared result and metadata types used
to represent operation outcomes in a structured and consistent way.
"""

from .backend_aware_toolkit import BackendAwareToolkit
from .base import BaseBackend
from .composite_backend import CompositeBackend
from .filesystem_backend import FilesystemBackend
from .policy_wrapper import PolicyWrapper
from .state_backend import StateBackend
from .types import (
    DeleteResult,
    EditResult,
    FileInfo,
    GrepMatch,
    WriteResult,
)

__all__ = [
    # Core backend protocol and toolkit integration
    "BaseBackend",
    "BackendAwareToolkit",
    # Concrete backend implementations
    "FilesystemBackend",
    "StateBackend",
    "CompositeBackend",
    "PolicyWrapper",
    # Shared data and result types
    "FileInfo",
    "WriteResult",
    "EditResult",
    "DeleteResult",
    "GrepMatch",
]
