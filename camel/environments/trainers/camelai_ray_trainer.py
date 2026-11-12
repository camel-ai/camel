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

from camel_env.single_step_env import SingleStepEnv
from recipes.camelai.env_dataset import EnvDataset
from torchdata.stateful_dataloader import StatefulDataLoader
from verl.trainer.ppo.ray_trainer import RayPPOTrainer


class CamelEnvTrainer(RayPPOTrainer):
    def __init__(self, *args, env: SingleStepEnv, **kwargs):
        self._env = env
        super().__init__(*args, **kwargs)

    # Get observations from SingleStepEnv
    def _create_dataloader(
        self,
        train_dataset=None,  # ignored
        val_dataset=None,
        collate_fn=None,
        train_sampler=None,
    ):
        def _first_sample_only(batch):
            """StatefulDataLoader always wraps a single item in a list."""
            return batch[0]

        if collate_fn is None:
            collate_fn = _first_sample_only

        self.train_dataset = EnvDataset(
            env=self._env,
            tokenizer=self.tokenizer,
            max_prompt_len=self.config.data.max_prompt_length,
            batch_size=self.config.data.train_batch_size,
        )
        self.train_dataloader = StatefulDataLoader(
            dataset=self.train_dataset,
            batch_size=1,  # each yield is a batch already
            collate_fn=collate_fn,
            drop_last=False,
            num_workers=0,  # TODO update
        )

        self.val_dataset = []
        self.val_dataloader = []

        # TODO rethink step handling
        # Total steps: either user-specified, or one step per epoch
        self.total_training_steps = (
            self.config.trainer.total_training_steps
            if self.config.trainer.total_training_steps is not None
            else self.config.trainer.total_epochs
        )
