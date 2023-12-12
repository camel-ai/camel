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
from camel.functions.retrieval_function import RetrievalFunction

# Initialize the RetrievalFunction instance
retrieval_instance = RetrievalFunction()


def local_retrieval():
    r"""Performs a local retrieval example. This process involves generating
    vector storage on the local path during the first run, followed by the
    retrieval operation. Once the vector storage is created, subsequent runs
    will only involve retrieval, bypassing the initial generation step. If
    desired, the vector storage can be manually deleted after running the
    example."""
    retrieved_info = retrieval_instance.run_retrieval(
        storage_type='local', content_input_paths=[
            "examples/rag/example_database/camel paper.pdf",
            "https://docs.vllm.ai/en/latest/"
        ], vector_storage_local_path="examples/rag/",
        query="Who do you want to say a big THANK YOU to?")
    print(retrieved_info)


def remote_retrieval():
    r"""Performs a remote retrieval example. This process involves generating
    vector storage on the remote cloud service during the first run, followed
    by the retrieval operation. Once the vector storage is created, subsequent
    runs will only involve retrieval, bypassing the initial generation step.
    """
    retrieved_info = retrieval_instance.run_retrieval(
        storage_type='remote', content_input_paths=[
            "examples/rag/example_database/camel paper.pdf",
            "https://docs.vllm.ai/en/latest/"
        ], url_and_api_key=[
            "https://c7ac871b-0dca-4586-8b03-9ffb4e40363e."
            "us-east4-0.gcp.cloud.qdrant.io:6333",
            "axny37nzYHwg8jxbW-TnC90p8MibC1Tl4ypSwM87boZhSqvedvW_7w"
        ], query="Who do you want to say a big THANK YOU to?")
    print(retrieved_info)


def main():
    print("Result from local retrieval:")
    local_retrieval()
    print("Result from remote retrieval:")
    remote_retrieval()


if __name__ == "__main__":
    main()
