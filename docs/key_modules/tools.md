# Tools

## 1. Concept
Tools serve as interfaces that allow LLMs and Agents to interact with the world. A tool is essentially a function that has a name, a description, input parameters, and an output type. In this section, we will introduce the tools currently supported by CAMEL and explain how to define your own tools and Toolkits.

**Tools:** Tools are akin to OpenAI Functions and can be easily converted to that format. In CAMEL, we offer a variety of commonly used tools that you can utilize directly. While built-in tools can be quite useful, it's highly likely that you'll need to define your own tools. This guide for detailed instructions on how to create custom tools.

**Toolkits:** Toolkits are collections of tools that are designed to work well together. 

## 2. Get Started

To enhance your agents' capabilities with CAMEL tools, start by installing our additional tools package:
```sh
pip install 'camel-ai[tools]'
```

In CAMEL, a tool is an `FunctionTool` that LLMs can call.


### 2.1 How to Define Your Own Tool?

Developers can create custom tools tailored to their agent’s specific needs:

```python
from camel.toolkits import FunctionTool

def add(a: int, b: int) -> int:
    r"""Adds two numbers.

    Args:
        a (int): The first number to be added.
        b (int): The second number to be added.

    Returns:
        integer: The sum of the two numbers.
    """
    return a + b
    
add_tool = FunctionTool(add)
```

```python
print(add_tool.get_function_name())
```

```markdown
>>> add
```

```python
print(add_tool.get_function_description())
```

```markdown
>>> Adds two numbers.
```

```python
print(add_tool.get_openai_function_schema())
```

```markdown
>>> 
{'name': 'add',
 'description': 'Adds two numbers.',
 'parameters': {'properties': {'a': {'type': 'integer',
    'description': 'The first number to be added.'},
   'b': {'type': 'integer', 'description': 'The second number to be added.'}},
  'required': ['a', 'b'],
  'type': 'object'}}
```

```python
print(add_tool.get_openai_tool_schema())
```

```markdown
>>> 
{'type': 'function',
 'function': {'name': 'add',
  'description': 'Adds two numbers.',
  'parameters': {'properties': {'a': {'type': 'integer',
     'description': 'The first number to be added.'},
    'b': {'type': 'integer', 'description': 'The second number to be added.'}},
   'required': ['a', 'b'],
   'type': 'object'}}}
```

### 2.2 Toolkits

Toolkits are collections of tools that are designed to be used together for specific tasks. All Toolkits expose a `get_tools` method which returns a list of tools. You can therefore do:

```python
from camel.toolkits import SearchToolkit

# Initialize a toolkit
toolkit = SearchToolkit()

# Get list of tools
tools = toolkit.get_tools()
```

To utilize specific tools from the toolkits, you can implement code like the following:

```python
from camel.toolkits import SearchToolkit

google_tool = FunctionTool(SearchToolkit().search_google)
wiki_tool = FunctionTool(SearchToolkit().search_wiki)
```

Here is a list of the available CAMEL tools and their descriptions:

| Toolkit | Description |
| ----- | ----- |
| CodeExecutionToolkit | A toolkit for code execution which can run code by "internal_python", "jupyter" or "docker”. | 
| GithubToolkit | A gitHub toolkit for interacting with GitHub repositories: retrieving open issues, retrieving specific issues, and creating pull requests. | 
| GoogleMapsToolkit  | A GoogleMaps toolkit for validating addresses, retrieving elevation, and fetching timezone information using the Google Maps API. | 
| MathToolkit | A simple math toolkit for basic mathematical operations such as addition, subtraction, and multiplication. |
| SearchToolkit | A search toolkit for for searching information on the web using search engines like Google, DuckDuckGo, Wikipedia and Wolfram Alpha. | 
| SlackToolkit | A Slack iteration toolkit for creating a new channel, joining an existing channel, leaving a channel. | 
| TwitterToolkit | A Twitter operation toolkit for creating a tweet, deleting a tweet, and getting the authenticated user's profile information. | 
| WeatherToolkit | A weather data toolkit which provides methods for fetching weather data for a given city using the OpenWeatherMap API. | 
| RetrievalToolkit | A information retrieval toolkit for retrieving information from a local vector storage system based on a specified query. | 


## 3. Conclusion

Tools are essential for extending the capabilities of CAMEL agents, empowering them to perform a wide range of tasks and collaborate efficiently.
