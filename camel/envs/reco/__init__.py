from gymnasium.envs.registration import register
from llfbench.utils import generate_combinations_dict
from llfbench.envs.reco.wrapper import MovieRecGymWrapper

environments = [
    'movie'
]

def make_env(env_name,
             instruction_type='b',
             feedback_type='r',
             **kwargs):
    """ Make the original env and wrap it with the LLFWrapper. """
    import importlib
    MovieCls = getattr(importlib.import_module("llfbench.envs.reco.movie_rec"), 'MovieRec')
    env = MovieCls(instruction_type=instruction_type, **kwargs)  # `feedback` doesn't matter here, as we will override it.
    return MovieRecGymWrapper(env, instruction_type=instruction_type, feedback_type=feedback_type)

register(
    id=f"llf-reco-{environments[0]}-v0",
    entry_point='llfbench.envs.reco:make_env',
    kwargs=dict(env_name=environments[0], feedback_type='a', instruction_type='b')
)