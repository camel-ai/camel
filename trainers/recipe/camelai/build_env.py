# Copyright 2024 Bytedance Ltd. and/or its affiliates
#
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

from __future__ import annotations
from camel_env.single_step_env import SingleStepEnv


def build_single_step_env(cfg) -> SingleStepEnv:
    """
    Factory that interprets the `cfg.env` section of your Hydra config
    and returns a ready-to-roll SingleStepEnv.

    Expected `cfg.env` keys (extend as you wish):
    -------------------------------------------------
    - name:        str   -> environment name (future-proofing)
    - system_msg:  str   -> system prompt fed to CAMEL agents
    - n_tasks:     int   -> number of parallel tasks (default 1)
    - **kwargs     any   -> passed straight through to env ctor
    """

    # -----------------------------------------------------------------
    #  Parse the sub-config (fill in sane defaults)
    # -----------------------------------------------------------------
    env_cfg    = cfg.get("env", {})       # optional top-level section
    name       = env_cfg.get("name", "camel_single_step")
    system_msg = env_cfg.get("system_msg", "You are a helpful assistant.")
    n_tasks    = env_cfg.get("n_tasks", 1)

    # Any extra user-supplied keys are forwarded as-is
    extra_kwargs = {
        k: v
        for k, v in env_cfg.items()
        if k not in {"name", "system_msg", "n_tasks"}
    }

    # -----------------------------------------------------------------
    #  Instantiate the concrete environment
    # -----------------------------------------------------------------
    if name != "camel_single_step":
        raise ValueError(f"Unknown env name: {name!r}")

    env = SingleStepEnv(
        sys_msg       = system_msg,
        parallel_tasks= n_tasks,
        **extra_kwargs,
    )

    return env
