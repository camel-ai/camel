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
import random
from pathlib import Path
from typing import Any, Dict, Literal, Optional

import tree_sitter_python as tspython
from tqdm import tqdm
from tree_sitter import Language, Parser

from camel.agents import ChatAgent
from camel.benchmarks.base import BaseBenchmark
from camel.messages import BaseMessage
from camel.utils import download_github_subdirectory

logger = logging.getLogger(__name__)


# Mapping of dataset names to file names
# 'Oracle' retriver used here which means all the full
# API documentation will be included in the prompt
dataset_mapping = {
    "huggingface": {
        "api": "huggingface_api.jsonl",
        "eval": "huggingface_eval.json",
        "train": "huggingface_train.json",
        "questions": "questions_huggingface_oracle.jsonl",
    },
    "tensorflowhub": {
        "api": "tensorflowhub_api.jsonl",
        "eval": "tensorflow_eval.json",
        "train": "tensorflow_train.json",
        "questions": "questions_tensorflowhub_oracle.jsonl",
    },
    "torchhub": {
        "api": "torchhub_api.jsonl",
        "eval": "torchhub_eval.json",
        "train": "torchhub_train.json",
        "questions": "questions_torchhub_oracle.jsonl",
    },
}


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
        subdir = "/gorilla/eval/eval-data/questions"
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
            r"""Helper function to load JSON lines from a file."""
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
                            "error": str(error) if error else None,
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
            "accuracy": correct / total if total else "N/A",
            "hallucination rate": hallucination / total if total else "N/A",
        }


# This code is modified from the
# evaluators in the original repo
# https://github.com/ShishirPatil/gorilla
# Get all the subtrees given a root_node
def get_all_sub_trees(root_node):
    node_stack = []
    sub_tree_sexp_list = []
    depth = 1
    # text = root_node.text
    node_stack.append([root_node, depth])
    while len(node_stack) != 0:
        cur_node, cur_depth = node_stack.pop()
        if cur_node.child_count > 0:
            sub_tree_sexp_list.append(
                [
                    str(cur_node),
                    cur_depth,
                    cur_node,
                    cur_node.children[0].text,
                ]
            )
        else:
            sub_tree_sexp_list.append(
                [str(cur_node), cur_depth, cur_node, None]
            )
        for child_node in cur_node.children:
            if len(child_node.children) != 0:
                depth = cur_depth + 1
                node_stack.append([child_node, depth])
    return sub_tree_sexp_list


# Parse the program into AST trees
def ast_parse(candidate):
    PY_LANGUAGE = Language(tspython.language())
    parser = Parser(PY_LANGUAGE)

    candidate_tree = parser.parse(bytes(candidate, "utf8")).root_node
    return candidate_tree


# Get all the arguments in the ast tree
def get_args(node, dataset_name):
    if node.child_count == 0:
        return []
    args_list = []
    if dataset_name == "huggingface":
        for child in node.children[0].children[0].children[1].children:
            if "=" in child.text.decode():
                args_list.append(child.children[2].text)
            elif (
                child.text.decode() != "("
                and child.text.decode() != ")"
                and child.text.decode() != ","
            ):
                args_list.append(child.text)
    elif dataset_name == "tensorflowhub":
        for child in node.children[0].children[0].children[1].children:
            if (
                'model=' in child.text.decode()
                or 'model =' in child.text.decode()
            ):
                args_list.append(child.children[2].text)
            elif (
                child.text.decode() != "("
                and child.text.decode() != ")"
                and child.text.decode() != ","
            ):
                args_list.append(child.text)
    elif dataset_name == "torchhub":
        for child in node.children[0].children[0].children[1].children:
            if (
                "repo_or_dir" in child.text.decode()
                or "model" in child.text.decode()
            ):
                args_list.append(child.children[2].text)
    return args_list


# Check if there is an api match
def ast_check(candidate_subtree_list, base_tree_list, dataset_name):
    for idx, base_tree in enumerate(base_tree_list):
        if base_tree.children[0].children[0].child_count == 0:
            continue
        api_name = base_tree.children[0].children[0].children[0].text
        for candidate_tree in candidate_subtree_list:
            if candidate_tree[3] == api_name:
                break
        # Now we have a sub-tree
        candidate_tree = candidate_tree[2]
        args_list = get_args(base_tree, dataset_name)
        if len(args_list) == 0:
            continue
        ast_match = True
        for arg in args_list:
            if (
                arg.decode().lstrip("'").rstrip("'")
                not in candidate_tree.text.decode()
            ):
                ast_match = False
                break
        if ast_match:
            return idx
    return -1


def evaluate_response(
    response, question_id, dataset_name, api_database, qa_pairs, ast_database
):
    try:
        # Index the "api_call" domain
        output = response.split("api_call")
        if len(output) == 1:
            api_call = output[0]
        else:
            # Parse the output
            output = output[1].split("api_provider")[0]
            if ":" not in output:
                start = 0
            else:
                start = output.index(":")
            if ")" not in output:
                end = -2
            else:
                end = output.rindex(")")
            api_call = output[start + 2 : end + 1]

        try:
            ast_tree = ast_parse(api_call)
        except Exception as parse_error:
            print(f"Error parsing api_call: {api_call}, error: {parse_error}")
            return parse_error, False, False
        # Search for a subtree
        ast_subtree_list = get_all_sub_trees(ast_tree)
        # Check which ast tree is matching
        database_index = ast_check(
            ast_subtree_list, ast_database, dataset_name
        )
        # We cannot index this ast in our database
        if database_index == -1:
            halluncination = True
            correct = False
        # We index our reference api_call
        ref_api_call = api_database[database_index]
        # Check for functionality
        if ref_api_call['domain'] == qa_pairs[question_id - 1]['domain']:
            correct = True
            halluncination = False
        else:
            return None, False, False
    except Exception as e:
        print(f'Error parsing response: {response}, error: {e}')
        return e, False, False

    return None, correct, halluncination
