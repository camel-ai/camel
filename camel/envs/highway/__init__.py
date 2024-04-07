import gymnasium as gym
from gymnasium.envs.registration import register
from llfbench.utils import generate_combinations_dict
from llfbench.envs.highway.wrapper import HighwayWrapper

ENVIRONMENTS = (
    'parking-v0',
)


def make_env(env_name,
             instruction_type='b',
             feedback_type='a',
             ):
    """ Make the original env and wrap it with the LLFWrapper. """
    env = gym.make(env_name)
    return HighwayWrapper(env, instruction_type=instruction_type, feedback_type=feedback_type)

for env_name in ENVIRONMENTS:
    # default version (backwards compatibility)
    register(
        id=f"llf-highway-{env_name}",
        entry_point='llfbench.envs.highway:make_env',
        kwargs=dict(env_name=env_name, feedback_type='a', instruction_type='b')
    )