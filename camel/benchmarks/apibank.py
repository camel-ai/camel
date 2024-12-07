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

import json
import logging
import os
import random
import pandas as pd
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Union

from tqdm import tqdm
from camel.agents import ChatAgent
from camel.benchmarks import BaseBenchmark
from camel.messages.base import BaseMessage
from camel.models.model_factory import ModelFactory

class APIBankBenchmark(BaseBenchmark):
    r"""
    TODO: Write the docstring
    """

    def __init__(
        self,
        data_dir: str,
        save_to: str,
        processes: int = 1,
    ):
        super().__init__("apibank", data_dir, save_to, processes)