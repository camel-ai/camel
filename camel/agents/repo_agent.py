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
import time
from enum import Enum, auto
from string import Template
from typing import TYPE_CHECKING, List, Optional, Tuple, Union

if TYPE_CHECKING:
    from github.MainClass import Github
from pydantic import BaseModel

from camel.agents import ChatAgent
from camel.logger import get_logger
from camel.messages import BaseMessage
from camel.models import BaseModelBackend, ModelFactory
from camel.responses import ChatAgentResponse
from camel.retrievers import VectorRetriever
from camel.types import (
    ModelPlatformType,
    ModelType,
    OpenAIBackendRole,
    RoleType,
)
from camel.utils import track_agent
from camel.utils.chunker import CodeChunker

logger = get_logger(__name__)


class ProcessingMode(Enum):
    FULL_CONTEXT = auto()
    RAG = auto()


class GitHubFile(BaseModel):
    r"""Model to hold GitHub file information.

    Attributes:
        content (str): The content of the GitHub text.
        file_path (str): The path of the file.
        html_url (str): The actual url of the file.
    """

    content: str
    file_path: str
    html_url: str


class RepositoryInfo(BaseModel):
    r"""Model to hold GitHub repository information.

    Attributes:
        repo_name (str): The full name of the repository.
        repo_url (str): The URL of the repository.
        contents (list): A list to hold the repository contents.
    """

    repo_name: str
    repo_url: str
    contents: List[GitHubFile] = []


@track_agent(name="RepoAgent")
class RepoAgent(ChatAgent):
    r"""A specialized agent designed to interact with GitHub repositories for
    code generation tasks.
    The RepoAgent enhances a base ChatAgent by integrating context from
    one or more GitHub repositories. It supports two processing modes:
    - FULL_CONTEXT: loads and injects full repository content into the
        prompt.
    - RAG (Retrieval-Augmented Generation): retrieves relevant
        code/documentation chunks using a vector store when context
        length exceeds a specified token limit.

    Attributes:
        vector_retriever (VectorRetriever): Retriever used to
            perform semantic search in RAG mode. Required if repo content
            exceeds context limit.
        system_message (Optional[str]): The system message
            for the chat agent. (default: :str:`"You are a code assistant
            with repo context."`)
        repo_paths (Optional[List[str]]): List of GitHub repository URLs to
            load during initialization. (default: :obj:`None`)
        model (BaseModelBackend): The model backend to use for generating
            responses. (default: :obj:`ModelPlatformType.DEFAULT`
            with `ModelType.DEFAULT`)
        max_context_tokens (Optional[int]): Maximum number of tokens allowed
            before switching to RAG mode. (default: :obj:`2000`)
        github_auth_token (Optional[str]): GitHub personal access token
            for accessing private or rate-limited repositories. (default:
            :obj:`None`)
        chunk_size (Optional[int]): Maximum number of characters per code chunk
            when indexing files for RAG. (default: :obj:`8192`)
        top_k (int): Number of top-matching chunks to retrieve from the vector
            store in RAG mode. (default: :obj:`5`)
        similarity (Optional[float]): Minimum similarity score required to
            include a chunk in the RAG context. (default: :obj:`0.6`)
        collection_name (Optional[str]): Name of the vector database
            collection to use for storing and retrieving chunks. (default:
            :obj:`None`)
        **kwargs: Inherited from ChatAgent

    Note:
        The current implementation of RAG mode requires using Qdrant as the
        vector storage backend. The VectorRetriever defaults to QdrantStorage
        if no storage is explicitly provided. Other vector storage backends
        are not currently supported for the RepoAgent's RAG functionality.
    """

    def __init__(
        self,
        vector_retriever: VectorRetriever,
        system_message: Optional[
            str
        ] = "You are a code assistant with repo context.",
        repo_paths: Optional[List[str]] = None,
        model: Optional[BaseModelBackend] = None,
        max_context_tokens: int = 2000,
        github_auth_token: Optional[str] = None,
        chunk_size: Optional[int] = 8192,
        top_k: Optional[int] = 5,
        similarity: Optional[float] = 0.6,
        collection_name: Optional[str] = None,
        **kwargs,
    ):
        if model is None:
            model = ModelFactory.create(
                model_platform=ModelPlatformType.DEFAULT,
                model_type=ModelType.DEFAULT,
            )

        super().__init__(system_message=system_message, model=model, **kwargs)
        self.max_context_tokens = max_context_tokens
        self.vector_retriever = vector_retriever
        self.github_auth_token = github_auth_token
        self.chunk_size = chunk_size
        self.num_tokens = 0
        self.processing_mode = ProcessingMode.FULL_CONTEXT
        self.top_k = top_k
        self.similarity = similarity
        self.collection_name = collection_name
        self.prompt_template = Template(
            "$type: $repo\n"
            "You are an AI coding assistant. "
            "Your task is to generate code based on provided GitHub "
            "repositories. \n"
            "### Instructions: \n1. **Analyze the Repositories**: "
            "Identify which repositories contain relevant "
            "information for the user's request. Ignore unrelated ones.\n"
            "2. **Extract Context**: Use code, documentation, "
            "dependencies, and tests to understand functionality.\n"
            "3. **Generate Code**: Create clean, efficient, and "
            "well-structured code that aligns with relevant repositories. \n"
            "4. **Justify Output**: Explain which repositories "
            "influenced your solution and why others were ignored."
            "\n If the repositories lack necessary details, "
            "infer best practices and suggest improvements.\n"
            "Now, analyze the repositories and generate the "
            "required code."
        )
        self.full_text = ""
        self.chunker = CodeChunker(chunk_size=chunk_size or 8192)
        self.repos: List[RepositoryInfo] = []
        if repo_paths:
            self.repos = self.load_repositories(repo_paths)
        if len(self.repos) > 0:
            self.construct_full_text()
            self.num_tokens = self.count_tokens()
            if not self.check_switch_mode():
                self.update_memory(
                    message=BaseMessage.make_user_message(
                        role_name=RoleType.USER.value,
                        content=self.full_text,
                    ),
                    role=OpenAIBackendRole.SYSTEM,
                )

    def parse_url(self, url: str) -> Tuple[str, str]:
        r"""Parse the GitHub URL and return the (owner, repo_name) tuple.

        Args:
            url (str): The URL to be parsed.

        Returns:
            Tuple[str, str]: The (owner, repo_name) tuple.
        """
        try:
            url_path = url.replace("https://github.com/", "")
            parts = url_path.split("/")
            if len(parts) != 2:
                raise ValueError("Incorrect GitHub repo URL format.")
            else:
                return parts[0], parts[1]
        except Exception as e:
            logger.error(f"Error parsing URL: {e}")
            raise Exception(e)

    def load_repositories(
        self,
        repo_urls: List[str],
    ) -> List[RepositoryInfo]:
        r"""Load the content of a GitHub repository.

        Args:
            repo_urls (str): The list of Repo URLs.

        Returns:
            List[RepositoryInfo]: A list of objects containing information
                about the all repositories, including the contents.
        """
        from github.MainClass import Github

        github_client = Github(self.github_auth_token)
        res = []

        for repo_url in repo_urls:
            try:
                res.append(self.load_repository(repo_url, github_client))
            except Exception as e:
                logger.error(f"Error loading repository: {e}")
                raise Exception(e)
            time.sleep(1)
        logger.info(f"Successfully loaded {len(res)} repositories.")
        return res

    def load_repository(
        self,
        repo_url: str,
        github_client: "Github",
    ) -> RepositoryInfo:
        r"""Load the content of a GitHub repository.

        Args:
            repo_urls (str): The Repo URL to be loaded.
            github_client (GitHub): The established GitHub client.

        Returns:
            RepositoryInfo: The object containing information
                about the repository, including the contents.
        """
        from github.ContentFile import ContentFile

        try:
            owner, repo_name = self.parse_url(repo_url)
            repo = github_client.get_repo(f"{owner}/{repo_name}")
            contents = repo.get_contents("")
        except Exception as e:
            logger.error(f"Error loading repository: {e}")
            raise Exception(e)

        info = RepositoryInfo(
            repo_name=repo.full_name,
            repo_url=repo.html_url,
            contents=[],
        )

        # Create a list to process repository contents
        content_list: List[ContentFile] = []
        if isinstance(contents, list):
            content_list = contents
        else:
            # Handle single ContentFile case
            content_list = [contents]

        while content_list:
            file = content_list.pop(0)
            if file.type == "file":
                if any(
                    file.path.endswith(ext)
                    for ext in [
                        ".png",
                        ".jpg",
                        ".pdf",
                        ".zip",
                        ".gitignore",
                        ".mp4",
                        ".avi",
                        ".mov",
                        ".mp3",
                        ".wav",
                        ".tar",
                        ".gz",
                        ".7z",
                        ".rar",
                        ".iso",
                        ".gif",
                        ".docx",
                    ]
                ):
                    logger.info(f"Skipping binary file: {file.path}")
                    continue
                try:
                    file_obj = repo.get_contents(file.path)

                    # Handle file_obj which could be a single ContentFile or a
                    # list
                    if isinstance(file_obj, list):
                        if not file_obj:  # Skip empty lists
                            continue
                        file_obj = file_obj[
                            0
                        ]  # Take the first item if it's a list

                    if getattr(file_obj, "encoding", None) != "base64":
                        logger.warning(
                            f"Skipping file with unsupported "
                            f"encoding: {file.path}"
                        )
                        continue

                    try:
                        content_bytes = file_obj.decoded_content
                        file_content = content_bytes.decode("utf-8")
                    except UnicodeDecodeError:
                        logger.warning(f"Skipping non-UTF-8 file: {file.path}")
                        continue
                    except Exception as e:
                        logger.error(
                            f"Failed to decode file content at "
                            f"{file.path}: {e}"
                        )
                        continue

                    github_file = GitHubFile(
                        content=file_content,
                        file_path=f"{owner}/{repo_name}/{file.path}",
                        html_url=file.html_url,
                    )
                    info.contents.append(github_file)
                except Exception as e:
                    logger.error(f"Error loading file: {e}")
                    raise Exception(e)
                logger.info(f"Successfully loaded file: {file.path}")
            elif file.type == "dir":
                dir_contents = repo.get_contents(file.path)
                # Handle dir_contents which could be a single ContentFile or a
                # list
                if isinstance(dir_contents, list):
                    content_list.extend(dir_contents)
                else:
                    content_list.append(dir_contents)
        return info

    def count_tokens(self) -> int:
        r"""To count the tokens that's currently in the memory

        Returns:
            int: The number of tokens
        """
        counter = self.model_backend.token_counter
        content_token_count = counter.count_tokens_from_messages(
            messages=[
                BaseMessage.make_user_message(
                    role_name=RoleType.USER.value,
                    content=self.full_text,
                ).to_openai_message(OpenAIBackendRole.USER)
            ]
        )
        return content_token_count

    def construct_full_text(self):
        r"""Construct full context text from repositories by concatenation."""
        repo_texts = [
            {"content": f.content, "path": f.file_path}
            for repo in self.repos
            for f in repo.contents
        ]
        self.full_text = self.prompt_template.safe_substitute(
            type="Repository",
            repo="\n".join(
                f"{repo['path']}\n{repo['content']}" for repo in repo_texts
            ),
        )

    def add_repositories(self, repo_urls: List[str]):
        r"""Add a GitHub repository to the list of repositories.

        Args:
            repo_urls (str): The Repo URL to be added.
        """
        new_repos = self.load_repositories(repo_urls)
        self.repos.extend(new_repos)
        self.construct_full_text()
        self.num_tokens = self.count_tokens()
        if self.processing_mode == ProcessingMode.RAG:
            for repo in new_repos:
                for f in repo.contents:
                    self.vector_retriever.process(
                        content=f.content,
                        should_chunk=True,
                        extra_info={"file_path": f.file_path},
                        chunker=self.chunker,
                    )
        else:
            self.check_switch_mode()

    def check_switch_mode(self) -> bool:
        r"""Check if the current context exceeds the context window; if so,
        switch to RAG mode.

        Returns:
            bool: True if the mode was switched, False otherwise.
        """
        if self.processing_mode == ProcessingMode.RAG:
            return False

        if self.num_tokens > self.max_context_tokens:
            if not self.vector_retriever:
                logger.warning(
                    f"Token count ({self.num_tokens}) exceeds limit "
                    f"({self.max_context_tokens}). "
                    "Either reduce repository size or provide a "
                    "VectorRetriever."
                )
                return False

            logger.info("Switching to RAG mode and indexing repositories...")
            self.processing_mode = ProcessingMode.RAG
            for repo in self.repos:
                for f in repo.contents:
                    self.vector_retriever.process(
                        content=f.content,
                        should_chunk=True,
                        extra_info={"file_path": f.file_path},
                        chunker=self.chunker,
                    )
            self._system_message = None
            self.reset()
            return True
        return False

    def step(
        self, input_message: Union[BaseMessage, str], *args, **kwargs
    ) -> ChatAgentResponse:
        r"""Overrides `ChatAgent.step()` to first retrieve relevant context
        from the vector store before passing the input to the language model.
        """
        if (
            self.processing_mode == ProcessingMode.RAG
            and self.vector_retriever
        ):
            if isinstance(input_message, BaseMessage):
                user_query = input_message.content
            else:
                user_query = input_message
            retrieved_content = []
            retries = 1
            for attempt in range(retries):
                try:
                    raw_rag_content = self.vector_retriever.query(
                        query=user_query,
                        top_k=self.top_k or 5,
                        similarity_threshold=self.similarity or 0.6,
                    )
                    # Remove duplicates and retrieve the whole file
                    paths = []
                    for record in raw_rag_content:
                        file_path = record["extra_info"]["file_path"]
                        if file_path not in paths:
                            retrieved_content.append(
                                {
                                    "content": self.search_by_file_path(
                                        file_path
                                    ),
                                    "similarity": record["similarity score"],
                                }
                            )
                            paths.append(file_path)

                    retrieved_content = sorted(
                        retrieved_content,
                        key=lambda x: x["similarity"],
                        reverse=True,
                    )

                    full_prompt = self.prompt_template.safe_substitute(
                        type="Retrieved code",
                        repo="\n".join(
                            [record["content"] for record in retrieved_content]
                        ),
                    )

                    new_query = user_query + "\n" + full_prompt
                    if isinstance(input_message, BaseMessage):
                        input_message.content = new_query
                    else:
                        input_message = BaseMessage.make_user_message(
                            role_name="User", content=new_query
                        )
                    break
                except Exception:
                    if attempt < retries - 1:
                        sleep_time = 2**attempt
                        logger.info(
                            f"Retrying qdrant query in {sleep_time} seconds..."
                        )
                        time.sleep(sleep_time)
                    else:
                        logger.error(
                            f"Failed to query qdrant record after {retries} "
                            "attempts."
                        )

        return super().step(input_message, *args, **kwargs)

    def reset(self):
        super().reset()
        if self.processing_mode == ProcessingMode.FULL_CONTEXT:
            message = BaseMessage.make_user_message(
                role_name=RoleType.USER.value,
                content=self.full_text,
            )
            self.update_memory(message, OpenAIBackendRole.SYSTEM)
        else:
            self.num_tokens = 0

    def search_by_file_path(self, file_path: str) -> str:
        r"""Search for all payloads in the vector database where
        file_path matches the given value (the same file),
        then sort by piece_num and concatenate text fields to return a
        complete result.

        Args:
            file_path (str): The `file_path` value to filter the payloads.

        Returns:
            str: A concatenated string of the `text` fields sorted by
                `piece_num`.
        """
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        try:
            storage_instance = self.vector_retriever.storage
            collection_name = (
                self.collection_name or storage_instance.collection_name  # type: ignore[attr-defined]
            )
            source_data, _ = storage_instance.client.scroll(
                collection_name=collection_name,
                limit=1000,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="extra_info.file_path",
                            match=MatchValue(value=file_path),
                        )
                    ]
                ),
                with_payload=True,
                with_vectors=False,
            )
        except Exception as e:
            logger.error(
                f"Error during database initialization or scroll: {e}"
            )
            raise Exception(e)

        results = []
        for point in source_data:
            payload = point.payload
            piece_num = payload["metadata"]["piece_num"]
            text = payload["text"]
            if piece_num is not None and text:
                results.append({"piece_num": piece_num, "text": text})

        sorted_results = sorted(results, key=lambda x: x["piece_num"])
        full_doc = "\n".join([item["text"] for item in sorted_results])

        return full_doc
