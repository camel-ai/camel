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
import time
from argparse import ArgumentParser
from typing import Dict, List

import uvicorn
from fastapi import FastAPI, HTTPException, Request, status

from camel.serve.inference import (
    chat_completion_hf,
    chat_completion_vllm,
    extract_hf_param,
    extract_vllm_param,
)
from camel.serve.model_manager import create_LLM_manager
from camel.serve.utils import load_model
from camel.types.server_types import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ListModelResponse,
    ModelRegistrationRequest,
    ModelRemovalRequest,
)

TIMEOUT_KEEP_ALIVE = 5

app = FastAPI()


@app.get("/v1/models", response_model=Dict[str, ListModelResponse])
async def list_models():
    model_list = LLM_MGR.list_models()
    return model_list


#TODO: make the return match the openai api
@app.post("/v1/chat/completions", status_code=status.HTTP_200_OK)
async def chat_completions(request: Request):
    """
    Creates a chat completion for chat messages.
    The chat completion bascially generates a response base on
    input user-assisstant dialoues.
    """
    body = await request.json()
    model_alias = body.pop("model", None)
    check_model_availability(model_alias)  # eheck if model is launched

    messages: List[Dict[str, str]] = body.get("messages", None)
    model, tokenizer = LLM_MGR.get_model(model_alias), LLM_MGR.get_tokenizer(
        model_alias)
    serving_engine = LLM_MGR.get_serving_engine(model_alias)
    if serving_engine == "VLLM":
        vllm_params = extract_vllm_param(body)
        output = chat_completion_vllm(model, tokenizer, messages, vllm_params)
    else:
        # for unassigned parameters, use model default
        fullname = LLM_MGR.get_repo_name(model_alias)
        hf_params = extract_hf_param(fullname, body)
        output = chat_completion_hf(model, tokenizer, messages, hf_params)
    return output


@app.post("/v1/register", status_code=status.HTTP_201_CREATED)
async def add_model(request: ModelRegistrationRequest) -> None:

    # load model
    model, tokenizer = load_model(request.model, request.vllm,
                                  request.hf_param)

    basename = os.path.basename(request.model)
    if request.alias is not None:
        alias = request.alias
    else:
        alias = basename
    LLM_MGR.register_model(alias=alias, repo_name=request.model, model=model,
                           tokenizer=tokenizer, vllm=request.vllm)


@app.delete("/v1/delete")
async def remove_model(request: ModelRemovalRequest):
    check_model_availability(request.alias)
    try:
        LLM_MGR.delete_model(request.alias)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return


def check_model_availability(alias) -> None:
    if alias not in LLM_MGR:
        raise KeyError(f"Model {alias} not found.")


if __name__ == "__main__":
    parser = ArgumentParser("CAMEL Openai compatible API Server")
    parser.add_argument("--host", type=str, default=None, help="host name")
    parser.add_argument("-p", "--port", type=int, default=8000,
                        help="port number")

    args = parser.parse_args()

    LLM_MGR = create_LLM_manager()
    uvicorn.run(app, host=args.host, port=args.port, log_level="debug",
                timeout_keep_alive=5)
