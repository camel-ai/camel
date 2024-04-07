from gymnasium.envs.registration import register
from llfbench.envs.gridworld.gridworld import Gridworld
from llfbench.envs.gridworld.wrapper import GridworldWrapper


ENVIRONMENTS = (
    'gridworld-v0',
)


def make_env(env_name,
             instruction_type='b',
             feedback_type='r',
             ):

    """ Make the original env and wrap it with the LLFWrapper. """
    env = Gridworld(instruction_type=instruction_type, feedback_type=feedback_type)
    # we don't pass arguments here, because _reset in BanditGymWrapper calls __init__ of the env without arguments.
    return GridworldWrapper(env, instruction_type=instruction_type, feedback_type=feedback_type)


for env_name in ENVIRONMENTS:
    # default version (backwards compatibility)
    register(
        id=f"llf-{env_name}",
        entry_point='llfbench.envs.gridworld:make_env',
        kwargs=dict(env_name=env_name, feedback_type='a', instruction_type='b')
    )
