<a id="camel.toolkits.gitlab_toolkit"></a>

<a id="camel.toolkits.gitlab_toolkit.GitLabToolkit"></a>

## GitLabToolkit

```python
class GitLabToolkit(GitBaseToolkit):
```

A class representing a toolkit for interacting with GitLab repositories.

This class provides methods for retrieving project information, files, issues, merge requests,
and performing various GitLab operations. It supports both GitLab.com and self-hosted GitLab instances.

**Parameters:**

- **access_token** (str, optional): The access token to authenticate with GitLab. If not provided, it will be obtained from environment variables.
- **instance_url** (str, optional): The URL of the GitLab instance. Defaults to https://gitlab.com.
- **namespace** (str, optional): Default namespace to use for operations.
- **timeout** (float, optional): The timeout for API requests.

<a id="camel.toolkits.gitlab_toolkit.GitLabToolkit.__init__"></a>

### __init__

```python
def __init__(
    self,
    access_token: Optional[str] = None,
    instance_url: str = "https://gitlab.com",
    namespace: Optional[str] = None,
    timeout: Optional[float] = None
):
```

Initializes a new instance of the GitLabToolkit class.

**Parameters:**

- **access_token** (str, optional): The access token to authenticate with GitLab.
- **instance_url** (str, optional): The URL of the GitLab instance. Defaults to https://gitlab.com.
- **namespace** (str, optional): Default namespace to use for operations.
- **timeout** (float, optional): The timeout for API requests.

<a id="camel.toolkits.gitlab_toolkit.GitLabToolkit.gitlab_get_all_file_paths"></a>

### gitlab_get_all_file_paths

```python
def gitlab_get_all_file_paths(self, project_id: ProjectIdentifier, path: str = ''):
```

Recursively retrieves all file paths in a GitLab project.

**Parameters:**

- **project_id** (Union[int, str]): The project ID or path.
- **path** (str): The directory path to start from. Defaults to root.

**Returns:**

  List[str]: A list of file paths within the project.

<a id="camel.toolkits.gitlab_toolkit.GitLabToolkit.gitlab_retrieve_file_content"></a>

### gitlab_retrieve_file_content

```python
def gitlab_retrieve_file_content(self, project_id: ProjectIdentifier, file_path: str):
```

Retrieves the content of a file from a GitLab project.

**Parameters:**

- **project_id** (Union[int, str]): The project ID or path.
- **file_path** (str): The path of the file to retrieve.

**Returns:**

  str: The content of the file.

<a id="camel.toolkits.gitlab_toolkit.GitLabToolkit.gitlab_get_issue_list"></a>

### gitlab_get_issue_list

```python
def gitlab_get_issue_list(
    self,
    project_id: Optional[ProjectIdentifier] = None,
    state: Literal['opened', 'closed', 'all'] = 'all'
):
```

Retrieves issues from a GitLab project or namespace.

**Parameters:**

- **project_id** (Union[int, str, None]): The project ID or path. If None, retrieves from namespace.
- **state** (Literal["opened", "closed", "all"]): The state of issues to retrieve.

**Returns:**

  List[Dict[str, Any]]: A list of issue objects.

<a id="camel.toolkits.gitlab_toolkit.GitLabToolkit.gitlab_get_issue_content"></a>

### gitlab_get_issue_content

```python
def gitlab_get_issue_content(self, project_id: ProjectIdentifier, issue_iid: IssueIdentifier):
```

Retrieves the content of a specific issue.

**Parameters:**

- **project_id** (Union[int, str]): The project ID or path.
- **issue_iid** (int): The issue IID.

**Returns:**

  Dict[str, Any]: The issue details.

<a id="camel.toolkits.gitlab_toolkit.GitLabToolkit.gitlab_get_merge_request_list"></a>

### gitlab_get_merge_request_list

```python
def gitlab_get_merge_request_list(
    self,
    project_id: Optional[ProjectIdentifier] = None,
    state: Literal['opened', 'closed', 'merged', 'all'] = 'all'
):
```

Retrieves merge requests from a GitLab project or namespace.

**Parameters:**

- **project_id** (Union[int, str, None]): The project ID or path. If None, retrieves from namespace.
- **state** (Literal["opened", "closed", "merged", "all"]): The state of merge requests to retrieve.

**Returns:**

  List[Dict[str, Any]]: A list of merge request objects.

<a id="camel.toolkits.gitlab_toolkit.GitLabToolkit.gitlab_create_merge_request"></a>

### gitlab_create_merge_request

```python
def gitlab_create_merge_request(
    self,
    project_id: ProjectIdentifier,
    source_branch: str,
    target_branch: str,
    title: str,
    description: str = "",
    assignee_id: Optional[int] = None
):
```

Creates a new merge request in a GitLab project.

**Parameters:**

- **project_id** (Union[int, str]): The project ID or path.
- **source_branch** (str): The source branch name.
- **target_branch** (str): The target branch name.
- **title** (str): The title of the merge request.
- **description** (str, optional): The description of the merge request.
- **assignee_id** (int, optional): The ID of the assignee.

**Returns:**

  Dict[str, Any]: The created merge request details.

<a id="camel.toolkits.gitlab_toolkit.GitLabToolkit.get_tools"></a>

### get_tools

```python
def get_tools(self):
```

**Returns:**

  List[FunctionTool]: A list of FunctionTool objects representing the functions in the toolkit.