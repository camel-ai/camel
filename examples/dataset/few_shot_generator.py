import asyncio
from pathlib import Path

from camel.datasets import StaticDataset, FewShotGenerator
from camel.verifiers import PythonVerifier, VerifierInput

from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.configs import ChatGPTConfig
from camel.logger import get_logger

logger = get_logger(__name__)

verifier = PythonVerifier(required_packages=["sympy"])
asyncio.run(verifier.setup())

raw_data2 = [
    {
        "question": "Evaluate the limit as x approaches 0 of (sin(3*x) - 3*x) / x**3.",
        "final_answer": "-9/2",
        "rationale": '''from sympy import symbols, limit, sin
x = symbols('x')
expr = (sin(3*x) - 3*x) / x**3
result = limit(expr, x, 0)
print(result)'''
    },
    {
        "question": "Evaluate the definite integral of (1 - x**2)**3 from x = 0 to x = 1.",
        "final_answer": "16/35",
        "rationale": '''from sympy import symbols, integrate
x = symbols('x')
expr = (1 - x**2)**3
result = integrate(expr, (x, 0, 1))
print(result)'''
    },
    {
        "question": "Evaluate the limit as n approaches infinity of n*(sqrt(n**2 + 1) - n).",
        "final_answer": "1/2",
        "rationale": '''from sympy import symbols, limit, sqrt
n = symbols('n', positive=True)
expr = n*(sqrt(n**2 + 1) - n)
result = limit(expr, n, float("inf"))
print(result)'''
    },
    {
        "question": "Compute the sum of the series sum from n = 1 to 50 of 1/(n*(n+1)).",
        "final_answer": "50/51",
        "rationale": '''from sympy import symbols, summation
n = symbols('n', positive=True, integer=True)
expr = 1/(n*(n+1))
result = summation(expr, (n, 1, 50))
print(result)'''
    }
]

seed_dataset = StaticDataset(raw_data2)

from dotenv import load_dotenv

load_dotenv()


model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O_MINI,
    model_config_dict=ChatGPTConfig().as_dict(),
)
generator = FewShotGenerator(seed_dataset=seed_dataset, verifier=verifier, model=model)

new_data = asyncio.run(generator.generate_new(n=2, max_retries=5))

for dp in new_data:
    print(dp)

generator.save_to_jsonl(Path("generated_data.jsonl"))

asyncio.run(verifier.cleanup())