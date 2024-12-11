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

from typing import Any, Protocol, Union


class OpenBBBaseProtocol(Protocol):
    """Protocol defining the base interface for OpenBB SDK functionality."""

    account: Any
    user: Any
    equity: Any
    etf: Any
    index: Any
    regulators: Any
    stocks: Any
    calendar: Any
    economy: Any
    currency: Any
    crypto: Any
    indices: Any
    futures: Any
    bonds: Any
    to_df: Any
    results: Any
    to_dict: Any


class OpenBBClient:
    """Type class for OpenBB client implementation."""

    def __init__(self) -> None:
        """Initialize the OpenBB client type."""
        self.account: Any = None
        self.user: Any = None
        self.equity: Any = None
        self.etf: Any = None
        self.index: Any = None
        self.regulators: Any = None
        self.stocks: Any = None
        self.calendar: Any = None
        self.economy: Any = None
        self.currency: Any = None
        self.crypto: Any = None
        self.indices: Any = None
        self.futures: Any = None
        self.bonds: Any = None


OpenBBType = Union[OpenBBBaseProtocol, OpenBBClient]
