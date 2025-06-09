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


import asyncio

import numpy as np
import torch
from camel_env.single_step_env import SingleStepEnv
from torch.utils.data import IterableDataset


class EnvDataset(IterableDataset):
    """Stream (prompt-only) batches from a CAMEL SingleStepEnv."""

    def __init__(
        self,
        env: SingleStepEnv,
        tokenizer,
        max_prompt_len: int,
        batch_size: int,
    ):
        super().__init__()
        self.env = env
        self.tokenizer = tokenizer
        self.max_prompt = max_prompt_len
        self.batch_size = batch_size

    # verl workaround so len(dataloader) doesn't crash
    def __len__(self) -> int:
        return 1

    def __iter__(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        obs_list = loop.run_until_complete(
            self.env.reset(batch_size=self.batch_size)
        )

        while True:
            # If the current prompt batch is done, start a new one
            if self.env._batch_done():
                obs_list = loop.run_until_complete(
                    self.env.reset(batch_size=self.batch_size)
                )

            prompts = [o.question for o in obs_list]

            enc = self.tokenizer(
                prompts,
                add_special_tokens=False,
                truncation=True,
                max_length=self.max_prompt,
                padding="max_length",
                return_attention_mask=True,
                return_tensors="pt",
            )

            B, L = enc["input_ids"].shape
            yield {
                # tensors (CPU, long)
                "input_ids": enc["input_ids"],
                "attention_mask": enc["attention_mask"],
                "position_ids": torch.arange(L).unsqueeze(0).repeat(B, 1),
                "prompts": enc["input_ids"],
                # non-tensor extras
                "raw_prompt": np.array(prompts, dtype=object),
                "raw_prompt_ids": np.array(
                    [
                        ids.tolist() for ids in enc["input_ids"]
                    ],  # mock values, never consumed by the trainer
                    dtype=object,
                ),
                "data_source": np.array(["env"] * B, dtype=object),
                "_env_obs": np.array(obs_list, dtype=object),
            }
