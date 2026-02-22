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
from github import Github, Repository
from typing import List, Optional, Tuple, Union
from enum import Enum, auto
from string import Template
import re
import os

logger = get_logger(__name__)

class FileDiff(BaseModel):
    r"""
    Represents the differences for a specific file in a commit.

    Attributes:
        filename (str): The file's path relative to the repository root.
        status (str): The change status of the file. One of: 'added', 'modified', or 'removed'.
        patch (Optional[str]): The Git patch (diff) content for the file, if available.
        additions (int): Number of lines added in this file.
        deletions (int): Number of lines deleted in this file.
        changes (int): Total number of changed lines (additions + deletions).
        blob_url (Optional[str]): URL linking to the file's blob view for the specific commit on GitHub.
    """
    filename: str
    status: str = None
    patch: Optional[str] = None
    additions: int = 0
    deletions: int = 0
    changes: int = 0
    blob_url: Optional[str] = None

    def __str__(self):
        patch = repr(self.patch)
        return (
            f"FileDiff(filename='{self.filename}', status='{self.status}', "
            f"additions={self.additions}, deletions={self.deletions}, "
            f"changes={self.changes}, blob_url={repr(self.blob_url)}, patch={patch})"
        )

    def __repr__(self) -> str:
        return self.__str__()

class CommitDiffInfo(BaseModel):
    r"""
    Model representing a Git commit with its associated file differences.

    Attributes:
        commit_sha (str): The SHA hash uniquely identifying the commit.
        message (str): The commit message describing the changes.
        files_diff (List[FileDiff]): A list of FileDiff objects representing
            the changes made to files in this commit.
    """
    commit_sha: str = None
    message: str = None
    files_diff: List[FileDiff] = None

class PRDiffInfo(BaseModel):
    r"""
    Model representing a Pull Request with its associated file differences.

    Attributes:
        pr_number (int): The unique identifier of the pull request.
        title (str): The title of the pull request.
        description (str): The description or body text of the pull request.
        files_diff (List[FileDiff]): A list of FileDiff objects representing
            the cumulative changes across all commits in the PR.
        commit_diffs (List[CommitDiffInfo]): Optional list of individual commit diffs (if needed).
    """
    pr_number: int = None
    title: Optional[str] = None
    description: Optional[str] = None
    files_diff: List[FileDiff] = None
    commit_diffs: Optional[List[CommitDiffInfo]] = None

@track_agent(name="CodeReviewAgent")
class CodeReviewAgent(ChatAgent):
    def __init__(
        self,
        system_message: Optional[str] = "You are an automated code review assistant, helping to quickly identify potential issues and improvements in code.",
        model: Optional[BaseModelBackend] = None,
        github_token: str = None,
        repo_full_name: str = None,
        max_context_tokens: Optional[int] = 2000,
        **kwargs,
    ) -> None:
        """
        Initialize a CodeReviewAgent for automated code analysis and review.

        This agent performs intelligent code reviews on GitHub repositories using an AI model.
        It supports two modes of operation:
        
        - **Standard Review**: Reviews changes in a pull request (PR).
        - **Incremental Review**: Reviews changes in a specific commit (commit-by-commit basis).

        The agent integrates with the GitHub API to access repository contents and diffs,
        and uses prompt templates to guide the language model in generating structured review comments.

        Args:
            system_message (Optional[str]): System prompt describing the agent's role.
                Defaults to a predefined message describing the agent as a code review assistant.
            model (Optional[BaseModelBackend]): Backend language model for generating review comments.
                If not provided, a default model will be used.
            github_token (str): GitHub personal access token for API authentication.
            repo_full_name (str): Full name of the GitHub repository (e.g., "owner/repo").
            max_context_tokens (Optional[int]): Maximum number of tokens to allocate for context during review.
            **kwargs: Additional arguments forwarded to the base `ChatAgent` class.

        Attributes:
            github_client (Github): GitHub API client instance.
            repo (Repository): GitHub repository object targeted for review.
            incremental_review (bool): Whether to perform an incremental (commit-based) review.
            incremental_review_prompt_template (Template): Prompt template used in incremental review mode.
            standard_review_prompt_template (Template): Prompt template used in standard PR review mode.
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
        self.is_incremental_review = False
        self.max_context_tokens = max_context_tokens
        self.incremental_review_prompt_template = Template(
        "You are an AI code reviewer working in **incremental review mode**, focused on analyzing changes in each file of a single commit.\n\n"
        "Your goal is to provide structured, actionable code review feedback for **each changed file** based on the provided patch content and metadata.\n\n"
        "---\n\n"
        "### Commit Summary:\n\n"
        "$files_diff_detail_commit_summary\n\n"
        "---\n\n"
        "### File Diff Content:\n\n"
        "Below are the full unified diffs of all changed files in this commit:\n\n"
        "$files_diff_detail_file_diffs\n\n"
        "---\n\n"
        "### Review Guidelines:\n\n"
        "1. **Read the Patch Carefully:**\n"
        "   - Focus on the newly added lines (lines starting with `+`), but consider the full diff context as needed.\n"
        "   - Use the file status (`added`, `modified`, `removed`) to distinguish new, modified, or deleted files.\n\n"
        "2. **You must review every changed file:**\n"
        "   - Regardless of file status, provide a detailed review of the changes in that file.\n\n"
        "3. **Review from Four Core Dimensions:**\n"
        "   - 🔐 **Security:** Check for unsafe input handling, hardcoded secrets, dangerous external calls, and missing validations.\n"
        "   - 🎨 **Code Style:** Evaluate naming conventions, indentation, spacing, and overall formatting consistency.\n"
        "   - ⚙️ **Performance:** Identify costly operations in loops, large memory allocations, or unnecessary complexity.\n"
        "   - 🧩 **Maintainability:** Judge code clarity, modularity, meaningful naming, and potential technical debt.\n\n"
        "4. **File-by-File Analysis:**\n"
        "   - Write an overall impression summary per file (if applicable).\n"
        "   - For each dimension, either raise issues or explicitly state “No major issues found.”\n\n"
        "5. **Constructive and Respectful Tone:**\n"
        "   - When problems are found, explain *why they matter* and suggest *how to fix them*.\n"
        "   - Praise clean, well-written code when appropriate.\n\n"
        "6. **Output Format (Strict):**\n"
        "   - Use **Markdown** syntax.\n"
        "   - Use top-level headings per file like `## File: filename.py`.\n"
        "   - Use bullet points for each review dimension.\n"
        "   - Use code blocks to show specific issues or suggestions when helpful.\n\n"
        "---\n\n"
        "### Additional User Requests:\n\n"
        "$review_request"
        )

        self.standard_review_prompt_template = Template(
        "You are an AI code reviewer working in **standard review mode**, analyzing all file diffs in a single Pull Request (PR).\n\n"
        "Your goal is to provide structured, actionable code review feedback for **each changed file** based on the provided patch contents and metadata.\n\n"
        "---\n\n"
        "### PR Summary:\n\n"
        "$files_diff_detail_commit_summary\n\n"
        "---\n\n"
        "### File Diff Content:\n\n"
        "Below are the full unified diffs of all changed files in this PR:\n\n"
        "$files_diff_detail_file_diffs\n\n"
        "---\n\n"
        "### Review Guidelines:\n\n"
        "1. **Carefully read each patch:**\n"
        "   - Focus primarily on added lines (lines starting with `+`), but consider the full diff context as needed.\n"
        "   - Use file status (`added`, `modified`, `removed`) to understand the nature of changes.\n\n"
        "2. **Review every file individually:**\n"
        "   - Provide detailed review comments per file regardless of file status.\n\n"
        "3. **Assess from Four Core Perspectives:**\n"
        "   - 🔐 **Security:** Look for unsafe inputs, hardcoded secrets, dangerous external calls, missing validations.\n"
        "   - 🎨 **Code Style:** Check naming conventions, indentation, spacing, consistent formatting.\n"
        "   - ⚙️ **Performance:** Identify any costly loops, excessive memory use, or unnecessary complexity.\n"
        "   - 🧩 **Maintainability:** Evaluate code clarity, modularity, meaningful names, and potential tech debt.\n\n"
        "4. **File-by-file analysis:**\n"
        "   - Summarize overall impressions per file if any.\n"
        "   - For each dimension, either report issues or state “No major issues found.”\n\n"
        "5. **Maintain a constructive and respectful tone:**\n"
        "   - Explain why issues matter and suggest improvements.\n"
        "   - Praise well-written and clean code where appropriate.\n\n"
        "6. **Output format (strict):**\n"
        "   - Use **Markdown**.\n"
        "   - Use top-level headers like `## File: filename.py` for each file.\n"
        "   - Use bullet points for each dimension.\n"
        "   - Use code blocks to highlight specific issues or recommendations.\n\n"
        "---\n\n"
        "### Additional User Requests:\n\n"
        "$review_request"
        )
        self._EXCLUDED_SUFFIXES = {
        ".png", ".jpg", ".jpeg", ".pdf", ".zip", ".gitignore",
        ".mp4", ".avi", ".mov", ".mp3", ".wav", ".tar", ".gz",
        ".7z", ".rar", ".iso", ".gif", ".docx", ".rst", "json"
        }

    def get_commit_diff_by_sha(self, commit_sha: str) -> Optional[CommitDiffInfo]:
        """
        Retrieve the commit diff information for a specific commit SHA.

        Args:
            commit_sha (str): The SHA of the commit to retrieve diffs for.

        Returns:
            Optional[CommitDiffInfo]: A CommitDiffInfo object containing commit SHA, message,
                                    and file diffs, or None if retrieval fails.
        """
        try:
            full_commit = self.repo.get_commit(commit_sha)
            files_diff = []
            for file in full_commit.files:
                if any(file.filename.lower().endswith(suffix) for suffix in self._EXCLUDED_SUFFIXES):
                    continue
                files_diff.append(FileDiff(
                    filename=file.filename,
                    status=file.status,
                    patch=file.patch,
                    additions=file.additions,
                    deletions=file.deletions,
                    changes=file.changes,
                    blob_url=file.blob_url
                ))
            return CommitDiffInfo(
                commit_sha=commit_sha,
                message=full_commit.commit.message,
                files_diff=files_diff
            )
        except Exception as e:
            logger.info(f"[get_commit_diff_by_sha] Failed to retrieve diff for commit {commit_sha}: {e}")
            return None

    def get_pr_diff_info(self, pr_number: int) -> PRDiffInfo:
        """
        Retrieve overall Pull Request level diff information along with commit-level diffs.

        Args:
            pr_number (int): The pull request number to fetch the diff information from.

        Returns:
            PRDiffInfo: An object containing PR metadata (number, title, description),
                        a list of cumulative file diffs across the entire PR,
                        and a list of commit-level diffs.
        """
        try:
            pr = self.repo.get_pull(pr_number)

            pr_files_diff = []
            for f in pr.get_files():
                if any(f.filename.lower().endswith(suffix) for suffix in self._EXCLUDED_SUFFIXES):
                    continue
                pr_files_diff.append(FileDiff(
                    filename=f.filename,
                    status=f.status,
                    patch=f.patch,
                    additions=f.additions,
                    deletions=f.deletions,
                    changes=f.changes,
                    blob_url=f.blob_url
                ))

            commit_diffs = []
            for commit in pr.get_commits():
                diff_info = self.get_commit_diff_by_sha(commit.sha)
                if diff_info:
                    commit_diffs.append(diff_info)

            return PRDiffInfo(
                pr_number=pr.number,
                title=pr.title,
                description=pr.body,
                files_diff=pr_files_diff,
                commit_diffs=commit_diffs
            )
        except Exception as e:
            logger.info(f"[get_pr_diff_info] Failed to retrieve PR diff info for PR #{pr_number}: {e}")
            return PRDiffInfo(pr_number=pr_number, files_diff=[], commit_diffs=[])

    def build_diff_summary_text(
        self,
        pr_diff: Optional[PRDiffInfo] = None,
        commit_diff: Optional[CommitDiffInfo] = None
    ) -> str:
        """
        Build a structured summary text from either a Pull Request or a single Commit diff.

        This method supports both standard (PR-level) and incremental (commit-level) review modes.
        It generates a concise textual summary of the PR or commit and its associated file changes.

        Exactly one of `pr_diff` or `commit_diff` must be provided.

        Args:
            pr_diff (Optional[PRDiffInfo]): Diff information for the entire Pull Request.
                Should be provided when performing a standard PR-level review.
            commit_diff (Optional[CommitDiffInfo]): Diff information for a single commit.
                Should be provided when performing an incremental commit-level review.

        Returns:
            str: A formatted summary string containing commit or PR metadata and a list of file-level changes.

        Raises:
            ValueError: If neither or both of `pr_diff` and `commit_diff` are provided.
        """
        try:
            if (pr_diff is None and commit_diff is None) or (pr_diff and commit_diff):
                raise ValueError("Exactly one of pr_diff or commit_diff must be provided.")

            if self.is_incremental_review:
                diff_info = commit_diff
                summary_lines = [
                    f"Commit SHA: `{diff_info.commit_sha}`",
                    f"Message: {diff_info.message.strip() if diff_info.message else 'No commit message'}",
                    ""
                ]
            else:
                diff_info = pr_diff
                summary_lines = [f"PR #{diff_info.pr_number}"]
                if diff_info.title:
                    summary_lines.append(f"Title: {diff_info.title}")
                if diff_info.description:
                    summary_lines.append(f"Description: {diff_info.description.strip()}")
                summary_lines.append("")

            target_diffs = diff_info.files_diff or []
            if not target_diffs:
                summary_lines.append("No file changes found.")
                return "\n".join(summary_lines)

            summary_lines.append("File Change Summary:\n")
            for f in target_diffs:
                summary_lines.append(
                    f"- `{f.filename}`: {f.status}, +{f.additions}/-{f.deletions}, total: {f.changes}"
                )

            return "\n".join(summary_lines)
        except Exception as e:
            logger.info(f"[build_diff_summary_text] Failed to build summary: {e}")
            return "Failed to generate diff summary."

    def count_tokens(self, message: str) -> int:
        r"""
        Count the tokens for a given user message content.

        Args:
            message (str): The message content to be tokenized.

        Returns:
            int: Number of tokens used.
        """
        counter = self.model_backend.token_counter

        return counter.count_tokens_from_messages([
            BaseMessage.make_user_message(
                role_name=RoleType.USER.value,
                content=message,
            ).to_openai_message(OpenAIBackendRole.USER)
        ])

    def get_review_context(
        self,
        input_message: Union[str, BaseMessage],
        pr_number: Optional[int],
        commit_sha: Optional[str],
    ) -> Tuple[List[FileDiff], str, Template]:
        r"""
        Based on review mode, fetch context info including changed files, diff summary, and prompt template.

        Args:
            input_message (str | BaseMessage): The review instruction or request.
            pr_number (int | None): PR number for NORMAL mode.
            commit_sha (str | None): Commit SHA for INCREMENTAL mode.

        Returns:
            Tuple[List[FileDiff], str, Template]: changed_files, diff_summary, prompt_template
        """
        try:
            if self.is_incremental_review:
                if commit_sha is None:
                    raise ValueError("Parameter 'commit_sha' is required in INCREMENTAL mode.")

                logger.info(f"[INCREMENTAL] Fetching commit info for SHA {commit_sha}...")
                context_info = self.get_commit_diff_by_sha(commit_sha)
                changed_files = context_info.files_diff if context_info else []
                logger.info(f"[INCREMENTAL] Commit {commit_sha} contains {len(changed_files)} changed files.")

                diff_summary = self.build_diff_summary_text(commit_diff=context_info)
                prompt_template = self.incremental_review_prompt_template

                logger.info(f"[Incremental Review] Starting review with query: {input_message}")

            else:
                if pr_number is None:
                    raise ValueError("Parameter 'pr_number' is required in NORMAL mode.")

                logger.info(f"[NORMAL] Fetching pull request info for PR #{pr_number}...")
                context_info = self.get_pr_diff_info(pr_number)
                changed_files = context_info.files_diff
                logger.info(f"[NORMAL] PR #{pr_number} contains {len(changed_files)} changed files.")

                diff_summary = self.build_diff_summary_text(pr_diff=context_info)
                prompt_template = self.standard_review_prompt_template

                logger.info(f"[Standard Review] Starting review with query: {input_message}")

            return changed_files, diff_summary, prompt_template

        except Exception as e:
            logger.error(f"Error occurred while fetching diff info: {e}")
            raise

    def chunk_file_diffs_by_token(
        self,
        template: Template,
        file_diffs: List[FileDiff],
    ) -> List[Tuple[str, List[str]]]:
        r"""
        Split a list of FileDiffs into multiple message strings, each fitting within the token limit
        when inserted into the fixed placeholder '$files_diff_detail_file_diffs' in the given template.
        Also returns filenames included in each message for traceability.

        Args:
            template (Template): The message template containing the placeholder '$files_diff_detail_file_diffs'.
            file_diffs (List[FileDiff]): A list of FileDiff objects representing file changes.

        Returns:
            List[Tuple[str, List[str]]]: A list of (prompt_message, filenames_in_this_chunk)
        """
        placeholder_key = "files_diff_detail_file_diffs"
        base_text = template.safe_substitute(files_diff_detail_file_diffs="")
        base_token_count = self.count_tokens(base_text)

        if base_token_count > self.max_context_tokens:
            raise ValueError("The fixed part of the template exceeds the token limit.")

        results = []
        current_diff_text = ""
        current_filenames = []

        for fd in file_diffs:
            file_header = f"### File: {fd.filename} [{fd.status}]\n"
            patch_text = fd.patch or ""
            diff_text = file_header + patch_text + "\n"

            tentative_text = current_diff_text + diff_text
            full_text = template.safe_substitute(files_diff_detail_file_diffs=tentative_text)
            token_cnt = self.count_tokens(full_text)

            if token_cnt <= self.max_context_tokens:
                current_diff_text = tentative_text
                current_filenames.append(fd.filename)
            else:
                if current_diff_text:
                    msg = template.safe_substitute(files_diff_detail_file_diffs=current_diff_text)
                    results.append((msg, current_filenames))

                # check if this file's diff alone is too large
                single_file_text = template.safe_substitute(files_diff_detail_file_diffs=diff_text)
                if self.count_tokens(single_file_text) > self.max_context_tokens:
                    lines = patch_text.splitlines(keepends=True)
                    small_chunk = file_header
                    small_files = []

                    for line in lines:
                        candidate = small_chunk + line
                        candidate_text = template.safe_substitute(files_diff_detail_file_diffs=candidate)
                        if self.count_tokens(candidate_text) <= self.max_context_tokens:
                            small_chunk = candidate
                        else:
                            msg = template.safe_substitute(files_diff_detail_file_diffs=small_chunk)
                            results.append((msg, [fd.filename]))
                            small_chunk = file_header + line
                    if small_chunk != file_header:
                        msg = template.safe_substitute(files_diff_detail_file_diffs=small_chunk)
                        results.append((msg, [fd.filename]))
                    current_diff_text = ""
                    current_filenames = []
                else:
                    current_diff_text = diff_text
                    current_filenames = [fd.filename]

        if current_diff_text:
            msg = template.safe_substitute(files_diff_detail_file_diffs=current_diff_text)
            results.append((msg, current_filenames))

        return results

    def step(
        self,
        input_message: Union[str, BaseMessage],
        pr_number: Optional[int] = None,
        commit_sha: Optional[str] = None,
    ) -> ChatAgentResponse:
        r"""
        Perform a code review by analyzing either a pull request (NORMAL mode)
        or a specific commit (INCREMENTAL mode). This method fetches changed files,
        generates review prompts using a template, invokes the agent to review each
        file group, and collects the results.

        Args:
            input_message (Union[str, BaseMessage]): The review instruction guiding the process.
            pr_number (int, optional): Pull request number used in NORMAL mode.
            commit_sha (str, optional): Commit SHA used in INCREMENTAL mode.

        Returns:
            ChatAgentResponse: Contains assistant messages with review results for each file group.
        """
        if commit_sha is not None:
            self.is_incremental_review = True
        elif pr_number is not None:
            self.is_incremental_review = False
        else:
            return ChatAgentResponse(
                msgs=[],
                terminated=True,
                info={"error": "Either pr_number or commit_sha must be provided."}
            )
        
        try:
            changed_files, diff_summary, prompt_template = self.get_review_context(
                input_message=input_message,
                pr_number=pr_number,
                commit_sha=commit_sha
            )
        except Exception as e:
            logger.error(f"[CodeReviewAgent] Failed to get review context: {e}")
            return ChatAgentResponse(msgs=[], terminated=True, info={"error": str(e)})

        review_request = input_message if isinstance(input_message, str) else input_message.content

        system_prompt_template_str = prompt_template.safe_substitute(
            pr_diff_summary=diff_summary,
            review_request=review_request,
            files_diff_detail_file_diffs="${files_diff_detail_file_diffs}"  # Placeholder for file diffs
        )

        final_prompt_template = Template(system_prompt_template_str)

        # Split changed files into chunks to stay within token limits
        diff_chunks = self.chunk_file_diffs_by_token(
            template=final_prompt_template,
            file_diffs=changed_files,
        )

        for i, (chunk, filenames) in enumerate(diff_chunks):
            print(f"--- Chunk #{i+1} ---")
            print("Files included:", filenames)
            print("Message preview:", chunk[:200], "...\n")

        all_msgs = []
        for idx, (chunk, filenames)  in enumerate(diff_chunks):
            user_msg = BaseMessage.make_user_message(
                role_name="User",
                content=chunk
            )

            try:
                result = super().step(user_msg)
                response_content = result.msgs[0].content if result.msgs else "[Empty response from agent]"
            except Exception as e:
                logger.error(f"[CodeReviewAgent] Error during step for chunk {idx}: {e}")
                response_content = f"[Error during review of chunk {idx}: {e}]"

            all_msgs.append(BaseMessage.make_assistant_message(
                role_name="CodeReview_Agent",
                content=response_content
            ))

        return ChatAgentResponse(msgs=all_msgs, terminated=False, info={"num_chunks": len(all_msgs)})

    def reset(self):
        super().reset()
        self.is_incremental_review = False






