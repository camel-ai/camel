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

r"""
Reward manager that delegates reward computation to a live SingleStepEnv.

* It receives a DataProto batch from VERL.
* Decodes the model's responses to plain text.
* Runs `env.step()` with these responses (wrapped in Action objects).
* Extracts scalar rewards from the returned StepResult objects.
* Broadcasts each scalar along the token dimension → shape (B, T)
  as required by VERL.
* Returns the structure expected by `RayPPOTrainer.compute_reward`.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Tuple

import numpy as np
import torch
from camel_env.models import Action
from camel_env.single_step_env import SingleStepEnv
from verl import DataProto
from verl.workers.reward_manager import register


@register("camel_env")  # value to use in config: reward_model.reward_manager: camel_env
class CamelEnvRewardManager:
    r"""RewardManager that pulls rewards from a SingleStepEnv instance."""

    def __init__(
        self,
        tokenizer,
        env: SingleStepEnv,
        broadcast: bool = True,
        **_,
    ):
        self.tokenizer = tokenizer
        self.env: SingleStepEnv = env
        self.broadcast = broadcast

        self._loop = asyncio.new_event_loop()

    def __call__(
        self,
        data: DataProto,
        return_dict: bool = False,
        *args,
        **kwargs,
    ) -> torch.Tensor | Dict[str, Any]:

        # Decode model outputs
        responses_ids = data.batch["responses"]
        batch_size, seq_len = responses_ids.shape
        responses_text: List[str] = self.tokenizer.batch_decode(
            responses_ids, skip_special_tokens=True
        )

        batch_size_in_env = self.env.current_batch_size

        actions = [
            Action(index=i % batch_size_in_env, llm_response=txt)
            for i, txt in enumerate(responses_text)
        ]

        # collect rewards
        step_results = self._loop.run_until_complete(
            self.env.step(actions)
        )

        if batch_size == 1 and not isinstance(step_results, list):
            step_results = [step_results]


        scalar_rewards = torch.tensor(
            [sr[1] if isinstance(sr, tuple) else sr.reward
             for sr in step_results],
            dtype=torch.float32,
        )

        if self.broadcast:
            reward_tensor = scalar_rewards[:, None].repeat(1, seq_len)
        else:
            reward_tensor = scalar_rewards[:, None]

        if not return_dict:
            return reward_tensor

        extra_info: Dict[str, List[Any]] = {
            "scalar_reward": scalar_rewards.cpu().tolist(),
        }

        return {
            "reward_tensor": reward_tensor,
            "reward_extra_info": extra_info,
        }
