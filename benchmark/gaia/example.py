import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from gaia import GAIABenchmark
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.configs import GeminiConfig

model = ModelFactory.create(
    model_platform=ModelPlatformType.GEMINI,
    model_type=ModelType.GEMINI_1_5_PRO,
    model_config_dict=GeminiConfig(temperature=0.2).__dict__,
)
gaia = GAIABenchmark()
gaia.download()
scores = gaia.eval("validation", 1, model = model)
print(scores)
