# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
import json
import os
import re
import string
import warnings
from typing import List, Literal, Optional, Tuple, Union

from camel.agents import ChatAgent
from camel.messages import BaseMessage


class GAIABenchmark:
    current_task = None
    r"""
    Please using huggingface-cli login to get authorization
    From Hugging Face download GAIA dataset
    This Class will create a folder to cache GAIA dataset
    """

    def __init__(self) -> None:
        r"""Initialize the GAIABenchmark."""
        self.val_tasks = {}
        self.test_tasks = {}
        SCRIPT_PATH = os.path.realpath(__file__)
        self.script_dir = os.path.dirname(SCRIPT_PATH)
        self.data_dir = os.path.join(self.script_dir, "Dataset")
        os.makedirs(self.data_dir, exist_ok=True)

    def download(self) -> None:
        from huggingface_hub import snapshot_download

        # Download GAIA dataset
        snapshot_download(
            repo_id="gaia-benchmark/GAIA",
            repo_type="dataset",
            local_dir=self.data_dir,
            local_dir_use_symlinks=True,
        )
        validation = os.path.join(self.data_dir, "2023", "validation")
        test = os.path.join(self.data_dir, "2023", "test")
        with open(os.path.join(validation, "metadata.jsonl")) as f:
            for line in f:
                data = json.loads(line)
                level = data['Level']
                if data['file_name'] != '':
                    data['file_path'] = os.path.join(
                        validation, data['file_name']
                    )
                if level not in self.val_tasks:
                    self.val_tasks[level] = []
                self.val_tasks[level].append(data)
        with open(os.path.join(test, "metadata.jsonl")) as f:
            for line in f:
                data = json.loads(line)
                if data['task_id'] == "0-0-0-0-0":
                    continue
                level = data['Level']
                if data['file_name'] != '':
                    data['file_path'] = os.path.join(test, data['file_name'])
                if level not in self.test_tasks:
                    self.test_tasks[level] = []
                self.test_tasks[level].append(data)
        for level in sorted(self.val_tasks.keys()):
            print(f"Val tasks level {level}: {len(self.val_tasks[level])}")
        for level in sorted(self.test_tasks.keys()):
            print(f"Test tasks level {level}: {len(self.test_tasks[level])}")

    def eval(
        self,
        agent: ChatAgent,
        level: Union[List[Literal[1, 2, 3]], Literal["all"]],
        val_or_test: Literal['validation', 'test'] = "validation",
        vector_storage_api_key: Union[Tuple[str, str], None] = None,
    ) -> float:
        r"""evaluation agent method.

        Args:
            agent (ChatAgent): Agent for evaluation
            val_or_test (Literal['validation', 'test']):
            agent (ChatAgent): The agent to be evaluated.
            val_or_test (Literal['validation', 'test']): Choose the dataset
                for evaluation (validation or test). Defaults to "validation".
            level (Union[List[Literal[1, 2, 3]], Literal["all"]]): Choose the
                evaluation levels. Can be a list of levels [1, 2, 3] or "all"
                for all levels. Defaults to level 1.
            vector_storage_api_key (Union[Tuple[str, str], None]): Input the
                remote vector database API key to enable RAG. If not provided,
                a local vector database will be created and used by default.

        Returns:
            float: The evaluation score of the agent.
        """

        # if vector_storage_api_key:
        #     self.auto_retriever = AutoRetriever(
        #         url_and_api_key=vector_storage_api_key
        #     )
        # else:
        #     vector_storage_local_path = os.path.join(self.data_dir, "storage")
        #     os.makedirs(vector_storage_local_path, exist_ok=True)
        #     self.auto_retriever = AutoRetriever(
        #         vector_storage_local_path=vector_storage_api_key
        #     )
        results = []
        scores = []

        if val_or_test == "validation":
            tasks = self.val_tasks
        elif val_or_test == "test":
            tasks = self.test_tasks

        if isinstance(level, int):
            levels = [level]
        elif level == ["all"]:
            levels = list(tasks.keys())
        else:
            levels = level
        print(levels)

        for level in levels:
            for task in tasks[level]:
                final_answer = task['Final answer']
                if task['file_name'] != '':
                    # user_msg = self.get_rag_msg(task)
                    print("Skipping RAG for now")
                    continue
                else:
                    user_msg = BaseMessage.make_user_message(
                        role_name="User",
                        content=task['Question'],
                    )
                try:
                    response = agent.step(user_msg)
                except Exception as e:
                    print(f"Error in task {task['task_id']}: {e}")
                    results.append(
                        {
                            "task_id": task['task_id'],
                            "model_answer": "Error",
                        }
                    )
                    print(
                        f"Task {task['task_id']} response: Error. Expected: {final_answer}"
                    )
                    scores.append(False)
                    continue
                    # raise e
                print(
                    f"Task {task['task_id']} response: {response.msgs[0].content}"
                )
                model_answer = self.get_final_answer(response.msgs[0].content)
                print(f"Task {task['task_id']} model answer: {model_answer}")
                # Find tool usage
                tool_calls = response.info.get('tool_calls', [])
                if tool_calls:
                    print(f"Task {task['task_id']} used tools: {tool_calls}")
                    print(f"Tool results: {response.msgs[0].content}")

                results.append(
                    {
                        "task_id": task['task_id'],
                        "model_answer": model_answer,
                    }
                )
                score = self.question_scorer(model_answer, final_answer)
                if score:
                    print(f"Correct!: {task['task_id']}")
                else:
                    print(
                        f"Wrong!: {task['task_id']}. Expected: {final_answer}, Got: {model_answer}"
                    )
                scores.append(score)
        self.save_results(results)
        true_count = scores.count(True)
        total_count = len(scores)
        eval_score = (true_count / total_count) * 100 if total_count > 0 else 0
        print("Here is a breakdown of the evaluation:")
        print(f"Total questions: {total_count}")
        print(f"Correct answers: {true_count}")
        print(f"Accuracy: {eval_score:.2f}%")
        return eval_score

    def save_results(
        self,
        results: List,
    ) -> None:
        r"""Save the evaluation results to a file.

        Args:
            results (List): A list of results to be saved.
        Returns:
            None
        """
        results_file = os.path.join(self.script_dir, "results.jsonl")
        with open(results_file, 'w') as f:
            for result in results:
                f.write(json.dumps(result) + "\n")
        print(f"Results saved to {results_file}")

    def submit(
        self,
        file_path: str,
        mail: str,
        model_name: str = "",
        model_family: str = "",
        prompt: str = "",
        url: str = "",
        organisation: str = "",
        val_or_test: Literal['validation', 'test'] = "validation",
    ) -> str:
        """Submit the result to GAIA leaderboard. This function is
        unavailable now.
        """
        from gradio_client import Client, handle_file

        client = Client("gaia-benchmark/leaderboard")
        result = client.predict(
            val_or_test=val_or_test,
            model=model_name,
            model_family=model_family,
            system_prompt=prompt,
            url=url,
            path_to_file=handle_file(file_path),
            organisation=organisation,
            mail=mail,
            api_name="/add_new_eval",
        )
        return result

    def get_rag_msg(self, task) -> BaseMessage:
        r"""Generate a message using (RAG) for a given task.

        Args:
            task (dict): A dictionary containing the task details.

        Returns:
            BaseMessage: camel Message object containing the generated content.

        Note:
            Currently, not all file formats are supported. Support for
                additional formats will be added in future updates.
        """
        import logging

        logging.basicConfig(
            level=logging.ERROR,
            format='%(asctime)s - %(levelname)s - %(message)s',
        )
        try:
            print(f"Retrieving content for task: {task['task_id']}")
            print(f"Question: {task['Question']}")
            print(f"File path: {task['file_path']}")
            retrieved_msg = self.auto_retriever.run_vector_retriever(
                query=task['Question'],
                content_input_paths=task['file_path'],
                similarity_threshold=0.2,
                top_k=1,
            )
            user_raw_msg = (
                f"Here is the query to you: {task['Question']}\n"
                f"Based on the retrieved content: {retrieved_msg}, \n"
            )
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}", exc_info=True)
            user_raw_msg = task['Question']
        return BaseMessage.make_user_message(
            role_name="User",
            content=user_raw_msg,
        )

    # scorer part
    # https://huggingface.co/spaces/gaia-benchmark/leaderboard/blob/main/scorer.py
    def question_scorer(self, model_answer: str, ground_truth: str) -> bool:
        def is_float(element: any) -> bool:
            try:
                float(element)
                return True
            except ValueError:
                return False

        if is_float(ground_truth):
            print(f"Evaluating {model_answer} as a number.")
            normalized_answer = self.normalize_number_str(model_answer)
            return normalized_answer == float(ground_truth)

        elif any(char in ground_truth for char in [",", ";"]):
            print(f"Evaluating {model_answer} as a comma separated list.")
            gt_elems = self.split_string(ground_truth)
            ma_elems = self.split_string(model_answer)

            if len(gt_elems) != len(ma_elems):
                warnings.warn(
                    "Answer lists have different lengths, returning False.",
                    UserWarning,
                )
                return False

            comparisons = []
            for ma_elem, gt_elem in zip(ma_elems, gt_elems):
                if is_float(gt_elem):
                    normalized_ma_elem = self.normalize_number_str(ma_elem)
                    comparisons.append(normalized_ma_elem == float(gt_elem))
                else:
                    ma_elem = self.normalize_str(ma_elem, remove_punct=False)
                    gt_elem = self.normalize_str(gt_elem, remove_punct=False)
                    comparisons.append(ma_elem == gt_elem)
            return all(comparisons)
        else:
            print(f"Evaluating {model_answer} as a string.")
            ma_elem = self.normalize_str(model_answer)
            gt_elem = self.normalize_str(ground_truth)
            return ma_elem == gt_elem

    def normalize_number_str(self, number_str: str) -> float:
        for char in ["$", "%", ","]:
            number_str = number_str.replace(char, "")
        try:
            return float(number_str)
        except ValueError:
            print(f"String {number_str} cannot be normalized to number str.")
            return float("inf")

    def split_string(
        self, s: str, char_list: Optional[List[str]] = None
    ) -> list[str]:
        if char_list is None:
            char_list = [",", ";"]
        pattern = f"[{''.join(char_list)}]"
        return re.split(pattern, s)

    def normalize_str(self, input_str, remove_punct=True) -> str:
        no_spaces = re.sub(r"\s", "", input_str)
        if remove_punct:
            translator = str.maketrans("", "", string.punctuation)
            return no_spaces.lower().translate(translator)
        else:
            return no_spaces.lower()

    def get_final_answer(self, content: str) -> str:
        final_answer_index = content.find("FINAL ANSWER")
        if final_answer_index == -1:
            return "FINAL ANSWER not found"
        start_index = final_answer_index + len("FINAL ANSWER: ")
        final_answer_content = content[start_index:].strip()
        return final_answer_content
