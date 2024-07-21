import logging

from synthetic_datagen.agent_systems.single_agent import SingleAgent
from synthetic_datagen.self_instruct.self_instruct_spec import SelfInstructSpec
from implementations.synthetic_datagen.agent_systems.eval_agent import NemotronRewardEvalAgent
from camel.synthetic_datagen.method_factory import SyntheticDataGeneratorMethodType
from camel.synthetic_datagen.pipeline import DataGeneratorPipeline
from synthetic_datagen.utils.seed_instruction import Instance, SeedInstruction


logging.basicConfig(level=logging.INFO)

spec = SelfInstructSpec()

