<a id="camel.toolkits.terminal_toolkit"></a>

<a id="camel.toolkits.terminal_toolkit.TerminalToolkit"></a>

## TerminalToolkit

```python
class TerminalToolkit(BaseToolkit):
```

A toolkit for terminal operations across multiple operating systems.

This toolkit provides a set of functions for terminal operations such as
searching for files by name or content, executing shell commands, and
managing terminal sessions.

**Parameters:**

- **timeout** (Optional[float]): The timeout for terminal operations.
- **shell_sessions** (Optional[Dict[str, Any]]): A dictionary to store shell session information. If None, an empty dictionary will be used. (default: :obj:`{}`)
- **working_dir** (str): The working directory for operations. If specified, all execution and write operations will be restricted to this directory. Read operations can access paths outside this directory.(default: :obj:`"./workspace"`)
- **need_terminal** (bool): Whether to create a terminal interface. (default: :obj:`True`)
- **use_shell_mode** (bool): Whether to use shell mode for command execution. (default: :obj:`True`)
- **clone_current_env** (bool): Whether to clone the current Python environment.(default: :obj:`False`)
- **safe_mode** (bool): Whether to enable safe mode to restrict operations. (default: :obj:`True`)

**Note:**

Most functions are compatible with Unix-based systems (macOS, Linux).
For Windows compatibility, additional implementation details are
needed.

<a id="camel.toolkits.terminal_toolkit.TerminalToolkit.__init__"></a>

### __init__

```python
def __init__(
    self,
    timeout: Optional[float] = None,
    shell_sessions: Optional[Dict[str, Any]] = None,
    working_dir: str = './workspace',
    need_terminal: bool = True,
    use_shell_mode: bool = True,
    clone_current_env: bool = False,
    safe_mode: bool = True
):
```

<a id="camel.toolkits.terminal_toolkit.TerminalToolkit._setup_file_output"></a>

### _setup_file_output

```python
def _setup_file_output(self):
```

Set up file output to replace GUI, using a fixed file to simulate
terminal.

<a id="camel.toolkits.terminal_toolkit.TerminalToolkit._clone_current_environment"></a>

### _clone_current_environment

```python
def _clone_current_environment(self):
```

Create a new Python virtual environment.

<a id="camel.toolkits.terminal_toolkit.TerminalToolkit._create_terminal"></a>

### _create_terminal

```python
def _create_terminal(self):
```

Create a terminal GUI. If GUI creation fails, fallback
to file output.

<a id="camel.toolkits.terminal_toolkit.TerminalToolkit._update_terminal_output"></a>

### _update_terminal_output

```python
def _update_terminal_output(self, output: str):
```

Update terminal output and send to agent.

**Parameters:**

- **output** (str): The output to be sent to the agent

<a id="camel.toolkits.terminal_toolkit.TerminalToolkit._is_path_within_working_dir"></a>

### _is_path_within_working_dir

```python
def _is_path_within_working_dir(self, path: str):
```

Check if the path is within the working directory.

**Parameters:**

- **path** (str): The path to check

**Returns:**

  bool: Returns True if the path is within the working directory,
otherwise returns False

<a id="camel.toolkits.terminal_toolkit.TerminalToolkit._enforce_working_dir_for_execution"></a>

### _enforce_working_dir_for_execution

```python
def _enforce_working_dir_for_execution(self, path: str):
```

Enforce working directory restrictions, return error message
if execution path is not within the working directory.

**Parameters:**

- **path** (str): The path to be used for executing operations

**Returns:**

  Optional[str]: Returns error message if the path is not within
the working directory, otherwise returns None

<a id="camel.toolkits.terminal_toolkit.TerminalToolkit._copy_external_file_to_workdir"></a>

### _copy_external_file_to_workdir

```python
def _copy_external_file_to_workdir(self, external_file: str):
```

Copy external file to working directory.

**Parameters:**

- **external_file** (str): The path of the external file

**Returns:**

  Optional[str]: New path after copying to the working directory,
returns None on failure

<a id="camel.toolkits.terminal_toolkit.TerminalToolkit.file_find_in_content"></a>

### file_find_in_content

```python
def file_find_in_content(
    self,
    file: str,
    regex: str,
    sudo: bool = False
):
```

Search for text within a file's content using a regular expression.

This function is useful for finding specific patterns or lines of text
within a given file. It uses `grep` on Unix-like systems and `findstr`
on Windows.

**Parameters:**

- **file** (str): The absolute path of the file to search within.
- **regex** (str): The regular expression pattern to match.
- **sudo** (bool, optional): Whether to use sudo privileges for the search. Defaults to False. Note: Using sudo requires the process to have appropriate permissions. (default: :obj:`False`)

**Returns:**

  str: The matching content found in the file. If no matches are
found, an empty string is returned. Returns an error message
if the file does not exist or another error occurs.

<a id="camel.toolkits.terminal_toolkit.TerminalToolkit.file_find_by_name"></a>

### file_find_by_name

```python
def file_find_by_name(self, path: str, glob: str):
```

Find files by name in a specified directory using a glob pattern.

This function recursively searches for files matching a given name or
pattern within a directory. It uses `find` on Unix-like systems and
`dir` on Windows.

**Parameters:**

- **path** (str): The absolute path of the directory to search in.
- **glob** (str): The filename pattern to search for, using glob syntax (e.g., "*.py", "data*").

**Returns:**

  str: A newline-separated string containing the paths of the files
that match the pattern. Returns an error message if the
directory does not exist or another error occurs.

<a id="camel.toolkits.terminal_toolkit.TerminalToolkit._sanitize_command"></a>

### _sanitize_command

```python
def _sanitize_command(self, command: str, exec_dir: str):
```

Check and modify command to ensure safety.

**Parameters:**

- **command** (str): The command to check
- **exec_dir** (str): The directory to execute the command in

**Returns:**

  Tuple: (is safe, modified command or error message)

<a id="camel.toolkits.terminal_toolkit.TerminalToolkit.shell_exec"></a>

### shell_exec

```python
def shell_exec(
    self,
    id: str,
    command: str,
    interactive: bool = False
):
```

Executes a shell command in a specified session.

This function creates and manages shell sessions to execute commands,
simulating a real terminal. It can run commands in both non-interactive
(capturing output) and interactive modes. Each session is identified by
a unique ID. If a session with the given ID does not exist, it will be
created.

**Parameters:**

- **id** (str): A unique identifier for the shell session. This is used to manage multiple concurrent shell processes.
- **command** (str): The shell command to be executed.
- **interactive** (bool, optional): If `True`, the command runs in interactive mode, connecting it to the terminal's standard input. This is useful for commands that require user input, like `ssh`. Defaults to `False`. Interactive mode is only supported on macOS and Linux. (default: :obj:`False`)

**Returns:**

  str: The standard output and standard error from the command. If an
error occurs during execution, a descriptive error message is
returned.

**Note:**

When `interactive` is set to `True`, this function may block if the
command requires input. In safe mode, some commands that are
considered dangerous are restricted.

<a id="camel.toolkits.terminal_toolkit.TerminalToolkit.shell_view"></a>

### shell_view

```python
def shell_view(self, id: str):
```

View the full output history of a specified shell session.

Retrieves the accumulated output (both stdout and stderr) generated by
commands in the specified session since its creation. This is useful
for checking the complete history of a session, especially after a
command has finished execution.

**Parameters:**

- **id** (str): The unique identifier of the shell session to view.

**Returns:**

  str: The complete output history of the shell session. Returns an
error message if the session is not found.

<a id="camel.toolkits.terminal_toolkit.TerminalToolkit.shell_wait"></a>

### shell_wait

```python
def shell_wait(self, id: str, seconds: Optional[int] = None):
```

Wait for a command to finish in a specified shell session.

Blocks execution and waits for the running process in a shell session
to complete. This is useful for ensuring a long-running command has
finished before proceeding.

**Parameters:**

- **id** (str): The unique identifier of the target shell session.
- **seconds** (Optional[int], optional): The maximum time to wait, in seconds. If `None`, it waits indefinitely. (default: :obj:`None`)

**Returns:**

  str: A message indicating that the process has completed, including
the final output. If the process times out, it returns a
timeout message.

<a id="camel.toolkits.terminal_toolkit.TerminalToolkit.shell_write_to_process"></a>

### shell_write_to_process

```python
def shell_write_to_process(
    self,
    id: str,
    input: str,
    press_enter: bool
):
```

Write input to a running process in a specified shell session.

Sends a string of text to the standard input of a running process.
This is useful for interacting with commands that require input. This
function cannot be used with a command that was started in
interactive mode.

**Parameters:**

- **id** (str): The unique identifier of the target shell session.
- **input** (str): The text to write to the process's stdin.
- **press_enter** (bool): If `True`, a newline character (`\n`) is appended to the input, simulating pressing the Enter key.

**Returns:**

  str: A status message indicating whether the input was sent, or an
error message if the operation fails.

<a id="camel.toolkits.terminal_toolkit.TerminalToolkit.shell_kill_process"></a>

### shell_kill_process

```python
def shell_kill_process(self, id: str):
```

Terminate a running process in a specified shell session.

Forcibly stops a command that is currently running in a shell session.
This is useful for ending processes that are stuck, running too long,
or need to be cancelled.

**Parameters:**

- **id** (str): The unique identifier of the shell session containing the process to be terminated.

**Returns:**

  str: A status message indicating that the process has been
terminated, or an error message if the operation fails.

<a id="camel.toolkits.terminal_toolkit.TerminalToolkit.ask_user_for_help"></a>

### ask_user_for_help

```python
def ask_user_for_help(self, id: str):
```

Pause the agent and ask a human for help with a command.

This function should be used when the agent is stuck and requires
manual intervention, such as solving a CAPTCHA or debugging a complex
issue. It pauses the agent's execution and allows a human to take
control of a specified shell session. The human can execute one
command to resolve the issue, and then control is returned to the
agent.

**Parameters:**

- **id** (str): The identifier of the shell session for the human to interact with. If the session does not exist, it will be created.

**Returns:**

  str: A status message indicating that the human has finished,
including the number of commands executed. If the takeover
times out or fails, an error message is returned.

<a id="camel.toolkits.terminal_toolkit.TerminalToolkit.__del__"></a>

### __del__

```python
def __del__(self):
```

Clean up resources when the object is being destroyed.
Terminates all running processes and closes any open file handles.

<a id="camel.toolkits.terminal_toolkit.TerminalToolkit.get_tools"></a>

### get_tools

```python
def get_tools(self):
```

**Returns:**

  List[FunctionTool]: A list of FunctionTool objects representing the
functions in the toolkit.
