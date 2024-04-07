import gymnasium as gym
from gymnasium.envs.registration import register
from llfbench.utils import generate_combinations_dict
from llfbench.envs.metaworld.wrapper import MetaworldWrapper
from collections import defaultdict
import importlib
import metaworld
import random
import time
from gymnasium.wrappers import TimeLimit
import numpy as np

BENCHMARK = metaworld.MT1
ENVIRONMENTS = tuple(BENCHMARK.ENV_NAMES)

def make_env(env_name,
             instruction_type='b',
             feedback_type='a',
             ):
    """ Make the original env and wrap it with the LLFWrapper. """
    benchmark = BENCHMARK(env_name)
    env = benchmark.train_classes[env_name]()
    class Wrapper(gym.Wrapper):
         # a small wrapper to make sure the task is set
         # and to make the env compatible with the old gym api
        def __init__(self, env):
            super().__init__(env)
            self.env.max_path_length = float('inf')
            # We remove the internal time limit. We will redefine the time limit in the wrapper.
        @property
        def env_name(self):
            return env_name
        def reset(self, *, seed=None, options=None):
            random.seed(seed)
            np.random.seed(seed)
            task = random.choice(benchmark.train_tasks)
            self.env.set_task(task)
            return self.env.reset(seed=seed, options=options)
    env = Wrapper(env)
    return TimeLimit(MetaworldWrapper(env, instruction_type=instruction_type, feedback_type=feedback_type), max_episode_steps=30)


for env_name in ENVIRONMENTS:
    # default version (backward compatibility)
    register(
        id=f"llf-metaworld-{env_name}",
        entry_point='llfbench.envs.metaworld:make_env',
        kwargs=dict(env_name=env_name, feedback_type='a', instruction_type='b')
    )
