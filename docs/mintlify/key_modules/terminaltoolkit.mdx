---
title: "Terminal Toolkit"
icon: "terminal"
---

<Note type="info" title="What is the Terminal Toolkit?">
  The <b>Terminal Toolkit</b> provides a secure and powerful way for CAMEL agents to interact with a terminal. It allows agents to execute shell commands, manage files, and even ask for human help, all within a controlled, sandboxed environment.
</Note>

<CardGroup cols={2}>
  <Card title="Secure Sandboxed Execution" icon="lock">
    All file-writing and execution commands are restricted to a designated `working_directory` to prevent unintended system modifications. Dangerous commands are blocked by default.
  </Card>
  <Card title="Multi-Session Management" icon="window-restore">
    Run multiple, independent terminal sessions concurrently. Each session maintains its own state and history, allowing for complex, parallel workflows.
  </Card>
  <Card title="Virtual Environment Management" icon="binary">
    Automatically create and manage isolated Python virtual environments, ensuring that package installations and script executions don't conflict with your system setup.
  </Card>
  <Card title="Human-in-the-Loop" icon="hand">
    When an agent gets stuck, it can pause its execution and request human assistance. A human can then take over the terminal session to resolve the issue before handing control back.
  </Card>
</CardGroup>

## Initialization

To get started, initialize the `TerminalToolkit`. You can configure its behavior, such as the working directory and environment settings.

<Tabs>
<Tab title="Default">
```python
from camel.toolkits import TerminalToolkit

# Initialize with default settings.
# Safe mode is ON and working_directory is './workspace'
terminal_toolkit = TerminalToolkit()
```
</Tab>
<Tab title="Custom Workspace">
```python
from camel.toolkits import TerminalToolkit

# Specify a custom sandboxed working directory
terminal_toolkit = TerminalToolkit(
    working_directory="./my_safe_workspace"
)
```
</Tab>
<Tab title="Cloned Environment">
```python
from camel.toolkits import TerminalToolkit

# Clone the current python environment into the workspace
# for the agent to use without affecting the original.
terminal_toolkit = TerminalToolkit(clone_current_env=True)
```
</Tab>
</Tabs>

## Usage Examples

### Executing Commands
The `shell_exec` function is the primary way to execute commands. Each command is run within a session, identified by a unique `id`.

**How it works**
- `block=True` (default): waits for completion and returns combined stdout/stderr.
- `block=False`: starts a background session for interactive/long-running tasks.
- The `id` is how you later view output or terminate the session.

<Tabs>
<Tab title="Listing Files">
```python
# Execute the 'ls -l' command in 'session_1'
output = terminal_toolkit.shell_exec(id='session_1', command='ls -l')
print(output)
```
</Tab>
<Tab title="Running a Python Script">
```python
# First, create a python script inside the workspace
write_script_cmd = """
echo 'print("Hello from a sandboxed CAMEL environment!")' > hello.py
"""
terminal_toolkit.shell_exec(id='session_1', command=write_script_cmd)

# Now, execute the script
output = terminal_toolkit.shell_exec(id='session_1', command='python hello.py')
print(output)
```
</Tab>
</Tabs>

### Interacting with Processes
You can manage long-running or interactive processes.

**Tip**: `shell_view` returns only *new* output since the last call. Call it
periodically to stream logs.

<Tabs>
<Tab title="Writing to a Process">
You can write to a process's standard input using `shell_write_to_process`. Start the process in non-blocking mode, then send input and read output.
```python
# Start a python REPL in a new session
terminal_toolkit.shell_exec(id='interactive_session', command='python', block=False)

# Write code to the python process
terminal_toolkit.shell_write_to_process(
    id='interactive_session',
    command='print("Hello, interactive world!")'
)

# View the output
output = terminal_toolkit.shell_view(id='interactive_session')
print(output)
```
</Tab>
<Tab title="Killing a Process">
Forcibly terminate a running process using `shell_kill_process`.
```python
# Start a long-running process
terminal_toolkit.shell_exec(id='long_process', command='sleep 100', block=False)

# Kill the process before it finishes
result = terminal_toolkit.shell_kill_process(id='long_process')
print(result)
```
</Tab>
</Tabs>

### Advanced Usage

#### Non-blocking Sessions and Timeouts
Blocking commands that exceed `timeout` are converted into background sessions. You can then view output or terminate them.

This is useful for long tasks where you still want a quick response, but
need to keep the process alive in the background.

```python
# If this exceeds timeout, it becomes a background session automatically
output = terminal_toolkit.shell_exec(
    id='long_task',
    command='python long_running_job.py',
    block=True,
    timeout=5,
)
print(output)

# Later, check output or terminate
print(terminal_toolkit.shell_view(id='long_task'))
print(terminal_toolkit.shell_kill_process(id='long_task'))
```

#### Safe Mode Allowlist
When `safe_mode=True`, you can restrict execution to an explicit allowlist.

This is helpful for production deployments where only specific commands
should be allowed.

```python
terminal_toolkit = TerminalToolkit(
    safe_mode=True,
    allowed_commands=["ls", "cat", "python", "pip", "uv"]
)
```

#### Docker Backend
Run commands inside a pre-existing Docker container for stronger isolation.

The container must already exist and be running.

```python
terminal_toolkit = TerminalToolkit(
    use_docker_backend=True,
    docker_container_name="camel-runtime",
    working_directory="/workspace",
)
```

#### Environment and Dependencies
Clone the current environment or preinstall dependencies into the sandboxed workspace.

Use this to ensure tools like `python`, `pip`, or `uv` are available
inside the sandboxed workspace.

```python
terminal_toolkit = TerminalToolkit(
    working_directory="./workspace",
    clone_current_env=True,
    install_dependencies=["python-pptx", "pandas"],
)
```

#### Write Files Directly
Use `shell_write_content_to_file` to write large files without shell escaping issues.

Relative paths are resolved under `working_directory`. In safe mode, the
path must stay inside that directory.

```python
content = "line1\nline2\nline3\n"
result = terminal_toolkit.shell_write_content_to_file(
    content=content,
    file_path="notes/demo.txt",
)
print(result)
```

### Safe Mode
When `safe_mode` is enabled (default), the toolkit blocks commands that could be harmful to your system.

<Card title="Example of a Blocked Command" icon="shield-halved">
```python
# This command attempts to delete a file outside the workspace.
# The toolkit will block it and return an error message.
output = terminal_toolkit.shell_exec(id='session_1', command='rm /etc/hosts')

print(output)
# Expected Output:
# Command rejected: Safety restriction: Cannot delete files outside of working directory ...
```
</Card>


### Human-in-the-Loop
When an agent gets stuck, it can use `shell_ask_user_for_help` to request human intervention.

This call blocks and waits for a human response in the console, then returns
the user's input or the resulting command output.

<Card title="Asking for Human Help" icon="hand">
```python
# The agent is stuck, so it asks for help in 'session_1'
help_result = terminal_toolkit.shell_ask_user_for_help(
    id='session_1',
    prompt="The tool is asking for a filename. Please type 'config.json'.",
)

# The script will now pause and wait for the user to type a response
# in the console. It will then resume with the user's input.
print(help_result)
```
</Card>

## References
- `camel/toolkits/terminal_toolkit/terminal_toolkit.py`
- `examples/toolkits/terminal_toolkit.py`
- `examples/runtimes/shared_runtime_multi_toolkit.py`
