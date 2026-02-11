# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========

import json
import logging
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import tree_sitter_python as tspython
from tqdm import tqdm
from tree_sitter import Language, Parser

from camel.agents import ChatAgent
from camel.benchmarks._utils import save_to_jsonl
from camel.benchmarks.base import BaseBenchmark
from camel.utils import download_github_subdirectory

logger = logging.getLogger(__name__)


class APIBenchBenchmark(BaseBenchmark):
    r"""APIBench Benchmark adopted from `Gorilla: Large Language Model
    Connected with Massive APIs`
    <https://huggingface.co/datasets/gorilla-llm/APIBench>.

    Args:
        data_dir (Optional[str]): The directory to save the data.
        save_to (Optional[str]): The file to save the results. If None,
            uses default 'apibench.jsonl'. (default: :obj:`None`)
        processes (int, optional): The number of processes to use.
            (default: :obj:`1`)
    """

    # Mapping of dataset names to file names
    # 'Oracle' retriever used here which means all the full
    # API documentation will be included in the prompt
    DATASET_MAPPING = {
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

    def __init__(
        self,
        data_dir: Optional[str] = None,
        save_to: Optional[str] = None,
        processes: int = 1,
    ):
        r"""Initialize the APIBench benchmark.

        Args:
            data_dir (Optional[str]): Path to the data directory.
            save_to (Optional[str]): The file to save the results. If None,
                uses default 'apibench.jsonl'. (default: :obj:`None`)
            processes (int, optional): The number of processes to use for
                parallel processing. (default: :obj:`1`)
        """
        self.data_dir = data_dir or str(Path(__file__).parent / "data")
        self.save_to = save_to or "apibench.jsonl"
        super().__init__("apibench", self.data_dir, self.save_to, processes)

        self._ast_database: List[Any] = []
        self._dataset_name: Optional[str] = None

    def download(self) -> None:
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
        download_github_subdirectory(repo, subdir, self.data_dir)

    def load(
        self,
        dataset_name: str,
        force_download: bool = False,
    ) -> None:
        r"""Load the APIBench Benchmark dataset.

        Args:
            dataset_name (str): Name of the specific dataset to be loaded.
            force_download (bool, optional): Whether to force
                download the data. (default: :obj:`False`)

        Raises:
            ValueError: If the dataset name is invalid.
            FileNotFoundError: If the dataset directory does not exist.
        """
        if dataset_name not in self.DATASET_MAPPING:
            raise ValueError(
                f"Invalid dataset name: {dataset_name}. "
                f"Must be one of {list(self.DATASET_MAPPING.keys())}"
            )

        self._dataset_name = dataset_name

        if force_download:
            logger.info("Force downloading data.")
            self.download()

        dataset_path = Path(self.data_dir) / dataset_name
        if not dataset_path.exists():
            raise FileNotFoundError(
                f"Dataset directory does not exist: {dataset_path}"
            )

        for label in ['api', 'eval', 'questions']:
            file_name = self.DATASET_MAPPING[dataset_name][label]
            file_path = (
                dataset_path / file_name
                if label == 'questions'
                else Path(self.data_dir) / file_name
            )

            data = self._load_json_lines(file_path)

            if label == 'eval':
                # Extract 'api_data' specifically for eval label
                data = [item['api_data'] for item in data]

            self._data[label] = data

        # Build AST database
        self._ast_database = []
        for data in self._data['api']:
            ast_tree = self._ast_parse(data['api_call'])
            self._ast_database.append(ast_tree)
        self._data['ast'] = self._ast_database

    def run(
        self,
        pipeline_template: ChatAgent,
        randomize: bool = False,
        subset: Optional[int] = None,
    ) -> Dict[str, Any]:
        r"""Run the benchmark.

        Args:
            pipeline_template (ChatAgent): The agent to run the benchmark.
            randomize (bool, optional): Whether to randomize the data.
                (default: :obj:`False`)
            subset (Optional[int], optional): The subset of data to run.
                (default: :obj:`None`)

        Returns:
            Dict[str, Any]: Dictionary containing:
                - total: Total number of questions evaluated
                - correct: Number of correct answers
                - hallucination: Number of hallucinated answers
                - accuracy: Accuracy score
                - hallucination_rate: Hallucination rate

        Raises:
            ValueError: If dataset is not loaded.
        """
        if not self._data.get('questions'):
            raise ValueError(
                "Dataset not loaded. Please call load() before run()."
            )

        if self._dataset_name not in self.DATASET_MAPPING:
            raise ValueError(f"Invalid dataset: {self._dataset_name}.")

        logger.info(f"Running APIBench benchmark on {self._dataset_name}.")
        questions = self._data['questions']

        # Shuffle and subset data if necessary
        if randomize:
            random.shuffle(questions)
        if subset:
            questions = questions[:subset]

        logger.info(f"Number of tasks: {len(questions)}")

        # Clear the results file if it exists
        open(self.save_to, "w").close()

        # Initialize results storage
        self._results = []

        for question in tqdm(questions, desc="Running"):
            prompt = self._encode_question(question["text"], self._dataset_name)
            try:
                # Generate response
                responses = pipeline_template.step(prompt)
                response = responses.msgs[0].content

                # Evaluate response
                error, correct, hallucination = self._evaluate_response(
                    response,
                    question['question_id'],
                    self._dataset_name,
                    self._data['api'],
                    self._data['eval'],
                    self._data['ast'],
                )
                result_dict = {
                    "question": question,
                    "agent_response": response,
                    "correct": correct,
                    "hallucination": hallucination,
                    "error": str(error) if error else None,
                }
            except Exception as e:
                logger.warning(
                    f"Error in processing task: {question}: {e}"
                )
                result_dict = {
                    "question": question,
                    "agent_response": None,
                    "correct": False,
                    "hallucination": False,
                    "error": str(e),
                }

            self._results.append(result_dict)
            pipeline_template.reset()

            save_to_jsonl(self.save_to, result_dict, mode="a")

        total = len(self._results)
        correct = sum(r["correct"] for r in self._results)
        hallucination = sum(r["hallucination"] for r in self._results)

        return {
            "total": total,
            "correct": correct,
            "hallucination": hallucination,
            "accuracy": correct / total if total else "N/A",
            "hallucination_rate": hallucination / total if total else "N/A",
        }

    def _load_json_lines(self, file_path: Path) -> List[Dict[str, Any]]:
        r"""Helper function to load JSON lines from a file.

        Args:
            file_path (Path): Path to the JSONL file.

        Returns:
            List[Dict[str, Any]]: List of JSON objects.

        Raises:
            FileNotFoundError: If the file is not found.
            ValueError: If there's an error decoding JSON.
        """
        try:
            with open(file_path, "r") as f:
                return [json.loads(line) for line in f]
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {file_path}")
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Error decoding JSON in file {file_path}: {e}"
            )

    def _encode_question(self, question: str, dataset_name: str) -> str:
        r"""Encode multiple prompt instructions into a single string.

        This function is migrated from the original repo:
        https://github.com/ShishirPatil/gorilla

        Args:
            question (str): The question text.
            dataset_name (str): Name of the dataset.

        Returns:
            str: The encoded prompt.
        """
        if dataset_name == "torchhub":
            domains = (
                "1. $DOMAIN is inferred from the task description and "
                "should include one of {Classification, Semantic Segmentation, "
                "Object Detection, Audio Separation, Video Classification, "
                "Text-to-Speech}."
            )
        elif dataset_name == "huggingface":
            domains = (
                "1. $DOMAIN should include one of {Multimodal Feature "
                "Extraction, Multimodal Text-to-Image, Multimodal "
                "Image-to-Text, Multimodal Text-to-Video, "
                "Multimodal Visual Question Answering, Multimodal Document "
                "Question Answer, Multimodal Graph Machine Learning, "
                "Computer Vision Depth Estimation, Computer Vision Image "
                "Classification, Computer Vision Object Detection, "
                "Computer Vision Image Segmentation, Computer Vision "
                "Image-to-Image, Computer Vision Unconditional "
                "Image Generation, Computer Vision Video Classification, "
                "Computer Vision Zero-Shor Image Classification, "
                "Natural Language Processing Text Classification, "
                "Natural Language Processing Token Classification, "
                "Natural Language Processing Table Question Answering, "
                "Natural Language Processing Question Answering, "
                "Natural Language Processing, Zero-Shot Classification "
                "Natural Language Processing Translation, Natural Language "
                "Processing Summarization, Natural Language Processing "
                "Conversational, Natural Language Processing Text "
                "Generation, Natural Language Processing Fill-Mask, "
                "Natural Language Processing Text2Text Generation, "
                "Natural Language Processing Sentence Similarity, "
                "Audio Text-to-Speech, Audio Automatic Speech Recognition, "
                "Audio Audio-to-Audio, Audio Audio Classification, "
                "Audio Voice Activity Detection, Tabular Tabular "
                "Classification, Tabular Tabular Regression, "
                "Reinforcement Learning Reinforcement Learning, "
                "Reinforcement Learning Robotics }"
            )
        elif dataset_name == "tensorflowhub":
            domains = (
                "1. $DOMAIN is inferred from the task description "
                "and should include one of {text-sequence-alignment, "
                "text-embedding, text-language-model, text-preprocessing, "
                "text-classification, text-generation, text-question-answering, "
                "text-retrieval-question-answering, text-segmentation, "
                "text-to-mel, image-classification, image-feature-vector, "
                "image-object-detection, image-segmentation, "
                "image-generator, image-pose-detection, image-rnn-agent, "
                "image-augmentation, image-classifier, image-style-transfer, "
                "image-aesthetic-quality, image-depth-estimation, "
                "image-super-resolution, image-deblurring, image-extrapolation, "
                "image-text-recognition, image-dehazing, image-deraining, "
                "image-enhancemenmt, image-classification-logits, "
                "image-frame-interpolation, image-text-detection, image-denoising, "
                "image-others, video-classification, video-feature-extraction, "
                "video-generation, video-audio-text, video-text, "
                "audio-embedding, audio-event-classification, audio-command-detection, "
                "audio-paralinguists-classification, audio-speech-to-text, "
                "audio-speech-synthesis, audio-synthesis, audio-pitch-extraction}"
            )
        else:
            logger.error("Error: API name is not supported.")
            domains = ""

        prompt = (
            question
            + "\nWrite a python program in 1 to 2 lines to call API in "
            + dataset_name
            + ".\n\nThe answer should follow the format: <<<domain>>> $DOMAIN, "
            "<<<api_call>>>: $API_CALL, <<<api_provider>>>: $API_PROVIDER, "
            "<<<explanation>>>: $EXPLANATION, <<<code>>>: $CODE}. "
            "Here are the requirements:\n"
            + domains
            + "\n2. The $API_CALL should have only 1 line of code "
            "that calls api.\n 3. The $API_PROVIDER should be the "
            "programming framework used.\n4. $EXPLANATION should be "
            "a step-by-step explanation.\n5. The $CODE is the python code.\n6. "
            "Do not repeat the format in your answer."
        )
        return prompt

    def _ast_parse(self, candidate: str) -> Any:
        r"""Parse the program into AST trees.

        Args:
            candidate (str): The code to parse.

        Returns:
            The root node of the AST tree.
        """
        py_language = Language(tspython.language())
        parser = Parser(py_language)
        candidate_tree = parser.parse(bytes(candidate, "utf8")).root_node
        return candidate_tree

    def _get_all_sub_trees(self, root_node: Any) -> List[List[Any]]:
        r"""Get all the subtrees given a root_node.

        This code is modified from the evaluators in the original repo:
        https://github.com/ShishirPatil/gorilla

        Args:
            root_node: The root node of the AST.

        Returns:
            List of subtrees with their metadata.
        """
        node_stack = []
        sub_tree_sexp_list = []
        depth = 1
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

    def _get_args(self, node: Any, dataset_name: str) -> List[Any]:
        r"""Get all the arguments in the ast tree.

        Args:
            node: The AST node.
            dataset_name (str): Name of the dataset.

        Returns:
            List of arguments.
        """
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

    def _ast_check(
        self,
        candidate_subtree_list: List[List[Any]],
        base_tree_list: List[Any],
        dataset_name: str,
    ) -> int:
        r"""Check if there is an api match.

        Args:
            candidate_subtree_list: List of candidate subtrees.
            base_tree_list: List of base trees to match against.
            dataset_name (str): Name of the dataset.

        Returns:
            int: Index of the matching tree, or -1 if no match.
        """
        for idx, base_tree in enumerate(base_tree_list):
            if base_tree.children[0].children[0].child_count == 0:
                continue
            api_name = base_tree.children[0].children[0].children[0].text
            for candidate_tree in candidate_subtree_list:
                if candidate_tree[3] == api_name:
                    break
            # Now we have a sub-tree
            candidate_tree = candidate_tree[2]
            args_list = self._get_args(base_tree, dataset_name)
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

    def _evaluate_response(
        self,
        response: str,
        question_id: int,
        dataset_name: str,
        api_database: List[Dict[str, Any]],
        qa_pairs: List[Dict[str, Any]],
        ast_database: List[Any],
    ) -> Tuple[Optional[Exception], bool, bool]:
        r"""Evaluate the agent's response.

        This code is modified from the evaluators in the original repo:
        https://github.com/ShishirPatil/gorilla

        Args:
            response (str): The agent's response.
            question_id (int): The question ID.
            dataset_name (str): Name of the dataset.
            api_database: List of API data.
            qa_pairs: List of question-answer pairs.
            ast_database: List of AST trees.

        Returns:
            Tuple of (error, correct, hallucination).
        """
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
                ast_tree = self._ast_parse(api_call)
            except Exception as parse_error:
                logger.error(
                    f"Error parsing api_call: {api_call}, error: {parse_error}"
                )
                return parse_error, False, False

            # Search for a subtree
            ast_subtree_list = self._get_all_sub_trees(ast_tree)

            # Check which ast tree is matching
            database_index = self._ast_check(
                ast_subtree_list, ast_database, dataset_name
            )

            # We cannot index this ast in our database
            if database_index == -1:
                hallucination = True
                correct = False
                return None, correct, hallucination

            # We index our reference api_call
            ref_api_call = api_database[database_index]

            # Check for functionality
            if ref_api_call['domain'] == qa_pairs[question_id - 1]['domain']:
                correct = True
                hallucination = False
            else:
                return None, False, False
        except Exception as e:
            logger.error(f'Error parsing response: {response}, error: {e}')
            return e, False, False

        return None, correct, hallucination
