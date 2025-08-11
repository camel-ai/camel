from openai import OpenAI
client = OpenAI(api_key="sk-4bd18871dc144aed9aa6db6ec647520e", base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")

response = client.beta.chat.completions.parse(
  model="qwen-plus",
  messages=[
    {
      "role": "system",
      "content": [
        {
          "type": "text",
          "text": "You are a helpful assistant"
        }
      ]
    },
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "search what is the capital of France, what is the capital of Japan, what is the capital of China"
        }
      ]
    },
    {
      "role": "assistant",
      "content": [],
      "tool_calls": [
        {
          "type": "function",
          "id": "call_61dbpvFk37MyP95ecDWxE4hI",
          "function": {
            "name": "search_wiki",
            "arguments": "{\"query\":\"capital of France\",\"language\":\"en\"}"
          }
        },
        {
          "type": "function",
          "id": "call_DUQDLzrlCmWTX5vDRahyuhlB",
          "function": {
            "name": "search_wiki",
            "arguments": "{\"query\":\"capital of Japan\",\"language\":\"en\"}"
          }
        },
        {
          "type": "function",
          "id": "call_HnibWkxbBrTjJXo2JG8JsWLs",
          "function": {
            "name": "search_wiki",
            "arguments": "{\"query\":\"capital of China\",\"language\":\"en\"}"
          }
        }
      ]
    },
    {
      "role": "tool",
      "content": [
        {
          "type": "text",
          "text": "paris"
        }
      ],
      "tool_call_id": "call_61dbpvFk37MyP95ecDWxE4hI"
    },
    {
      "role": "tool",
      "content": [
        {
          "type": "text",
          "text": "tokyo"
        }
      ],
      "tool_call_id": "call_DUQDLzrlCmWTX5vDRahyuhlB"
    },
    {
      "role": "tool",
      "content": [
        {
          "type": "text",
          "text": "beijing"
        }
      ],
      "tool_call_id": "call_HnibWkxbBrTjJXo2JG8JsWLs"
    },
    {
      "role": "assistant",
      "content": [
        {
          "type": "text",
          "text": "The capitals are as follows:\n- The capital of France is Paris.\n- The capital of Japan is Tokyo.\n- The capital of China is Beijing."
        }
      ]
    }
  ],
  response_format={
    "type": "text"
  },
  tools=[
    {
      "type": "function",
      "function": {
        "name": "search_wiki",
        "description": "Search for information from Wikipedia based on a query",
        "parameters": {
          "type": "object",
          "properties": {
            "query": {
              "type": "string",
              "description": "The search term or question to look up on Wikipedia"
            },
            "language": {
              "type": "string",
              "description": "ISO 639-1 two-letter code for the language of Wikipedia, e.g., 'en' for English",
              "default": "en"
            }
          },
          "required": [
            "query",
            "language"
          ],
          "additionalProperties": False
        },
        "strict": True
      }
    }
  ],
  temperature=1,
  max_completion_tokens=2048,
  top_p=1,
  presence_penalty=0
)


print(response)