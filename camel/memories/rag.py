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
from typing import List

from colorama import Fore
from unstructured.chunking.title import chunk_by_title
from unstructured.partition.pdf import partition_pdf

from camel.embeddings import BaseEmbedding
from camel.memories import (
    AgentMemory,
    ChatHistoryMemory,
    ContextRecord,
    MemoryRecord,
    VectorDBMemory,
)
from camel.memories.context_creators import BaseContextCreator
from camel.storages import BaseVectorStorage, VectorRecord
from camel.types import OpenAIBackendRole

RAG_PROMPT = """Given context about the subject, answer the question based on the context provided to the best of your ability.
Context: {context}
Question:
{question}
Answer:"""


class RAGmemory(AgentMemory):

    def __init__(
        self,
        context_creator: BaseContextCreator,
        chat_hisoty_memory: ChatHistoryMemory,
        vector_storage: BaseVectorStorage,
        embedding: BaseEmbedding[str],
        files,
    ) -> None:
        self._context_creator = context_creator
        self.chat_history_memory = chat_hisoty_memory
        self.vector_storage = vector_storage
        self.embedding = embedding
        if files is not None:
            self.load_files(files)
        self._question_topic = ""

    def get_context_creator(self) -> BaseContextCreator:
        return self._context_creator

    def load_files(self, files: List[str]) -> None:
        for file in files:
            elements = partition_pdf(file)
            chunks = chunk_by_title(
                elements,
                new_after_n_chars=1000,
                max_characters=2000,
            )
            texts = [chunk.text for chunk in chunks]
            embeddings = self.embedding.embed_list(texts)
            records = [
                VectorRecord(vector=embeddings[i], payload={"text": texts[i]})
                for i in range(len(texts))
            ]

            self.vector_storage.add(records)

    def write_records(self, records: List[MemoryRecord]) -> None:
        for i in range(len(records)):
            record = records[i]
            if record.role_at_backend == OpenAIBackendRole.USER:
                self._question_topic += "\n" + record.message.content
                dict_record = record.to_dict()
                dict_record["message"]["content"] = self._formulate_context(
                    record.message.content)
                records[i] = MemoryRecord.from_dict(dict_record)
                print(Fore.RED + records[i].message.content + Fore.RESET)
        self.chat_history_memory.write_records(records)

    def _formulate_context(self, question) -> str:
        query_embedding = self.embedding.embed(self._question_topic)
        results = self.vector_storage.simple_query(query_embedding, 5)
        content = [result["text"] for result in results]
        for c in content:
            print(Fore.BLUE + c + Fore.RESET)
            print("====================")
        return RAG_PROMPT.format(context=content, question=question)

    def retrieve(self) -> List[ContextRecord]:
        return self.chat_history_memory.retrieve()

    def clear(self) -> None:
        self.chat_history_memory.clear()
