import os
import random
from typing import Iterator, List

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from torch.utils.data import IterableDataset

from camel.agents import ChatAgent
from camel.logger import get_logger
from camel.verifiers import BaseVerifier

from .base import DataPoint, SeedDataset

logger = get_logger(__name__)

class GenerativeDataset(IterableDataset):
    r"""A dataset that generates and stores data points in Parquet.

    Attributes:
        seed_dataset (SeedDataset): Initial dataset for examples.
        verifier (BaseVerifier): Verifies generated rationales.
        agent (ChatAgent): Generates new data points.
        cache_path (str): Path to store Parquet file.
        chunk_size (int): Number of data points per generation chunk.
        shuffle (bool): Whether to shuffle the dataset on init.
        seed (int): Random seed for reproducibility.
        max_gen_retries (int): Max retries for chunk generation.
    """

    def __init__(
        self,
        seed_dataset: SeedDataset,
        verifier: BaseVerifier,
        agent: ChatAgent,
        cache_path: str = "dataset.parquet",
        chunk_size: int = 1000,
        shuffle: bool = False,
        seed: int = 42,
        max_gen_retries: int = 10,
    ):
        super().__init__()
        self.seed_dataset = seed_dataset
        self.verifier = verifier
        self.agent = agent
        self.cache_path = cache_path
        self.chunk_size = chunk_size
        self.shuffle = shuffle
        self.seed = seed
        self.max_gen_retries = max_gen_retries
        random.seed(self.seed)

        self.schema = pa.schema(
            [
                pa.field("question", pa.string()),
                pa.field("rationale", pa.string()),
                pa.field("final_answer", pa.string()),
            ]
        )

        if not os.path.exists(self.cache_path):
            self._initialize_parquet()

        if self.shuffle:
            self.shuffle_parquet()

    def _initialize_parquet(self):
        r"""Initialize a new Parquet dataset with an empty table."""
        table = pa.Table.from_pydict(
            {"question": [], "rationale": [], "final_answer": []},
            schema=self.schema,
        )
        pq.write_table(table, self.cache_path)
        logger.info(f"Initialized new Parquet dataset at {self.cache_path}")

    def shuffle_parquet(self):
        r"""Shuffle the dataset and save it back to the Parquet file."""
        table = pq.read_table(self.cache_path)
        df = table.to_pandas()
        df = df.sample(frac=1, random_state=self.seed).reset_index(drop=True)
        shuffled_table = pa.Table.from_pandas(df, schema=self.schema)
        pq.write_table(shuffled_table, self.cache_path)
        logger.info(f"Shuffled dataset saved to {self.cache_path}")

    def __iter__(self, on_demand_gen: bool = False) -> Iterator[DataPoint]:
        r"""Yield data points, generating new ones on demand if enabled.

        Args:
            on_demand_gen (bool): Generate new data if dataset is exhausted.
        """
        import asyncio
        dataset = pq.ParquetDataset(self.cache_path)
        yielded_fragments = 0

        while True:
            fragments = list(dataset.fragments)

            # Handle empty dataset with on-demand generation
            if not fragments and on_demand_gen:
                new_data = asyncio.run(self.generate_new(self.chunk_size))
                if new_data:
                    self.append(new_data)
                    dataset = pq.ParquetDataset(self.cache_path)
                else:
                    logger.warning("Failed to generate initial data.")
                    return

            # Yield existing fragments
            if yielded_fragments < len(fragments):
                for fragment in fragments[yielded_fragments:]:
                    table = fragment.to_table()
                    df = table.to_pandas()
                    rows = df.to_dict(orient="records")
                    for row in rows:
                        yield DataPoint(
                            question=row["question"],
                            rationale=row["rationale"],
                            final_answer=row["final_answer"],
                        )
                yielded_fragments = len(fragments)

            # Generate new data if enabled
            elif on_demand_gen:
                gen_retries = 0
                while gen_retries < self.max_gen_retries:
                    new_data = asyncio.run(self.generate_new(self.chunk_size))
                    if new_data:
                        self.append(new_data)
                        dataset = pq.ParquetDataset(self.cache_path)
                        break
                    else:
                        gen_retries += 1
                if gen_retries >= self.max_gen_retries:
                    logger.warning("Max retries reached. Stopping.")
                    return
            else:
                return

    def append(self, new_data: List[DataPoint]) -> None:
        r"""Append new data points to the Parquet file.

        Args:
            new_data (List[DataPoint]): List of new data points to append.
        """
        if not new_data:
            return
        data_dict = {
            "question": [dp.question for dp in new_data],
            "rationale": [dp.rationale for dp in new_data],
            "final_answer": [dp.final_answer for dp in new_data],
        }
        new_table = pa.Table.from_pandas(pd.DataFrame(data_dict), schema=self.schema)
        if os.path.exists(self.cache_path):
            existing_table = pq.read_table(self.cache_path)
            combined_table = pa.concat_tables([existing_table, new_table])
        else:
            combined_table = new_table
        pq.write_table(combined_table, self.cache_path)
        logger.info(f"Appended {len(new_data)} new data points to {self.cache_path}")

    async def generate_new(self, n: int) -> List[DataPoint]:
        r"""Generate new data points asynchronously.

        Args:
            n (int): Number of data points to attempt to generate.

        Returns:
            List[DataPoint]: List of successfully generated data points.
        """
        valid_data_points: List[DataPoint] = []
        for _ in range(n):
            attempts = 0
            while attempts < self.chunk_size:
                try:
                    indices = random.sample(range(len(self.seed_dataset)), 3)
                    examples = [self.seed_dataset[i] for i in indices]
                    prompt = self._construct_prompt(examples)
                    agent_output = self.agent.step(
                        prompt, response_format=DataPoint
                    ).msgs[0].parsed
                    if not isinstance(agent_output, dict):
                        raise TypeError("Agent output must be a dict")
                    if "question" not in agent_output or "rationale" not in agent_output:
                        raise KeyError("Missing required keys in agent output")
                    rationale = agent_output["rationale"]
                    verifier_response = await self.verifier.verify(rationale)
                    if verifier_response.result:
                        final_answer = str(verifier_response.result)
                        new_datapoint = DataPoint(
                            question=agent_output["question"],
                            rationale=rationale,
                            final_answer=final_answer,
                        )
                        valid_data_points.append(new_datapoint)
                        break
                except (TypeError, KeyError, AttributeError) as e:
                    logger.warning(f"Error in generation: {e}, retrying...")
                attempts += 1
            if attempts == self.chunk_size:
                logger.warning(f"Failed to generate after {self.chunk_size} tries.")
        return valid_data_points

    def _construct_prompt(self, examples: List[DataPoint]) -> str:
        r"""Construct a prompt for generating a new data point.

        Args:
            examples (List[DataPoint]): List of example data points.

        Returns:
            str: The constructed prompt string.
        """
        prompt = "Generate a new datapoint similar to these examples:\n\n"
        for i, example in enumerate(examples, 1):
            prompt += f"Example {i}:\n"
            prompt += f"Question: {example.question}\n"
            prompt += f"Rationale: {example.rationale}\n"
            prompt += f"Final Answer: {example.final_answer}\n\n"
        return prompt + "New datapoint:"