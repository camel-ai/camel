import numpy as np
from gymnasium.envs.registration import register
from llfbench.envs.optimization.wrapper import LossLandscapeGymWrapper

ENVIRONMENTS = (
    'Booth',
    'McCormick',
    'Rosenbrock',
    'SixHumpCamel',
)

def make_env(env_name,
             instruction_type='b',
             feedback_type='r',
             **kwargs):
    """ Make the original env and wrap it with the LLFWrapper. """
    import importlib
    LossCls = getattr(importlib.import_module("llfbench.envs.optimization.loss_descent"), env_name)
    env = LossCls(**kwargs)  # `feedback` doesn't matter here, as we will override it.
    return LossLandscapeGymWrapper(env, instruction_type=instruction_type, feedback_type=feedback_type)

for env_name in ENVIRONMENTS:
    register(
        id=f"llf-optimization-{env_name}-v0",
        entry_point='llfbench.envs.optimization:make_env',
        kwargs={'env_name': env_name, 'instruction_type': 'b', 'feedback_type': 'a'},
    )