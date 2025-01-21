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
from camel.retrievers import ElasticRetriever

retriever = ElasticRetriever(
    host="https://localhost:9200",
    index_name="camel",
    auth_kwargs={
        "http_auth": ("user", "password"),
        "ca_certs": "http_ca.crt",
    },
    create_index=False,
)

retriever.process(
    "https://docs.camel-ai.org/key_modules/retrievers.html",
    meta_data={
        "title": "Retrievers",
    },
)

query = "What is retriever?"

results = retriever.retrieve(query)
for result in results:
    print(result)
