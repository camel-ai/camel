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
import ast
import os
from typing import Any

import openai
import torch
from tqdm.auto import tqdm
from transformers import pipeline
from transformers.pipelines.pt_utils import KeyDataset

from synthetic_datagen.method_factory import (
    SyntheticDataGeneratorFactory,
    SyntheticDataGeneratorMethodType,
)
from synthetic_datagen.utils.generate_utils import md_to_text


class DataGeneratorPipeline:
    """
    Manages the pipeline for synthetic data generation, curation
    and evaluation.
    """

    def __init__(
        self, spec: Any, method_type: SyntheticDataGeneratorMethodType
    ):
        """
        Initialize the pipeline with a specific generator
        type and specification.

        Args:
            spec (Any): Configuration for the generator.
            method_type (SyntheticDataGeneratorMethodType): Type of
            generator to use.
        """
        self.generator = SyntheticDataGeneratorFactory.create(
            method_type, spec
        )

    def run_generate(self):
        """Execute the data generation step of the pipeline."""
        self.generator.generate()

    def run_curate(self):
        """Execute the data curation step of the pipeline."""
        self.generator.curate()

    def run_evaluate(self):
        """Execute the data evaluation step of the pipeline."""
        self.generator.evaluate()


class ChatGPTPipeline:
    def __init__(self, model):
        self.model = model
        openai.api_key = os.environ["OPENAI_API_KEY"]

    def __call__(self, dataset):
        ret = []
        gen_count = 0
        import pdb

        pdb.set_trace()
        for d in dataset:
            response = None
            count = 0
            while not response and count < 3:
                try:
                    response = openai.ChatCompletion.create(
                        # model="gpt-3.5-turbo-0613",
                        model=self.model,
                        messages=[{"role": "user", "content": d['text']}],
                    )
                except Exception:
                    count += 1
                    print('chatgpt_error')
            if response:
                ret.append(response["choices"][0]["message"]['content'])
            else:
                ret.append("")
            gen_count += 1
            if gen_count % 10 == 0:
                print(gen_count)
        return ret


class GradioClientPipeline:
    def __init__(self, host, **kwargs):
        from gradio_client import Client

        self.client = Client(host)
        self.kwargs = kwargs

    def __call__(self, dataset):
        ret = []
        for d in dataset:
            self.kwargs['instruction_nochat'] = d['text']
            res = self.client.predict(
                str(dict(self.kwargs)), api_name='/submit_nochat_api'
            )
            ret.append(md_to_text(ast.literal_eval(res)['response']))
        return ret


class HFPipeline:
    def __init__(self, model, max_new_tokens=None, batch_size=None, **kwargs):
        from transformers import AutoModelForCausalLM, AutoTokenizer

        print("loading tokenizer")
        tokenizer = AutoTokenizer.from_pretrained(model, padding_side="left")
        print("loading model")
        model_obj = AutoModelForCausalLM.from_pretrained(
            model, torch_dtype=torch.bfloat16, device_map="auto"
        )
        pad_token_id = model_obj.config.eos_token_id
        del model_obj
        print("loading pipeline")
        self.pipeline = pipeline(
            model=model,
            tokenizer=tokenizer,
            torch_dtype=torch.bfloat16,
            trust_remote_code=True,
            device_map="auto",
            **kwargs,
        )
        print("loading pipeline done.")
        self.pipeline.tokenizer.pad_token_id = pad_token_id
        self.max_new_tokens = max_new_tokens
        self.batch_size = batch_size

    def __call__(self, dataset):
        """
        Passes dataset to LLM and returns the responses.
        :param dataset:  Hugging Face dataset containing a
                    'text' column with prompts.
        :return: list of strings with responses.
        """
        ret = []
        for i, out in enumerate(
            tqdm(
                self.pipeline(
                    KeyDataset(dataset, "text"),
                    max_new_tokens=self.max_new_tokens,
                    batch_size=self.batch_size,
                )
            )
        ):
            # remove input in case pipeline is using completion/plain prompt
            response = out[0]["generated_text"]
            response = response.replace(dataset[i]['text'], '').strip()
            ret.append(response)
        return ret
