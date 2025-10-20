<a id="camel.toolkits.gitee_toolkit"></a>

<a id="camel.toolkits.gitee_toolkit.GiteeToolkit"></a>

## GiteeToolkit

```python
class GiteeToolkit(GitBaseToolkit):
```

A class representing a toolkit for interacting with Gitee repositories.

This class provides methods for retrieving repository information, files, issues, pull requests,
and performing various Gitee operations. It supports multiple Gitee instances and provides rate limit handling.

**Parameters:**

- **access_token** (str, optional): The access token to authenticate with Gitee. If not provided, it will be obtained from environment variables.
- **instance_name** (str, optional): The name of the Gitee instance to use. Defaults to "default".
- **namespace** (str, optional): Default namespace to use for operations.
- **timeout** (float, optional): The timeout for API requests.

<a id="camel.toolkits.gitee_toolkit.GiteeToolkit.__init__"></a>

### __init__

```python
def __init__(
    self,
    access_token: Optional[str] = None,
    instance_name: str = "default",
    namespace: Optional[str] = None,
    timeout: Optional[float] = None
):
```

Initializes a new instance of the GiteeToolkit class.

**Parameters:**

- **access_token** (str, optional): The access token to authenticate with Gitee.
- **instance_name** (str, optional): The name of the Gitee instance to use.
- **namespace** (str, optional): Default namespace to use for operations.
- **timeout** (float, optional): The timeout for API requests.

<a id="camel.toolkits.gitee_toolkit.GiteeToolkit.gitee_get_all_file_paths"></a>

### gitee_get_all_file_paths

```python
def gitee_get_all_file_paths(self, repo_name: str, path: str = ''):
```

Recursively retrieves all file paths in a Gitee repository.

**Parameters:**

- **repo_name** (str): The repository name in format "owner/repo".
- **path** (str): The directory path to start from. Defaults to root.

**Returns:**

  List[str]: A list of file paths within the repository.

<a id="camel.toolkits.gitee_toolkit.GiteeToolkit.gitee_retrieve_file_content"></a>

### gitee_retrieve_file_content

```python
def gitee_retrieve_file_content(self, repo_name: str, file_path: str):
```

Retrieves the content of a file from a Gitee repository.

**Parameters:**

- **repo_name** (str): The repository name in format "owner/repo".
- **file_path** (str): The path of the file to retrieve.

**Returns:**

  str: The content of the file.

<a id="camel.toolkits.gitee_toolkit.GiteeToolkit.gitee_get_issue_list"></a>

### gitee_get_issue_list

```python
def gitee_get_issue_list(
    self,
    repo_name: str,
    state: Literal['open', 'closed', 'all'] = 'all'
):
```

Retrieves issues from a Gitee repository.

**Parameters:**

- **repo_name** (str): The repository name in format "owner/repo".
- **state** (Literal["open", "closed", "all"]): The state of issues to retrieve.

**Returns:**

  List[Dict[str, Any]]: A list of issue objects.

<a id="camel.toolkits.gitee_toolkit.GiteeToolkit.gitee_get_issue_content"></a>

### gitee_get_issue_content

```python
def gitee_get_issue_content(self, repo_name: str, issue_number: int):
```

Retrieves the content of a specific issue.

**Parameters:**

- **repo_name** (str): The repository name in format "owner/repo".
- **issue_number** (int): The issue number.

**Returns:**

  Dict[str, Any]: The issue details.

<a id="camel.toolkits.gitee_toolkit.GiteeToolkit.gitee_get_pull_request_list"></a>

### gitee_get_pull_request_list

```python
def gitee_get_pull_request_list(
    self,
    repo_name: str,
    state: Literal['open', 'closed', 'merged', 'all'] = 'all'
):
```

Retrieves pull requests from a Gitee repository.

**Parameters:**

- **repo_name** (str): The repository name in format "owner/repo".
- **state** (Literal["open", "closed", "merged", "all"]): The state of pull requests to retrieve.

**Returns:**

  List[Dict[str, Any]]: A list of pull request objects.

<a id="camel.toolkits.gitee_toolkit.GiteeToolkit.gitee_create_pull_request"></a>

### gitee_create_pull_request

```python
def gitee_create_pull_request(
    self,
    repo_name: str,
    head: str,
    base: str,
    title: str,
    body: str = ""
):
```

Creates a new pull request in a Gitee repository.

**Parameters:**

- **repo_name** (str): The repository name in format "owner/repo".
- **head** (str): The source branch name.
- **base** (str): The target branch name.
- **title** (str): The title of the pull request.
- **body** (str, optional): The description of the pull request.

**Returns:**

  Dict[str, Any]: The created pull request details.

<a id="camel.toolkits.gitee_toolkit.GiteeToolkit.get_tools"></a>

### get_tools

```python
def get_tools(self):
```

**Returns:**

  List[FunctionTool]: A list of FunctionTool objects representing the functions in the toolkit.