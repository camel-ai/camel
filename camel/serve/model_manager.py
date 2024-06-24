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
import os
from dataclasses import dataclass
from typing import Any, Dict, Literal

import torch


class ModelManager:
    def __init__(self):
        self.models: Dict[str, model_info] = {}

    def __contains__(self, model_name) -> bool:
        return model_name in self.models

    def list_models(self):
        res = {
            model: {
                "alias": self.models[model].alias,
                "basename": self.models[model].basename,
                "serving_engine": self.models[model].serving_engine,
            }
            for model in self.models
        }
        return res

    def get_model(self, alias):
        return self.models[alias].model

    def get_tokenizer(self, alias):
        return self.models[alias].tokenizer

    def get_basename(self, alias):
        return self.models[alias].basename

    def get_repo_name(self, alias):
        return self.models[alias].repo_name

    def get_serving_engine(self, alias):
        return self.models[alias].serving_engine

    def register_model(
        self,
        alias: str,
        repo_name: str,
        model: Any,
        tokenizer: Any,
        vllm: bool,
    ) -> None:
        serving_engine: Literal["Huggingface", "VLLM"]
        serving_engine = "Huggingface" if not vllm else "VLLM"
        self.models[alias] = model_info(
            alias=alias,
            basename=os.path.basename(repo_name),
            repo_name=repo_name,
            serving_engine=serving_engine,
            model=model,
            tokenizer=tokenizer,
        )

    def delete_model(self, model_name: str) -> None:
        del self.models[model_name]
        torch.cuda.empty_cache()


@dataclass
class model_info:
    alias: str
    basename: str
    repo_name: str
    serving_engine: Literal["Huggingface", "VLLM"]
    model: Any
    tokenizer: Any


def create_LLM_manager():
    return ModelManager()
