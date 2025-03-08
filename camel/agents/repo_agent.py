import time
from enum import Enum, auto
from string import Template
from typing import Optional, List, Tuple

from github import Github
from pydantic import BaseModel

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import BaseModelBackend, ModelFactory
from camel.responses import ChatAgentResponse
from camel.retrievers import VectorRetriever
from camel.types import ModelPlatformType, ModelType, RoleType, \
    OpenAIBackendRole
from camel.logger import get_logger

logger = get_logger(__name__)

class ProcessingMode(Enum):
    FULL_CONTEXT = auto()
    RAG = auto()

class GitHubFile(BaseModel):
    r"""Model to hold GitHub file information.

    Attributes:
        content (str): The content of the GitHub text.
        file_path (str): The path of the file.
        html_url (str): The ContentFile object.
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


class RepoAgent(ChatAgent):
    def __init__(
        self,
        system_message: Optional[str] = "You are a code assistant with repo context.",
        repo_paths: Optional[List[str]] = None,
        model: Optional[BaseModelBackend] = None,
        max_context_tokens: int = 2000000,
        vector_retriever: Optional[VectorRetriever] = None,
        github_auth_token: Optional[str] = None,
        chunk_size: Optional[int] = 8192,
        top_k: Optional[int] = 5,
        similarity: Optional[float] = 0.6,
        collection_name: Optional[str] = None,
        **kwargs
    ):
        if model is None:
            model = ModelFactory.create(
                model_platform=ModelPlatformType.ANTHROPIC,
                model_type=ModelType.CLAUDE_3_5_SONNET,
            )

        super().__init__(system_message=system_message, model=model, **kwargs)
        self.max_context_tokens = max_context_tokens
        self.vector_retriever = vector_retriever
        self.github_auth_token = github_auth_token
        self.chunk_size = chunk_size
        self.repos = self.load_repositories(repo_paths)
        self.num_tokens = 0
        self.processing_mode = ProcessingMode.FULL_CONTEXT
        self.top_k = top_k
        self.similarity = similarity
        self.collection_name = collection_name
        self.prompt_template = Template("$type: $repo"
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
            "required code.")
        self.full_text = ""

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
        try:
            url_path = url.replace("https://github.com/", "")
            parts = url_path.split("/")
            if len(parts) != 2:
                raise Exception("Incorrect GitHub repo URL format.")
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
            RepositoryInfo: An object containing information about the repository,
                including its contents.
        """
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
        github_client: Github,
    ) -> RepositoryInfo:
        r"""Load the content of a GitHub repository.
        """
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
            content=[],
        )

        while contents:
            file = contents.pop(0)
            if file.type == "file":
                if any(file.path.endswith(ext) for ext in
                       [".png", ".jpg", ".pdf", ".zip", ".gitignore"]):
                    logger.info(f"Skipping binary file: {file.path}")
                    continue
                try:
                    file_content = repo.get_contents(
                        file.path
                    ).decoded_content.decode("utf-8")
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
                contents.extend(repo.get_contents(file.path))
        return info

    def count_tokens(self) -> int:
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
        """Construct full context text from repositories."""
        repo_texts = [
            {"content": f.content, "path": f.file_path}
            for repo in self.repos for f in repo.contents
        ]
        self.full_text = self.prompt_template.safe_substitute(
            type="Repository",
            repo="\n".join(
                f"{repo['path']}\n{repo['content']}" for repo in repo_texts
            )
        )

    def add_repositories(self, repo_urls: List[str]):
        r"""Add a GitHub repository to the list of repositories."""
        new_repos = self.load_repositories(repo_urls)
        self.repos.extend(new_repos)
        self.construct_full_text()
        self.num_tokens = self.count_tokens()
        if self.processing_mode == ProcessingMode.RAG:
            for repo in new_repos:
                for f in repo.contents:
                    self.vector_retriever.process(
                        content=f.content,
                        chunk_type="chunk_by_title",
                        max_characters=self.chunk_size,
                        should_chunk=True,
                        file_path=f.file_path,
                    )
        else:
            self.check_switch_mode()

    def check_switch_mode(self) -> bool:
        if self.processing_mode == ProcessingMode.RAG:
            return False

        if self.num_tokens > self.max_context_tokens:
            if not self.vector_retriever:
                logger.warning(
                    f"Token count ({self.num_tokens}) exceeds limit "
                    f"({self.max_context_tokens}). "
                    "Either reduce repository size or provide a VectorRetriever."
                )
                return False

            logger.info("Switching to RAG mode and indexing repositories...")
            self.processing_mode = ProcessingMode.RAG
            for repo in self.repos:
                for f in repo.contents:
                    self.vector_retriever.process(
                        content=f.content,
                        chunk_type="chunk_by_title",
                        max_characters=self.chunk_size,
                        should_chunk=True,
                        file_path=f.file_path,
                    )
            self.reset()
            return True
        return False

    def step(
        self,
        input_message: BaseMessage,
        *args,
        **kwargs
    ) -> ChatAgentResponse:
        r""" Overrides `ChatAgent.step()` to first retrieve relevant context
        from the vector store before passing the input to the language model.
        """
        if (self.processing_mode == ProcessingMode.RAG and
                self.vector_retriever):
            retrieved_content = []
            retries = 3
            for attempt in range(retries):
                try:
                    raw_rag_content = self.vector_retriever.query(
                        query=input_message.content,
                        top_k=self.top_k,
                        similarity_threshold=self.similarity,
                    )
                    # Remove duplicates and retrieve the whole file
                    paths = []
                    for record in raw_rag_content:
                        if record["file_path"] not in paths:
                            retrieved_content.append(
                                {
                                    "content": self.search_by_file_path(
                                        record["file_path"]
                                    ),
                                    "similarity": record["similarity score"]
                                }
                            )
                            paths.append(record["file_path"])

                    retrieved_content = sorted(
                        retrieved_content,
                        key=lambda x: x["similarity"],
                        reverse=True,
                    )

                    user_query = input_message.content
                    full_prompt = self.prompt_template.safe_substitute(
                        type="Retrieved code",
                        repo="\n".join(
                            [
                                record["content"] for record in
                                retrieved_content
                            ]
                        )
                    )
                    input_message.content = user_query + "\n" + full_prompt
                except Exception:
                    if attempt < retries - 1:
                        sleep_time = 2 ** attempt
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


    async def search_by_file_path(
        self, file_path: str
    ) -> str:
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

        try:
            storage_instance = self.vector_retriever.storage
            source_data, _ = storage_instance.client.scroll(
                collection_name=self.collection_name ,
                limit=1000,
                scroll_filter={
                    "must": [
                        {
                            "key": "file_path",
                            "match": {"value": file_path},
                        },
                    ]
                },
                sort=[{"metadata.piece_num": "asc"}],
                with_payload=True,
                with_vectors=False,
            )
        except Exception as e:
            logger.error(
                f"Error during database initialization or scroll: {e}"
            )
            raise

        results = []
        for point in source_data:
            payload = point.payload
            piece_num = payload["metadata"]["piece_num"]
            text = payload["text"]
            if piece_num is not None and text:
                results.append({"piece_num": piece_num, "text": text})

        full_doc = "\n".join([item["text"] for item in results])

        return full_doc

