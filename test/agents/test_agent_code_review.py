import sys
import pytest
from unittest.mock import MagicMock, patch
from string import Template

from camel.agents.code_review_agent import CodeReviewAgent, CommitDiffInfo, FileDiff, PRDiffInfo
from camel.models import BaseModelBackend, ModelFactory
from camel.messages import BaseMessage
from camel.responses import ChatAgentResponse
from camel.types import ModelType

# Globally patch the github module to avoid real network requests during tests
mock_github_module = MagicMock()
mock_github_class = MagicMock()
mock_repo = MagicMock()
mock_github_class.return_value.get_repo.return_value = mock_repo
mock_github_module.Github = mock_github_class
sys.modules['github'] = mock_github_module

@pytest.fixture(autouse=True)
def mock_model_factory():
    r"""
    Mock the ModelFactory to return a mocked backend model.
    This avoids loading actual model implementations during tests.
    """
    mock_backend = MagicMock(spec=BaseModelBackend)
    mock_backend.model_type = ModelType.DEFAULT
    mock_backend.token_limit = 4096
    mock_backend.token_counter = MagicMock()
    with patch('camel.models.ModelFactory.create', return_value=mock_backend):
        yield

@pytest.fixture(autouse=True)
def mock_github_client():
    r"""
    Patch the Github client inside CodeReviewAgent to use the mock Github class.
    This prevents real GitHub API calls during tests.
    """
    with patch('camel.agents.code_review_agent.Github', mock_github_class):
        yield

@pytest.fixture
def agent():
    r"""
    Instantiate the CodeReviewAgent with dummy GitHub token and repo info.
    """
    return CodeReviewAgent(
        github_token="fake-token",
        repo_full_name="owner/repo"
    )

def test_get_commit_diff_by_sha(agent):
    r"""
    Test getting commit diff info by commit SHA.
    Mocks GitHub commit and file attributes.
    """
    mock_commit = MagicMock()
    mock_file = MagicMock(
        filename="file.py",
        status="modified",
        patch="patch content",
        additions=1,
        deletions=1,
        changes=2,
        blob_url="https://github.com/org/repo/blob/sha/file.py"
    )
    mock_commit.files = [mock_file]
    mock_commit.commit.message = "commit message"
    
    agent.repo.get_commit = MagicMock(return_value=mock_commit)

    result = agent.get_commit_diff_by_sha("sha123")

    assert isinstance(result, CommitDiffInfo)
    assert result.commit_sha == "sha123"
    assert result.message == "commit message"
    assert len(result.files_diff) == 1

    file_diff = result.files_diff[0]
    assert file_diff.filename == "file.py"
    assert file_diff.status == "modified"
    assert file_diff.patch == "patch content"
  
def test_get_pr_diff_info(agent):
    r"""
    Test retrieving PR diff info including files and commits.
    Mocks GitHub Pull Request, files and commits.
    """
    mock_pr = MagicMock()
    mock_pr.number = 123
    mock_pr.title = "Fix bug"
    mock_pr.body = "This PR fixes a bug"

    mock_file = MagicMock(
        filename="fix.py",
        status="modified",
        patch="@@ -1 +1 @@",
        additions=10,
        deletions=2,
        changes=12,
        blob_url="https://github.com/org/repo/blob/sha/fix.py"
    )
    mock_pr.get_files.return_value = [mock_file]

    mock_commit = MagicMock()
    mock_commit.sha = "abc123"
    mock_pr.get_commits.return_value = [mock_commit]

    agent.repo.get_pull = MagicMock(return_value=mock_pr)

    result = agent.get_pr_diff_info(123)

    assert isinstance(result, PRDiffInfo)
    assert result.pr_number == 123
    assert result.title == "Fix bug"
    assert result.description == "This PR fixes a bug"
    assert len(result.files_diff) == 1
    assert len(result.commit_diffs) == 1

    file_diff = result.files_diff[0]
    assert file_diff.filename == "fix.py"
    assert file_diff.status == "modified"
    assert file_diff.patch == "@@ -1 +1 @@"
    assert file_diff.additions == 10
    assert file_diff.deletions == 2
    assert file_diff.changes == 12
    assert file_diff.blob_url.startswith("https://github.com/")

def test_build_diff_summary_text_pr_mode(agent):
    r"""
    Test building diff summary text in PR review mode.
    """
    agent.is_incremental_review = False  
    pr_diff = PRDiffInfo(
        pr_number=42,
        title="Add feature X",
        description="This PR introduces feature X and related changes.",
        files_diff=[
            FileDiff(
                filename="feature_x.py",
                status="added",
                patch="+print('hello')",
                additions=5,
                deletions=0,
                changes=5,
                blob_url="https://github.com/repo/blob/sha/feature_x.py"
            )
        ],
        commit_diffs=[]
    )

    summary = agent.build_diff_summary_text(pr_diff=pr_diff)

    assert "PR #42" in summary
    assert "Title: Add feature X" in summary
    assert "Description: This PR introduces feature X" in summary
    assert "- `feature_x.py`: added, +5/-0, total: 5" in summary

def test_build_diff_summary_text_commit_mode(agent):
    r"""
    Test building diff summary text in incremental commit review mode.
    """
    agent.is_incremental_review = True  

    commit_diff = CommitDiffInfo(
        commit_sha="abc123",
        message="Refactor function",
        files_diff=[
            FileDiff(
                filename="refactor.py",
                status="modified",
                patch="-old +new",
                additions=8,
                deletions=2,
                changes=10,
                blob_url="https://github.com/repo/blob/sha/refactor.py"
            )
        ]
    )

    summary = agent.build_diff_summary_text(commit_diff=commit_diff)

    assert "Commit SHA: `abc123`" in summary
    assert "Message: Refactor function" in summary
    assert "- `refactor.py`: modified, +8/-2, total: 10" in summary

def test_build_diff_summary_text_value_error(agent):
    r"""
    Test build_diff_summary_text returns error string if both pr_diff and commit_diff provided or none.
    """
    agent.is_incremental_review = False

    result = agent.build_diff_summary_text(
        pr_diff=PRDiffInfo(pr_number=1, title="", description="", files_diff=[], commit_diffs=[]),
        commit_diff=CommitDiffInfo(commit_sha="sha", message="", files_diff=[])
    )
    assert result == "Failed to generate diff summary."

    result = agent.build_diff_summary_text()
    assert result == "Failed to generate diff summary."
    
def test_get_review_context_incremental_mode(agent):
    r"""
    Test get_review_context returns correct data in incremental mode (commit_sha).
    """
    agent.is_incremental_review = True
    agent.incremental_review_prompt_template = Template(template="Dummy template content")
    commit_sha = "abc123"

    mock_commit_diff = CommitDiffInfo(
        commit_sha=commit_sha,
        message="Commit message",
        files_diff=[
            FileDiff(filename="file1.py", status="modified", patch="", additions=1, deletions=0, changes=1, blob_url="")
        ]
    )
    agent.get_commit_diff_by_sha = MagicMock(return_value=mock_commit_diff)
    agent.build_diff_summary_text = MagicMock(return_value="diff summary text")

    changed_files, diff_summary, prompt_template = agent.get_review_context(
        input_message="Review this commit",
        pr_number=None,
        commit_sha=commit_sha
    )

    assert changed_files == mock_commit_diff.files_diff
    assert diff_summary == "diff summary text"
    assert prompt_template == agent.incremental_review_prompt_template
    agent.get_commit_diff_by_sha.assert_called_once_with(commit_sha)
    agent.build_diff_summary_text.assert_called_once_with(commit_diff=mock_commit_diff)

def test_get_review_context_normal_mode(agent):
    r"""
    Test get_review_context returns correct data in normal PR mode.
    """
    agent.is_incremental_review = False
    agent.standard_review_prompt_template = Template(template="Dummy template content")  
    pr_number = 123

    mock_pr_diff = PRDiffInfo(
        pr_number=pr_number,
        title="Title",
        description="Description",
        files_diff=[
            FileDiff(filename="file2.py", status="added", patch="", additions=5, deletions=0, changes=5, blob_url="")
        ],
        commit_diffs=[]
    )
    agent.get_pr_diff_info = MagicMock(return_value=mock_pr_diff)
    agent.build_diff_summary_text = MagicMock(return_value="diff summary text")

    changed_files, diff_summary, prompt_template = agent.get_review_context(
        input_message="Review this PR",
        pr_number=pr_number,
        commit_sha=None
    )

    assert changed_files == mock_pr_diff.files_diff
    assert diff_summary == "diff summary text"
    assert prompt_template == agent.standard_review_prompt_template
    agent.get_pr_diff_info.assert_called_once_with(pr_number)
    agent.build_diff_summary_text.assert_called_once_with(pr_diff=mock_pr_diff)

def test_get_review_context_missing_params(agent):
    r"""
    Test get_review_context raises ValueError when required parameters are missing.
    """
    agent.is_incremental_review = True
    with pytest.raises(ValueError, match="Parameter 'commit_sha' is required"):
        agent.get_review_context(input_message="msg", pr_number=None, commit_sha=None)

    agent.is_incremental_review = False
    with pytest.raises(ValueError, match="Parameter 'pr_number' is required"):
        agent.get_review_context(input_message="msg", pr_number=None, commit_sha=None)

def test_chunk_file_diffs_by_token_basic(agent):
    r"""
    Test chunking file diffs when total token count is within limit.
    Should return a single chunk containing all files.
    """
    template = Template("Header\n$files_diff_detail_file_diffs\nFooter")
    agent.max_context_tokens = 50

    def fake_count_tokens(text):
        return len(text) // 5  # Simple token count estimate

    agent.count_tokens = MagicMock(side_effect=fake_count_tokens)

    file_diffs = [
        FileDiff(filename="file1.py", status="modified", patch="patch1\nline2\n", additions=3, deletions=1, changes=4, blob_url=""),
        FileDiff(filename="file2.py", status="added", patch="patch2\nline2\n", additions=5, deletions=0, changes=5, blob_url=""),
    ]

    results = agent.chunk_file_diffs_by_token(template, file_diffs)

    assert len(results) == 1
    combined_text, filenames = results[0]
    assert "file1.py" in combined_text and "file2.py" in combined_text
    assert filenames == ["file1.py", "file2.py"]

def test_chunk_file_diffs_by_token_single_file_too_large(agent):
    r"""
    Test chunking when a single file's diff exceeds token limit.
    The file should be split into multiple chunks by lines.
    """
    template = Template("Header\n$files_diff_detail_file_diffs\nFooter")
    agent.max_context_tokens = 20

    def fake_count_tokens(text):
        if text == "Header\n\nFooter":
            return 5
        return len(text)

    agent.count_tokens = MagicMock(side_effect=fake_count_tokens)

    long_patch = "line1\nline2\nline3\nline4\nline5\n"
    file_diffs = [
        FileDiff(filename="bigfile.py", status="modified", patch=long_patch, additions=5, deletions=0, changes=5, blob_url="")
    ]

    results = agent.chunk_file_diffs_by_token(template, file_diffs)

    assert len(results) > 1
    for _, files in results:
        assert files == ["bigfile.py"]

def test_step_normal_mode(agent):
    r"""
    Test step method in NORMAL mode with PR number.
    Mocks internal methods to simulate the full step process.
    """
    agent.is_incremental_review = False
    input_message = "Please review this PR."

    mock_changed_files = [MagicMock(filename="file1.py")]
    mock_diff_summary = "PR #123 summary"
    mock_template = MagicMock()
    mock_template.safe_substitute.return_value = "Prompt with ${files_diff_detail_file_diffs}"

    agent.get_review_context = MagicMock(return_value=(
        mock_changed_files,
        mock_diff_summary,
        mock_template
    ))

    agent.chunk_file_diffs_by_token = MagicMock(return_value=[
        ("chunk text with diffs", ["file1.py"])
    ])

    with patch.object(agent.__class__.__bases__[0], "step", return_value=ChatAgentResponse(
        msgs=[BaseMessage.make_assistant_message(role_name="CodeReview_Agent", content="Review result")],
        terminated=False,
        info={}
    )):
        result = agent.step(input_message, pr_number=123)

    assert isinstance(result, ChatAgentResponse)
    assert not result.terminated
    assert len(result.msgs) == 1
    assert "Review result" in result.msgs[0].content
    agent.get_review_context.assert_called_once()
    agent.chunk_file_diffs_by_token.assert_called_once()

def test_step_incremental_mode(agent):
    r"""
    Test step method in INCREMENTAL mode with commit SHA.
    Mocks internal methods to simulate the full step process.
    """
    agent.is_incremental_review = True
    input_message = "Please review this commit."

    mock_changed_files = [MagicMock(filename="file2.py")]
    mock_diff_summary = "Commit abc123 summary"
    mock_template = MagicMock()
    mock_template.safe_substitute.return_value = "Prompt with ${files_diff_detail_file_diffs}"

    agent.get_review_context = MagicMock(return_value=(
        mock_changed_files,
        mock_diff_summary,
        mock_template
    ))

    agent.chunk_file_diffs_by_token = MagicMock(return_value=[
        ("chunk text with diffs", ["file2.py"])
    ])

    with patch.object(agent.__class__.__bases__[0], "step", return_value=ChatAgentResponse(
        msgs=[BaseMessage.make_assistant_message(role_name="CodeReview_Agent", content="Commit review result")],
        terminated=False,
        info={}
    )):
        result = agent.step(input_message, commit_sha="abc123")

    assert isinstance(result, ChatAgentResponse)
    assert not result.terminated
    assert len(result.msgs) == 1
    assert "Commit review result" in result.msgs[0].content
    agent.get_review_context.assert_called_once()
    agent.chunk_file_diffs_by_token.assert_called_once()

def test_step_missing_parameters(agent):
    r"""
    Test step method when neither pr_number nor commit_sha is provided.
    Should return a terminated ChatAgentResponse with an error message.
    """
    input_message = "Missing parameters test"

    result = agent.step(input_message)

    assert isinstance(result, ChatAgentResponse)
    assert result.terminated
    assert "error" in result.info
    assert "Either pr_number or commit_sha must be provided." in result.info["error"]

"""
=========================================================== test session starts ============================================================
platform win32 -- Python 3.12.0, pytest-8.4.1, pluggy-1.6.0 -- D:\Anaconda3\envs\Camel-dev\python.exe
cachedir: .pytest_cache
rootdir: E:\EnjoyAI\camel
configfile: pyproject.toml
plugins: anyio-4.9.0
collected 13 items                                                                                                                          

test_agent_code_review.py::test_get_commit_diff_by_sha PASSED                                                                         [  7%] 
test_agent_code_review.py::test_get_pr_diff_info PASSED                                                                               [ 15%] 
test_agent_code_review.py::test_build_diff_summary_text_pr_mode PASSED                                                                [ 23%]
test_agent_code_review.py::test_build_diff_summary_text_commit_mode PASSED                                                            [ 30%] 
test_agent_code_review.py::test_build_diff_summary_text_value_error PASSED                                                            [ 38%] 
test_agent_code_review.py::test_get_review_context_incremental_mode PASSED                                                            [ 46%] 
test_agent_code_review.py::test_get_review_context_normal_mode PASSED                                                                 [ 53%]
test_agent_code_review.py::test_get_review_context_missing_params PASSED                                                              [ 61%] 
test_agent_code_review.py::test_chunk_file_diffs_by_token_basic PASSED                                                                [ 69%] 
test_agent_code_review.py::test_chunk_file_diffs_by_token_single_file_too_large PASSED                                                [ 76%] 
test_agent_code_review.py::test_step_normal_mode PASSED                                                                               [ 84%]
test_agent_code_review.py::test_step_incremental_mode PASSED                                                                          [ 92%] 
test_agent_code_review.py::test_step_missing_parameters PASSED                                                                        [100%] 

====================================================== 13 passed, 4 warnings in 1.62s ====================================================== 

"""