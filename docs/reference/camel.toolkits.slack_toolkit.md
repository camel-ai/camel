<a id="camel.toolkits.slack_toolkit"></a>

<a id="camel.toolkits.slack_toolkit.SlackToolkit"></a>

## SlackToolkit

```python
class SlackToolkit(BaseToolkit):
```

A class representing a toolkit for Slack operations.

This class provides methods for Slack operations such as creating a new
channel, joining an existing channel, leaving a channel.

<a id="camel.toolkits.slack_toolkit.SlackToolkit.__init__"></a>

### __init__

```python
def __init__(self, timeout: Optional[float] = None):
```

Initializes a new instance of the SlackToolkit class.

**Parameters:**

- **timeout** (Optional[float]): The timeout value for API requests in seconds. If None, no timeout is applied. (default: :obj:`None`)

<a id="camel.toolkits.slack_toolkit.SlackToolkit._login_slack"></a>

### _login_slack

```python
def _login_slack(
    self,
    slack_token: Optional[str] = None,
    ssl: Optional[SSLContext] = None
):
```

Authenticate using the Slack API.

**Parameters:**

- **slack_token** (str, optional): The Slack API token. If not provided, it attempts to retrieve the token from the environment variable SLACK_BOT_TOKEN or SLACK_USER_TOKEN.
- **ssl** (SSLContext, optional): SSL context for secure connections. Defaults to `None`.

**Returns:**

  WebClient: A WebClient object for interacting with Slack API.

<a id="camel.toolkits.slack_toolkit.SlackToolkit.create_slack_channel"></a>

### create_slack_channel

```python
def create_slack_channel(self, name: str, is_private: Optional[bool] = True):
```

Creates a new slack channel, either public or private.

**Parameters:**

- **name** (str): Name of the public or private channel to create.
- **is_private** (bool, optional): Whether to create a private channel instead of a public one. Defaults to `True`.

**Returns:**

  str: JSON string containing information about Slack
channel created.

<a id="camel.toolkits.slack_toolkit.SlackToolkit.join_slack_channel"></a>

### join_slack_channel

```python
def join_slack_channel(self, channel_id: str):
```

Joins an existing Slack channel.

**Parameters:**

- **channel_id** (str): The ID of the Slack channel to join.

**Returns:**

  str: A confirmation message indicating whether join successfully
or an error message.

<a id="camel.toolkits.slack_toolkit.SlackToolkit.leave_slack_channel"></a>

### leave_slack_channel

```python
def leave_slack_channel(self, channel_id: str):
```

Leaves an existing Slack channel.

**Parameters:**

- **channel_id** (str): The ID of the Slack channel to leave.

**Returns:**

  str: A confirmation message indicating whether leave successfully
or an error message.

<a id="camel.toolkits.slack_toolkit.SlackToolkit.get_slack_channel_information"></a>

### get_slack_channel_information

```python
def get_slack_channel_information(self):
```

**Returns:**

  str: JSON string containing information about Slack channels.

<a id="camel.toolkits.slack_toolkit.SlackToolkit.get_slack_channel_message"></a>

### get_slack_channel_message

```python
def get_slack_channel_message(self, channel_id: str):
```

Retrieve messages from a Slack channel.

**Parameters:**

- **channel_id** (str): The ID of the Slack channel to retrieve messages from.

**Returns:**

  str: JSON string containing filtered message data.

<a id="camel.toolkits.slack_toolkit.SlackToolkit.send_slack_message"></a>

### send_slack_message

```python
def send_slack_message(
    self,
    message: str,
    channel_id: str,
    file_path: Optional[str] = None,
    user: Optional[str] = None
):
```

Send a message to a Slack channel.

**Parameters:**

- **message** (str): The message to send.
- **channel_id** (str): The ID of the Slack channel to send message.
- **file_path** (Optional[str]): The path of the file to send. Defaults to `None`.
- **user** (Optional[str]): The user ID of the recipient. Defaults to `None`.

**Returns:**

  str: A confirmation message indicating whether the message was sent
successfully or an error message.

<a id="camel.toolkits.slack_toolkit.SlackToolkit.delete_slack_message"></a>

### delete_slack_message

```python
def delete_slack_message(self, time_stamp: str, channel_id: str):
```

Delete a message to a Slack channel.

**Parameters:**

- **time_stamp** (str): Timestamp of the message to be deleted.
- **channel_id** (str): The ID of the Slack channel to delete message.

**Returns:**

  str: A confirmation message indicating whether the message
was delete successfully or an error message.

<a id="camel.toolkits.slack_toolkit.SlackToolkit.get_tools"></a>

### get_tools

```python
def get_tools(self):
```

**Returns:**

  List[FunctionTool]: A list of FunctionTool objects
representing the functions in the toolkit.
