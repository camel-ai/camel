# OpenAI-Compatible Server for CAMEL ChatAgent

The `ChatAgent` class now includes a `to_openai_compatible_server()` method that creates a FastAPI application with OpenAI-compatible endpoints. This allows you to serve your CAMEL ChatAgent as a drop-in replacement for OpenAI's API.

## Features

- **OpenAI-Compatible API**: Supports the `/v1/chat/completions` endpoint
- **Streaming Support**: Supports both regular and streaming responses
- **Tool/Function Calling**: Supports OpenAI-style function calling
- **Easy Integration**: Drop-in replacement for OpenAI API clients

## Installation

Make sure you have the required dependencies:

```bash
pip install fastapi uvicorn
```

## Basic Usage

### Method 1: Direct Server Creation

```python
from camel.agents import ChatAgent
import uvicorn

# Create a ChatAgent
agent = ChatAgent(
    system_message="You are a helpful assistant.",
    model="gpt-4o-mini"  # or any supported model
)

# Create the FastAPI server
app = agent.to_openai_compatible_server()

# Serve the application
uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Method 2: Using the Example Script

```bash
# Run the example script
python example_openai_server.py

# Or use uvicorn command line
uvicorn example_openai_server:app --host 0.0.0.0 --port 8000
```

## Testing the Server

### Quick Test with Simple Client

Use the provided simple client example:

```bash
# Start the server (in one terminal)
python example_openai_server.py

# Test the server (in another terminal)
python simple_client_example.py
```

### Comprehensive Testing

For more thorough testing including function calling and error handling:

```bash
# Start the server (in one terminal)
python example_openai_server.py

# Run comprehensive tests (in another terminal)
python example_client.py
```

The comprehensive client test will check:
- ✅ Basic chat completion
- ✅ System message handling  
- ✅ Streaming responses
- ✅ Multi-turn conversations
- ✅ Function calling
- ✅ Error handling

### cURL Examples

You can also test the server using cURL commands:

**Basic Chat:**
```bash
curl -X POST "http://localhost:8000/v1/chat/completions" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer dummy-key" \
     -d '{
       "model": "camel-model",
       "messages": [
         {"role": "user", "content": "Hello! How are you?"}
       ]
     }'
```

**With System Message:**
```bash
curl -X POST "http://localhost:8000/v1/chat/completions" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer dummy-key" \
     -d '{
       "model": "camel-model",
       "messages": [
         {"role": "system", "content": "You are a helpful assistant."},
         {"role": "user", "content": "Explain quantum physics simply"}
       ]
     }'
```

**Streaming Response:**
```bash
curl -X POST "http://localhost:8000/v1/chat/completions" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer dummy-key" \
     -d '{
       "model": "camel-model",
       "messages": [
         {"role": "user", "content": "Tell me a story"}
       ],
       "stream": true
     }'
```

## Using the API

Once the server is running, you can use it just like the OpenAI API:

### With OpenAI Python Client

```python
import openai

client = openai.OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="dummy-key"  # Any string works
)

response = client.chat.completions.create(
    model="camel-model",
    messages=[
        {"role": "user", "content": "Hello, how are you?"}
    ]
)

print(response.choices[0].message.content)
```

### With cURL

```bash
curl -X POST "http://localhost:8000/v1/chat/completions" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer dummy-key" \
     -d '{
       "model": "camel-model",
       "messages": [
         {"role": "user", "content": "Hello, how are you?"}
       ]
     }'
```

### Streaming Responses

```python
response = client.chat.completions.create(
    model="camel-model",
    messages=[
        {"role": "user", "content": "Tell me a story"}
    ],
    stream=True
)

for chunk in response:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

## Tool/Function Calling

The server supports OpenAI-style function calling:

```python
# Define a function
functions = [
    {
        "name": "get_weather",
        "description": "Get the current weather",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "The city and state"
                }
            },
            "required": ["location"]
        }
    }
]

response = client.chat.completions.create(
    model="camel-model",
    messages=[
        {"role": "user", "content": "What's the weather like in New York?"}
    ],
    functions=functions
)

# Handle function calls
if response.choices[0].message.function_call:
    function_name = response.choices[0].message.function_call.name
    function_args = response.choices[0].message.function_call.arguments
    # Process the function call...
```

## Advanced Configuration

You can customize the ChatAgent before creating the server:

```python
from camel.agents import ChatAgent
from camel.toolkits import FunctionTool

# Create a custom tool
def my_custom_tool(query: str) -> str:
    """A custom tool for the agent."""
    return f"Processed: {query}"

# Create agent with custom configuration
agent = ChatAgent(
    system_message="You are a specialized assistant.",
    model="gpt-4o",
    tools=[my_custom_tool],
    temperature=0.8,
    max_tokens=1000
)

# Create and serve the API
app = agent.to_openai_compatible_server()
```

## Error Handling

The server includes proper error handling and returns appropriate HTTP status codes and error messages compatible with the OpenAI API format.

## Limitations

- The server currently supports the `/v1/chat/completions` endpoint
- Some advanced OpenAI features may not be fully supported
- Function calling is supported for external tools (tools that return requests rather than executing directly)

## Troubleshooting

### Import Errors

If you get import errors for FastAPI or uvicorn:

```bash
pip install fastapi uvicorn
```

### Port Already in Use

If port 8000 is already in use, specify a different port:

```python
uvicorn.run(app, host="0.0.0.0", port=8080)
```

### Model Configuration

Make sure your ChatAgent is properly configured with a valid model before creating the server. The model should be available and properly authenticated if using external APIs. 