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


r"""Initializes the SingleStepEnv

This function creates a SingleStepEnv that we need in order to get our
observations for the training run and in order to compute our reward

Returns:
    SingleStepEnv
"""

import asyncio
import json
from pathlib import Path

from camel_env.single_step_env import SingleStepEnv
from dotenv import load_dotenv

from camel.configs import ChatGPTConfig
from camel.datasets import FewShotGenerator, StaticDataset
from camel.logger import get_logger
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.verifiers import MathVerifier

logger = get_logger(__name__)


async def _setup_verifier_and_dataset(raw_data: list[dict]):
    r"""
    Internal helper to configure the dataset and the verifier.
    This function should be modified to fit the training purposes.

    Either use a Generator or a StaticDataset for the creation of a
    SingleStepEnvironment.
    Default implementation here will utilize a FewShotGenerator.

    Additionally, choose a suitable verifier for your specific task.
    Default implementation here will utilize a PythonVerifier.

    Args:
        raw_data (list[dict]): The input data for either the seed dataset or
            the StaticDataset.

    Returns:
        tuple[FewShotGenerator, MathVerifier]: A tuple containing the dataset
            and the configured verifier instance.
    """

    seed_dataset = StaticDataset(data=raw_data)

    # Default: MathVerifier
    # Do not setup the verifier as the environment handles this for us
    verifier = MathVerifier(float_rounding=6, numeric_precision=15)

    # Load environment variables for API keys
    load_dotenv()

    # Default model 4o-mini
    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O_MINI,
        model_config_dict=ChatGPTConfig().as_dict(),
    )

    dataset = FewShotGenerator(
        seed_dataset=seed_dataset,
        verifier=verifier,
        model=model,
    )

    return dataset, verifier


def build_single_step_env(dataset_path: str) -> SingleStepEnv:
    r"""Initializes a minimal SingleStepEnv

    Args:
        dataset_path (str): Path to a seed dataset or StaticDataset depending
            on implementation.

    Returns:
        SingleStepEnv: The initialized SingleStepEnv ready we want to train on.
    """

    path = Path(dataset_path)
    with path.open('r', encoding='utf-8') as f:
        raw_data = json.load(f)

    dataset, verifier = asyncio.run(_setup_verifier_and_dataset(raw_data))

    # Import your environment here for training
    env = SingleStepEnv(
        dataset=dataset,
        verifier=verifier,
    )

    return env
