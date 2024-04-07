import gym as old_gym
import gymnasium as gym
from gymnasium.envs.registration import register
from llfbench.utils import generate_combinations_dict
from llfbench.envs.bandits.wrapper import BanditGymWrapper
import gym_bandits  # this is needed so that gym_bandits is registered


ENVIRONMENTS = (
    'BanditTenArmedRandomFixed-v0',
    'BanditTenArmedRandomRandom-v0',
    'BanditTenArmedGaussian-v0',
    'BanditTenArmedUniformDistributedReward-v0',
    'BanditTwoArmedDeterministicFixed-v0',
    'BanditTwoArmedHighHighFixed-v0',
    'BanditTwoArmedHighLowFixed-v0',
    'BanditTwoArmedLowLowFixed-v0',
)


def make_env(env_name,
             instruction_type='b',
             feedback_type='a',
             ):
    """ Make the original env and wrap it with the LLFWrapper. """
    env = old_gym.make(env_name)  # env_name is the original env name of gym_bandits
    # we don't pass arguments here, because _reset in BanditGymWrapper calls __init__ of the env without arguments.
    return BanditGymWrapper(env, instruction_type=instruction_type, feedback_type=feedback_type)


for env_name in ENVIRONMENTS:
    # default version (backwards compatibility)
    register(
        id=f"llf-bandits-{env_name}",
        entry_point='llfbench.envs.bandits:make_env',
        kwargs=dict(env_name=env_name, feedback_type='a', instruction_type='b')
    )