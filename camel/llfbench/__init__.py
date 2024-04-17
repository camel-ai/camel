from camel.llfbench import envs
import gymnasium as gym

def make(env_name, *, instruction_type=None, feedback_type=None):
    env = gym.make(env_name)
    if instruction_type is not None:
        env.set_instruction_type(instruction_type)
    if feedback_type is not None:
        env.set_feedback_type(feedback_type)
    return env

def supported_types(env_name):
    """ Return the supported INSTRUCTION_TYPES and FEEDBACK_TYPES for the given env_name. """
    env = gym.make(env_name)
    return env.INSTRUCTION_TYPES, env.FEEDBACK_TYPES
