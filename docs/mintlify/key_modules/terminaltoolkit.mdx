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

<Tabs>
<Tab title="Writing to a Process">
You can write to a process's standard input using `shell_write_to_process`. This is useful for interactive command-line tools.
```python
# Start a python REPL in a new session
terminal_toolkit.shell_exec(id='interactive_session', command='python')

# Write code to the python process
terminal_toolkit.shell_write_to_process(
    id='interactive_session',
    input='print("Hello, interactive world!")',
    press_enter=True
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
terminal_toolkit.shell_exec(id='long_process', command='sleep 100')

# Kill the process before it finishes
result = terminal_toolkit.shell_kill_process(id='long_process')
print(result)
```
</Tab>
</Tabs>


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
When an agent gets stuck, it can use `ask_user_for_help` to request human intervention.

<Card title="Asking for Human Help" icon="hand">
```python
# The agent is stuck, so it asks for help in 'session_1'
help_result = terminal_toolkit.ask_user_for_help(id='session_1')

# The script will now pause and wait for the user to type commands
# in the console. After the user types '/exit', the script will resume.
print(help_result)
```
</Card> 