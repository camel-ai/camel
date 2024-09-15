# 🐫 Agents with RAG

## Philosophical Bits
[![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1sTJ0x_MYRGA76KCg_3I00wj4RL3D2Twp?usp=sharing)


In this notebook, we show the useage of CAMEL Retrieve Module in both customized way and auto way. We will also show how to combine `AutoRetriever` with `ChatAgent`, and further combine `AutoRetriever` with `RolePlaying` by using `Function Calling`.

4 main parts included:
- Customized RAG
- Auto RAG
- Single Agent with Auto RAG
- Role-playing with Auto RAG

## Load Data
Let's first load the CAMEL paper from https://arxiv.org/pdf/2303.17760.pdf. This will be our local example data.
```python
import os
import requests

os.makedirs('local_data', exist_ok=True)

url = "https://arxiv.org/pdf/2303.17760.pdf"
response = requests.get(url)
with open('local_data/camel paper.pdf', 'wb') as file:
     file.write(response.content)
```

## 1. Customized RAG
In this section we will set our customized RAG pipeline, we will take `VectorRetriever` as an example.
Set embedding model, we will use `OpenAIEmbedding` as the embedding model, so we need to set the `OPENAI_API_KEY` in below.
```python
import os

os.environ["OPENAI_API_KEY"] = "Your Key"
```

Import and set the embedding instance:
```python
from camel.embeddings import OpenAIEmbedding

embedding_instance = OpenAIEmbedding()
```

Import and set the vector storage instance:
```python
from camel.storages import MilvusStorage

storage_instance = MilvusStorage(
    vector_dim=embedding_instance.get_output_dim(),
    url_and_api_key=("Your Milvus URI","Your Milvus Token"),
    collection_name="camel_paper",
)
```

Import and set the retriever instance:
```python
from camel.retrievers import VectorRetriever

vector_retriever = VectorRetriever(embedding_model=embedding_instance)
```

We use integrated `Unstructured Module` to splite the content into small chunks, the content will be splited automacitlly with its `chunk_by_title` function, the max character for each chunk is 500 characters, which is a suitable length for `OpenAIEmbedding`. All the text in the chunks will be embed and stored to the vector storage instance, it will take some time, please wait..
```python
vector_retriever.process(
    content="local_data/camel paper.pdf",
    storage=storage_instance,
)
```

Now we can retrieve information from the vector storage by giving a query. By default it will give you back the text content from top 1 chunk with highest Cosine similarity score, and the similarity score should be higher than 0.75 to ensure the retrieved content is relevant to the query. You can also change the `top_k` value and `similarity_threshold` value with your needs.

The returned string list includes:
- similarity score
- content path
- metadata
- text
```python
retrieved_info = vector_retriever.query(
    query="What is CAMEL?", storage=storage_instance, top_k=1
)
print(retrieved_info)
```
```markdown
>>> [{'similarity score': '0.8321741223335266', 'content path': 'local_data/camel paper.pdf', 'metadata': {'filetype': 'application/pdf', 'languages': ['eng'], 'last_modified': '2024-03-24T17:58:24', 'page_number': 45}, 'text': 'CAMEL Data and Code License The intended purpose and licensing of CAMEL is solely for research use. The source code is licensed under Apache 2.0. The datasets are licensed under CC BY NC 4.0, which permits only non-commercial usage. It is advised that any models trained using the dataset should not be utilized for anything other than research purposes.\n\n45'}]
```

Let's try an irrelevant query:
```python
retrieved_info_irrevelant = vector_retriever.query(
    query="Compared with dumpling and rice, which should I take for dinner?",
    storage=storage_instance,
    top_k=1,
)

print(retrieved_info_irrevelant)

```
```markdown
>>> [{'text': 'No suitable information retrieved from local_data/camel paper.pdf                 with similarity_threshold = 0.75.'}]
```

## 2. Auto RAG
In this section we will run the `AutoRetriever` with default settings. It uses `OpenAIEmbedding` as default embedding model and `Milvus` as default vector storage.

What you need to do is:
- Set content input paths, which can be local paths or remote urls
- Set remote url and api key for Milvus
- Give a query

The Auto RAG pipeline would create collections for given content input paths, the collection name will be set automaticlly based on the content input path name, if the collection exists, it will do the retrieve directly.
```python
from camel.retrievers import AutoRetriever
from camel.types import StorageType

auto_retriever = AutoRetriever(
        url_and_api_key=("Your Milvus URI","Your Milvus Token"),
        storage_type=StorageType.MILVUS,
        embedding_model=embedding_instance)

retrieved_info = auto_retriever.run_vector_retriever(
    query="What is CAMEL-AI",
    contents=[
        "local_data/camel paper.pdf",  # example local path
        "https://www.camel-ai.org/",  # example remote url
    ],
    top_k=1,
    return_detailed_info=True,
)

print(retrieved_info)
```
```markdown
>>> Original Query:
{What is CAMEL-AI}
Retrieved Context:
{'similarity score': '0.8369356393814087', 'content path': 'local_data/camel paper.pdf', 'metadata': {'filetype': 'application/pdf', 'languages': ['eng'], 'last_modified': '2024-03-24T17:58:24', 'page_number': 7}, 'text': 'Section 3.2, to simulate assistant-user cooperation. For our analysis, we set our attention on AI Society setting. We also gathered conversational data, named CAMEL AI Society and CAMEL Code datasets and problem-solution pairs data named CAMEL Math and CAMEL Science and analyzed and evaluated their quality. Moreover, we will discuss potential extensions of our framework and highlight both the risks and opportunities that future AI society might present.'}
{'similarity score': '0.8378663659095764', 'content path': 'https://www.camel-ai.org/', 'metadata': {'emphasized_text_contents': ['Mission', 'CAMEL-AI.org', 'is an open-source community dedicated to the study of autonomous and communicative agents. We believe that studying these agents on a large scale offers valuable insights into their behaviors, capabilities, and potential risks. To facilitate research in this field, we provide, implement, and support various types of agents, tasks, prompts, models, datasets, and simulated environments.', 'Join us via', 'Slack', 'Discord', 'or'], 'emphasized_text_tags': ['span', 'span', 'span', 'span', 'span', 'span', 'span'], 'filetype': 'text/html', 'languages': ['eng'], 'link_texts': [None, None, None], 'link_urls': ['#h.3f4tphhd9pn8', 'https://join.slack.com/t/camel-ai/shared_invite/zt-1vy8u9lbo-ZQmhIAyWSEfSwLCl2r2eKA', 'https://discord.gg/CNcNpquyDc'], 'page_number': 1, 'url': 'https://www.camel-ai.org/'}, 'text': 'Mission\n\nCAMEL-AI.org is an open-source community dedicated to the study of autonomous and communicative agents. We believe that studying these agents on a large scale offers valuable insights into their behaviors, capabilities, and potential risks. To facilitate research in this field, we provide, implement, and support various types of agents, tasks, prompts, models, datasets, and simulated environments.\n\nJoin us via\n\nSlack\n\nDiscord\n\nor'}
```

## 3. Single Agent with Auto RAG
In this section we will show how to combine the `AutoRetriever` with one `ChatAgent`.

Let's set an agent function, in this function we can get the response by providing a query to this agent.
```python
from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.types import RoleType
from camel.retrievers import AutoRetriever
from camel.types import StorageType

def single_agent(query: str) ->str :
    # Set agent role
    assistant_sys_msg = BaseMessage(
        role_name="Assistant",
        role_type=RoleType.ASSISTANT,
        meta_dict=None,
        content="You are a helpful assistant to answer question, I will give you the Original Query and Retrieved Context, answer the Original Query based on the Retrieved Context, if you can't answer the question just say I don't know.",
    )

    # Add auto retriever
    auto_retriever = AutoRetriever(
            url_and_api_key=("Your Milvus URI","Your Milvus Token"),
            storage_type=StorageType.MILVUS,
            embedding_model=embedding_instance)

    retrieved_info = auto_retriever.run_vector_retriever(
        query=query,
        contents=[
            "local_data/camel paper.pdf",  # example local path
            "https://www.camel-ai.org/",  # example remote url
        ],
        # vector_storage_local_path="storage_default_run",
        top_k=1,
        return_detailed_info=True,
    )

    # Pass the retrieved infomation to agent
    user_msg = BaseMessage.make_user_message(role_name="User", content=retrieved_info)
    agent = ChatAgent(assistant_sys_msg)

    # Get response
    assistant_response = agent.step(user_msg)
    return assistant_response.msg.content

print(single_agent("What is CAMEL-AI"))
```
```markdown
>>> CAMEL-AI is an open-source community dedicated to the study of autonomous and communicative agents. It provides, implements, and supports various types of agents, tasks, prompts, models, datasets, and simulated environments to facilitate research in this field.
```

## 4. Role-playing with Auto RAG
In this section we will show how to combine the `AutoRetriever` with `RolePlaying` by applying `Function Calling`.

First, we need to set a retriever function with well-written docstring for LLM to understand what this function is used for, the main code is the same with the Auto RAG section.
```python
from typing import List
from camel.toolkits import FunctionTool
from camel.retrievers import AutoRetriever
from camel.types import StorageType

def local_retriever(query: str) -> str:
    r"""Performs an auto local retriever for information. Given a query,
    this function will retrieve the information from the local vector storage,
    and return the retrieved information back. It is useful for information
    retrieve.

    Args:
        query (string): Question you want to be answered.

    Returns:
        str: Aggregated information retrieved in response to the query.

    Example:
        local_retriever(query = "what is camel?")
    """
    auto_retriever = AutoRetriever(
            url_and_api_key=("Your Milvus URI","Your Milvus Token"),
            storage_type=StorageType.MILVUS,
            embedding_model=embedding_instance)

    retrieved_info = auto_retriever.run_vector_retriever(
        query=query,
        contents=[
            "local_data/camel paper.pdf",  # example local path
        ],
        top_k=1
    )
    return retrieved_info

# add the function to FunctionTool list
RETRIEVER_FUNCS: List[FunctionTool] = [
    FunctionTool(func)
    for func in [
        local_retriever,
    ]
]
```
Run the role-playing with defined retriever function:
```python
from camel.utils import role_playing_with_function
from camel.toolkits import MATH_FUNCS  # import another function from camel

role_playing_with_function(
    task_prompt=(
        "What is the main termination reasons for AI Society dataset, how many number of messages did camel decided to limit, what's the value plus 100?"
    ),
    tools=[*RETRIEVER_FUNCS, *MATH_FUNCS],
)
```
```markdown
>>> 
AI Assistant sys message:
BaseMessage(role_name='Searcher', role_type=<RoleType.ASSISTANT: 'assistant'>, meta_dict={'task': "What is the main termination reasons for AI Society dataset, how many number of messages did camel decided to limit, what's the value plus 100?", 'assistant_role': 'Searcher', 'user_role': 'Professor'}, content="===== RULES OF ASSISTANT =====\nNever forget you are a Searcher and I am a Professor. Never flip roles! Never instruct me!\nWe share a common interest in collaborating to successfully complete a task.\nYou must help me to complete the task.\nHere is the task: What is the main termination reasons for AI Society dataset, how many number of messages did camel decided to limit, what's the value plus 100?. Never forget our task!\nI must instruct you based on your expertise and my needs to complete the task.\n\nI must give you one instruction at a time.\nYou must write a specific solution that appropriately solves the requested instruction and explain your solutions.\nYou must decline my instruction honestly if you cannot perform the instruction due to physical, moral, legal reasons or your capability and explain the reasons.\nUnless I say the task is completed, you should always start with:\n\nSolution: <YOUR_SOLUTION>\n\n<YOUR_SOLUTION> should be very specific, include detailed explanations and provide preferable detailed implementations and examples and lists for task-solving.\nAlways end <YOUR_SOLUTION> with: Next request.")

AI User sys message:
BaseMessage(role_name='Professor', role_type=<RoleType.USER: 'user'>, meta_dict={'task': "What is the main termination reasons for AI Society dataset, how many number of messages did camel decided to limit, what's the value plus 100?", 'assistant_role': 'Searcher', 'user_role': 'Professor'}, content='===== RULES OF USER =====\nNever forget you are a Professor and I am a Searcher. Never flip roles! You will always instruct me.\nWe share a common interest in collaborating to successfully complete a task.\nI must help you to complete the task.\nHere is the task: What is the main termination reasons for AI Society dataset, how many number of messages did camel decided to limit, what\'s the value plus 100?. Never forget our task!\nYou must instruct me based on my expertise and your needs to solve the task ONLY in the following two ways:\n\n1. Instruct with a necessary input:\nInstruction: <YOUR_INSTRUCTION>\nInput: <YOUR_INPUT>\n\n2. Instruct without any input:\nInstruction: <YOUR_INSTRUCTION>\nInput: None\n\nThe "Instruction" describes a task or question. The paired "Input" provides further context or information for the requested "Instruction".\n\nYou must give me one instruction at a time.\nI must write a response that appropriately solves the requested instruction.\nI must decline your instruction honestly if I cannot perform the instruction due to physical, moral, legal reasons or my capability and explain the reasons.\nYou should instruct me not ask me questions.\nNow you must start to instruct me using the two ways described above.\nDo not add anything else other than your instruction and the optional corresponding input!\nKeep giving me instructions and necessary inputs until you think the task is completed.\nWhen the task is completed, you must only reply with a single word <CAMEL_TASK_DONE>.\nNever say <CAMEL_TASK_DONE> unless my responses have solved your task.')

Original task prompt:
What is the main termination reasons for AI Society dataset, how many number of messages did camel decided to limit, what's the value plus 100?

Specified task prompt:
None

Final task prompt:
What is the main termination reasons for AI Society dataset, how many number of messages did camel decided to limit, what's the value plus 100?

AI User:

Instruction: Provide the main termination reasons from the AI Society dataset.
Input: None


AI Assistant:

Function Execution: local_retriever
	Args: {'query': 'main termination reasons for AI Society dataset'}
	Result: Original Query:
{main termination reasons for AI Society dataset}
Retrieved Context:
Next we examine the conversation termination reasons for both AI Society and Code datasets. As can be seen in Figure 8, the main termination reasons for AI Society dataset is Assistant Instruct whereas for Code it is Token Limit. The latter is expected as the since responses that contain code tend to be long. It is also interesting to note that in both datasets, the termination due to Maximum Number of Messages is low indicating that the limit of 40 maximum messages is reasonable. Our decision

Solution: The main termination reason for the AI Society dataset is "Assistant Instruct." This indicates that the conversations in this dataset typically end when the assistant is instructed to terminate the conversation.

Next request.


AI User:

Instruction: Identify the number of messages that camel decided to limit.
Input: None


AI Assistant:

Function Execution: local_retriever
	Args: {'query': 'number of messages camel decided to limit'}
	Result: Original Query:
{number of messages camel decided to limit}
Retrieved Context:
to limit the number of messages to 40 is also cost-related. Even if we provide a set of termination conditions, we still want to put a safeguard to the maximum limit of the message. It is because after the task is completed the agents will provide short outputs like "thank you" and "welcome". If no safeguard is set and termination fails, the conversation will only end until it exceeds the token limit, which may end up with thousands of API calls and hundreds of USD dollars cost.

Solution: Camel decided to limit the number of messages to 40 as a safeguard to prevent excessive API calls and associated costs.

Next request.


AI User:

Instruction: Calculate the value of the message limit plus 100.
Input: None


AI Assistant:

Function Execution: add
	Args: {'a': 40, 'b': 100}
	Result: 140

Solution: The value of the message limit plus 100 is 140.

Next request.


AI User:

CAMEL_TASK_DONE


AI Assistant:

Solution: Understood, the task is completed.

If you have any more tasks or need further assistance, feel free to provide new instructions.
```
