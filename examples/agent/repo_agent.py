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
import os

from camel.agents import RepoAgent
from camel.embeddings import OpenAIEmbedding
from camel.retrievers import VectorRetriever
from camel.storages.vectordb_storages import QdrantStorage

vector_storage = QdrantStorage(
    vector_dim=OpenAIEmbedding().get_output_dim(),
    collection_name="tmp_collection",
    path="local_data/",
)

vr = VectorRetriever(embedding_model=OpenAIEmbedding(), storage=vector_storage)

repo_agent = RepoAgent(
    repo_paths=["https://github.com/camel-ai/camel"],
    chunk_size=8192,
    top_k=5,
    similarity=0.3,
    vector_retriever=vr,
    github_auth_token=os.getenv("GITHUB_AUTH_TOKEN"),
)

response = repo_agent.step("How to use a ChatAgent in CAMEL?")

print(response.msgs[0].content)
