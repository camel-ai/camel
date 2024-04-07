import importlib
from camel.envs import gridworld
from camel.envs import bandits
from camel.envs import optimization
from camel.envs import reco
from camel.envs import poem
from camel.envs import highway

if importlib.util.find_spec('metaworld'):
    from camel.envs import metaworld

if importlib.util.find_spec('alfworld'):
    from camel.envs import alfworld
