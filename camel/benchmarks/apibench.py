# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========

import json
import logging
import os
import random
import requests
from pathlib import Path
from typing import Any, Dict, Literal, Optional

from tqdm import tqdm

from camel.agents import ChatAgent
from camel.benchmarks import BaseBenchmark
from camel.messages.base import BaseMessage

from .utils.ast_eval import ast_parse, evaluate_response

logger = logging.getLogger(__name__)

dataset_mapping = {
    "huggingface": {
        "api": "huggingface_api.jsonl",
        "eval": "huggingface_eval.json",
        "train": "huggingface_train.json",
        "questions": "questions_huggingface_0_shot.jsonl",
    },
    "tensorflowhub": {
        "api": "tensorflowhub_api.jsonl",
        "eval": "tensorflow_eval.json",
        "train": "tensorflow_train.json",
        "questions": "questions_tensorflowhub_0_shot.jsonl",
    },
    "torchhub": {
        "api": "torchhub_api.jsonl",
        "eval": "torchhub_eval.json",
        "train": "torchhub_train.json",
        "questions": "questions_torchhub_0_shot.jsonl",
    },
}


def download_github_subdirectory(
    repo: str, subdir: str, data_dir: Path, branch="main"
):
    r"""Download subdirectory of the Github repo of
    the benchmark.

    This function downloads all files and subdirectories from a
    specified subdirectory of a GitHub repository and
    saves them to a local directory.

    Args:
        repo (str): The name of the GitHub repository
                in the format "owner/repo".
        subdir (str): The path to the subdirectory
            within the repository to download.
        data_dir (Path): The local directory where
            the files will be saved.
        branch (str, optional): The branch of the repository to use.
            Defaults to "main".
    """
    api_url = (
        f"https://api.github.com/repos/{repo}/contents/{subdir}?ref={branch}"
    )
    headers = {"Accept": "application/vnd.github.v3+json"}
    response = requests.get(api_url, headers=headers)
    response.raise_for_status()
    files = response.json()
    os.makedirs(data_dir, exist_ok=True)

    for file in tqdm(files, desc="Downloading"):
        file_path = data_dir / file["name"]

        if file["type"] == "file":
            file_url = file["download_url"]
            file_response = requests.get(file_url)
            with open(file_path, "wb") as f:
                f.write(file_response.content)
        elif file["type"] == "dir":
            download_github_subdirectory(
                repo,
                subdir / file["name"],
                file_path,
                branch,
            )


# This function is migrated from the original repo:
# https://github.com/ShishirPatil/gorilla
def encode_question(question: str, dataset_name: str) -> str:
    r"""Encode multiple prompt instructions into a single string."""

    if dataset_name == "torchhub":
        domains = "1. $DOMAIN is inferred from the task description and \
        should include one of {Classification, Semantic Segmentation, \
        Object Detection, Audio Separation, Video Classification, \
        Text-to-Speech}."
    elif dataset_name == "huggingface":
        domains = "1. $DOMAIN should include one of {Multimodal Feature \
            Extraction, Multimodal Text-to-Image, Multimodal \
            Image-to-Text, Multimodal Text-to-Video, \
            Multimodal Visual Question Answering, Multimodal Document \
            Question Answer, Multimodal Graph Machine Learning, \
            Computer Vision Depth Estimation, Computer Vision Image \
            Classification, Computer Vision Object Detection, \
            Computer Vision Image Segmentation, Computer Vision \
            Image-to-Image, Computer Vision Unconditional \
            Image Generation, Computer Vision Video Classification, \
            Computer Vision Zero-Shor Image Classification, \
            Natural Language Processing Text Classification, \
            Natural Language Processing Token Classification, \
            Natural Language Processing Table Question Answering, \
            Natural Language Processing Question Answering, \
            Natural Language Processing, Zero-Shot Classification \
            Natural Language Processing Translation, Natural Language \
            Processing Summarization, Natural Language Processing \
            Conversational, Natural Language Processing Text \
            Generation, Natural Language Processing Fill-Mask, \
            Natural Language Processing Text2Text Generation, \
            Natural Language Processing Sentence Similarity, \
            Audio Text-to-Speech, Audio Automatic Speech Recognition, \
            Audio Audio-to-Audio, Audio Audio Classification, \
            Audio Voice Activity Detection, Tabular Tabular \
            Classification, Tabular Tabular Regression, \
            Reinforcement Learning Reinforcement Learning, \
            Reinforcement Learning Robotics }"
    elif dataset_name == "tensorflowhub":
        domains = "1. $DOMAIN is inferred from the task description \
        and should include one of {text-sequence-alignment, \
        text-embedding, text-language-model, text-preprocessing, \
        text-classification, text-generation, text-question-answering, \
        text-retrieval-question-answering, text-segmentation, \
        text-to-mel, image-classification, image-feature-vector, \
        image-object-detection, image-segmentation, \
        image-generator, image-pose-detection, image-rnn-agent, \
        image-augmentation, image-classifier, image-style-transfer, \
        image-aesthetic-quality, image-depth-estimation, \
        image-super-resolution, image-deblurring, image-extrapolation, \
        image-text-recognition, image-dehazing, image-deraining, \
        image-enhancemenmt, image-classification-logits, \
        image-frame-interpolation, image-text-detection, image-denoising, \
        image-others, video-classification, video-feature-extraction, \
        video-generation, video-audio-text, video-text, \
        audio-embedding, audio-event-classification, audio-command-detection, \
        audio-paralinguists-classification, audio-speech-to-text, \
        audio-speech-synthesis, audio-synthesis, audio-pitch-extraction}"
    else:
        logger.info("Error: API name is not supported.")

    prompt = (
        question
        + "\nWrite a python program in 1 to 2 lines to call API in "
        + dataset_name
        + ".\n\nThe answer should follow the format: <<<domain>>> $DOMAIN, \
        <<<api_call>>>: $API_CALL, <<<api_provider>>>: $API_PROVIDER, \
        <<<explanation>>>: $EXPLANATION, <<<code>>>: $CODE}. \
        Here are the requirements:\n"
        + domains
        + "\n2. The $API_CALL should have only 1 line of code \
        that calls api.\n 3. The $API_PROVIDER should be the \
        programming framework used.\n4. $EXPLANATION should be \
        a step-by-step explanation.\n5. The $CODE is the python code.\n6. \
        Do not repeat the format in your answer."
    )
    return prompt


class APIBenchBenchmark(BaseBenchmark):
    r"""APIBench Benchmark adopted from `Gorilla: Large Language Model
    Connected with Massive APIs`
    <https://huggingface.co/datasets/gorilla-llm/APIBench>.

    Args:
        data_dir (str): The directory to save the data.
        save_to (str): The file to save the results.
        processes (int, optional): The number of processes to use.
            (default: :obj:`1`)
    """

    # TODO: Integrate retriever (pending)

    def __init__(
        self,
        data_dir: str,
        save_to: str,
        processes: int = 1,
    ):
        r"""Initialize the APIBench benchmark.

        Args:
            data_dir (str): The directory to save the data.
            save_to (str): The file to save the results.
            processes (int, optional): The number of processes to use for
                parallel processing. (default: :obj:`1`)
        """
        super().__init__("apibench", data_dir, save_to, processes)

    def download(self):
        r"""Download the APIBench dataset."""
        from huggingface_hub import snapshot_download

        snapshot_download(
            repo_id="gorilla-llm/APIBench",
            repo_type="dataset",
            local_dir=self.data_dir,
            local_dir_use_symlinks=True,
        )

        repo = "ShishirPatil/gorilla"
        subdir = "eval/eval-data/questions"
        data_dir = self.data_dir

        download_github_subdirectory(repo, subdir, data_dir)

    def load(self, dataset_name: str, force_download: bool = False):  # type: ignore[override]
        r"""Load the APIBench Benchmark dataset.

        Args:
            dataset_name (str): Name of the specific dataset to be loaded.
            force_download (bool, optional): Whether to force
            download the data. (default: :obj:`False`)
        """

        if force_download:
            logger.info("Force downloading data.")
            self.download()

        def load_json_lines(file_path: Path):
            """Helper function to load JSON lines from a file."""
            try:
                with open(file_path, "r") as f:
                    return [json.loads(line) for line in f]
            except FileNotFoundError:
                raise FileNotFoundError(f"File not found: {file_path}")
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"Error decoding JSON in file {file_path}: {e}"
                )

        dataset_path = self.data_dir / dataset_name
        if not dataset_path.exists():
            raise FileNotFoundError(
                f"Dataset directory does not exist: {dataset_path}"
            )

        for label in ['api', 'eval', 'questions']:
            file_name = dataset_mapping[dataset_name][label]
            file_path = (
                dataset_path / file_name
                if label == 'questions'
                else self.data_dir / file_name
            )

            # Load data based on label type
            if label in ['api', 'questions', 'eval']:
                data = load_json_lines(file_path)

                if label == 'eval':
                    # Extract 'api_data' specifically for eval label
                    data = [item['api_data'] for item in data]

                self._data[label] = data
            else:
                raise ValueError(f"Unknown label: {label}")

        ast_database = []
        for data in self._data['api']:
            ast_tree = ast_parse(data['api_call'])
            ast_database.append(ast_tree)
        self._data['ast'] = ast_database

    def run(  # type: ignore[override]
        self,
        agent: ChatAgent,
        dataset_name: Literal["huggingface", "tensorflowhub", "torchhub"],
        randomize: bool = False,
        subset: Optional[int] = None,
    ) -> Dict[str, Any]:
        r"""Run the benchmark.

        Args:
            agent (ChatAgent): The agent to run the
                benchmark.
            dataset_name (Literal["huggingface",
                "tensorflowhub", "torchhub"]):
                The dataset to run the benchmark.
            randomize (bool, optional): Whether to randomize the data.
                (default: :obj:`False`)
            subset (Optional[int], optional): The subset of data to run.
                (default: :obj:`None`)
        """

        if dataset_name not in dataset_mapping:
            raise ValueError(f"Invalid value for dataset: {dataset_name}.")

        logger.info(f"Running APIBench benchmark on {dataset_name}.")
        self.load(dataset_name)
        datas = self._data['questions']

        # Shuffle and subset data if necessary
        if randomize:
            random.shuffle(datas)
        if subset:
            datas = datas[:subset]

        logger.info(f"Number of tasks: {len(datas)}")

        # Initialize results storage
        self._results = []

        with open(self.save_to, "w") as f:
            for question in tqdm(datas, desc="Running"):
                prompt = encode_question(question["text"], dataset_name)
                msg = BaseMessage.make_user_message(
                    role_name="User", content=prompt
                )
                try:
                    # Generate response
                    responses = agent.step(msg)
                    response = responses.msgs[0].content
                    api_database = self._data['api']
                    qa_pairs = self._data['eval']
                    ast_database = self._data['ast']
                    question_id = question['question_id']

                    # Evaluate response
                    error, correct, hallucination = evaluate_response(
                        response,
                        question_id,
                        dataset_name,
                        api_database,
                        qa_pairs,
                        ast_database,
                    )
                    self._results.append(
                        {
                            "question": question,
                            "agent_response": response,
                            "correct": correct,
                            "hallucination": hallucination,
                            "error": str(error),
                        }
                    )
                except Exception as e:
                    logger.warning(
                        f"Error in processing task: {question}: {e}"
                    )
                    self._results.append(
                        {
                            "question": question,
                            "agent_response": None,
                            "correct": False,
                            "hallucination": False,
                            "error": str(e),
                        }
                    )

                agent.reset()

                f.write(json.dumps(self._results[-1], indent=2) + "\n")
                f.flush()

        total = len(self._results)
        correct = sum(r["correct"] for r in self.results)
        hallucination = sum(r["hallucination"] for r in self.results)

        return {
            "total": total,
            "correct": correct,
            "hallucination": hallucination,
            "accuracy": correct / total,
            "hallucination rate": hallucination / total,
        }
