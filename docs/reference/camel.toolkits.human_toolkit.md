<a id="camel.toolkits.human_toolkit"></a>

<a id="camel.toolkits.human_toolkit.HumanToolkit"></a>

## HumanToolkit

```python
class HumanToolkit(BaseToolkit):
```

A class representing a toolkit for human interaction.

<a id="camel.toolkits.human_toolkit.HumanToolkit.ask_human_via_console"></a>

### ask_human_via_console

```python
def ask_human_via_console(self, question: str):
```

Use this tool to ask a question to the user when you are stuck,
need clarification, or require a decision to be made. This is a
two-way communication channel that will wait for the user's response.
You should use it to:
- Clarify ambiguous instructions or requirements.
- Request missing information that you cannot find (e.g., login
credentials, file paths).
- Ask for a decision when there are multiple viable options.
- Seek help when you encounter an error you cannot resolve on your own.

**Parameters:**

- **question** (str): The question to ask the user.

**Returns:**

  str: The user's response to the question.

<a id="camel.toolkits.human_toolkit.HumanToolkit.send_message_to_user"></a>

### send_message_to_user

```python
def send_message_to_user(self, message: str):
```

Use this tool to send a message to the user to keep them
informed about your progress, decisions, or actions.
This is a one-way communication channel from you to the user and does
not require a response. You should use it to:
- Announce what you are about to do
(e.g., "I will now search for papers on GUI Agents.")
- Report the result of an action
(e.g., "I have found 15 relevant papers.")
- State a decision
(e.g., "I will now analyze the top 10 papers.")
- Inform the user about your current state if you are performing a
task.

**Parameters:**

- **message** (str): The message to send to the user.

<a id="camel.toolkits.human_toolkit.HumanToolkit.get_tools"></a>

### get_tools

```python
def get_tools(self):
```

**Returns:**

  List[FunctionTool]: A list of FunctionTool objects
representing the functions in the toolkit.
