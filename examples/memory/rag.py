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
import sys
from pathlib import Path
from typing import Dict, List

from camel.agents import ChatAgent
from camel.embeddings import OpenAIEmbedding
from camel.memories import ChatHistoryMemory, ScoreBasedContextCreator
from camel.memories.rag import RAGmemory
from camel.messages import BaseMessage
from camel.storages import QdrantStorage, VectorDistance
from camel.types import ModelType, RoleType
from camel.utils import OpenAITokenCounter


def get_result_files(folder_path, debug=False) -> List[Dict]:
    file_list = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith('.json'):
                file_path = os.path.join(root, file)
                file_list.append(file_path)
    return file_list


def agent_rag(paths: List[str]) -> None:
    files = []
    for path in paths:
        files += Path(path).rglob("*.pdf")
    print(f"Load file: {files}")

    model_type = ModelType.GPT_4_TURBO
    context_creator = ScoreBasedContextCreator(
        OpenAITokenCounter(model_type),
        model_type.token_limit,
    )
    embedding = OpenAIEmbedding()
    memory = RAGmemory(
        context_creator,
        ChatHistoryMemory(),
        QdrantStorage(
            embedding.get_output_dim(),
            path="./ragdb",
            create_collection=True,
            collection="kaust_handbook",
            distance=VectorDistance.COSINE,
        ),
        embedding=embedding,
        files=files,
    )
    print(memory.vector_storage._check_collection("kaust_handbook"))
    content = """You are a helpful assistant that can answer user's questions according to the given context.
The only information you can use is the given context. You should not provide any other information besides the given contet.
If you think the given context is not enough to answer the question, you can instruct the user to provide more information.
Please do not mention the word "context" in your answer. It should be hided from the user."""
    system_message = BaseMessage("General assistant", RoleType.ASSISTANT,
                                 meta_dict=None, content=content)
    agent = ChatAgent(
        system_message=system_message,
        model_type=model_type,
        memory=memory,
    )
    print(
        "Hello. I'm KAUST elf. I can answer any question according to the KAUST student handbooks."
    )
    for _ in range(50):
        question = input("Please type your quesiton: ")
        user_msg = BaseMessage("User", RoleType.USER, meta_dict=None,
                               content=question)
        response = agent.step(user_msg)
        print(response.msg.content)


if __name__ == "__main__":
    paths = sys.argv[1:]
    if not paths:
        paths = ["./"]

    agent_rag(paths)
