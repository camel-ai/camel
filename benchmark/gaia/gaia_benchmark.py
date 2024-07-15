import os, json, re, string, warnings
from camel.agents import ChatAgent
from typing import Literal, List, Union
from camel.messages import BaseMessage
import time
SCRIPT_PATH = os.path.realpath(__file__)
SCRIPT_DIR = os.path.dirname(SCRIPT_PATH)
DATASET_DIR = os.path.join(SCRIPT_DIR, "Dataset")
if not os.path.isdir(DATASET_DIR):
    os.mkdir(DATASET_DIR)
class GAIABenchmark:
    r"""
    Please using huggingface-cli login to get authorization
    From Hugging Face download GAIA dataset
    This Class will create a folder to cache GAIA dataset
    """
    def __init__(self) -> None:
        self.validation_tasks = [[], [], []]
        self.test_tasks = [[], [], []]

    def download(self) -> None:
        r"""
        download GAIA dataset
        """
        from huggingface_hub import snapshot_download
        snapshot_download(
            repo_id="gaia-benchmark/GAIA",
            repo_type="dataset",
            local_dir= DATASET_DIR,
            local_dir_use_symlinks=True,
        )
        validation = os.path.join(DATASET_DIR, "2023", "validation")
        test = os.path.join(DATASET_DIR, "2023", "test")
        with open(os.path.join(validation, "metadata.jsonl")) as f:
            for line in f:
                data = json.loads(line)
                self.validation_tasks[data["Level"] - 1].append(data)
        with open(os.path.join(test, "metadata.jsonl")) as f:
            for line in f:
                data = json.loads(line)
                if data["task_id"] == "0-0-0-0-0":
                    continue
                self.test_tasks[data["Level"] - 1].append(data)

    def eval(self, 
            agent: ChatAgent,
            val_or_test : Literal['validation', 'test'] = "validation", 
            level: Union[List[Literal[1, 2, 3]], Literal["all"]] = [1], 
            ) -> float:
        results = []
        scores = []
        if val_or_test == "validation":
            tasks = self.validation_tasks
        elif val_or_test == "test":
            tasks = self.test_tasks
        
        levels = [0, 1, 2] if level == "all" else [level - 1]
        for lvl in levels:
            for task in tasks[lvl]:
                final_answer = task['Final answer']
                user_msg = BaseMessage.make_user_message(
                    role_name="User",
                    content=task['Question'],
                )
                retries = 0
                max_retries = 5
                initial_backoff = 1
                max_backoff = 100
                backoff = initial_backoff
                while retries < max_retries:
                    try:
                        response = agent.step(user_msg)
                        model_answer = self.get_final_answer(response.msgs[0].content)
                        results.append({
                            "task_id": task['task_id'],
                            "model_answer": model_answer,
                        })
                        score = self.question_scorer(model_answer, final_answer)
                        scores.append(score)
                        break
                    except Exception as e:
                        if retries < max_retries:
                            wait_time = min(backoff, max_backoff)
                            print(f"error: {e}. Retrying in {wait_time} seconds")
                            time.sleep(wait_time)
                            backoff *= 4
                            retries += 1
                        else:
                            print(f"failed, error: {e}")
                            break
        self.save_results(results)
        true_count = scores.count(True)
        total_count = len(scores)
        eval_score = (true_count / total_count) * 100 if total_count > 0 else 0
        return eval_score

    def save_results(
        self, 
        results : List,
        ) -> None:
        results_file = os.path.join(SCRIPT_DIR, "results.jsonl")
        with open(results_file, 'w') as f:
            for result in results:
                f.write(json.dumps(result) + "\n")
        print(f"Results saved to {results_file}")

    def submit(self, 
               file_path: str, 
               model_name: str,
               url: str,
               organisation: str,
               mail: str,
               val_or_test: Literal['validation', 'test'] = "validation",
               ) -> str:
        from gradio_client import Client, handle_file
        client = Client("gaia-benchmark/leaderboard")
        result = client.predict(
            val_or_test=val_or_test,
            model=model_name,
            model_family=model_name,
            system_prompt= self.task_prompt,
            url=url,
            path_to_file=handle_file(file_path),
            organisation=organisation,
            mail=mail,
            api_name="/add_new_eval"
        )
        return result

#https://huggingface.co/spaces/gaia-benchmark/leaderboard/blob/main/scorer.py
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
                    UserWarning)
                return False

            comparisons = []
            for ma_elem, gt_elem in zip(ma_elems, gt_elems):
                if is_float(gt_elem):
                    normalized_ma_elem = self.normalize_number_str(ma_elem)
                    comparisons.append(normalized_ma_elem == float(gt_elem))
                else:
                    ma_elem = self.normalize_str(ma_elem, remove_punct=False)
                    gt_elem = self.normalize_str(gt_elem, remove_punct=False)
                    comparisons.append(
                        ma_elem == gt_elem
                    )
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
    
    def split_string(self, 
                    s: str, 
                    char_list: list[str] = [",", ";"]) -> list[str]:
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
        
    
