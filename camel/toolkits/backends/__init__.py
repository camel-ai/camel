r"""Backend abstractions and implementations for CAMEL toolkits.

This package defines the core backend protocol and provides concrete
implementations for interacting with different storage systems. Backends
offer a unified interface for reading, writing, editing, deleting, and
searching content, regardless of the underlying storage mechanism.

The package includes filesystem-backed, in-memory state, composite, and
policy-enforced backends, as well as shared result and metadata types used
to represent operation outcomes in a structured and consistent way.
"""

from .types import (
    FileInfo,
    WriteResult,
    EditResult,
    DeleteResult,
    GrepMatch,
)

from .base import BaseBackend
from .filesystem_backend import FilesystemBackend
from .state_backend import StateBackend
from .composite_backend import CompositeBackend
from .policy_wrapper import PolicyWrapper
from .backend_aware_toolkit import BackendAwareToolkit

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
