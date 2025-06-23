---
title: "Messages"
icon: messages
---

<Card title="What is BaseMessage?" icon="message">
  The <code>BaseMessage</code> class is the backbone for all message objects in
  the CAMEL chat system. It offers a consistent structure for agent
  communication and easy conversion between message types.
</Card>

Explore and run every code sample directly in this <a href="https://colab.research.google.com/drive/1qyi4bnAbnYink-FKaAlJG9OipyEWXEsT?usp=sharing" target="_blank"><b>Colab notebook</b></a>.

---

## Get Started

<Card title="Creating a `BaseMessage`" icon="terminal">
  To create a <code>BaseMessage</code> instance, supply these arguments:
  <ul>
    <li><b>role_name</b>: Name of the user or assistant</li>
    <li><b>role_type</b>: <code>RoleType.ASSISTANT</code> or <code>RoleType.USER</code></li>
    <li><b>content</b>: The actual message text</li>
    <li><b>meta_dict</b> (optional): Additional metadata</li>
    <li><b>video_bytes</b> (optional): Attach video bytes</li>
    <li><b>image_list</b> (optional): List of PIL Image objects</li>
    <li><b>image_detail</b> (optional): Level of image detail (default: "auto")</li>
    <li><b>video_detail</b> (optional): Level of video detail (default: "low")</li>
  </ul>
  <b>Example:</b>
  ```python
  from camel.messages import BaseMessage
  from camel.types import RoleType

message = BaseMessage(
role_name="test_user",
role_type=RoleType.USER,
content="test content"
)

````
</Card>

<Card title="Convenient Constructors" icon="user">
Easily create messages for user or assistant agents:
```python
user_message = BaseMessage.make_user_message(
    role_name="user_name",
    content="test content for user",
)

assistant_message = BaseMessage.make_assistant_message(
    role_name="assistant_name",
    content="test content for assistant",
)
````

</Card>

---

## Methods in the `BaseMessage` Class

<Card title="Flexible Message Manipulation" icon="shuffle">
  The <code>BaseMessage</code> class lets you:
  <ul>
    <li>
      Create a new instance with updated content:
      <br />
      <code>new_message = message.create_new_instance("new test content")</code>
    </li>
    <li>
      Convert to OpenAI message formats:
      <br />
      <code>
        openai_message =
        message.to_openai_message(role_at_backend=OpenAIBackendRole.USER)
      </code>
      <br />
      <code>openai_system_message = message.to_openai_system_message()</code>
      <br />
      <code>openai_user_message = message.to_openai_user_message()</code>
      <br />
      <code>
        openai_assistant_message = message.to_openai_assistant_message()
      </code>
    </li>
    <li>
      Convert to a Python dictionary:
      <br />
      <code>message_dict = message.to_dict()</code>
    </li>
  </ul>
  <Tip>
    These methods allow you to transform a <code>BaseMessage</code> into the
    right format for different LLM APIs and agent flows.
  </Tip>
</Card>

---

## Using `BaseMessage` with `ChatAgent`

<Card title="Rich Message Example" icon="image">
  <b>You can send multimodal messages (including images) to your agents:</b>
</Card>

```python
from io import BytesIO
import requests
from PIL import Image

from camel.agents import ChatAgent
from camel.messages import BaseMessage

# Download an image
url = "https://raw.githubusercontent.com/camel-ai/camel/master/misc/logo_light.png"
img = Image.open(BytesIO(requests.get(url).content))

# Build system and user messages
sys_msg = BaseMessage.make_assistant_message(
    role_name="Assistant",
    content="You are a helpful assistant.",
)

user_msg = BaseMessage.make_user_message(
    role_name="User", content="what's in the image?", image_list=[img]
)

# Create agent and send message
camel_agent = ChatAgent(system_message=sys_msg)
response = camel_agent.step(user_msg)
print(response.msgs[0].content)
```

<Note type="success">
  The image features a logo for "CAMEL-AI." It includes a stylized purple camel
  graphic alongside the text "CAMEL-AI," which is also in purple. The design
  appears modern and is likely related to artificial intelligence.
</Note>

---

## Conclusion

<Card title="Summary" icon="star">
  The <code>BaseMessage</code> class is essential for structured, clear, and
  flexible communication in the CAMEL-AI ecosystem—making it simple to create,
  convert, and handle messages across any workflow.
</Card>

For further details, check out the <a href="https://docs.camel-ai.org/key_modules/messages.html" target="_blank">key modules documentation</a>.
