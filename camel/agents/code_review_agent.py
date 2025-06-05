from camel.logger import get_logger
from camel.models import BaseModelBackend, ModelFactory
from camel.configs import ChatGPTConfig
from camel.messages import BaseMessage
from camel.responses import ChatAgentResponse
from camel.utils import track_agent
from camel.agents import ChatAgent
from camel.types import (
    ModelPlatformType,
    ModelType,
    OpenAIBackendRole,
    RoleType,
)

from pydantic import BaseModel
from github import Github
from typing import List, Optional, Tuple, Union
from enum import Enum, auto
from string import Template
import re
import os

logger = get_logger(__name__)

class ChangeMode(Enum):
    r"""Enum for change modes in a pull request.

    Attributes:
        NORMAL: All modified files are considered; no incremental updates.
        INCREMENTAL: Only the changes introduced in the current commit are reviewed.
    """
    NORMAL = auto()
    INCREMENTAL = auto()


class ChangedFile(BaseModel):
    r"""Model to hold information about a file changed in a PR or commit.

    Attributes:
        filename (str): File path.
        change_type (str): Change type ('added', 'modified', 'deleted').
        patch (Optional[str]): Git diff content of the change.
    """
    filename: str
    change_type: str
    patch: Optional[str] = None

    def __str__(self) -> str:
        patch = repr(self.patch)
        return f"ChangedFile(filename='{self.filename}', change_type='{self.change_type}', patch={patch})"

    def __repr__(self) -> str:
        return self.__str__()


class CommitInfo(BaseModel):
    r"""Model for representing a single commit.

    Attributes:
        commit_message (str): Commit message.
        changed_files (List[ChangedFile]): List of files changed in the commit.
    """
    commit_message: str
    changed_files: List[ChangedFile]

    def __str__(self) -> str:
        return f"CommitInfo(commit_message='{self.commit_message}', changed_files={self.changed_files})"

    def __repr__(self) -> str:
        return self.__str__()


class PullRequestInfo(BaseModel):
    r"""Model for representing a pull request.

    Attributes:
        pr_id (int): Pull request ID.
        pr_title (str): Title of the pull request.
        pr_body (str): Body/description of the pull request.
        changed_files (List[ChangedFile]): List of changed files.
    """
    pr_id: int
    pr_title: str
    pr_body: str
    changed_files: List[ChangedFile]

    def __str__(self) -> str:
        files_str = ", ".join([str(file) for file in self.changed_files])
        return f"PullRequest(pr_id={self.pr_id}, pr_title='{self.pr_title}', pr_body='{self.pr_body}', changed_files=[{files_str}])"

    def __repr__(self) -> str:
        return self.__str__()


@track_agent(name="CodeReviewAgent")
class CodeReviewAgent(ChatAgent):
    def __init__(
        self,
        system_message: Optional[str] = "You are an automated code review assistant, helping to quickly identify potential issues and improvements in code.",
        model: Optional[BaseModelBackend] = None,
        github_token: str = None,
        repo_full_name: str = None,
        change_model: ChangeMode = ChangeMode.NORMAL,
        **kwargs,
    ) -> None:
        r"""
        Initialize the CodeReviewAgent.

        Args:
            system_message (Optional[str]): System prompt for the agent.
            model (Optional[BaseModelBackend]): AI model backend.
            github_token (str): GitHub personal access token.
            repo_full_name (str): Full name of the repo (e.g., 'owner/repo').
            change_model (ChangeMode): Change analysis mode.
        """
        if model is None:
            model = ModelFactory.create(
                model_platform=ModelPlatformType.DEFAULT,
                model_type=ModelType.DEFAULT,
            )

        super().__init__(system_message=system_message, model=model, **kwargs)
        self.github_token = github_token
        self.repo_full_name = repo_full_name
        self.github_client = Github(self.github_token)
        self.repo = self.github_client.get_repo(self.repo_full_name)
        self.change_model = change_model
        self.prompt_template = Template(
            "$diff_summary\n"
            "You are an AI code reviewer. "
            "Your task is to review code diffs based on the provided file changes.\n"
            "### Instructions:\n"
            "1. **Understand the Context**: "
            "Carefully read the diff content for each file. Consider additions, deletions, and modifications, "
            "as well as the structure and logic of the code.\n"
            "2. **Review from Four Dimensions**:\n"
            "   - **Security**: Identify potential security vulnerabilities "
            "(e.g., unsafe inputs, hardcoded secrets, insufficient validation, unsafe dependencies).\n"
            "   - **Code Style**: Check for adherence to coding conventions and formatting standards "
            "(e.g., naming, indentation, consistent syntax).\n"
            "   - **Performance**: Evaluate efficiency. Identify performance bottlenecks or optimization opportunities.\n"
            "   - **Maintainability**: Assess code readability, structure, and ease of future modification "
            "(e.g., meaningful naming, modularity, clarity).\n"
            "3. **Summarize Suggestions**: "
            "Provide structured, actionable comments per file and per dimension. "
            "State explicitly if a dimension has no issues.\n"
            "4. **Be Constructive**: "
            "Justify criticisms with reasoning and offer better alternatives. Praise well-written code where appropriate.\n"
            "5. **Output Format**: "  
            "Your output **must be in Markdown**. Use proper headings, bullet points, and code blocks to make the review clear and easy to read.\n"
            "### Additional User Request:\n"
            "$review_request"
        )

    def sanitize_filename(self, path: str) -> str:
        r"""
        Sanitize file path into safe flat filename for saving as markdown.

        Args:
            path (str): Original file path.

        Returns:
            str: Sanitized filename.
        """
        filename = path.replace(os.sep, '__').replace('/', '__')
        filename = re.sub(r'[\\:*?"<>|]', '_', filename)
        filename = filename.replace('.py', '_py')
        return f"{filename}.md"

    def save_review_markdowns(self, changed_files: List[ChangedFile], review_outputs: List[str], save_dir: str = "./review") -> None:
        r"""
        Save each file's code review output as a markdown file.

        Args:
            changed_files (List[ChangedFile]): Files changed.
            review_outputs (List[str]): Corresponding AI review outputs.
            save_dir (str): Output directory.
        """
        os.makedirs(save_dir, exist_ok=True)

        for file, review in zip(changed_files, review_outputs):
            try:
                filename = self.sanitize_filename(file.filename)
                filepath = os.path.join(save_dir, filename)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(f"# Code Review for `{file.filename}`\n\n")
                    f.write(review)
                logger.info(f"Saved review for {file.filename} -> {filepath}")
            except Exception as e:
                logger.exception(f"Failed to save review for {file.filename}: {str(e)}")

    def fetch_pull_request_info(self, pr_number: int) -> PullRequestInfo:
        r"""
        Fetch PR info and changed files.

        Args:
            pr_number (int): PR number.

        Returns:
            PullRequestInfo: PR metadata and file changes.
        """
        try:
            pr = self.repo.get_pull(pr_number)
            pr_id = pr.id
            pr_title = pr.title
            pr_body = pr.body
            files = pr.get_files()
            pr_file_objects = [
                ChangedFile(
                    filename=file.filename,
                    change_type=file.status,
                    patch=getattr(file, 'patch', '')
                )
                for file in files
            ]
        except Exception as e:
            logger.error(f"Error fetching PR information: {e}")
            raise

        return PullRequestInfo(
            pr_id=pr_id,
            pr_title=pr_title,
            pr_body=pr_body,
            changed_files=pr_file_objects
        )

    def fetch_commit_info(self, commit_sha: str) -> CommitInfo:
        r"""
        Fetch commit info and changed files.

        Args:
            commit_sha (str): Commit SHA.

        Returns:
            CommitInfo: Commit metadata and file changes.
        """
        try:
            commit = self.repo.get_commit(commit_sha)
            commit_message = commit.commit.message
            files = commit.files
            commit_file_objects = [
                ChangedFile(
                    filename=file.filename,
                    change_type=file.status,
                    patch=getattr(file, 'patch', '')
                )
                for file in files
            ]
        except Exception as e:
            logger.error(f"Error fetching commit information: {e}")
            raise

        return CommitInfo(
            commit_message=commit_message,
            changed_files=commit_file_objects
        )

    def review(
        self,
        query: str,
        pr_number: int = None,
        commit_sha: str = None,
    ):
        """
        Perform a code review by analyzing either a pull request (NORMAL mode)
        or a specific commit (INCREMENTAL mode). This function fetches changed files,
        generates review prompts using a template, invokes the agent to review each
        file, and saves the review results.

        Args:
            query (str): The review request or question to guide the review.
            pr_number (int, optional): Pull request number used in NORMAL mode.
            commit_sha (str, optional): Commit SHA used in INCREMENTAL mode.

        Returns:
            ChatAgentResponse: Contains assistant messages for each reviewed file.
        """
        try:
            if self.change_model == ChangeMode.NORMAL:
                if pr_number is None:
                    raise ValueError("Parameter 'pr_number' is required in NORMAL mode.")
                
                logger.info(f"[NORMAL] Fetching pull request info for PR #{pr_number}...")
                context_info = self.fetch_pull_request_info(pr_number)
                changed_files = context_info.changed_files
                logger.info(f"[NORMAL] PR #{pr_number} contains {len(changed_files)} changed files.")

            elif self.change_model == ChangeMode.INCREMENTAL:
                if commit_sha is None:
                    raise ValueError("Parameter 'commit_sha' is required in INCREMENTAL mode.")
                
                logger.info(f"[INCREMENTAL] Fetching commit info for SHA {commit_sha}...")
                context_info = self.fetch_commit_info(commit_sha)
                changed_files = context_info.changed_files
                logger.info(f"[INCREMENTAL] Commit {commit_sha} contains {len(changed_files)} changed files.")

            logger.info(f"[{self.change_model.value}] Starting review with query: {query}")

        except Exception as e:
            logger.exception("Error during code review")
            raise

        all_msgs = []
        review_outputs = []

        for file in changed_files:
            diff_summary = f"--- {file.filename} ({file.change_type}) ---\n{file.patch or '[No diff available]'}"
            full_prompt = self.prompt_template.safe_substitute(
                diff_summary=diff_summary,
                review_request=query,
            )
            user_msg = BaseMessage.make_user_message(
                role_name="User",
                content=full_prompt,
            )
            result = super().step(user_msg)
            response_content = result.msgs[0].content if result.msgs else ""

            all_msgs.append(BaseMessage.make_assistant_message(role_name="CodeReview_Agent", content=f"### {file.filename}\n{response_content}"))
            review_outputs.append(response_content)
        
        self.save_review_markdowns(changed_files, review_outputs)
        return ChatAgentResponse(msgs=all_msgs, terminated=False, info={})

