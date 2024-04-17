import importlib
from camel.llfbench.envs import gridworld
from camel.llfbench.envs import bandits
from camel.llfbench.envs import optimization
from camel.llfbench.envs import reco
from camel.llfbench.envs import poem
from camel.llfbench.envs import highway

if importlib.util.find_spec('metaworld'):
    from camel.llfbench.envs import metaworld

if importlib.util.find_spec('alfworld'):
    from camel.llfbench.envs import alfworld
