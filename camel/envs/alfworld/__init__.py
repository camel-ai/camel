from gymnasium.envs.registration import register
from llfbench.envs.alfworld.alfworld import Alfworld
from llfbench.envs.alfworld.wrapper import AlfworldWrapper



ENVIRONMENTS = (
    'alfworld-v0',
)


def make_env(env_name,
             instruction_type='b',
             feedback_type='r',
             ):

    """ Make the original env and wrap it with the LLFWrapper. """
    assert env_name.startswith("alfworld"), f"alfworld environment {env_name} must start with alfworld"
    env = Alfworld(instruction_type=instruction_type, feedback_type=feedback_type)
    return AlfworldWrapper(env, instruction_type=instruction_type, feedback_type=feedback_type)


for env_name in ENVIRONMENTS:
    # default version (backwards compatibility)
    register(
        id=f"llf-{env_name}",
        entry_point='llfbench.envs.alfworld:make_env',
        kwargs=dict(env_name=env_name, feedback_type='a', instruction_type='b')
    )
