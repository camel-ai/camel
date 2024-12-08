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
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union

from tqdm import tqdm

from .apibench_eval.eval_scripts.ast_eval import ast_parse, evaluate_response

from camel.agents import ChatAgent
from camel.benchmarks import BaseBenchmark
from camel.messages.base import BaseMessage

logger = logging.getLogger(__name__)

dataset_mapping = {
    "huggingface": {
        "api": "huggingface_api.jsonl",
        "eval": "huggingface_eval.json",
        "train": "huggingface_train.json",
        "questions": "questions_huggingface_0_shot.jsonl"
        },
    "tensorflowhub": {
        "api": "tensorflowhub_api.jsonl",
        "eval": "tensorflow_eval.json",
        "train": "tensorflow_train.json",
        "questions": "questions_tensorflowhub_0_shot.jsonl"
        },
    "torchhub": {
        "api": "torchhub_api.jsonl",
        "eval": "torchhub_eval.json",
        "train": "torchhub_train.json",
        "questions": "questions_torchhub_0_shot.jsonl"
        },
        }

def encode_question(question, dataset_name):
        """Encode multiple prompt instructions into a single string."""

        if dataset_name == "torchhub":
            domains = "1. $DOMAIN is inferred from the task description and should include one of {Classification, Semantic Segmentation, Object Detection, Audio Separation, Video Classification, Text-to-Speech}."
        elif dataset_name == "huggingface":
            domains = "1. $DOMAIN should include one of {Multimodal Feature Extraction, Multimodal Text-to-Image, Multimodal Image-to-Text, Multimodal Text-to-Video, \
            Multimodal Visual Question Answering, Multimodal Document Question Answer, Multimodal Graph Machine Learning, Computer Vision Depth Estimation,\
            Computer Vision Image Classification, Computer Vision Object Detection, Computer Vision Image Segmentation, Computer Vision Image-to-Image, \
            Computer Vision Unconditional Image Generation, Computer Vision Video Classification, Computer Vision Zero-Shor Image Classification, \
            Natural Language Processing Text Classification, Natural Language Processing Token Classification, Natural Language Processing Table Question Answering, \
            Natural Language Processing Question Answering, Natural Language Processing Zero-Shot Classification, Natural Language Processing Translation, \
            Natural Language Processing Summarization, Natural Language Processing Conversational, Natural Language Processing Text Generation, Natural Language Processing Fill-Mask,\
            Natural Language Processing Text2Text Generation, Natural Language Processing Sentence Similarity, Audio Text-to-Speech, Audio Automatic Speech Recognition, \
            Audio Audio-to-Audio, Audio Audio Classification, Audio Voice Activity Detection, Tabular Tabular Classification, Tabular Tabular Regression, \
            Reinforcement Learning Reinforcement Learning, Reinforcement Learning Robotics }"
        elif dataset_name == "tensorflowhub":
            domains = "1. $DOMAIN is inferred from the task description and should include one of {text-sequence-alignment, text-embedding, text-language-model, text-preprocessing, text-classification, text-generation, text-question-answering, text-retrieval-question-answering, text-segmentation, text-to-mel, image-classification, image-feature-vector, image-object-detection, image-segmentation, image-generator, image-pose-detection, image-rnn-agent, image-augmentation, image-classifier, image-style-transfer, image-aesthetic-quality, image-depth-estimation, image-super-resolution, image-deblurring, image-extrapolation, image-text-recognition, image-dehazing, image-deraining, image-enhancemenmt, image-classification-logits, image-frame-interpolation, image-text-detection, image-denoising, image-others, video-classification, video-feature-extraction, video-generation, video-audio-text, video-text, audio-embedding, audio-event-classification, audio-command-detection, audio-paralinguists-classification, audio-speech-to-text, audio-speech-synthesis, audio-synthesis, audio-pitch-extraction}"
        else:
            print("Error: API name is not supported.")

        prompt = question + "\nWrite a python program in 1 to 2 lines to call API in " + dataset_name + ".\n\nThe answer should follow the format: <<<domain>>> $DOMAIN, <<<api_call>>>: $API_CALL, <<<api_provider>>>: $API_PROVIDER, <<<explanation>>>: $EXPLANATION, <<<code>>>: $CODE}. Here are the requirements:\n" + domains + "\n2. The $API_CALL should have only 1 line of code that calls api.\n3. The $API_PROVIDER should be the programming framework used.\n4. $EXPLANATION should be a step-by-step explanation.\n5. The $CODE is the python code.\n6. Do not repeat the format in your answer."
        return prompt

class APIBenchBenchmark(BaseBenchmark): # TODO: Integrate retriver

    def __init__(
        self,
        data_dir: str,
        save_to: str,
        #retriever: Union[BaseRetriever] = None,
        #retrieve_kwargs: Optional[Dict[str, Any]] = None,
        processes: int = 1,
    ):
        super().__init__("apibench", data_dir, save_to, processes)
        #self._retriever = retriever
        #self._retrieve_kwargs = retrieve_kwargs or dict()

    def download(self):
        r"""Download the GAIA dataset."""
        from huggingface_hub import snapshot_download

        snapshot_download(
            repo_id="gorilla-llm/APIBench",
            repo_type="dataset",
            local_dir=self.data_dir,
            local_dir_use_symlinks=True,
        )

    def load(self, dataset_name):
        current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        for label in ['api', 'eval', 'questions']:
            file_name = dataset_mapping[dataset_name][label]
            if label == 'questions':
                file_path = current_dir / f"apibench_eval/questions/{dataset_name}/{file_name}"
                questions = []
                with open(file_path, "r") as f:
                    for line in f:
                        questions.append(json.loads(line))
                self._data[label] = questions
            if label == 'api':
                file_path = self.data_dir / file_name
                api_database = []
                with open(file_path, "r") as f:
                    for line in f:
                        api_database.append(json.loads(line))
                self._data[label] = api_database
            elif label == 'eval':
                file_path = self.data_dir / file_name
                data = []
                with open(file_path, "r") as f:
                    for line in f:
                        data.append(json.loads(line)['api_data'])
                self._data[label] = data

        ast_database = []
        for data in api_database:
            ast_tree = ast_parse(data['api_call'])
            ast_database.append(ast_tree)
        self._data['ast'] = ast_database

    
        
    def run(  # type: ignore[override]
        self,
        agent: ChatAgent,
        dataset: Union[int, List[int], Literal[
            "huggingface",
            "tensorflowhub",
            "torchhub"
        ]],
        randomize: bool = False,
        subset: Optional[int] = None,
    ) -> Dict[str, Any]:
        r"""Run the benchmark
        """
        if dataset not in dataset_mapping:
            raise ValueError(f"Invalid value for dataset: {dataset}.")
        
        logger.info(f"Running APIBench benchmark on {dataset}.")
        self.load(dataset)
        datas = self._data['questions']
        if randomize:
            random.shuffle(datas)
        if subset:
            datas = datas[:subset]
        logger.info(f"Number of tasks: {len(datas)}")
        self._results = []

        with open(self.save_to, "w") as f:
            for question in tqdm(datas, desc="Running"):
                prompt = encode_question(question["text"], dataset)
                msg = BaseMessage.make_user_message(
                    role_name="User",
                    content=prompt
                )
                try:
                    response = agent.step(msg)
                    response = response.msgs[0].content
                    api_database = self._data['api']
                    qa_pairs = self._data['eval']
                    ast_database = self._data['ast']
                    question_id = question['question_id']

                    error, correct, hallucination = evaluate_response(response, question_id, dataset, api_database, qa_pairs, ast_database)
                    self._results.append(
                            {
                                "question": question,
                                "agent_response": response,
                                "correct": correct,
                                "hallucination": hallucination,
                                "error": str(error)
                            }
                        )
                except Exception as e:
                    logger.warning(f"Error in processing task: {question}: {e}")
                    self._results.append(
                        {
                                "question": question,
                                "agent_response": None,
                                "correct": False,
                                "hallucination": False,
                                "error": str(e)
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
            "hallucination rate": hallucination / total
        }



        


