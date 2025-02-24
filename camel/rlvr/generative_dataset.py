import random
from typing import Dict, List
from pydantic import BaseModel, ValidationError, Field
from camel.agents import ChatAgent
from camel.verifiers import BaseVerifier
from torch.utils.data import Dataset

class DataPoint(BaseModel):
    """
    Represents a structured dataset entry containing a problem statement, rationale, and final answer.
    This format is used for both seed and synthetic datasets.
    """
    problem_statement: str = Field(..., description="The primary question or issue to be addressed.")
    rationale: str = Field(..., description="Logical reasoning or explanation behind the answer.")
    final_answer: str = Field(..., description="The definitive solution or conclusion to the problem.")

class SeedDataset(Dataset):
    """
    A PyTorch dataset containing validated seed examples for synthetic data generation.
    Ensures that all items adhere to the DataPoint schema.
    """
    # TODO: add auto-conversion from PyTorch and HF data
    def __init__(self, data: List[Dict[str, str]]):
        if len(data) < 3:
            raise ValueError("Seed dataset must contain at least 3 samples.")

        self.data: List[DataPoint] = []
        for i, item in enumerate(data):
            try:
                self.data.append(DataPoint(**item))
            except ValidationError as e:
                raise ValueError(f"Sample {i} validation error: {e}")

    def __getitem__(self, idx: int) -> DataPoint:
        return self.data[idx]

    def __len__(self) -> int:
        return len(self.data)

class SyntheticDataset(Dataset):
    def __init__(self) -> None:
        self.data: List[DataPoint] = []
    
    def add(self, item: DataPoint) -> None:
        self.data.append(item)
    
    def __getitem__(self, idx: int) -> DataPoint:
        return self.data[idx]
    
    def __len__(self) -> int:
        return len(self.data)

class GenerativeDataset(Dataset):
    """
    A PyTorch dataset class for generating synthetic datapoints using a Camel Agent and Verifier.
    Validates the seed dataset using Pydantic and stores synthetic data in its own Dataset.
    """
    def __init__(self, seed_dataset: SeedDataset, verifier: BaseVerifier, agent: ChatAgent, seed: int = 42):
        self.seed_dataset = seed_dataset
        self.verifier = verifier
        self.agent = agent
        self._synthetic_data = SyntheticDataset()
        
        self.seed = seed

        random.seed(self.seed)

    def _construct_prompt(self, examples: List[DataPoint]) -> str:
        prompt = "Generate a new datapoint similar to the following examples:\n\n"
        for i, example in enumerate(examples, 1):
            prompt += f"Example {i}:\n"
            prompt += f"Problem Statement: {example['problem_statement']}\n"
            prompt += f"Rationale: {example['rationale']}\n"
            prompt += f"Final Answer: {example['final_answer']}\n\n"
        prompt += "New datapoint:"
        return prompt

    async def generate_new(self, n: int) -> None:
        valid_data_points = []
        
        while len(valid_data_points) < 3:
            try:
                indices = random.sample(range(len(self.seed_dataset)), 3)
                examples = [self.seed_dataset[i] for i in indices]
                prompt = self._construct_prompt(examples)

                agent_output = self.agent.step(prompt, response_format=DataPoint).msgs[0].parsed
                
                if not isinstance(agent_output, dict):
                    raise TypeError("Agent output must be a dictionary")
                if 'problem_statement' not in agent_output or 'rationale' not in agent_output:
                    raise KeyError("Agent output missing required keys: 'problem_statement' or 'rationale'")
                
                rationale = agent_output['rationale']

                verifier_response = await self.verifier.verify(rationale)
                if not hasattr(verifier_response, 'content'):
                    raise AttributeError("Verifier response missing 'content' attribute")

                if not verifier_response.result:
                    continue
                
                final_answer = verifier_response.sub_results[0]

                new_datapoint = {
                    'problem_statement': agent_output['problem_statement'],
                    'rationale': rationale,
                    'final_answer': final_answer
                }

                datapoint = DataPoint(**new_datapoint)
                
                valid_data_points.append(datapoint)

            except (TypeError, KeyError, AttributeError, ValidationError) as e:
                print(f"Error encountered: {e}, retrying...")

        for datapoint in valid_data_points:
            self._synthetic_data.add(datapoint)

    def __getitem__(self, idx: int) -> DataPoint:
        return self._synthetic_data[idx]

    def __len__(self) -> int:
        return len(self._synthetic_data)
